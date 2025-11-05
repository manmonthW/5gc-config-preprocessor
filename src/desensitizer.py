"""
配置文件脱敏模块
用于识别和替换5GC配置文件中的敏感信息
"""

import re
import hashlib
import json
from typing import Dict, List, Any, Tuple
from pathlib import Path
import yaml
import logging

logger = logging.getLogger(__name__)

class ConfigDesensitizer:
    """配置文件脱敏处理器"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        初始化脱敏器
        
        Args:
            config_path: 配置文件路径
        """
        self.config = self._load_config(config_path)
        self.patterns = self._compile_patterns()
        self.mapping = {}  # 脱敏映射表
        self.statistics = {
            'total_replacements': 0,
            'by_type': {}
        }
    
    def _load_config(self, config_path: str) -> Dict:
        """加载配置文件"""
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config.get('desensitization', {})
    
    def _compile_patterns(self) -> Dict:
        """编译正则表达式模式"""
        compiled = {}
        patterns = self.config.get('patterns', {})
        
        for key, pattern_config in patterns.items():
            if 'pattern' in pattern_config:
                try:
                    compiled[key] = {
                        'regex': re.compile(pattern_config['pattern']),
                        'replacement': pattern_config.get('replacement', 'MASKED'),
                        'config': pattern_config
                    }
                    logger.info(f"已编译模式: {key}")
                except re.error as e:
                    logger.error(f"编译模式 {key} 失败: {e}")
        
        return compiled
    
    def desensitize_text(self, text: str, preserve_structure: bool = True) -> Tuple[str, Dict]:
        """
        对文本进行脱敏处理
        
        Args:
            text: 输入文本
            preserve_structure: 是否保留结构信息
            
        Returns:
            脱敏后的文本和映射关系
        """
        if not self.config.get('enabled', True):
            return text, {}
        
        result = text
        local_mapping = {}
        
        # 1. IP地址脱敏
        result, ip_map = self._desensitize_ip_addresses(result)
        local_mapping['ip_addresses'] = ip_map
        
        # 2. 电话号码脱敏
        result, phone_map = self._desensitize_phone_numbers(result)
        local_mapping['phone_numbers'] = phone_map
        
        # 3. IMSI/IMEI脱敏
        result, imsi_map = self._desensitize_identifiers(result, 'imsi')
        local_mapping['imsi'] = imsi_map
        
        result, imei_map = self._desensitize_identifiers(result, 'imei')
        local_mapping['imei'] = imei_map
        
        # 4. 密码脱敏
        result, pwd_map = self._desensitize_passwords(result)
        local_mapping['passwords'] = pwd_map
        
        # 5. 客户名称脱敏
        result, customer_map = self._desensitize_customer_names(result)
        local_mapping['customers'] = customer_map
        
        # 6. URL脱敏
        result, url_map = self._desensitize_urls(result)
        local_mapping['urls'] = url_map
        
        # 更新统计信息
        self._update_statistics(local_mapping)
        
        return result, local_mapping
    
    def _desensitize_ip_addresses(self, text: str) -> Tuple[str, Dict]:
        """IP地址脱敏"""
        mapping = {}
        if 'ip_addresses' not in self.patterns:
            return text, mapping
        
        pattern_info = self.patterns['ip_addresses']
        regex = pattern_info['regex']
        config = pattern_info['config']
        
        def replace_ip(match):
            ip = match.group(0)
            if ip not in mapping:
                if config.get('keep_subnet', False):
                    # 保留前两段
                    parts = ip.split('.')
                    masked = f"{parts[0]}.{parts[1]}.xxx.xxx"
                else:
                    masked = pattern_info['replacement']
                mapping[ip] = masked
            return mapping[ip]
        
        result = regex.sub(replace_ip, text)
        return result, mapping
    
    def _desensitize_phone_numbers(self, text: str) -> Tuple[str, Dict]:
        """电话号码脱敏"""
        mapping = {}
        if 'phone_numbers' not in self.patterns:
            return text, mapping
        
        pattern_info = self.patterns['phone_numbers']
        regex = pattern_info['regex']
        
        def replace_phone(match):
            phone = match.group(0)
            if phone not in mapping:
                # 保留前3位和后2位
                masked = f"{phone[:3]}****{phone[-2:]}"
                mapping[phone] = masked
            return mapping[phone]
        
        result = regex.sub(replace_phone, text)
        return result, mapping
    
    def _desensitize_identifiers(self, text: str, id_type: str) -> Tuple[str, Dict]:
        """IMSI/IMEI等标识符脱敏"""
        mapping = {}
        if id_type not in self.patterns:
            return text, mapping
        
        pattern_info = self.patterns[id_type]
        regex = pattern_info['regex']
        
        def replace_id(match):
            identifier = match.group(0)
            if identifier not in mapping:
                # 生成哈希映射
                hash_val = hashlib.md5(identifier.encode()).hexdigest()[:8]
                masked = f"{pattern_info['replacement']}_{hash_val}"
                mapping[identifier] = masked
            return mapping[identifier]
        
        result = regex.sub(replace_id, text)
        return result, mapping
    
    def _desensitize_passwords(self, text: str) -> Tuple[str, Dict]:
        """密码字段脱敏"""
        mapping = {}
        patterns_config = self.config.get('patterns', {}).get('passwords', {})
        keywords = patterns_config.get('keywords', [])
        
        result = text
        for keyword in keywords:
            # 查找密码模式: keyword=value 或 keyword: value
            pattern = rf'({keyword})\s*[=:]\s*([^\s,;]+)'
            regex = re.compile(pattern, re.IGNORECASE)
            
            def replace_pwd(match):
                full_match = match.group(0)
                key = match.group(1)
                value = match.group(2)
                masked_value = patterns_config.get('replacement', '********')
                masked = f"{key}={masked_value}"
                mapping[full_match] = masked
                return masked
            
            result = regex.sub(replace_pwd, result)
        
        return result, mapping
    
    def _desensitize_customer_names(self, text: str) -> Tuple[str, Dict]:
        """客户名称脱敏"""
        mapping = {}
        patterns_config = self.config.get('patterns', {}).get('customer_names', {})
        
        # 加载客户关键词列表
        keywords_file = patterns_config.get('keywords_file')
        if keywords_file and Path(keywords_file).exists():
            with open(keywords_file, 'r', encoding='utf-8') as f:
                keywords = [line.strip() for line in f if line.strip()]
        else:
            # 使用默认的运营商名称模式
            keywords = [
                'China Mobile', 'China Unicom', 'China Telecom',
                'Vodafone', 'Orange', 'T-Mobile', 'AT&T', 'Verizon',
                '中国移动', '中国联通', '中国电信'
            ]
        
        result = text
        for idx, keyword in enumerate(keywords):
            if keyword in result:
                replacement = f"CUSTOMER_{idx+1:03d}"
                result = result.replace(keyword, replacement)
                mapping[keyword] = replacement
        
        return result, mapping
    
    def _desensitize_urls(self, text: str) -> Tuple[str, Dict]:
        """URL脱敏"""
        mapping = {}
        if 'urls' not in self.patterns:
            return text, mapping
        
        pattern_info = self.patterns['urls']
        regex = pattern_info['regex']
        config = pattern_info['config']
        
        def replace_url(match):
            url = match.group(0)
            if url not in mapping:
                if config.get('keep_domain', False):
                    # 提取并脱敏域名
                    import urllib.parse
                    parsed = urllib.parse.urlparse(url)
                    domain_parts = parsed.netloc.split('.')
                    if len(domain_parts) > 1:
                        masked_domain = f"masked.{domain_parts[-1]}"
                    else:
                        masked_domain = "masked.domain"
                    masked = f"{parsed.scheme}://{masked_domain}/path"
                else:
                    masked = pattern_info['replacement']
                mapping[url] = masked
            return mapping[url]
        
        result = regex.sub(replace_url, text)
        return result, mapping
    
    def _update_statistics(self, mapping: Dict):
        """更新脱敏统计信息"""
        for category, items in mapping.items():
            if items:
                self.statistics['by_type'][category] = \
                    self.statistics['by_type'].get(category, 0) + len(items)
                self.statistics['total_replacements'] += len(items)
    
    def save_mapping(self, filepath: str):
        """保存脱敏映射表"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.mapping, f, ensure_ascii=False, indent=2)
        logger.info(f"脱敏映射表已保存至: {filepath}")
    
    def get_statistics(self) -> Dict:
        """获取脱敏统计信息"""
        return self.statistics
    
    def process_file(self, input_path: str, output_path: str = None) -> str:
        """
        处理整个配置文件
        
        Args:
            input_path: 输入文件路径
            output_path: 输出文件路径
            
        Returns:
            处理后的文件路径
        """
        # 读取文件
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 脱敏处理
        desensitized_content, mapping = self.desensitize_text(content)
        
        # 更新总映射表
        for key, value in mapping.items():
            if key not in self.mapping:
                self.mapping[key] = {}
            self.mapping[key].update(value)
        
        # 保存结果
        if output_path is None:
            output_path = input_path.replace('.', '_desensitized.')
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(desensitized_content)
        
        logger.info(f"文件已脱敏: {input_path} -> {output_path}")
        logger.info(f"脱敏统计: {self.statistics}")
        
        return output_path


if __name__ == "__main__":
    # 测试脱敏模块
    desensitizer = ConfigDesensitizer("config.yaml")
    
    # 测试文本
    test_text = """
    # 5GC Configuration File
    # Customer: China Mobile
    # Site: Beijing-001
    # Date: 2024-01-15
    
    [Network Configuration]
    server_ip = 192.168.1.100
    gateway_ip = 192.168.1.1
    dns_server = 8.8.8.8
    
    [Security]
    admin_password = MySecretPass123
    api_key = sk-1234567890abcdef
    
    [Subscriber Info]
    test_imsi = 460001234567890
    test_imei = 861234567890123
    test_phone = 13812345678
    
    [Service URLs]
    api_endpoint = https://api.customer.com/v1/service
    callback_url = https://callback.example.com/notify
    """
    
    # 执行脱敏
    result, mapping = desensitizer.desensitize_text(test_text)
    
    print("原始文本:")
    print(test_text)
    print("\n" + "="*50 + "\n")
    print("脱敏后文本:")
    print(result)
    print("\n" + "="*50 + "\n")
    print("脱敏映射:")
    print(json.dumps(mapping, indent=2, ensure_ascii=False))
    print("\n" + "="*50 + "\n")
    print("统计信息:")
    print(json.dumps(desensitizer.get_statistics(), indent=2))
