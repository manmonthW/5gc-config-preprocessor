from http.server import BaseHTTPRequestHandler
import sys
import os
import json
import tempfile
import base64
import re
import traceback
from pathlib import Path
from datetime import datetime

# Add debug directory to Python path
current_dir = Path(__file__).parent
debug_dir = current_dir.parent / 'debug'
sys.path.insert(0, str(debug_dir))

# Import debug system
try:
    from debug import api_logger, log_api_request, log_api_response
    DEBUG_AVAILABLE = True
except ImportError:
    DEBUG_AVAILABLE = False

try:
    import yaml
    YAML_SUPPORT = True
except ImportError:
    YAML_SUPPORT = False

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        response = {
            'message': 'Simple YAML Processor API',
            'version': '1.0.0',
            'description': 'Simplified YAML processing with basic desensitization',
            'timestamp': datetime.now().isoformat(),
            'features': [
                'YAML parsing and validation',
                'Basic IP address desensitization',
                'Password field masking',
                'Content preview'
            ],
            'yaml_support': YAML_SUPPORT,
            'debug_available': DEBUG_AVAILABLE
        }
        
        self.wfile.write(json.dumps(response, ensure_ascii=False, indent=2).encode('utf-8'))

    def do_POST(self):
        request_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        
        try:
            if DEBUG_AVAILABLE:
                api_logger.info(f"Starting simple YAML processing", request_id=request_id)
            
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                body = self.rfile.read(content_length).decode('utf-8')
                data = json.loads(body)
            else:
                raise ValueError("No request body provided")
            
            # Extract request data
            file_content = data.get('file_content', '')
            filename = data.get('filename', 'config.yaml')
            options = data.get('options', {})
            
            if DEBUG_AVAILABLE:
                api_logger.info(f"Processing file: {filename}", 
                              request_id=request_id,
                              filename=filename,
                              options=options)
            
            if not file_content:
                raise ValueError("file_content is required")
            
            # Decode base64 content
            try:
                decoded_content = base64.b64decode(file_content).decode('utf-8')
                if DEBUG_AVAILABLE:
                    api_logger.debug(f"File decoded successfully", 
                                   request_id=request_id,
                                   content_length=len(decoded_content))
            except Exception as e:
                raise ValueError(f"Invalid base64 content: {str(e)}")
            
            # Process the YAML content
            result = self.process_yaml_content(decoded_content, filename, options, request_id)
            
            self.send_success_response(result)
            
            if DEBUG_AVAILABLE:
                api_logger.info(f"Processing completed successfully", request_id=request_id)
            
        except Exception as e:
            error_details = {
                'request_id': request_id,
                'error_type': type(e).__name__,
                'error_message': str(e),
                'timestamp': datetime.now().isoformat(),
                'traceback': traceback.format_exc() if DEBUG_AVAILABLE else None
            }
            
            if DEBUG_AVAILABLE:
                api_logger.error(f"Simple YAML processing failed", 
                               request_id=request_id,
                               exception=e)
            
            self.send_error_response(500, f'Processing failed: {str(e)}', error_details)

    def process_yaml_content(self, content: str, filename: str, options: dict, request_id: str):
        """处理YAML内容的简化版本"""
        
        # 验证YAML格式
        if YAML_SUPPORT:
            try:
                yaml_data = yaml.safe_load(content)
                yaml_valid = True
                if DEBUG_AVAILABLE:
                    api_logger.debug(f"YAML parsing successful", request_id=request_id)
            except Exception as e:
                yaml_valid = False
                if DEBUG_AVAILABLE:
                    api_logger.warning(f"YAML parsing failed", request_id=request_id, exception=e)
        else:
            yaml_valid = "YAML module not available"
        
        # 基本脱敏处理
        processed_content = content
        desensitization_stats = {
            'total_replacements': 0,
            'by_type': {}
        }
        
        if options.get('desensitize', True):
            processed_content, desensitization_stats = self.basic_desensitization(content)
            if DEBUG_AVAILABLE:
                api_logger.debug(f"Desensitization completed", 
                               request_id=request_id,
                               stats=desensitization_stats)
        
        # 提取基本元数据
        metadata = self.extract_basic_metadata(content, filename)
        
        # 构建响应
        result = {
            'success': True,
            'message': 'YAML file processed successfully (simplified mode)',
            'request_id': request_id,
            'timestamp': datetime.now().isoformat(),
            'metadata': metadata,
            'statistics': {
                'file_size_mb': len(content) / (1024 * 1024),
                'yaml_valid': yaml_valid,
                'line_count': len(content.splitlines()),
                'desensitization': desensitization_stats
            },
            'processed_content': {
                'desensitized.yaml': processed_content[:2000] + '...' if len(processed_content) > 2000 else processed_content
            },
            'processing_mode': 'simplified',
            'yaml_support': YAML_SUPPORT
        }
        
        return result
    
    def basic_desensitization(self, content: str):
        """基本脱敏处理"""
        processed = content
        stats = {'total_replacements': 0, 'by_type': {}}
        
        # IP地址脱敏
        ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
        ip_matches = re.findall(ip_pattern, processed)
        if ip_matches:
            processed = re.sub(ip_pattern, 'xxx.xxx.xxx.xxx', processed)
            stats['by_type']['ip_addresses'] = len(ip_matches)
            stats['total_replacements'] += len(ip_matches)
        
        # 密码字段脱敏
        password_patterns = [
            (r'(password\s*[:=]\s*)["\']?[^"\'\s]+["\']?', r'\1"***MASKED***"'),
            (r'(passwd\s*[:=]\s*)["\']?[^"\'\s]+["\']?', r'\1"***MASKED***"'),
            (r'(secret\s*[:=]\s*)["\']?[^"\'\s]+["\']?', r'\1"***MASKED***"'),
            (r'(key\s*[:=]\s*)["\']?[^"\'\s]+["\']?', r'\1"***MASKED***"'),
        ]
        
        password_count = 0
        for pattern, replacement in password_patterns:
            matches = re.findall(pattern, processed, re.IGNORECASE)
            if matches:
                processed = re.sub(pattern, replacement, processed, flags=re.IGNORECASE)
                password_count += len(matches)
        
        if password_count > 0:
            stats['by_type']['passwords'] = password_count
            stats['total_replacements'] += password_count
        
        # 电话号码脱敏
        phone_pattern = r'\b(?:\+86)?1[3-9]\d{9}\b'
        phone_matches = re.findall(phone_pattern, processed)
        if phone_matches:
            processed = re.sub(phone_pattern, '***PHONE***', processed)
            stats['by_type']['phone_numbers'] = len(phone_matches)
            stats['total_replacements'] += len(phone_matches)
        
        return processed, stats
    
    def extract_basic_metadata(self, content: str, filename: str):
        """提取基本元数据"""
        lines = content.splitlines()
        
        metadata = {
            'file_name': filename,
            'file_size': len(content),
            'line_count': len(lines),
            'processing_time': datetime.now().isoformat(),
            'detected_patterns': {}
        }
        
        # 检测5GC相关模式
        patterns = {
            'amf': r'amf|AMF',
            'smf': r'smf|SMF', 
            'upf': r'upf|UPF',
            'nrf': r'nrf|NRF',
            'pcc': r'pcc|PCC',
            'pcf': r'pcf|PCF',
            'nfvi': r'nfvi|NFVI'
        }
        
        for pattern_name, pattern in patterns.items():
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                metadata['detected_patterns'][pattern_name] = len(matches)
        
        # 提取项目信息
        project_patterns = {
            'version': r'version\s*[:=]\s*["\']?([^"\'\s]+)',
            'name': r'name\s*[:=]\s*["\']?([^"\'\s]+)',
            'customer': r'customer\s*[:=]\s*["\']?([^"\'\s]+)'
        }
        
        for key, pattern in project_patterns.items():
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                metadata[key] = match.group(1)
        
        return metadata

    def send_success_response(self, data):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        response_json = json.dumps(data, ensure_ascii=False, indent=2)
        self.wfile.write(response_json.encode('utf-8'))

    def send_error_response(self, status_code, error_message, error_details=None):
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        error_data = {
            'error': error_message,
            'timestamp': datetime.now().isoformat()
        }
        
        if error_details:
            error_data['details'] = error_details
        
        if DEBUG_AVAILABLE:
            error_data['debug_enabled'] = True
        
        self.wfile.write(json.dumps(error_data, ensure_ascii=False, indent=2).encode('utf-8'))