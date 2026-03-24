from typing import Any, Dict, Optional, List
import pymysql
import psycopg2
import sqlite3
from .base import BaseComponent, ComponentType


class DatabaseComponent(BaseComponent):
    def __init__(self, component_id: str, action: str = "query"):
        super().__init__(component_id, ComponentType.DATABASE, f"Database_{action}")
        self.action = action
        self.category = "集成"
        self.description = f"执行数据库{action}操作"
        self.connection = None
        self.cursor = None

    def validate(self) -> tuple[bool, Optional[str]]:
        if self.action in ["query", "execute", "connect"]:
            if not self.get_property('db_type'):
                return False, "db_type is required"
        return True, None

    def execute(self, context: Any) -> Any:
        if self.action == "connect":
            return self._connect(context)
        elif self.action == "disconnect":
            return self._disconnect(context)
        elif self.action == "query":
            return self._query(context)
        elif self.action == "execute":
            return self._execute(context)
        elif self.action == "fetch_one":
            return self._fetch_one(context)
        elif self.action == "fetch_all":
            return self._fetch_all(context)
        elif self.action == "commit":
            return self._commit(context)
        elif self.action == "rollback":
            return self._rollback(context)
        
        return {}

    def _resolve_variable(self, value: Any, context: Any) -> Any:
        if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
            var_name = value[2:-1]
            return context.get('variables', {}).get(var_name, value)
        return value

    def _get_connection_params(self, context: Any) -> Dict[str, Any]:
        params = {}
        for key in ['host', 'port', 'database', 'user', 'password', 'charset']:
            value = self.get_property(key)
            if value:
                params[key] = self._resolve_variable(value, context)
        return params

    def _connect(self, context: Any) -> Dict[str, Any]:
        db_type = self.get_property('db_type', 'mysql').lower()
        params = self._get_connection_params(context)
        
        try:
            if db_type == 'mysql':
                self.connection = pymysql.connect(**params)
            elif db_type == 'postgresql':
                self.connection = psycopg2.connect(**params)
            elif db_type == 'sqlite':
                db_path = params.get('database', ':memory:')
                self.connection = sqlite3.connect(db_path)
            else:
                return {
                    'success': False,
                    'error': f'Unsupported database type: {db_type}'
                }
            
            self.cursor = self.connection.cursor()
            
            return {
                'success': True,
                'connected': True,
                'db_type': db_type
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _disconnect(self, context: Any) -> Dict[str, Any]:
        try:
            if self.cursor:
                self.cursor.close()
                self.cursor = None
            if self.connection:
                self.connection.close()
                self.connection = None
            
            return {
                'success': True,
                'connected': False
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _query(self, context: Any) -> Dict[str, Any]:
        sql = self._resolve_variable(self.get_property('sql'), context)
        
        if not self.connection:
            connect_result = self._connect(context)
            if not connect_result.get('success'):
                return connect_result
        
        try:
            self.cursor.execute(sql)
            
            columns = [desc[0] for desc in self.cursor.description] if self.cursor.description else []
            rows = self.cursor.fetchall()
            
            results = [dict(zip(columns, row)) for row in rows]
            
            output_var = self.get_property('output_variable', 'query_result')
            context['variables'][output_var] = results
            
            return {
                'success': True,
                'rows': len(results),
                'columns': columns,
                'data': results
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _execute(self, context: Any) -> Dict[str, Any]:
        sql = self._resolve_variable(self.get_property('sql'), context)
        
        if not self.connection:
            connect_result = self._connect(context)
            if not connect_result.get('success'):
                return connect_result
        
        try:
            self.cursor.execute(sql)
            affected_rows = self.cursor.rowcount
            
            return {
                'success': True,
                'affected_rows': affected_rows
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _fetch_one(self, context: Any) -> Dict[str, Any]:
        try:
            if not self.cursor:
                return {
                    'success': False,
                    'error': 'No active cursor'
                }
            
            row = self.cursor.fetchone()
            columns = [desc[0] for desc in self.cursor.description] if self.cursor.description else []
            
            result = dict(zip(columns, row)) if row else None
            
            output_var = self.get_property('output_variable', 'fetch_result')
            context['variables'][output_var] = result
            
            return {
                'success': True,
                'data': result
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _fetch_all(self, context: Any) -> Dict[str, Any]:
        try:
            if not self.cursor:
                return {
                    'success': False,
                    'error': 'No active cursor'
                }
            
            rows = self.cursor.fetchall()
            columns = [desc[0] for desc in self.cursor.description] if self.cursor.description else []
            
            results = [dict(zip(columns, row)) for row in rows]
            
            output_var = self.get_property('output_variable', 'fetch_result')
            context['variables'][output_var] = results
            
            return {
                'success': True,
                'rows': len(results),
                'data': results
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _commit(self, context: Any) -> Dict[str, Any]:
        try:
            if self.connection:
                self.connection.commit()
                return {
                    'success': True
                }
            return {
                'success': False,
                'error': 'No active connection'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _rollback(self, context: Any) -> Dict[str, Any]:
        try:
            if self.connection:
                self.connection.rollback()
                return {
                    'success': True
                }
            return {
                'success': False,
                'error': 'No active connection'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


class DatabaseQueryComponent(DatabaseComponent):
    def __init__(self, component_id: str):
        super().__init__(component_id, "query")
        self.category = "集成"
        self.description = "执行SQL查询"


class DatabaseExecuteComponent(DatabaseComponent):
    def __init__(self, component_id: str):
        super().__init__(component_id, "execute")
        self.category = "集成"
        self.description = "执行SQL语句"
