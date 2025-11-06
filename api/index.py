from http.server import BaseHTTPRequestHandler
import sys
import os
import json
import tempfile
import base64
import traceback
import chardet
from pathlib import Path
from urllib.parse import parse_qs
from datetime import datetime

# Add debug and src directories to Python path
current_dir = Path(__file__).parent
src_dir = current_dir.parent / 'src'
debug_dir = current_dir.parent / 'debug'
sys.path.insert(0, str(src_dir))
sys.path.insert(0, str(debug_dir))

MAX_PREVIEW_CHARS = 200_000  # limit processed content preview
MAX_PREVIEW_FILES = 3

# Import debug system
try:
    from debug import api_logger, log_api_request, log_api_response, is_debug_enabled, get_debug_info
    DEBUG_AVAILABLE = True
except ImportError:
    DEBUG_AVAILABLE = False
    print("Debug system not available", file=sys.stderr)

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        try:
            if DEBUG_AVAILABLE:
                log_api_request("OPTIONS", self.path)
            
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()
            
            if DEBUG_AVAILABLE:
                log_api_response(200)
                
        except Exception as e:
            if DEBUG_AVAILABLE:
                api_logger.error("OPTIONS request failed", exception=e)
            self.send_error_response(500, f"OPTIONS failed: {str(e)}")

    def do_GET(self):
        try:
            if DEBUG_AVAILABLE:
                log_api_request("GET", self.path, headers=dict(self.headers))
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response = {
                'message': '5GC Config Preprocessor API',
                'version': '1.0.0',
                'description': '5G Core Network configuration file preprocessing module',
                'timestamp': datetime.now().isoformat(),
                'endpoints': {
                    'POST /api': 'Process configuration file',
                    'GET /api': 'API information',
                    'GET /api/debug': 'Debug information (if enabled)'
                },
                'usage': {
                    'method': 'POST',
                    'body': {
                        'file_content': 'base64 encoded file content',
                        'filename': 'original filename',
                        'options': {
                            'desensitize': True,
                            'convert_format': True,
                            'chunk': True,
                            'extract_metadata': True
                        }
                    }
                }
            }
            
            # Add debug info if available and requested
            if DEBUG_AVAILABLE and self.path.endswith('/debug'):
                response['debug_info'] = get_debug_info()
                response['debug_available'] = True
            elif DEBUG_AVAILABLE:
                response['debug_available'] = True
            else:
                response['debug_available'] = False
            
            response_json = json.dumps(response, ensure_ascii=False, indent=2)
            self.wfile.write(response_json.encode('utf-8'))
            
            if DEBUG_AVAILABLE:
                log_api_response(200, f"Sent API info response ({len(response_json)} bytes)")
                
        except Exception as e:
            if DEBUG_AVAILABLE:
                api_logger.error("GET request failed", exception=e)
            self.send_error_response(500, f"GET failed: {str(e)}")

    def do_POST(self):
        request_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        
        try:
            if DEBUG_AVAILABLE:
                api_logger.info(f"Starting POST request processing", request_id=request_id)
                log_api_request("POST", self.path, headers=dict(self.headers))
            
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            if DEBUG_AVAILABLE:
                api_logger.debug(f"Request content length: {content_length}", request_id=request_id)
            
            if content_length > 0:
                body = self.rfile.read(content_length).decode('utf-8')
                if DEBUG_AVAILABLE:
                    api_logger.debug(f"Request body read successfully", 
                                   request_id=request_id, 
                                   body_length=len(body),
                                   body_preview=body[:200] + "..." if len(body) > 200 else body)
                data = json.loads(body)
            else:
                raise ValueError("No request body provided")
            
            # Extract and validate request data
            file_content = data.get('file_content', '')
            filename = data.get('filename', 'config.txt')
            options = data.get('options', {
                'desensitize': True,
                'convert_format': True,
                'chunk': False,
                'extract_metadata': True
            })
            
            if DEBUG_AVAILABLE:
                api_logger.info(f"Processing file: {filename}", 
                              request_id=request_id,
                              filename=filename,
                              options=options,
                              content_length=len(file_content))
            
            if not file_content:
                raise ValueError("file_content is required")
            
            # Decode base64 content
            try:
                decoded_bytes = base64.b64decode(file_content)
                decoded_text = ""
                detected_encoding = 'utf-8'
                detected_confidence = 1.0
                try:
                    decoded_text = decoded_bytes.decode('utf-8')
                except UnicodeDecodeError:
                    detection = chardet.detect(decoded_bytes)
                    detected_encoding = detection.get('encoding') or 'utf-8'
                    detected_confidence = detection.get('confidence', 0.0)
                    decoded_text = decoded_bytes.decode(detected_encoding, errors='replace')
                if DEBUG_AVAILABLE:
                    api_logger.debug(
                        "File content decoded successfully",
                        request_id=request_id,
                        decoded_length=len(decoded_bytes),
                        detected_encoding=detected_encoding,
                        detected_confidence=detected_confidence,
                        content_preview=decoded_text[:200] + "..." if len(decoded_text) > 200 else decoded_text
                    )
            except Exception as decode_error:
                if DEBUG_AVAILABLE:
                    api_logger.error(f"Base64 decoding failed", 
                                   request_id=request_id,
                                   exception=decode_error,
                                   content_sample=file_content[:100] if file_content else "empty")
                raise ValueError(f"Invalid base64 file content: {str(decode_error)}")
            
            # Create temporary file
            temp_file_path = None
            try:
                original_suffix = Path(filename).suffix or '.txt'
                with tempfile.NamedTemporaryFile(mode='wb', suffix=original_suffix, delete=False) as temp_file:
                    temp_file.write(decoded_bytes)
                    temp_file_path = temp_file.name
                
                if DEBUG_AVAILABLE:
                    api_logger.debug(f"Temporary file created", 
                                   request_id=request_id,
                                   temp_path=temp_file_path)
                
                # Try to import and use preprocessor
                try:
                    if DEBUG_AVAILABLE:
                        api_logger.debug(f"Attempting to import preprocessor", request_id=request_id)
                    
                    from preprocessor import ConfigPreProcessor
                    
                    if DEBUG_AVAILABLE:
                        api_logger.info(f"Preprocessor imported successfully", request_id=request_id)
                    
                    # Find config file
                    config_path = src_dir / 'config.yaml'
                    if not config_path.exists():
                        config_path = current_dir.parent / 'config.yaml'
                    
                    if DEBUG_AVAILABLE:
                        api_logger.debug(f"Using config file", 
                                       request_id=request_id,
                                       config_path=str(config_path),
                                       config_exists=config_path.exists())
                    
                    # Initialize preprocessor
                    preprocessor = ConfigPreProcessor(str(config_path))
                    
                    if DEBUG_AVAILABLE:
                        api_logger.info(f"ConfigPreProcessor initialized", request_id=request_id)
                    
                    # Process the file
                    result = preprocessor.process_file(
                        temp_file_path,
                        desensitize=options.get('desensitize', True),
                        convert_format=options.get('convert_format', True),
                        chunk=options.get('chunk', False),
                        extract_metadata=options.get('extract_metadata', True)
                    )
                    
                    if DEBUG_AVAILABLE:
                        api_logger.info(f"File processing completed", 
                                      request_id=request_id,
                                      success=result.success,
                                      message=result.message,
                                      processed_files_count=len(result.processed_files) if result.processed_files else 0)
                    
                    response_data = {
                        'success': result.success,
                        'message': result.message,
                        'processed_files': result.processed_files,
                        'metadata': result.metadata,
                        'statistics': result.statistics,
                        'request_id': request_id,
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    # Read processed content if available
                    if result.success and result.processed_files:
                        processed_content = {}
                        for file_path in result.processed_files[:MAX_PREVIEW_FILES]:
                            try:
                                file_path_obj = Path(file_path)
                                if file_path_obj.is_dir():
                                    continue
                                size_bytes = file_path_obj.stat().st_size
                                with open(file_path_obj, 'r', encoding='utf-8', errors='replace') as f:
                                    content = f.read(MAX_PREVIEW_CHARS)
                                    if size_bytes > MAX_PREVIEW_CHARS:
                                        remaining = size_bytes - MAX_PREVIEW_CHARS
                                        content += f"\n\n...[truncated {remaining} bytes]"
                                    processed_content[file_path_obj.name] = content
                                    if DEBUG_AVAILABLE:
                                        api_logger.debug(f"Read processed file", 
                                                       request_id=request_id,
                                                       file_name=file_path_obj.name,
                                                       content_length=len(content))
                            except Exception as read_error:
                                if DEBUG_AVAILABLE:
                                    api_logger.warning(f"Failed to read processed file", 
                                                     request_id=request_id,
                                                     file_path=file_path,
                                                     exception=read_error)
                                continue
                        response_data['processed_content'] = processed_content
                    
                    self.send_success_response(response_data)
                    
                    if DEBUG_AVAILABLE:
                        log_api_response(200, f"Processing successful for {filename}")
                    
                except ImportError as import_error:
                    if DEBUG_AVAILABLE:
                        api_logger.warning(f"Preprocessor import failed, using demo mode", 
                                         request_id=request_id,
                                         exception=import_error)
                    
                    # Fallback: create a demo response
                    response_data = {
                        'success': True,
                        'message': 'File processed successfully (demo mode - preprocessor not available)',
                        'processed_files': [f'demo_processed_{filename}'],
                        'metadata': {
                            'file_name': filename,
                            'file_size': len(decoded_bytes),
                            'processing_options': options,
                            'mode': 'demo'
                        },
                        'statistics': {
                            'file_size_mb': len(decoded_bytes) / (1024 * 1024),
                            'desensitization': {
                                'total_replacements': 0,
                                'by_type': {}
                            }
                        },
                        'processed_content': {
                            'demo_output.txt': decoded_text[:500] + '...' if len(decoded_text) > 500 else decoded_text
                        },
                        'request_id': request_id,
                        'timestamp': datetime.now().isoformat(),
                        'debug_info': {
                            'import_error': str(import_error),
                            'python_path': sys.path,
                            'current_dir': str(current_dir),
                            'src_dir': str(src_dir)
                        }
                    }
                    
                    self.send_success_response(response_data)
                    
                    if DEBUG_AVAILABLE:
                        log_api_response(200, f"Demo mode processing for {filename}")
                
            finally:
                # Clean up temporary file
                if temp_file_path:
                    try:
                        os.unlink(temp_file_path)
                        if DEBUG_AVAILABLE:
                            api_logger.debug(f"Temporary file cleaned up", 
                                           request_id=request_id,
                                           temp_path=temp_file_path)
                    except Exception as cleanup_error:
                        if DEBUG_AVAILABLE:
                            api_logger.warning(f"Failed to cleanup temporary file", 
                                             request_id=request_id,
                                             temp_path=temp_file_path,
                                             exception=cleanup_error)
            
        except Exception as e:
            error_details = {
                'request_id': request_id,
                'error_type': type(e).__name__,
                'error_message': str(e),
                'timestamp': datetime.now().isoformat()
            }
            
            if DEBUG_AVAILABLE:
                error_details['traceback'] = traceback.format_exc()
                api_logger.error(f"POST request processing failed", 
                               request_id=request_id,
                               exception=e,
                               **error_details)
            
            self.send_error_response(500, f'Processing failed: {str(e)}', error_details)

    def send_success_response(self, data):
        try:
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response_json = json.dumps(data, ensure_ascii=False, indent=2)
            self.wfile.write(response_json.encode('utf-8'))
        except Exception as e:
            if DEBUG_AVAILABLE:
                api_logger.error("Failed to send success response", exception=e)

    def send_error_response(self, status_code, error_message, error_details=None):
        try:
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
                log_api_response(status_code, error_message)
            else:
                error_data['debug_enabled'] = False
            
            self.wfile.write(json.dumps(error_data, ensure_ascii=False, indent=2).encode('utf-8'))
        except Exception as e:
            if DEBUG_AVAILABLE:
                api_logger.critical("Failed to send error response", exception=e)
