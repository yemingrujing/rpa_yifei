import json
import time
import threading
from typing import Any, Dict, List, Optional, Callable
from enum import Enum
import traceback


class NodeType(Enum):
    START = "start"
    END = "end"
    ACTION = "action"
    CONDITION = "condition"
    LOOP = "loop"
    TRY = "try"
    CATCH = "catch"
    FINALLY = "finally"
    FUNCTION = "function"
    SUBFLOW = "subflow"


class FlowStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


class FlowNode:
    def __init__(self, node_id: str, node_type: NodeType, name: str = "", data: Optional[Dict] = None):
        self.id = node_id
        self.type = node_type
        self.name = name or node_type.value
        self.data = data or {}
        self.next_nodes: List[str] = []
        self.branch_true: Optional[str] = None
        self.branch_false: Optional[str] = None
        self.condition: Optional[Callable] = None
        self.action: Optional[Callable] = None


class FlowContext:
    def __init__(self):
        self.variables: Dict[str, Any] = {}
        self.loop_count = 0
        self.max_loop = 1000
        self.current_node: Optional[str] = None
        self.error: Optional[Exception] = None
        self.metadata: Dict[str, Any] = {}

    def set_variable(self, name: str, value: Any):
        self.variables[name] = value

    def get_variable(self, name: str, default: Any = None) -> Any:
        return self.variables.get(name, default)

    def clear_error(self):
        self.error = None


