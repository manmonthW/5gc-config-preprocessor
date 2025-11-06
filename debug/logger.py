#!/usr/bin/env python3
"""
调试日志模块
提供统一的日志记录功能
"""

import sys
import json
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from .config import debug_config, LogLevel

class DebugLogger:
    """调试日志记录器"""
    
    def __init__(self, module_name: str = "app"):
        self.module_name = module_name
        self.log_file = debug_config.get_log_file_path(module_name)
    
    def _format_message(self, level: LogLevel, message: str, extra_data: Optional[Dict] = None):
        """格式化日志消息"""
        timestamp = datetime.now().isoformat()
        
        log_entry = {
            'timestamp': timestamp,
            'level': level.value,
            'module': self.module_name,
            'message': message
        }
        
        if extra_data:
            log_entry['data'] = extra_data
        
        return log_entry
    
    def _write_log(self, log_entry: Dict):
        """写入日志"""
        formatted_message = json.dumps(log_entry, ensure_ascii=False, indent=2)
        
        # 输出到控制台
        if debug_config.log_to_console:
            print(f"[{log_entry['level']}] {log_entry['message']}", file=sys.stderr)
            if 'data' in log_entry:
                print(f"Data: {json.dumps(log_entry['data'], ensure_ascii=False, indent=2)}", file=sys.stderr)
        
        # 输出到文件
        if debug_config.log_to_file and self.log_file:
            try:
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    f.write(formatted_message + '\n')
            except Exception as e:
                print(f"Failed to write log file: {e}", file=sys.stderr)
    
    def debug(self, message: str, **kwargs):
        """记录调试信息"""
        if debug_config.is_level_enabled(LogLevel.DEBUG):
            log_entry = self._format_message(LogLevel.DEBUG, message, kwargs if kwargs else None)
            self._write_log(log_entry)
    
    def info(self, message: str, **kwargs):
        """记录信息"""
        if debug_config.is_level_enabled(LogLevel.INFO):
            log_entry = self._format_message(LogLevel.INFO, message, kwargs if kwargs else None)
            self._write_log(log_entry)
    
    def warning(self, message: str, **kwargs):
        """记录警告"""
        if debug_config.is_level_enabled(LogLevel.WARNING):
            log_entry = self._format_message(LogLevel.WARNING, message, kwargs if kwargs else None)
            self._write_log(log_entry)
    
    def error(self, message: str, exception: Optional[Exception] = None, **kwargs):
        """记录错误"""
        if debug_config.is_level_enabled(LogLevel.ERROR):
            extra_data = kwargs.copy() if kwargs else {}
            
            if exception:
                extra_data['exception'] = {
                    'type': type(exception).__name__,
                    'message': str(exception),
                    'traceback': traceback.format_exc() if debug_config.detailed_errors else None
                }
            
            log_entry = self._format_message(LogLevel.ERROR, message, extra_data)
            self._write_log(log_entry)
    
    def critical(self, message: str, exception: Optional[Exception] = None, **kwargs):
        """记录严重错误"""
        if debug_config.is_level_enabled(LogLevel.CRITICAL):
            extra_data = kwargs.copy() if kwargs else {}
            
            if exception:
                extra_data['exception'] = {
                    'type': type(exception).__name__,
                    'message': str(exception),
                    'traceback': traceback.format_exc()
                }
            
            log_entry = self._format_message(LogLevel.CRITICAL, message, extra_data)
            self._write_log(log_entry)

# 创建全局日志实例
api_logger = DebugLogger("api")
processor_logger = DebugLogger("processor")
general_logger = DebugLogger("general")

def log_function_call(func_name: str, args: Dict = None, result: Any = None, error: Exception = None):
    """记录函数调用"""
    logger = general_logger
    
    call_info = {
        'function': func_name,
        'args': args,
        'timestamp': datetime.now().isoformat()
    }
    
    if error:
        call_info['error'] = {
            'type': type(error).__name__,
            'message': str(error)
        }
        logger.error(f"Function {func_name} failed", exception=error, **call_info)
    else:
        if result is not None:
            call_info['result_type'] = type(result).__name__
            if hasattr(result, '__dict__'):
                call_info['result_summary'] = str(result)[:200]
        
        logger.debug(f"Function {func_name} completed", **call_info)

def log_api_request(method: str, path: str, headers: Dict = None, body_summary: str = None):
    """记录API请求"""
    api_logger.info(
        f"API Request: {method} {path}",
        method=method,
        path=path,
        headers=headers,
        body_summary=body_summary
    )

def log_api_response(status_code: int, response_summary: str = None, error: Exception = None):
    """记录API响应"""
    if error:
        api_logger.error(
            f"API Response: {status_code} (Error)",
            status_code=status_code,
            response_summary=response_summary,
            exception=error
        )
    else:
        api_logger.info(
            f"API Response: {status_code}",
            status_code=status_code,
            response_summary=response_summary
        )