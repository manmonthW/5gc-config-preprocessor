#!/usr/bin/env python3
"""
Vercel serverless function for 5GC Config Preprocessor
"""

import sys
import os
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from preprocessor import ConfigPreProcessor
import json
import tempfile
import base64

def handler(request):
    """Vercel serverless function handler"""
    
    # Handle CORS
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Content-Type': 'application/json'
    }
    
    if request.method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': ''
        }
    
    if request.method == 'GET':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
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
            }, ensure_ascii=False, indent=2)
        }
    
    if request.method == 'POST':
        try:
            # Parse request body
            if hasattr(request, 'json') and request.json:
                data = request.json
            else:
                import json
                data = json.loads(request.body)
            
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
                return {
                    'statusCode': 400,
                    'headers': headers,
                    'body': json.dumps({
                        'error': 'file_content is required'
                    })
                }
            
            # Decode base64 content
            try:
                decoded_content = base64.b64decode(file_content).decode('utf-8')
            except:
                return {
                    'statusCode': 400,
                    'headers': headers,
                    'body': json.dumps({
                        'error': 'Invalid base64 file content'
                    })
                }
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
                temp_file.write(decoded_content)
                temp_file_path = temp_file.name
            
            try:
                # Process the file
                config_path = str(Path(__file__).parent.parent / 'config.yaml')
                preprocessor = ConfigPreProcessor(config_path)
                
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
                
                return {
                    'statusCode': 200,
                    'headers': headers,
                    'body': json.dumps(response_data, ensure_ascii=False, indent=2)
                }
                
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
            
        except Exception as e:
            return {
                'statusCode': 500,
                'headers': headers,
                'body': json.dumps({
                    'error': f'Processing failed: {str(e)}'
                })
            }
    
    return {
        'statusCode': 405,
        'headers': headers,
        'body': json.dumps({
            'error': 'Method not allowed'
        })
    }

# For Vercel
def app(request):
    return handler(request)