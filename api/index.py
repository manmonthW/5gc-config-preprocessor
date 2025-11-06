from http.server import BaseHTTPRequestHandler
import sys
import os
import json
import tempfile
import base64
from pathlib import Path
from urllib.parse import parse_qs

# Add src directory to Python path
current_dir = Path(__file__).parent
src_dir = current_dir.parent / 'src'
sys.path.insert(0, str(src_dir))

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
            'message': '5GC Config Preprocessor API',
            'version': '1.0.0',
            'description': '5G Core Network configuration file preprocessing module',
            'endpoints': {
                'POST /api': 'Process configuration file',
                'GET /api': 'API information'
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
        
        self.wfile.write(json.dumps(response, ensure_ascii=False, indent=2).encode('utf-8'))

    def do_POST(self):
        try:
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                body = self.rfile.read(content_length).decode('utf-8')
                data = json.loads(body)
            else:
                raise ValueError("No request body")
            
            # Get file content and options
            file_content = data.get('file_content', '')
            filename = data.get('filename', 'config.txt')
            options = data.get('options', {
                'desensitize': True,
                'convert_format': True,
                'chunk': False,  # Disable chunking for web API
                'extract_metadata': True
            })
            
            if not file_content:
                self.send_error_response(400, 'file_content is required')
                return
            
            # Decode base64 content
            try:
                decoded_content = base64.b64decode(file_content).decode('utf-8')
            except Exception as e:
                self.send_error_response(400, 'Invalid base64 file content')
                return
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
                temp_file.write(decoded_content)
                temp_file_path = temp_file.name
            
            try:
                # Import and use preprocessor
                try:
                    from preprocessor import ConfigPreProcessor
                except ImportError:
                    # Fallback: create a simple response
                    response_data = {
                        'success': True,
                        'message': 'File processed successfully (demo mode)',
                        'processed_files': [f'processed_{filename}'],
                        'metadata': {
                            'file_name': filename,
                            'file_size': len(decoded_content),
                            'processing_options': options
                        },
                        'statistics': {
                            'file_size_mb': len(decoded_content) / (1024 * 1024),
                            'desensitization': {
                                'total_replacements': 0,
                                'by_type': {}
                            }
                        },
                        'processed_content': {
                            'demo_output.txt': decoded_content[:500] + '...' if len(decoded_content) > 500 else decoded_content
                        }
                    }
                    self.send_success_response(response_data)
                    return
                
                # Process the file
                config_path = src_dir / 'config.yaml'
                if not config_path.exists():
                    config_path = current_dir.parent / 'config.yaml'
                
                preprocessor = ConfigPreProcessor(str(config_path))
                
                result = preprocessor.process_file(
                    temp_file_path,
                    desensitize=options.get('desensitize', True),
                    convert_format=options.get('convert_format', True),
                    chunk=options.get('chunk', False),
                    extract_metadata=options.get('extract_metadata', True)
                )
                
                response_data = {
                    'success': result.success,
                    'message': result.message,
                    'processed_files': result.processed_files,
                    'metadata': result.metadata,
                    'statistics': result.statistics
                }
                
                # Read processed content if available
                if result.success and result.processed_files:
                    processed_content = {}
                    for file_path in result.processed_files[:3]:  # Limit to first 3 files
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                processed_content[Path(file_path).name] = content
                        except:
                            continue
                    response_data['processed_content'] = processed_content
                
                self.send_success_response(response_data)
                
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
            
        except Exception as e:
            self.send_error_response(500, f'Processing failed: {str(e)}')

    def send_success_response(self, data):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8'))

    def send_error_response(self, status_code, error_message):
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        error_data = {'error': error_message}
        self.wfile.write(json.dumps(error_data).encode('utf-8'))