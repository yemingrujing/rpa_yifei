import time
import threading
import json
from typing import List, Dict, Any, Optional, Callable
from enum import Enum
import pyautogui
import pygetwindow as gw


class RecordingStatus(Enum):
    IDLE = "idle"
    RECORDING = "recording"
    PAUSED = "paused"
    STOPPED = "stopped"


class OperationType(Enum):
    MOUSE_MOVE = "mouse_move"
    MOUSE_CLICK = "mouse_click"
    MOUSE_RIGHT_CLICK = "mouse_right_click"
    MOUSE_DOUBLE_CLICK = "mouse_double_click"
    MOUSE_DRAG = "mouse_drag"
    KEYBOARD_TYPE = "keyboard_type"
    KEYBOARD_PRESS = "keyboard_press"
    KEYBOARD_HOTKEY = "keyboard_hotkey"
    WINDOW_ACTIVATE = "window_activate"
    WINDOW_WAIT = "window_wait"
    SCREENSHOT = "screenshot"
    DELAY = "delay"


class RecordedOperation:
    def __init__(self, operation_type: OperationType, timestamp: float, 
                 position: Optional[tuple] = None, 
                 data: Optional[Dict[str, Any]] = None):
        self.type = operation_type
        self.timestamp = timestamp
        self.position = position
        self.data = data or {}
        self.window_title = self._get_active_window_title()

    def _get_active_window_title(self) -> str:
        try:
            window = gw.getActiveWindow()
            return window.title if window else ""
        except:
            return ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': self.type.value,
            'timestamp': self.timestamp,
            'position': self.position,
            'window_title': self.window_title,
            'data': self.data
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RecordedOperation':
        op = cls(
            operation_type=OperationType(data['type']),
            timestamp=data['timestamp'],
            position=data.get('position'),
            data=data.get('data', {})
        )
        op.window_title = data.get('window_title', '')
        return op


