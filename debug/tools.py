#!/usr/bin/env python3
"""
调试工具模块
提供用于测试和调试的独立工具
"""

import os
import sys
import json
import base64
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# Add project paths
current_dir = Path(__file__).parent
project_dir = current_dir.parent
src_dir = project_dir / 'src'
sys.path.insert(0, str(src_dir))

try:
    from .logger import general_logger
except ImportError:
    # Direct import when running as script
    from logger import general_logger

class DebugTools:
    """调试工具类"""
    
    def __init__(self):
        self.project_dir = project_dir
        self.src_dir = src_dir
        self.api_dir = project_dir / 'api'
    
    def create_test_yaml(self, output_path: Optional[str] = None) -> str:
        """创建测试用的YAML文件"""
        test_yaml_content = """# 5GC Test Configuration
# This is a test file for debugging the preprocessor

project:
  name: "Test 5GC Project"
  version: "1.0.0"
  customer: "Test Customer Ltd"
  date: "2024-01-15"

global:
  site_id: "TEST001"
  region: "Test-Region"
  deployment_type: "distributed"
  
network:
  management_ip: "192.168.1.100"
  service_ip: "10.0.0.1"
  external_ip: "203.0.113.1"
  
security:
  admin_password: "AdminPass123!"
  api_key: "sk-1234567890abcdef"
  certificate_path: "/opt/certs/server.crt"

amf:
  name: "AMF_TEST_01"
  id: "0x0001"
  plmn_id: "46000"
  region_id: "0x02"
  set_id: "0x001"
  
  interfaces:
    - name: "N1"
      ip: "172.16.1.10"
      port: 38412
    - name: "N2" 
      ip: "172.16.2.10"
      port: 38412

subscribers:
  - imsi: "460001234567890"
    msisdn: "8613812345678"
    key: "465B5CE8B199B49FAA5F0A2EE238A6BC"
  - imsi: "460001234567891"
    msisdn: "8613812345679"
    key: "465B5CE8B199B49FAA5F0A2EE238A6BD"

logging:
  level: "DEBUG"
  file: "/var/log/5gc/test.log"
  max_size: "100MB"
"""
        
        if output_path is None:
            output_path = self.project_dir / "test_config.yaml"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(test_yaml_content)
        
        general_logger.info(f"Created test YAML file", file_path=str(output_path))
        return str(output_path)
    
    def test_base64_encoding(self, file_path: str) -> str:
        """测试Base64编码"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')
            
            general_logger.debug(f"Base64 encoding test successful", 
                               file_path=file_path,
                               original_length=len(content),
                               encoded_length=len(encoded))
            
            return encoded
        except Exception as e:
            general_logger.error(f"Base64 encoding test failed", 
                               file_path=file_path,
                               exception=e)
            raise
    
    def test_preprocessor_import(self) -> Dict[str, Any]:
        """测试预处理器导入"""
        result = {
            'import_successful': False,
            'error': None,
            'paths_checked': [],
            'config_file_found': False,
            'config_path': None
        }
        
        try:
            # 检查路径
            result['paths_checked'] = [str(p) for p in sys.path]
            
            # 尝试导入
            from preprocessor import ConfigPreProcessor
            result['import_successful'] = True
            
            general_logger.info("Preprocessor import successful")
            
            # 检查配置文件
            config_paths = [
                self.src_dir / 'config.yaml',
                self.project_dir / 'config.yaml'
            ]
            
            for config_path in config_paths:
                if config_path.exists():
                    result['config_file_found'] = True
                    result['config_path'] = str(config_path)
                    general_logger.debug(f"Found config file", config_path=str(config_path))
                    break
            
        except Exception as e:
            result['error'] = {
                'type': type(e).__name__,
                'message': str(e)
            }
            general_logger.error("Preprocessor import failed", exception=e)
        
        return result
    
    def test_api_request_simulation(self, yaml_content: str, filename: str = "test.yaml") -> Dict[str, Any]:
        """模拟API请求测试"""
        try:
            # 编码内容
            encoded_content = base64.b64encode(yaml_content.encode('utf-8')).decode('utf-8')
            
            # 创建请求数据
            request_data = {
                'file_content': encoded_content,
                'filename': filename,
                'options': {
                    'desensitize': True,
                    'convert_format': True,
                    'chunk': False,
                    'extract_metadata': True
                }
            }
            
            general_logger.info(f"Simulating API request", 
                              filename=filename,
                              content_length=len(yaml_content),
                              encoded_length=len(encoded_content))
            
            # 测试JSON序列化
            json_data = json.dumps(request_data)
            
            result = {
                'request_valid': True,
                'json_serializable': True,
                'request_size': len(json_data),
                'content_preview': yaml_content[:200] + "..." if len(yaml_content) > 200 else yaml_content
            }
            
            general_logger.debug("API request simulation successful", **result)
            return result
            
        except Exception as e:
            result = {
                'request_valid': False,
                'error': {
                    'type': type(e).__name__,
                    'message': str(e)
                }
            }
            general_logger.error("API request simulation failed", exception=e)
            return result
    
    def run_full_debug_test(self) -> Dict[str, Any]:
        """运行完整的调试测试"""
        test_results = {
            'timestamp': datetime.now().isoformat(),
            'tests': {}
        }
        
        general_logger.info("Starting full debug test suite")
        
        try:
            # 1. 测试预处理器导入
            test_results['tests']['preprocessor_import'] = self.test_preprocessor_import()
            
            # 2. 创建测试文件
            test_yaml_path = self.create_test_yaml()
            test_results['tests']['test_file_created'] = {'path': test_yaml_path}
            
            # 3. 测试Base64编码
            with open(test_yaml_path, 'r', encoding='utf-8') as f:
                yaml_content = f.read()
            
            encoded_content = self.test_base64_encoding(test_yaml_path)
            test_results['tests']['base64_encoding'] = {'successful': True}
            
            # 4. 测试API请求模拟
            test_results['tests']['api_simulation'] = self.test_api_request_simulation(yaml_content)
            
            # 5. 检查目录结构
            test_results['tests']['directory_structure'] = {
                'project_dir': str(self.project_dir),
                'src_dir_exists': self.src_dir.exists(),
                'api_dir_exists': self.api_dir.exists(),
                'config_yaml_exists': (self.project_dir / 'config.yaml').exists(),
                'debug_dir_exists': (self.project_dir / 'debug').exists()
            }
            
            general_logger.info("Full debug test completed successfully")
            
        except Exception as e:
            test_results['error'] = {
                'type': type(e).__name__,
                'message': str(e)
            }
            general_logger.error("Full debug test failed", exception=e)
        
        return test_results
    
    def generate_debug_report(self) -> str:
        """生成调试报告"""
        test_results = self.run_full_debug_test()
        
        report_lines = [
            "# 5GC Config Preprocessor Debug Report",
            f"Generated at: {test_results['timestamp']}",
            "",
            "## Test Results",
            ""
        ]
        
        for test_name, result in test_results.get('tests', {}).items():
            report_lines.append(f"### {test_name.replace('_', ' ').title()}")
            report_lines.append(f"```json")
            report_lines.append(json.dumps(result, indent=2, ensure_ascii=False))
            report_lines.append(f"```")
            report_lines.append("")
        
        if 'error' in test_results:
            report_lines.extend([
                "## Overall Error",
                "```json",
                json.dumps(test_results['error'], indent=2, ensure_ascii=False),
                "```"
            ])
        
        report_content = "\n".join(report_lines)
        
        # 保存报告
        report_path = self.project_dir / f"debug_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        general_logger.info(f"Debug report generated", report_path=str(report_path))
        return str(report_path)

# 创建全局调试工具实例
debug_tools = DebugTools()

def quick_debug_test():
    """快速调试测试"""
    print("Running quick debug test...")
    results = debug_tools.run_full_debug_test()
    print(json.dumps(results, indent=2, ensure_ascii=False))
    return results

def generate_test_data():
    """生成测试数据"""
    yaml_path = debug_tools.create_test_yaml()
    encoded = debug_tools.test_base64_encoding(yaml_path)
    
    print(f"Test YAML file created: {yaml_path}")
    print(f"Base64 encoded content (first 100 chars): {encoded[:100]}...")
    
    return yaml_path, encoded

if __name__ == "__main__":
    # 命令行调试入口
    import argparse
    
    parser = argparse.ArgumentParser(description="5GC Config Preprocessor Debug Tools")
    parser.add_argument('--test', action='store_true', help='Run quick debug test')
    parser.add_argument('--report', action='store_true', help='Generate debug report')
    parser.add_argument('--create-test-data', action='store_true', help='Create test data')
    
    args = parser.parse_args()
    
    if args.test:
        quick_debug_test()
    elif args.report:
        report_path = debug_tools.generate_debug_report()
        print(f"Debug report generated: {report_path}")
    elif args.create_test_data:
        generate_test_data()
    else:
        print("Use --test, --report, or --create-test-data")
        parser.print_help()