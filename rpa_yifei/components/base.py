from typing import Any, Dict, Optional, Callable
from enum import Enum
import json
import time


class ComponentType(Enum):
    INPUT = "input"
    OUTPUT = "output"
    MOUSE = "mouse"
    KEYBOARD = "keyboard"
    WAIT = "wait"
    CONDITION = "condition"
    LOOP = "loop"
    EXCEL = "excel"
    EMAIL = "email"
    API = "api"
    DATABASE = "database"
    FILE = "file"
    WEB = "web"
    CUSTOM = "custom"


class BaseComponent:
    def __init__(self, component_id: str, component_type: ComponentType, name: str = ""):
        self.id = component_id
        self.type = component_type
        self.name = name or self._get_default_name()
        self.properties: Dict[str, Any] = {}
        self.enabled = True
        self.description = ""
        self.category = ""
        self.icon = ""
        self.timeout = 30
        self.retry_count = 0
        self.retry_delay = 1
        self.on_error: Optional[Callable] = None
        self.input_mapping: Dict[str, str] = {}
        self.output_mapping: Dict[str, str] = {}

    def _get_default_name(self) -> str:
        return f"{self.type.value}_{self.id}"

    def set_property(self, key: str, value: Any):
        self.properties[key] = value

    def get_property(self, key: str, default: Any = None) -> Any:
        return self.properties.get(key, default)

    def set_properties(self, properties: Dict[str, Any]):
        self.properties.update(properties)

    def validate(self) -> tuple[bool, Optional[str]]:
        return True, None

    def execute(self, context: Any) -> Any:
        raise NotImplementedError("Component must implement execute method")

    def _retry_execute(self, context: Any) -> Any:
        last_error = None
        for attempt in range(self.retry_count + 1):
            try:
                return self.execute(context)
            except Exception as e:
                last_error = e
                if attempt < self.retry_count:
                    time.sleep(self.retry_delay)
        if self.on_error:
            self.on_error(last_error)
        raise last_error

    def get_schema(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'type': self.type.value,
            'name': self.name,
            'properties': self.properties,
            'enabled': self.enabled,
            'description': self.description,
            'category': self.category,
            'timeout': self.timeout,
            'retry_count': self.retry_count,
            'input_mapping': self.input_mapping,
            'output_mapping': self.output_mapping
        }

    def load_from_schema(self, schema: Dict[str, Any]):
        self.id = schema.get('id', self.id)
        self.name = schema.get('name', self.name)
        self.properties = schema.get('properties', {})
        self.enabled = schema.get('enabled', True)
        self.description = schema.get('description', '')
        self.category = schema.get('category', '')
        self.timeout = schema.get('timeout', 30)
        self.retry_count = schema.get('retry_count', 0)
        self.input_mapping = schema.get('input_mapping', {})
        self.output_mapping = schema.get('output_mapping', {})

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'type': self.type.value,
            'name': self.name,
            'properties': self.properties,
            'enabled': self.enabled,
            'description': self.description,
            'category': self.category,
            'timeout': self.timeout,
            'retry_count': self.retry_count,
            'retry_delay': self.retry_delay,
            'input_mapping': self.input_mapping,
            'output_mapping': self.output_mapping
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseComponent':
        component_type = ComponentType(data.get('type', 'custom'))
        component = cls(data.get('id', ''), component_type, data.get('name', ''))
        component.load_from_schema(data)
        return component

    def __repr__(self):
        return f"<{self.__class__.__name__} id={self.id} name={self.name} type={self.type.value}>"


class MouseComponent(BaseComponent):
    def __init__(self, component_id: str, action: str = "click"):
        super().__init__(component_id, ComponentType.MOUSE)
        self.action = action

    def execute(self, context: Any) -> Any:
        gui = context.get('gui_automation')
        if not gui:
            raise ValueError("GUI automation not available in context")
        
        x = self.get_property('x', 0)
        y = self.get_property('y', 0)
        
        if self.action == "click":
            gui.click(x, y)
        elif self.action == "right_click":
            gui.right_click(x, y)
        elif self.action == "double_click":
            gui.double_click(x, y)
        
        return {'x': x, 'y': y, 'action': self.action}


class KeyboardComponent(BaseComponent):
    def __init__(self, component_id: str, action: str = "type"):
        super().__init__(component_id, ComponentType.KEYBOARD)
        self.action = action

    def execute(self, context: Any) -> Any:
        gui = context.get('gui_automation')
        if not gui:
            raise ValueError("GUI automation not available in context")
        
        if self.action == "type":
            text = self.get_property('text', '')
            gui.type_text(text)
        elif self.action == "press":
            key = self.get_property('key', '')
            gui.press_key(key)
        elif self.action == "hotkey":
            keys = self.get_property('keys', [])
            gui.hotkey(*keys)
        
        return {'action': self.action}


class WaitComponent(BaseComponent):
    def __init__(self, component_id: str, wait_type: str = "seconds"):
        super().__init__(component_id, ComponentType.WAIT)
        self.wait_type = wait_type

    def execute(self, context: Any) -> Any:
        if self.wait_type == "seconds":
            seconds = self.get_property('seconds', 1)
            time.sleep(seconds)
            return {'waited': seconds}
        elif self.wait_type == "image":
            locator = context.get('element_locator')
            image_path = self.get_property('image_path', '')
            timeout = self.get_property('timeout', 30)
            found = locator.wait_for_image(image_path, timeout=timeout)
            return {'image_found': found}
        elif self.wait_type == "window":
            gui = context.get('gui_automation')
            title = self.get_property('window_title', '')
            timeout = self.get_property('timeout', 30)
            found = gui.wait_for_window(title, timeout=timeout)
            return {'window_found': found}
        
        return {}