class FlowEngine:
    def __init__(self):
        self.nodes: Dict[str, FlowNode] = {}
        self.context = FlowContext()
        self.status = FlowStatus.IDLE
        self.start_node: Optional[str] = None
        self.listeners: Dict[str, List[Callable]] = {
            'node_start': [],
            'node_complete': [],
            'node_error': [],
            'flow_start': [],
            'flow_complete': [],
            'flow_error': [],
            'variable_change': []
        }
        self._stop_flag = False
        self._pause_flag = False
        self._lock = threading.Lock()

    def add_node(self, node: FlowNode):
        self.nodes[node.id] = node

    def remove_node(self, node_id: str):
        if node_id in self.nodes:
            del self.nodes[node_id]

    def connect_nodes(self, from_node_id: str, to_node_id: str):
        if from_node_id in self.nodes and to_node_id in self.nodes:
            self.nodes[from_node_id].next_nodes.append(to_node_id)

    def set_condition_branch(self, node_id: str, true_node_id: str, false_node_id: str):
        if node_id in self.nodes:
            node = self.nodes[node_id]
            node.branch_true = true_node_id
            node.branch_false = false_node_id

    def set_condition(self, node_id: str, condition: Callable[[FlowContext], bool]):
        if node_id in self.nodes:
            self.nodes[node_id].condition = condition

    def set_action(self, node_id: str, action: Callable[[FlowContext], Any]):
        if node_id in self.nodes:
            self.nodes[node_id].action = action

    def add_listener(self, event: str, callback: Callable):
        if event in self.listeners:
            self.listeners[event].append(callback)

    def remove_listener(self, event: str, callback: Callable):
        if event in self.listeners and callback in self.listeners[event]:
            self.listeners[event].remove(callback)

    def _emit(self, event: str, *args, **kwargs):
        if event in self.listeners:
            for callback in self.listeners[event]:
                try:
                    callback(*args, **kwargs)
                except Exception as e:
                    print(f"Listener error: {e}")

    def execute_action(self, node: FlowNode) -> Any:
        self.context.current_node = node.id
        self._emit('node_start', node)

        if node.action:
            try:
                result = node.action(self.context)
                self._emit('node_complete', node, result)
                return result
            except Exception as e:
                self.context.error = e
                self._emit('node_error', node, e)
                raise
        return None

    def evaluate_condition(self, node: FlowNode) -> bool:
        if node.condition:
            try:
                return node.condition(self.context)
            except Exception as e:
                self.context.error = e
                return False
        return True

    def run(self, input_data: Optional[Dict] = None):
        with self._lock:
            if self.status == FlowStatus.RUNNING:
                return
            
            self.status = FlowStatus.RUNNING
            self.context = FlowContext()
            self._stop_flag = False
            self._pause_flag = False
            
            if input_data:
                for key, value in input_data.items():
                    self.context.set_variable(key, value)

        self._emit('flow_start', self.context)

        try:
            self._execute_flow()
            self.status = FlowStatus.COMPLETED
            self._emit('flow_complete', self.context)
        except StopIteration:
            self.status = FlowStatus.STOPPED
        except Exception as e:
            self.status = FlowStatus.FAILED
            self._emit('flow_error', e, self.context)
            raise

    def _execute_flow(self):
        if not self.start_node:
            return

        current_node_id = self.start_node
        visited = set()

        while current_node_id and not self._stop_flag:
            if self._pause_flag:
                time.sleep(0.1)
                continue

            if current_node_id in visited and self.nodes[current_node_id].type == NodeType.LOOP:
                break
            visited.add(current_node_id)

            if current_node_id not in self.nodes:
                break

            node = self.nodes[current_node_id]

            if node.type == NodeType.END:
                break

            elif node.type == NodeType.ACTION:
                self.execute_action(node)
                current_node_id = self._get_next_node(node)

            elif node.type == NodeType.CONDITION:
                condition_result = self.evaluate_condition(node)
                if condition_result and node.branch_true:
                    current_node_id = node.branch_true
                elif not condition_result and node.branch_false:
                    current_node_id = node.branch_false
                else:
                    current_node_id = self._get_next_node(node)

            elif node.type == NodeType.LOOP:
                self.context.loop_count += 1
                if self.context.loop_count >= self.context.max_loop:
                    raise Exception("Maximum loop count exceeded")
                
                if node.action:
                    should_continue = node.action(self.context)
                    if should_continue:
                        current_node_id = node.branch_true or self._get_next_node(node)
                    else:
                        current_node_id = node.branch_false or current_node_id
                else:
                    current_node_id = node.branch_true or self._get_next_node(node)

            elif node.type == NodeType.TRY:
                try:
                    current_node_id = self._get_next_node(node)
                except Exception as e:
                    self.context.error = e
                    catch_node_id = node.branch_false
                    if catch_node_id and catch_node_id in self.nodes:
                        current_node_id = catch_node_id
                    else:
                        raise

            elif node.type == NodeType.CATCH:
                if self.context.error:
                    if node.action:
                        node.action(self.context)
                    self.context.clear_error()
                current_node_id = self._get_next_node(node)

            elif node.type == NodeType.FUNCTION:
                self.execute_action(node)
                current_node_id = self._get_next_node(node)

            else:
                current_node_id = self._get_next_node(node)

    def _get_next_node(self, node: FlowNode) -> Optional[str]:
        if node.next_nodes:
            return node.next_nodes[0]
        return None

    def pause(self):
        self._pause_flag = True
        self.status = FlowStatus.PAUSED

    def resume(self):
        self._pause_flag = False
        self.status = FlowStatus.RUNNING

    def stop(self):
        self._stop_flag = True
        self.status = FlowStatus.STOPPED

    def reset(self):
        self.status = FlowStatus.IDLE
        self.context = FlowContext()
        self._stop_flag = False
        self._pause_flag = False

    def validate_flow(self) -> List[str]:
        errors = []
        
        if not self.start_node:
            errors.append("No start node defined")

        for node_id, node in self.nodes.items():
            if node.type != NodeType.END and not node.next_nodes and node.type != NodeType.CONDITION:
                if not any(n.type == NodeType.CONDITION for n in self.nodes.values()):
                    pass

        return errors

    def export_flow(self, file_path: str):
        flow_data = {
            'start_node': self.start_node,
            'nodes': []
        }
        
        for node_id, node in self.nodes.items():
            node_data = {
                'id': node.id,
                'type': node.type.value,
                'name': node.name,
                'data': node.data,
                'next_nodes': node.next_nodes,
                'branch_true': node.branch_true,
                'branch_false': node.branch_false
            }
            flow_data['nodes'].append(node_data)
        
        with open(file_path, 'w') as f:
            json.dump(flow_data, f, indent=2)

    def import_flow(self, file_path: str):
        with open(file_path, 'r') as f:
            flow_data = json.load(f)
        
        self.nodes.clear()
        self.start_node = flow_data.get('start_node')
        
        for node_data in flow_data.get('nodes', []):
            node = FlowNode(
                node_id=node_data['id'],
                node_type=NodeType(node_data['type']),
                name=node_data['name'],
                data=node_data.get('data', {})
            )
            node.next_nodes = node_data.get('next_nodes', [])
            node.branch_true = node_data.get('branch_true')
            node.branch_false = node_data.get('branch_false')
            self.add_node(node)

    def get_execution_log(self) -> List[Dict]:
        return []

    def get_status(self) -> FlowStatus:
        return self.status
