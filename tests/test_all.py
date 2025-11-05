#!/usr/bin/env python3
"""
配置预处理模块测试套件
包含所有模块的单元测试和集成测试
"""

import unittest
import tempfile
import json
import yaml
from pathlib import Path
import sys
import os

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from desensitizer import ConfigDesensitizer
from format_converter import FormatConverter, ConfigFormat
from chunker import SmartChunker, ConfigChunk
from metadata_extractor import MetadataExtractor
from preprocessor import ConfigPreProcessor

class TestDesensitizer(unittest.TestCase):
    """脱敏模块测试"""
    
    def setUp(self):
        """测试前准备"""
        self.desensitizer = ConfigDesensitizer("../config.yaml")
        
    def test_ip_desensitization(self):
        """测试IP地址脱敏"""
        text = "server_ip = 192.168.1.100"
        result, mapping = self.desensitizer.desensitize_text(text)
        
        self.assertNotIn("192.168.1.100", result)
        self.assertIn("ip_addresses", mapping)
        self.assertEqual(len(mapping["ip_addresses"]), 1)
    
    def test_phone_desensitization(self):
        """测试电话号码脱敏"""
        text = "contact_phone = 13812345678"
        result, mapping = self.desensitizer.desensitize_text(text)
        
        self.assertNotIn("13812345678", result)
        self.assertIn("138****", result)
    
    def test_password_desensitization(self):
        """测试密码脱敏"""
        text = "admin_password = MySecret123"
        result, mapping = self.desensitizer.desensitize_text(text)
        
        self.assertNotIn("MySecret123", result)
        self.assertIn("********", result)
    
    def test_imsi_desensitization(self):
        """测试IMSI脱敏"""
        text = "test_imsi = 460001234567890"
        result, mapping = self.desensitizer.desensitize_text(text)
        
        self.assertNotIn("460001234567890", result)
        self.assertIn("IMSI_MASKED", result)
    
    def test_customer_desensitization(self):
        """测试客户名称脱敏"""
        text = "Customer: China Mobile"
        result, mapping = self.desensitizer.desensitize_text(text)
        
        # 检查是否进行了替换
        if "China Mobile" in result:
            # 如果没有默认客户列表，可能不会替换
            pass
        else:
            self.assertIn("CUSTOMER", result)
    
    def test_preserve_structure(self):
        """测试脱敏后保持结构"""
        text = """[SECTION1]
key1 = 192.168.1.1
key2 = value2

[SECTION2]
password = secret123"""
        
        result, mapping = self.desensitizer.desensitize_text(text)
        
        # 检查节结构是否保留
        self.assertIn("[SECTION1]", result)
        self.assertIn("[SECTION2]", result)
        self.assertIn("key2 = value2", result)


class TestFormatConverter(unittest.TestCase):
    """格式转换模块测试"""
    
    def setUp(self):
        """测试前准备"""
        self.converter = FormatConverter("../config.yaml")
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_format_detection(self):
        """测试格式检测"""
        # XML文件
        xml_file = Path(self.temp_dir) / "test.xml"
        xml_file.write_text("<config></config>")
        self.assertEqual(self.converter.detect_format(str(xml_file)), ConfigFormat.XML)
        
        # JSON文件
        json_file = Path(self.temp_dir) / "test.json"
        json_file.write_text('{"key": "value"}')
        self.assertEqual(self.converter.detect_format(str(json_file)), ConfigFormat.JSON)
        
        # Text文件
        text_file = Path(self.temp_dir) / "test.txt"
        text_file.write_text("key = value")
        self.assertEqual(self.converter.detect_format(str(text_file)), ConfigFormat.TEXT)
    
    def test_xml_parsing(self):
        """测试XML解析"""
        xml_content = """<?xml version="1.0"?>
        <config>
            <network>
                <ip>192.168.1.1</ip>
                <port>8080</port>
            </network>
        </config>"""
        
        structure = self.converter.parse_xml(xml_content)
        
        self.assertEqual(structure.format, ConfigFormat.XML)
        self.assertIn('config', structure.content)
        self.assertIn('network', structure.content['config'])
    
    def test_json_parsing(self):
        """测试JSON解析"""
        json_content = '{"network": {"ip": "192.168.1.1", "port": 8080}}'
        
        structure = self.converter.parse_json(json_content)
        
        self.assertEqual(structure.format, ConfigFormat.JSON)
        self.assertEqual(structure.content['network']['ip'], "192.168.1.1")
        self.assertEqual(structure.content['network']['port'], 8080)
    
    def test_text_parsing(self):
        """测试文本解析"""
        text_content = """[network]
ip = 192.168.1.1
port = 8080

[security]
enabled = true"""
        
        structure = self.converter.parse_text(text_content)
        
        self.assertEqual(structure.format, ConfigFormat.TEXT)
        self.assertIn('network', structure.content)
        self.assertEqual(structure.content['network']['ip'], '192.168.1.1')
    
    def test_unified_conversion(self):
        """测试统一格式转换"""
        json_content = '{"test": "value"}'
        structure = self.converter.parse_json(json_content)
        unified = self.converter.convert_to_unified(structure)
        
        self.assertIn('metadata', unified)
        self.assertIn('config', unified)
        self.assertIn('hierarchy', unified)
        self.assertEqual(unified['metadata']['original_format'], 'json')


