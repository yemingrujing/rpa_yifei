from typing import Any, Dict, Optional, List
import requests
from .base import BaseComponent, ComponentType


class APIComponent(BaseComponent):
    def __init__(self, component_id: str, action: str = "request"):
        super().__init__(component_id, ComponentType.API, f"API_{action}")
        self.action = action
        self.category = "集成"
        self.description = f"执行API {action}操作"
        self.session = None

    def validate(self) -> tuple[bool, Optional[str]]:
        if self.action == "request":
            if not self.get_property('url'):
                return False, "url is required"
        return True, None

    def execute(self, context: Any) -> Any:
        if self.action == "request":
            return self._make_request(context)
        elif self.action == "init_session":
            return self._init_session(context)
        elif self.action == "close_session":
            return self._close_session(context)
        
        return {}

    def _resolve_variable(self, value: Any, context: Any) -> Any:
        if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
            var_name = value[2:-1]
            return context.get('variables', {}).get(var_name, value)
        return value

    def _make_request(self, context: Any) -> Dict[str, Any]:
        url = self._resolve_variable(self.get_property('url'), context)
        method = self.get_property('method', 'GET').upper()
        
        headers = self.get_property('headers', {})
        for key, value in headers.items():
            headers[key] = self._resolve_variable(value, context)
        
        params = self.get_property('params', {})
        for key, value in params.items():
            params[key] = self._resolve_variable(value, context)
        
        data = self.get_property('data')
        if data:
            data = self._resolve_variable(data, context)
        
        json_data = self.get_property('json')
        if json_data:
            json_data = self._resolve_variable(json_data, context)
        
        timeout = self.get_property('timeout', 30)
        verify_ssl = self.get_property('verify_ssl', True)
        
        auth = None
        auth_type = self.get_property('auth_type')
        if auth_type == 'basic':
            username = self._resolve_variable(self.get_property('username'), context)
            password = self._resolve_variable(self.get_property('password'), context)
            auth = (username, password)
        
        try:
            if self.session:
                response = self.session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    data=data,
                    json=json_data,
                    timeout=timeout,
                    verify=verify_ssl,
                    auth=auth
                )
            else:
                response = requests.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    data=data,
                    json=json_data,
                    timeout=timeout,
                    verify=verify_ssl,
                    auth=auth
                )
            
            status_code = response.status_code
            
            try:
                response_data = response.json()
            except:
                response_data = response.text
            
            output_var = self.get_property('output_variable', 'api_response')
            context['variables'][output_var] = {
                'status_code': status_code,
                'headers': dict(response.headers),
                'data': response_data
            }
            
            context['variables'][f'{output_var}_status'] = status_code
            context['variables'][f'{output_var}_data'] = response_data
            
            return {
                'success': 200 <= status_code < 300,
                'status_code': status_code,
                'data': response_data
            }
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'error': 'Request timeout'
            }
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _init_session(self, context: Any) -> Dict[str, Any]:
        self.session = requests.Session()
        return {
            'success': True,
            'message': 'Session initialized'
        }

    def _close_session(self, context: Any) -> Dict[str, Any]:
        if self.session:
            self.session.close()
            self.session = None
        return {
            'success': True,
            'message': 'Session closed'
        }


class APIRequestComponent(APIComponent):
    def __init__(self, component_id: str):
        super().__init__(component_id, "request")
        self.category = "集成"
        self.description = "发送HTTP请求"


class APIGetComponent(APIComponent):
    def __init__(self, component_id: str):
        super().__init__(component_id, "request")
        self.set_property('method', 'GET')
        self.category = "集成"
        self.description = "发送GET请求"


class APIPostComponent(APIComponent):
    def __init__(self, component_id: str):
        super().__init__(component_id, "request")
        self.set_property('method', 'POST')
        self.category = "集成"
        self.description = "发送POST请求"
