#!/usr/bin/env python3
"""
调试配置模块
独立的调试系统，便于在发布时分离
"""

import os
import json
import tempfile
from datetime import datetime
from enum import Enum
from pathlib import Path

class LogLevel(Enum):
    """日志级别"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class DebugConfig:
    """调试配置类"""
    
    def __init__(self):
        # 从环境变量获取调试设置
        self.enabled = os.getenv('DEBUG', 'true').lower() == 'true'
        self.log_level = os.getenv('LOG_LEVEL', 'DEBUG').upper()
        self.log_to_file = os.getenv('LOG_TO_FILE', 'true').lower() == 'true'
        self.log_to_console = os.getenv('LOG_TO_CONSOLE', 'true').lower() == 'true'
        self.detailed_errors = os.getenv('DETAILED_ERRORS', 'true').lower() == 'true'
        
        # 创建日志目录（在只读环境中自动降级）
        self.log_dir = Path(__file__).parent / 'logs'
        if self.enabled and self.log_to_file:
            self._ensure_log_dir()
    
    def get_log_file_path(self, module_name="app"):
        """获取日志文件路径"""
        if not self.log_to_file or not self.log_dir:
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d")
        return self.log_dir / f"{module_name}_{timestamp}.log"
    
    def is_level_enabled(self, level: LogLevel):
        """检查日志级别是否启用"""
        if not self.enabled:
            return False
        
        levels = {
            'DEBUG': 0,
            'INFO': 1,
            'WARNING': 2,
            'ERROR': 3,
            'CRITICAL': 4
        }
        
        current_level = levels.get(self.log_level, 0)
        check_level = levels.get(level.value, 0)
        
        return check_level >= current_level

    def _ensure_log_dir(self):
        """确保日志目录可写，在只读环境下自动回退"""
        try:
            self.log_dir.mkdir(exist_ok=True)
        except (OSError, PermissionError):
            fallback_dir = Path(tempfile.gettempdir()) / "config_preprocessor_logs"
            try:
                fallback_dir.mkdir(parents=True, exist_ok=True)
                self.log_dir = fallback_dir
            except Exception:
                # 最终回退：禁用文件日志，避免阻塞模块导入
                self.log_to_file = False
                self.log_dir = None

# 全局调试配置实例
debug_config = DebugConfig()

def is_debug_enabled():
    """检查是否启用调试"""
    return debug_config.enabled

def get_debug_info():
    """获取调试配置信息"""
    return {
        'enabled': debug_config.enabled,
        'log_level': debug_config.log_level,
        'log_to_file': debug_config.log_to_file,
        'log_to_console': debug_config.log_to_console,
        'detailed_errors': debug_config.detailed_errors,
        'log_dir': str(debug_config.log_dir) if debug_config.log_to_file else None
    }