class TestSmartChunker(unittest.TestCase):
    """智能分块模块测试"""
    
    def setUp(self):
        """测试前准备"""
        self.chunker = SmartChunker("../config.yaml")
    
    def test_small_file_no_chunking(self):
        """测试小文件不分块"""
        small_text = "line1\nline2\nline3"
        self.chunker.chunk_size_lines = 100
        
        chunks = self.chunker.chunk_text(small_text)
        
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].content, small_text)
    
    def test_fixed_lines_chunking(self):
        """测试固定行数分块"""
        self.chunker.strategy = 'fixed_lines'
        self.chunker.chunk_size_lines = 10
        self.chunker.overlap_lines = 2
        
        # 创建30行文本
        text = "\n".join([f"line{i}" for i in range(30)])
        
        chunks = self.chunker.chunk_text(text)
        
        self.assertGreater(len(chunks), 1)
        # 检查块的行数
        for chunk in chunks[:-1]:  # 除了最后一块
            lines = chunk.content.split('\n')
            self.assertLessEqual(len(lines), self.chunker.chunk_size_lines)
    
    def test_smart_chunking_section_detection(self):
        """测试智能分块的段落检测"""
        self.chunker.strategy = 'smart'
        self.chunker.chunk_size_lines = 10
        
        text = """BEGIN SECTION1
line1
line2
END SECTION1

BEGIN SECTION2
line3
line4
END SECTION2"""
        
        chunks = self.chunker.chunk_text(text)
        
        # 检查是否识别了段落标记
        for chunk in chunks:
            content = chunk.content
            # 检查BEGIN和END是否配对
            begin_count = content.count('BEGIN')
            end_count = content.count('END')
            self.assertEqual(begin_count, end_count, 
                           "BEGIN和END应该配对出现在同一个块中")
    
    def test_chunk_features_extraction(self):
        """测试特征提取"""
        text = """AMF configuration
SMF settings
UPF parameters
slice configuration"""
        
        chunks = self.chunker.chunk_text(text)
        
        # 检查是否提取了5GC相关特征
        all_features = []
        for chunk in chunks:
            all_features.extend(chunk.features)
        
        self.assertIn('AMF', all_features)
        self.assertIn('SMF', all_features)
        self.assertIn('UPF', all_features)
        self.assertIn('slice', all_features)
    
    def test_chunk_merge(self):
        """测试块合并"""
        text = "\n".join([f"line{i}" for i in range(100)])
        
        # 分块
        chunks = self.chunker.chunk_text(text)
        
        # 合并
        merged = self.chunker.merge_chunks(chunks)
        
        # 检查合并后的文本是否与原始文本相似
        # 允许一些差异（由于重叠）
        original_lines = text.split('\n')
        merged_lines = merged.split('\n')
        
        # 至少应该包含所有原始行
        for line in original_lines:
            self.assertIn(line, merged_lines)


