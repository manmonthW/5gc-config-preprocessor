"""
配置文件格式转换模块
支持XML、JSON、Text等多种格式的转换和标准化
"""

import json
import yaml
import re
import chardet

try:
    import xmltodict
    XML_SUPPORT = True
except ImportError:
    XML_SUPPORT = False
    xmltodict = None
from typing import Dict, Any, Union, List
from pathlib import Path
import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class ConfigFormat(Enum):
    """配置文件格式枚举"""
    XML = "xml"
    JSON = "json"
    YAML = "yaml"
    TEXT = "text"
    CONF = "conf"
    INI = "ini"
    UNKNOWN = "unknown"

@dataclass
class ConfigStructure:
    """配置文件结构表示"""
    format: ConfigFormat
    content: Any
    metadata: Dict
    hierarchy: Dict
    line_mapping: Dict  # 行号映射

class FormatConverter:
    """配置文件格式转换器"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """初始化转换器"""
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        self.supported_formats = self.config['file_processing']['supported_formats']
        self.encoding_detection = self.config['file_processing']['encoding_detection']
        self.default_encoding = self.config['file_processing']['default_encoding']
    
    def detect_format(self, file_path: str) -> ConfigFormat:
        """
        检测文件格式
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件格式枚举
        """
        file_path = Path(file_path)
        extension = file_path.suffix.lower().lstrip('.')
        
        # 通过扩展名判断
        if extension in ['xml']:
            return ConfigFormat.XML
        elif extension in ['json']:
            return ConfigFormat.JSON
        elif extension in ['yaml', 'yml']:
            return ConfigFormat.YAML
        elif extension in ['ini', 'cfg']:
            return ConfigFormat.INI
        elif extension in ['conf', 'config']:
            return ConfigFormat.CONF
        elif extension in ['txt', 'text', 'log']:
            return ConfigFormat.TEXT
        
        # 通过内容判断
        try:
            with open(file_path, 'r', encoding=self.default_encoding) as f:
                content = f.read(1024)  # 读取前1KB判断
                
            if content.strip().startswith('<'):
                return ConfigFormat.XML
            elif content.strip().startswith('{') or content.strip().startswith('['):
                return ConfigFormat.JSON
            elif ':' in content and '-' in content:
                return ConfigFormat.YAML
            else:
                return ConfigFormat.TEXT
        except:
            return ConfigFormat.UNKNOWN
    
    def detect_encoding(self, file_path: str) -> str:
        """
        检测文件编码
        
        Args:
            file_path: 文件路径
            
        Returns:
            编码格式
        """
        if not self.encoding_detection:
            return self.default_encoding
        
        with open(file_path, 'rb') as f:
            raw_data = f.read(10000)  # 读取前10KB
        
        result = chardet.detect(raw_data)
        encoding = result['encoding']
        confidence = result['confidence']
        
        if confidence > 0.7 and encoding:
            logger.info(f"检测到编码: {encoding} (置信度: {confidence:.2f})")
            return encoding
        else:
            logger.warning(f"编码检测置信度低，使用默认编码: {self.default_encoding}")
            return self.default_encoding
    
    def read_file(self, file_path: str) -> str:
        """
        读取文件内容
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件内容
        """
        encoding = self.detect_encoding(file_path)
        
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()
            return content
        except UnicodeDecodeError:
            logger.error(f"使用{encoding}编码读取失败，尝试其他编码")
            # 尝试其他常见编码
            for alt_encoding in ['utf-8', 'gbk', 'gb2312', 'latin-1']:
                try:
                    with open(file_path, 'r', encoding=alt_encoding) as f:
                        content = f.read()
                    logger.info(f"成功使用{alt_encoding}编码读取")
                    return content
                except:
                    continue
            raise ValueError(f"无法读取文件: {file_path}")
    
    def parse_xml(self, content: str) -> ConfigStructure:
        """解析XML格式配置"""
        if not XML_SUPPORT:
            raise ValueError("XML support not available - xmltodict module not installed")
        
        try:
            # 解析XML为字典
            parsed = xmltodict.parse(content)
            
            # 提取层级结构
            hierarchy = self._extract_hierarchy(parsed)
            
            # 创建行映射
            line_mapping = self._create_line_mapping_xml(content)
            
            return ConfigStructure(
                format=ConfigFormat.XML,
                content=parsed,
                metadata={'type': 'xml', 'root_element': list(parsed.keys())[0] if parsed else None},
                hierarchy=hierarchy,
                line_mapping=line_mapping
            )
        except Exception as e:
            logger.error(f"XML解析失败: {e}")
            raise
    
    def parse_json(self, content: str) -> ConfigStructure:
        """解析JSON格式配置"""
        try:
            # 解析JSON
            parsed = json.loads(content)
            
            # 提取层级结构
            hierarchy = self._extract_hierarchy(parsed)
            
            # 创建行映射
            line_mapping = self._create_line_mapping_json(content)
            
            return ConfigStructure(
                format=ConfigFormat.JSON,
                content=parsed,
                metadata={'type': 'json', 'is_array': isinstance(parsed, list)},
                hierarchy=hierarchy,
                line_mapping=line_mapping
            )
        except Exception as e:
            logger.error(f"JSON解析失败: {e}")
            raise

    def parse_yaml(self, content: str) -> ConfigStructure:
        """解析YAML格式配置"""
        try:
            parsed = yaml.safe_load(content)
        except Exception as e:
            logger.error(f"YAML解析失败: {e}")
            raise

        if parsed is None:
            parsed = {}
        elif isinstance(parsed, (str, int, float, bool)):
            # 保留标量内容，但转换为字典以便统一处理
            parsed = {'value': parsed}

        hierarchy = self._extract_hierarchy(parsed)
        line_mapping = self._create_line_mapping_yaml(content)

        metadata = {'type': 'yaml'}
        if isinstance(parsed, dict):
            metadata['root_keys'] = list(parsed.keys())
        elif isinstance(parsed, list):
            metadata['items'] = len(parsed)

        return ConfigStructure(
            format=ConfigFormat.YAML,
            content=parsed,
            metadata=metadata,
            hierarchy=hierarchy,
            line_mapping=line_mapping
        )
    
    def parse_text(self, content: str) -> ConfigStructure:
        """解析文本格式配置"""
        lines = content.split('\n')
        
        # 智能解析文本配置
        parsed_config = {}
        current_section = 'default'
        line_mapping = {}
        
        for line_no, line in enumerate(lines, 1):
            line = line.strip()
            
            # 跳过空行和注释
            if not line or line.startswith('#') or line.startswith(';'):
                continue
            
            # 检测节标题 [section]
            section_match = re.match(r'\[([^\]]+)\]', line)
            if section_match:
                current_section = section_match.group(1)
                if current_section not in parsed_config:
                    parsed_config[current_section] = {}
                line_mapping[f"section_{current_section}"] = line_no
                continue
            
            # 检测键值对
            # 支持多种格式: key=value, key:value, key value
            kv_patterns = [
                r'^([^=]+)=(.+)$',  # key=value
                r'^([^:]+):(.+)$',  # key:value
                r'^(\S+)\s+(.+)$'   # key value
            ]
            
            for pattern in kv_patterns:
                match = re.match(pattern, line)
                if match:
                    key = match.group(1).strip()
                    value = match.group(2).strip()
                    
                    if current_section not in parsed_config:
                        parsed_config[current_section] = {}
                    
                    parsed_config[current_section][key] = value
                    line_mapping[f"{current_section}.{key}"] = line_no
                    break
        
        # 提取层级结构
        hierarchy = self._extract_hierarchy(parsed_config)
        
        return ConfigStructure(
            format=ConfigFormat.TEXT,
            content=parsed_config,
            metadata={'type': 'text', 'sections': list(parsed_config.keys())},
            hierarchy=hierarchy,
            line_mapping=line_mapping
        )
    
    def parse_ini(self, content: str) -> ConfigStructure:
        """解析INI格式配置"""
        import configparser
        
        parser = configparser.ConfigParser()
        parser.read_string(content)
        
        # 转换为字典
        parsed_config = {}
        for section in parser.sections():
            parsed_config[section] = dict(parser[section])
        
        # 添加默认section
        if parser.defaults():
            parsed_config['DEFAULT'] = dict(parser.defaults())
        
        # 创建行映射
        line_mapping = self._create_line_mapping_ini(content)
        
        # 提取层级结构
        hierarchy = self._extract_hierarchy(parsed_config)
        
        return ConfigStructure(
            format=ConfigFormat.INI,
            content=parsed_config,
            metadata={'type': 'ini', 'sections': list(parsed_config.keys())},
            hierarchy=hierarchy,
            line_mapping=line_mapping
        )
    
    def _extract_hierarchy(self, data: Any, prefix: str = "") -> Dict:
        """
        提取配置的层级结构
        
        Args:
            data: 配置数据
            prefix: 键前缀
            
        Returns:
            层级结构字典
        """
        hierarchy = {}
        
        if isinstance(data, dict):
            for key, value in data.items():
                full_key = f"{prefix}.{key}" if prefix else key
                
                if isinstance(value, (dict, list)):
                    hierarchy[full_key] = {
                        'type': 'container',
                        'children': self._extract_hierarchy(value, full_key)
                    }
                else:
                    hierarchy[full_key] = {
                        'type': 'leaf',
                        'value_type': type(value).__name__
                    }
        
        elif isinstance(data, list):
            for idx, item in enumerate(data):
                full_key = f"{prefix}[{idx}]"
                
                if isinstance(item, (dict, list)):
                    hierarchy[full_key] = {
                        'type': 'container',
                        'children': self._extract_hierarchy(item, full_key)
                    }
                else:
                    hierarchy[full_key] = {
                        'type': 'leaf',
                        'value_type': type(item).__name__
                    }
        
        return hierarchy
    
    def _create_line_mapping_xml(self, content: str) -> Dict:
        """创建XML内容的行映射"""
        line_mapping = {}
        lines = content.split('\n')
        
        for line_no, line in enumerate(lines, 1):
            # 提取XML标签
            tag_match = re.search(r'<(\w+)[^>]*>', line)
            if tag_match:
                tag_name = tag_match.group(1)
                if tag_name not in line_mapping:
                    line_mapping[tag_name] = []
                line_mapping[tag_name].append(line_no)
        
        return line_mapping
    
    def _create_line_mapping_json(self, content: str) -> Dict:
        """创建JSON内容的行映射"""
        line_mapping = {}
        lines = content.split('\n')
        
        for line_no, line in enumerate(lines, 1):
            # 提取JSON键
            key_match = re.search(r'"([^"]+)"\s*:', line)
            if key_match:
                key_name = key_match.group(1)
                if key_name not in line_mapping:
                    line_mapping[key_name] = []
                line_mapping[key_name].append(line_no)
        
        return line_mapping
    
    def _create_line_mapping_ini(self, content: str) -> Dict:
        """创建INI内容的行映射"""
        line_mapping = {}
        lines = content.split('\n')
        current_section = 'DEFAULT'
        
        for line_no, line in enumerate(lines, 1):
            line = line.strip()
            
            # 节标题
            if line.startswith('[') and line.endswith(']'):
                current_section = line[1:-1]
                line_mapping[f"section_{current_section}"] = line_no
            # 键值对
            elif '=' in line and not line.startswith('#'):
                key = line.split('=')[0].strip()
                line_mapping[f"{current_section}.{key}"] = line_no
        
        return line_mapping

    def _create_line_mapping_yaml(self, content: str) -> Dict:
        """创建YAML内容的行映射"""
        line_mapping = {}
        lines = content.split('\n')
        for line_no, raw_line in enumerate(lines, 1):
            stripped = raw_line.strip()
            if not stripped or stripped.startswith('#'):
                continue

            if stripped.startswith('- '):
                candidate = stripped[2:].strip()
                if candidate and ':' in candidate:
                    key = candidate.split(':', 1)[0].strip().strip('\'"')
                else:
                    key = 'list_item'
            elif ':' in stripped:
                key = stripped.split(':', 1)[0].strip().strip('\'"')
            else:
                continue

            if key:
                line_mapping.setdefault(key, []).append(line_no)
        return line_mapping
    
    def convert_to_unified(self, structure: ConfigStructure) -> Dict:
        """
        转换为统一的内部格式
        
        Args:
            structure: 配置结构
            
        Returns:
            统一格式的配置字典
        """
        unified = {
            'metadata': {
                'original_format': structure.format.value,
                **structure.metadata
            },
            'config': self._normalize_config(structure.content),
            'hierarchy': structure.hierarchy,
            'line_mapping': structure.line_mapping
        }
        
        return unified
    
    def _normalize_config(self, config: Any) -> Dict:
        """
        标准化配置内容
        
        Args:
            config: 原始配置
            
        Returns:
            标准化的配置
        """
        if isinstance(config, dict):
            return {k: self._normalize_config(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._normalize_config(item) for item in config]
        else:
            # 转换为字符串
            return str(config) if config is not None else ""
    
    def save_unified(self, unified: Dict, output_path: str, format: str = 'json'):
        """
        保存统一格式的配置
        
        Args:
            unified: 统一格式配置
            output_path: 输出路径
            format: 输出格式
        """
        output_path = Path(output_path)
        
        if format == 'json':
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(unified, f, ensure_ascii=False, indent=2)
        elif format == 'yaml':
            with open(output_path, 'w', encoding='utf-8') as f:
                yaml.dump(unified, f, allow_unicode=True, default_flow_style=False)
        else:
            raise ValueError(f"不支持的输出格式: {format}")
        
        logger.info(f"统一格式配置已保存: {output_path}")
    
    def process_file(self, file_path: str) -> Dict:
        """
        处理配置文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            统一格式的配置
        """
        # 检测格式
        format_type = self.detect_format(file_path)
        logger.info(f"检测到文件格式: {format_type.value}")
        
        # 读取内容
        content = self.read_file(file_path)
        
        # 解析内容
        if format_type == ConfigFormat.XML:
            structure = self.parse_xml(content)
        elif format_type == ConfigFormat.JSON:
            structure = self.parse_json(content)
        elif format_type == ConfigFormat.YAML:
            structure = self.parse_yaml(content)
        elif format_type == ConfigFormat.INI:
            structure = self.parse_ini(content)
        elif format_type in [ConfigFormat.TEXT, ConfigFormat.CONF]:
            structure = self.parse_text(content)
        else:
            raise ValueError(f"不支持的文件格式: {format_type.value}")
        
        # 转换为统一格式
        unified = self.convert_to_unified(structure)
        
        return unified


if __name__ == "__main__":
    # 测试格式转换
    converter = FormatConverter("../config.yaml")
    
    # 创建测试文件
    test_files = {
        'test_config.xml': """<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <network>
        <interface>eth0</interface>
        <ip>192.168.1.100</ip>
        <netmask>255.255.255.0</netmask>
    </network>
    <services>
        <service name="web">
            <port>8080</port>
            <enabled>true</enabled>
        </service>
    </services>
</configuration>""",
        
        'test_config.json': """{
    "network": {
        "interface": "eth0",
        "ip": "192.168.1.100",
        "netmask": "255.255.255.0"
    },
    "services": [
        {
            "name": "web",
            "port": 8080,
            "enabled": true
        }
    ]
}""",
        
        'test_config.ini': """[network]
interface = eth0
ip = 192.168.1.100
netmask = 255.255.255.0

[service_web]
port = 8080
enabled = true"""
    }
    
    # 测试各种格式
    for filename, content in test_files.items():
        print(f"\n处理文件: {filename}")
        print("="*50)
        
        # 保存测试文件
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # 处理文件
        try:
            unified = converter.process_file(filename)
            print(f"原始格式: {unified['metadata']['original_format']}")
            print(f"配置节: {list(unified['config'].keys())}")
            print(f"层级结构示例: {list(unified['hierarchy'].keys())[:3]}")
            
            # 保存统一格式
            output_file = f"{filename}_unified.json"
            converter.save_unified(unified, output_file)
            print(f"已保存至: {output_file}")
        except Exception as e:
            print(f"处理失败: {e}")
        
        # 清理测试文件
        Path(filename).unlink(missing_ok=True)