class OperationRecorder:
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.status = RecordingStatus.IDLE
        self.operations: List[RecordedOperation] = []
        self.start_time: Optional[float] = None
        self.last_position: Optional[tuple] = None
        self.last_action_time: Optional[float] = None
        self.mouse_listener = None
        self.keyboard_listener = None
        self.capture_screenshots = self.config.get('capture_screenshots', True)
        self.record_delay = self.config.get('record_delay', 0.5)
        self.listeners: Dict[str, List[Callable]] = {
            'operation_recorded': [],
            'recording_started': [],
            'recording_stopped': [],
            'recording_paused': [],
            'recording_resumed': []
        }

    def start_recording(self):
        if self.status == RecordingStatus.RECORDING:
            return
        
        self.operations.clear()
        self.start_time = time.time()
        self.status = RecordingStatus.RECORDING
        self._start_system_listeners()
        self._emit('recording_started')

    def stop_recording(self) -> List[Dict[str, Any]]:
        if self.status == RecordingStatus.IDLE:
            return []
        
        self._stop_system_listeners()
        self.status = RecordingStatus.STOPPED
        self._emit('recording_stopped')
        
        return [op.to_dict() for op in self.operations]

    def pause_recording(self):
        if self.status == RecordingStatus.RECORDING:
            self.status = RecordingStatus.PAUSED
            self._emit('recording_paused')

    def resume_recording(self):
        if self.status == RecordingStatus.PAUSED:
            self.status = RecordingStatus.RECORDING
            self._emit('recording_resumed')

    def get_operations(self) -> List[Dict[str, Any]]:
        return [op.to_dict() for op in self.operations]

    def clear_operations(self):
        self.operations.clear()

    def add_operation(self, operation: RecordedOperation):
        if self.status == RecordingStatus.RECORDING:
            self.operations.append(operation)
            self._emit('operation_recorded', operation)

    def _start_system_listeners(self):
        pass

    def _stop_system_listeners(self):
        pass

    def record_mouse_move(self, x: int, y: int):
        if self.status != RecordingStatus.RECORDING:
            return
        
        current_time = time.time()
        
        if self.last_position:
            distance = ((x - self.last_position[0])**2 + (y - self.last_position[1])**2)**0.5
            if distance < 10:
                return
        
        if self.last_action_time and (current_time - self.last_action_time) < self.record_delay:
            return
        
        op = RecordedOperation(
            operation_type=OperationType.MOUSE_MOVE,
            timestamp=current_time,
            position=(x, y)
        )
        
        self.add_operation(op)
        self.last_position = (x, y)
        self.last_action_time = current_time

    def record_click(self, x: int, y: int, button: str = 'left'):
        if self.status != RecordingStatus.RECORDING:
            return
        
        current_time = time.time()
        
        if button == 'left':
            op = RecordedOperation(
                operation_type=OperationType.MOUSE_CLICK,
                timestamp=current_time,
                position=(x, y),
                data={'button': button}
            )
        elif button == 'right':
            op = RecordedOperation(
                operation_type=OperationType.MOUSE_RIGHT_CLICK,
                timestamp=current_time,
                position=(x, y),
                data={'button': button}
            )
        else:
            return
        
        self.add_operation(op)
        self.last_action_time = current_time

    def record_double_click(self, x: int, y: int):
        if self.status != RecordingStatus.RECORDING:
            return
        
        current_time = time.time()
        op = RecordedOperation(
            operation_type=OperationType.MOUSE_DOUBLE_CLICK,
            timestamp=current_time,
            position=(x, y)
        )
        
        self.add_operation(op)
        self.last_action_time = current_time

    def record_drag(self, start_pos: tuple, end_pos: tuple):
        if self.status != RecordingStatus.RECORDING:
            return
        
        current_time = time.time()
        op = RecordedOperation(
            operation_type=OperationType.MOUSE_DRAG,
            timestamp=current_time,
            position=end_pos,
            data={'start_pos': start_pos, 'end_pos': end_pos}
        )
        
        self.add_operation(op)
        self.last_action_time = current_time

    def record_keyboard_type(self, text: str):
        if self.status != RecordingStatus.RECORDING:
            return
        
        current_time = time.time()
        op = RecordedOperation(
            operation_type=OperationType.KEYBOARD_TYPE,
            timestamp=current_time,
            data={'text': text}
        )
        
        self.add_operation(op)
        self.last_action_time = current_time

    def record_keyboard_press(self, key: str):
        if self.status != RecordingStatus.RECORDING:
            return
        
        current_time = time.time()
        op = RecordedOperation(
            operation_type=OperationType.KEYBOARD_PRESS,
            timestamp=current_time,
            data={'key': key}
        )
        
        self.add_operation(op)
        self.last_action_time = current_time

    def record_hotkey(self, keys: List[str]):
        if self.status != RecordingStatus.RECORDING:
            return
        
        current_time = time.time()
        op = RecordedOperation(
            operation_type=OperationType.KEYBOARD_HOTKEY,
            timestamp=current_time,
            data={'keys': keys}
        )
        
        self.add_operation(op)
        self.last_action_time = current_time

    def record_delay(self, seconds: float):
        if self.status != RecordingStatus.RECORDING:
            return
        
        op = RecordedOperation(
            operation_type=OperationType.DELAY,
            timestamp=time.time(),
            data={'seconds': seconds}
        )
        
        self.add_operation(op)

    def record_window_activate(self, title: str):
        if self.status != RecordingStatus.RECORDING:
            return
        
        op = RecordedOperation(
            operation_type=OperationType.WINDOW_ACTIVATE,
            timestamp=time.time(),
            data={'title': title}
        )
        
        self.add_operation(op)

    def save_recording(self, file_path: str):
        with open(file_path, 'w') as f:
            json.dump(self.get_operations(), f, indent=2)

    def load_recording(self, file_path: str):
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        self.operations = [RecordedOperation.from_dict(op) for op in data]

    def generate_script(self, output_format: str = 'python') -> str:
        script_lines = []
        
        for op in self.operations:
            if op.type == OperationType.MOUSE_CLICK:
                x, y = op.position
                script_lines.append(f"gui.click({x}, {y})")
            
            elif op.type == OperationType.MOUSE_RIGHT_CLICK:
                x, y = op.position
                script_lines.append(f"gui.right_click({x}, {y})")
            
            elif op.type == OperationType.MOUSE_DOUBLE_CLICK:
                x, y = op.position
                script_lines.append(f"gui.double_click({x}, {y})")
            
            elif op.type == OperationType.MOUSE_DRAG:
                x, y = op.position
                start = op.data.get('start_pos', (0, 0))
                script_lines.append(f"gui.drag_to({x}, {y})")
            
            elif op.type == OperationType.KEYBOARD_TYPE:
                text = op.data.get('text', '').replace('\\n', '\\\\n')
                script_lines.append(f'gui.type_text("{text}")')
            
            elif op.type == OperationType.KEYBOARD_PRESS:
                key = op.data.get('key', '')
                script_lines.append(f'gui.press_key("{key}")')
            
            elif op.type == OperationType.KEYBOARD_HOTKEY:
                keys = op.data.get('keys', [])
                script_lines.append(f'gui.hotkey({", ".join(f"\"{k}\"" for k in keys)})')
            
            elif op.type == OperationType.WINDOW_ACTIVATE:
                title = op.data.get('title', '')
                script_lines.append(f'gui.activate_window("{title}")')
            
            elif op.type == OperationType.DELAY:
                seconds = op.data.get('seconds', 1)
                script_lines.append(f"time.sleep({seconds})")
        
        return '\n'.join(script_lines)

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

    def get_status(self) -> RecordingStatus:
        return self.status

    def get_operation_count(self) -> int:
        return len(self.operations)