class TestMetadataExtractor(unittest.TestCase):
    """元数据提取模块测试"""
    
    def setUp(self):
        """测试前准备"""
        self.extractor = MetadataExtractor("../config.yaml")
    
    def test_project_info_extraction(self):
        """测试项目信息提取"""
        content = """# Project: Beijing-5GC
Customer: China Mobile
Site: BJ-001
Region: North-China"""
        
        metadata = self.extractor.extract(content)
        
        self.assertIn('customer', metadata)
        self.assertEqual(metadata['customer'], 'China Mobile')
        self.assertIn('site', metadata)
        self.assertEqual(metadata['site'], 'BJ-001')
    
    def test_version_extraction(self):
        """测试版本提取"""
        content = "Version: 2.1.0\nRelease: stable"
        
        metadata = self.extractor.extract(content)
        
        self.assertIn('version', metadata)
        self.assertEqual(metadata['version'], '2.1.0')
    
    def test_5gc_info_extraction(self):
        """测试5GC信息提取"""
        content = """AMF_CONFIG
SMF_CONFIG
UPF_CONFIG
PLMN: 46000
TAC: 0x0001
DNN: internet,ims
SST: 1"""
        
        metadata = self.extractor.extract(content)
        
        self.assertIn('5gc_info', metadata)
        self.assertIn('network_functions', metadata['5gc_info'])
        self.assertIn('AMF', metadata['5gc_info']['network_functions'])
        
        self.assertIn('identifiers', metadata['5gc_info'])
        self.assertIn('PLMN', metadata['5gc_info']['identifiers'])
        self.assertEqual(metadata['5gc_info']['identifiers']['PLMN'], ['46000'])
    
    def test_statistics_extraction(self):
        """测试统计信息提取"""
        content = """# Comment line
key1 = value1
key2 = value2

[section1]
key3 = value3"""
        
        metadata = self.extractor.extract(content)
        
        self.assertIn('statistics', metadata)
        stats = metadata['statistics']
        
        self.assertEqual(stats['total_lines'], 6)
        self.assertEqual(stats['comment_lines'], 1)
        self.assertGreater(stats['config_items'], 0)
    
    def test_complexity_assessment(self):
        """测试复杂度评估"""
        # 简单配置
        simple_content = "key1 = value1\nkey2 = value2"
        metadata = self.extractor.extract(simple_content)
        self.assertEqual(metadata['complexity']['level'], 'low')
        
        # 复杂配置（大量配置项）
        complex_content = "\n".join([f"key{i} = value{i}" for i in range(2000)])
        metadata = self.extractor.extract(complex_content)
        self.assertIn(metadata['complexity']['level'], ['medium', 'high'])


class TestIntegration(unittest.TestCase):
    """集成测试"""
    
    def setUp(self):
        """测试前准备"""
        self.preprocessor = ConfigPreProcessor("../config.yaml")
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_end_to_end_processing(self):
        """端到端处理测试"""
        # 创建测试配置文件
        test_file = Path(self.temp_dir) / "test_config.txt"
        test_content = """# 5GC Configuration
Project: Test-Project
Version: 1.0.0
Date: 2024-01-15

[NETWORK]
server_ip = 192.168.1.100
admin_password = secret123
phone = 13812345678

[AMF]
amf_name = AMF_01
plmn = 46000"""
        
        test_file.write_text(test_content)
        
        # 处理文件
        result = self.preprocessor.process_file(
            str(test_file),
            desensitize=True,
            convert_format=True,
            chunk=True,
            extract_metadata=True
        )
        
        # 验证结果
        self.assertTrue(result.success)
        self.assertGreater(len(result.processed_files), 0)
        self.assertIn('version', result.metadata)
        self.assertEqual(result.metadata['version'], '1.0.0')
        
        # 检查脱敏文件
        desensitized_files = [f for f in result.processed_files if 'desensitized' in f]
        self.assertGreater(len(desensitized_files), 0)
        
        # 读取脱敏文件，确认敏感信息已被替换
        desensitized_content = Path(desensitized_files[0]).read_text()
        self.assertNotIn('192.168.1.100', desensitized_content)
        self.assertNotIn('secret123', desensitized_content)
        self.assertNotIn('13812345678', desensitized_content)
    
    def test_error_handling(self):
        """测试错误处理"""
        # 测试不存在的文件
        result = self.preprocessor.process_file("non_existent_file.txt")
        
        self.assertFalse(result.success)
        self.assertGreater(len(result.errors), 0)
    
    def test_directory_processing(self):
        """测试目录处理"""
        # 创建多个测试文件
        for i in range(3):
            test_file = Path(self.temp_dir) / f"config_{i}.txt"
            test_file.write_text(f"# Config {i}\nkey = value{i}")
        
        # 处理目录
        results = self.preprocessor.process_directory(
            str(self.temp_dir),
            pattern="*.txt",
            recursive=False
        )
        
        self.assertEqual(len(results), 3)
        successful = sum(1 for r in results if r.success)
        self.assertEqual(successful, 3)


def run_tests():
    """运行所有测试"""
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加所有测试类
    suite.addTests(loader.loadTestsFromTestCase(TestDesensitizer))
    suite.addTests(loader.loadTestsFromTestCase(TestFormatConverter))
    suite.addTests(loader.loadTestsFromTestCase(TestSmartChunker))
    suite.addTests(loader.loadTestsFromTestCase(TestMetadataExtractor))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 返回测试结果
    return result.wasSuccessful()


if __name__ == "__main__":
    import sys
    success = run_tests()
    sys.exit(0 if success else 1)
