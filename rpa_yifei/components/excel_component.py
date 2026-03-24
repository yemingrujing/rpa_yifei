from typing import Any, Dict, Optional, Union, List
import pandas as pd
from .base import BaseComponent, ComponentType
import os


class ExcelComponent(BaseComponent):
    def __init__(self, component_id: str, action: str = "read"):
        super().__init__(component_id, ComponentType.EXCEL, f"Excel_{action}")
        self.action = action
        self.category = "数据处理"
        self.description = f"执行Excel {action}操作"

    def validate(self) -> tuple[bool, Optional[str]]:
        if self.action in ["read", "write", "append"]:
            if not self.get_property('file_path'):
                return False, "file_path is required"
        return True, None

    def execute(self, context: Any) -> Any:
        data_handler = context.get('data_handler')
        if not data_handler:
            from ..core.data_handler import DataHandler
            data_handler = DataHandler()
        
        file_path = self._resolve_variable(self.get_property('file_path', ''), context)
        
        if self.action == "read":
            return self._read_excel(data_handler, file_path, context)
        elif self.action == "write":
            return self._write_excel(data_handler, file_path, context)
        elif self.action == "append":
            return self._append_excel(data_handler, file_path, context)
        elif self.action == "get_sheets":
            return self._get_sheets(data_handler, file_path)
        elif self.action == "get_ranges":
            return self._get_ranges(data_handler, file_path, context)
        
        return {}

    def _resolve_variable(self, value: Any, context: Any) -> Any:
        if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
            var_name = value[2:-1]
            return context.get('variables', {}).get(var_name, value)
        return value

    def _read_excel(self, data_handler, file_path: str, context: Any) -> Dict[str, Any]:
        sheet_name = self._resolve_variable(self.get_property('sheet_name'), context)
        header = self.get_property('header', 0)
        
        df = data_handler.read_excel(file_path, sheet_name=sheet_name, header=header)
        
        output_var = self.get_property('output_variable', 'excel_data')
        context['variables'][output_var] = df
        
        rows = self.get_property('rows')
        if rows:
            df = df.head(rows)
        
        columns = self.get_property('columns')
        if columns:
            df = df[columns]
        
        return {
            'success': True,
            'rows': len(df),
            'columns': list(df.columns),
            'data': df.to_dict('records') if self.get_property('return_dict', True) else df.values.tolist()
        }

    def _write_excel(self, data_handler, file_path: str, context: Any) -> Dict[str, Any]:
        sheet_name = self.get_property('sheet_name', 'Sheet1')
        data = self._resolve_variable(self.get_property('data'), context)
        
        if isinstance(data, str) and data.startswith('${'):
            var_name = data[2:-1]
            data = context['variables'].get(var_name, [])
        
        data_handler.write_excel(file_path, data, sheet_name=sheet_name, mode='write')
        
        return {
            'success': True,
            'file_path': file_path,
            'rows': len(data) if isinstance(data, list) else 1
        }

    def _append_excel(self, data_handler, file_path: str, context: Any) -> Dict[str, Any]:
        sheet_name = self.get_property('sheet_name', 'Sheet1')
        data = self._resolve_variable(self.get_property('data'), context)
        
        if isinstance(data, str) and data.startswith('${'):
            var_name = data[2:-1]
            data = context['variables'].get(var_name, [])
        
        data_handler.append_to_excel(file_path, data, sheet_name=sheet_name)
        
        return {
            'success': True,
            'file_path': file_path,
            'rows': len(data) if isinstance(data, list) else 1
        }

    def _get_sheets(self, data_handler, file_path: str) -> Dict[str, Any]:
        sheets = data_handler.get_excel_sheets(file_path)
        return {
            'success': True,
            'sheets': sheets
        }

    def _get_ranges(self, data_handler, file_path: str, context: Any) -> Dict[str, Any]:
        sheet_name = self._resolve_variable(self.get_property('sheet_name'), context)
        start_row = self.get_property('start_row', 1)
        end_row = self.get_property('end_row', 100)
        start_col = self.get_property('start_col', 1)
        end_col = self.get_property('end_col', 10)
        
        data = data_handler.read_excel_range(
            file_path, sheet_name, start_row, end_row, start_col, end_col
        )
        
        return {
            'success': True,
            'data': data,
            'rows': len(data),
            'columns': len(data[0]) if data else 0
        }


class ExcelReadComponent(ExcelComponent):
    def __init__(self, component_id: str):
        super().__init__(component_id, "read")
        self.category = "数据处理"
        self.description = "读取Excel文件数据"


class ExcelWriteComponent(ExcelComponent):
    def __init__(self, component_id: str):
        super().__init__(component_id, "write")
        self.category = "数据处理"
        self.description = "写入数据到Excel文件"


class ExcelAppendComponent(ExcelComponent):
    def __init__(self, component_id: str):
        super().__init__(component_id, "append")
        self.category = "数据处理"
        self.description = "追加数据到Excel文件"
