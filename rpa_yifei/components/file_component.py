from typing import Any, Dict, Optional, List
import os
import shutil
import glob
from .base import BaseComponent, ComponentType


class FileComponent(BaseComponent):
    def __init__(self, component_id: str, action: str = "read"):
        super().__init__(component_id, ComponentType.FILE, f"File_{action}")
        self.action = action
        self.category = "文件操作"
        self.description = f"执行文件{action}操作"

    def validate(self) -> tuple[bool, Optional[str]]:
        if self.action in ["read", "write", "copy", "move", "delete"]:
            if not self.get_property('path'):
                return False, "path is required"
        return True, None

    def execute(self, context: Any) -> Any:
        if self.action == "read":
            return self._read_file(context)
        elif self.action == "write":
            return self._write_file(context)
        elif self.action == "copy":
            return self._copy_file(context)
        elif self.action == "move":
            return self._move_file(context)
        elif self.action == "delete":
            return self._delete_file(context)
        elif self.action == "exists":
            return self._check_exists(context)
        elif self.action == "list":
            return self._list_files(context)
        elif self.action == "create_dir":
            return self._create_directory(context)
        elif self.action == "get_info":
            return self._get_file_info(context)
        
        return {}

    def _resolve_variable(self, value: Any, context: Any) -> Any:
        if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
            var_name = value[2:-1]
            return context.get('variables', {}).get(var_name, value)
        return value

    def _read_file(self, context: Any) -> Dict[str, Any]:
        path = self._resolve_variable(self.get_property('path'), context)
        encoding = self.get_property('encoding', 'utf-8')
        
        try:
            with open(path, 'r', encoding=encoding) as f:
                content = f.read()
            
            output_var = self.get_property('output_variable', 'file_content')
            context['variables'][output_var] = content
            
            return {
                'success': True,
                'content': content,
                'size': len(content)
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _write_file(self, context: Any) -> Dict[str, Any]:
        path = self._resolve_variable(self.get_property('path'), context)
        content = self._resolve_variable(self.get_property('content'), context)
        encoding = self.get_property('encoding', 'utf-8')
        mode = self.get_property('mode', 'w')
        
        try:
            directory = os.path.dirname(path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)
            
            with open(path, mode, encoding=encoding) as f:
                f.write(content)
            
            return {
                'success': True,
                'path': path,
                'size': len(content)
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _copy_file(self, context: Any) -> Dict[str, Any]:
        source = self._resolve_variable(self.get_property('path'), context)
        destination = self._resolve_variable(self.get_property('destination'), context)
        
        try:
            if os.path.isdir(source):
                shutil.copytree(source, destination)
            else:
                directory = os.path.dirname(destination)
                if directory and not os.path.exists(directory):
                    os.makedirs(directory)
                shutil.copy2(source, destination)
            
            return {
                'success': True,
                'source': source,
                'destination': destination
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _move_file(self, context: Any) -> Dict[str, Any]:
        source = self._resolve_variable(self.get_property('path'), context)
        destination = self._resolve_variable(self.get_property('destination'), context)
        
        try:
            directory = os.path.dirname(destination)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)
            
            shutil.move(source, destination)
            
            return {
                'success': True,
                'source': source,
                'destination': destination
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _delete_file(self, context: Any) -> Dict[str, Any]:
        path = self._resolve_variable(self.get_property('path'), context)
        
        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
            
            return {
                'success': True,
                'path': path
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _check_exists(self, context: Any) -> Dict[str, Any]:
        path = self._resolve_variable(self.get_property('path'), context)
        
        exists = os.path.exists(path)
        
        output_var = self.get_property('output_variable', 'file_exists')
        context['variables'][output_var] = exists
        
        return {
            'success': True,
            'exists': exists,
            'path': path
        }

    def _list_files(self, context: Any) -> Dict[str, Any]:
        path = self._resolve_variable(self.get_property('path'), context)
        pattern = self.get_property('pattern', '*')
        recursive = self.get_property('recursive', False)
        
        try:
            if recursive:
                files = glob.glob(os.path.join(path, '**', pattern), recursive=True)
            else:
                files = glob.glob(os.path.join(path, pattern))
            
            files = [f for f in files if os.path.isfile(f)]
            
            output_var = self.get_property('output_variable', 'file_list')
            context['variables'][output_var] = files
            
            return {
                'success': True,
                'count': len(files),
                'files': files
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _create_directory(self, context: Any) -> Dict[str, Any]:
        path = self._resolve_variable(self.get_property('path'), context)
        
        try:
            os.makedirs(path, exist_ok=True)
            
            return {
                'success': True,
                'path': path
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _get_file_info(self, context: Any) -> Dict[str, Any]:
        path = self._resolve_variable(self.get_property('path'), context)
        
        try:
            stat = os.stat(path)
            
            info = {
                'path': path,
                'name': os.path.basename(path),
                'size': stat.st_size,
                'created': stat.st_ctime,
                'modified': stat.st_mtime,
                'accessed': stat.st_atime,
                'is_file': os.path.isfile(path),
                'is_dir': os.path.isdir(path)
            }
            
            output_var = self.get_property('output_variable', 'file_info')
            context['variables'][output_var] = info
            
            return {
                'success': True,
                'info': info
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


class FileReadComponent(FileComponent):
    def __init__(self, component_id: str):
        super().__init__(component_id, "read")
        self.category = "文件操作"
        self.description = "读取文件内容"


class FileWriteComponent(FileComponent):
    def __init__(self, component_id: str):
        super().__init__(component_id, "write")
        self.category = "文件操作"
        self.description = "写入文件内容"


class FileCopyComponent(FileComponent):
    def __init__(self, component_id: str):
        super().__init__(component_id, "copy")
        self.category = "文件操作"
        self.description = "复制文件"


class FileDeleteComponent(FileComponent):
    def __init__(self, component_id: str):
        super().__init__(component_id, "delete")
        self.category = "文件操作"
        self.description = "删除文件"
