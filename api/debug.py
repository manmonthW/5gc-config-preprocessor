from http.server import BaseHTTPRequestHandler
import sys
import os
import json
from pathlib import Path
from datetime import datetime

# Add debug and src directories to Python path
current_dir = Path(__file__).parent
src_dir = current_dir.parent / 'src'
debug_dir = current_dir.parent / 'debug'
sys.path.insert(0, str(src_dir))
sys.path.insert(0, str(debug_dir))

# Import debug system
try:
    from debug import debug_tools, get_debug_info, is_debug_enabled
    DEBUG_AVAILABLE = True
except ImportError:
    DEBUG_AVAILABLE = False

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            if not DEBUG_AVAILABLE:
                response = {
                    'error': 'Debug system not available',
                    'debug_enabled': False,
                    'timestamp': datetime.now().isoformat()
                }
            else:
                # Run debug tests
                test_results = debug_tools.run_full_debug_test()
                
                response = {
                    'debug_enabled': is_debug_enabled(),
                    'debug_config': get_debug_info(),
                    'test_results': test_results,
                    'system_info': {
                        'python_version': sys.version,
                        'python_path': sys.path[:5],  # Show first 5 paths
                        'current_dir': str(current_dir),
                        'src_dir': str(src_dir),
                        'debug_dir': str(debug_dir)
                    },
                    'timestamp': datetime.now().isoformat()
                }
            
            response_json = json.dumps(response, ensure_ascii=False, indent=2)
            self.wfile.write(response_json.encode('utf-8'))
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            error_response = {
                'error': f'Debug endpoint failed: {str(e)}',
                'error_type': type(e).__name__,
                'timestamp': datetime.now().isoformat()
            }
            
            self.wfile.write(json.dumps(error_response, ensure_ascii=False, indent=2).encode('utf-8'))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()