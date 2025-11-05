"""
元数据提取模块
用于从配置文件中提取项目信息、版本、时间戳等元数据
"""

import re
import yaml
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
from collections import Counter

logger = logging.getLogger(__name__)

class MetadataExtractor:
    """配置文件元数据提取器"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """初始化元数据提取器"""
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        self.config = config.get('metadata', {})
        
        # 编译正则表达式
        self.project_patterns = [
            re.compile(p) for p in self.config.get('project_patterns', [])
        ]
        self.version_patterns = [
            re.compile(p) for p in self.config.get('version_patterns', [])
        ]
        self.timestamp_patterns = [
            re.compile(p) for p in self.config.get('timestamp_patterns', [])
        ]
        
        # 5GC特定模式
        self.nf_patterns = self._init_nf_patterns()
        self.feature_patterns = self._init_feature_patterns()
    
    def _init_nf_patterns(self) -> Dict[str, re.Pattern]:
        """初始化网元识别模式"""
        patterns = {
            'AMF': re.compile(r'\b(AMF|amf)[_\-]?\w*', re.IGNORECASE),
            'SMF': re.compile(r'\b(SMF|smf)[_\-]?\w*', re.IGNORECASE),
            'UPF': re.compile(r'\b(UPF|upf)[_\-]?\w*', re.IGNORECASE),
            'NRF': re.compile(r'\b(NRF|nrf)[_\-]?\w*', re.IGNORECASE),
            'UDM': re.compile(r'\b(UDM|udm)[_\-]?\w*', re.IGNORECASE),
            'AUSF': re.compile(r'\b(AUSF|ausf)[_\-]?\w*', re.IGNORECASE),
            'NSSF': re.compile(r'\b(NSSF|nssf)[_\-]?\w*', re.IGNORECASE),
            'PCF': re.compile(r'\b(PCF|pcf)[_\-]?\w*', re.IGNORECASE),
            'BSF': re.compile(r'\b(BSF|bsf)[_\-]?\w*', re.IGNORECASE),
            'CHF': re.compile(r'\b(CHF|chf)[_\-]?\w*', re.IGNORECASE),
            'SEPP': re.compile(r'\b(SEPP|sepp)[_\-]?\w*', re.IGNORECASE),
            'SCP': re.compile(r'\b(SCP|scp)[_\-]?\w*', re.IGNORECASE),
            'NEF': re.compile(r'\b(NEF|nef)[_\-]?\w*', re.IGNORECASE),
        }
        return patterns
    
    def _init_feature_patterns(self) -> Dict[str, re.Pattern]:
        """初始化功能特性识别模式"""
        patterns = {
            'slice': re.compile(r'\b(slice|sst|sd|NSSAI)', re.IGNORECASE),
            'roaming': re.compile(r'\b(roaming|VPLMN|HPLMN)', re.IGNORECASE),
            'handover': re.compile(r'\b(handover|mobility|HO)', re.IGNORECASE),
            'QoS': re.compile(r'\b(QoS|5QI|QFI|AMBR|GBR)', re.IGNORECASE),
            'charging': re.compile(r'\b(charging|CHF|billing|CDR)', re.IGNORECASE),
            'authentication': re.compile(r'\b(auth|AUSF|SUPI|SUCI|AKA)', re.IGNORECASE),
            'security': re.compile(r'\b(security|encryption|integrity|ciphering)', re.IGNORECASE),
            'policy': re.compile(r'\b(policy|PCF|PCC|rule)', re.IGNORECASE),
            'session': re.compile(r'\b(session|PDU|PDN|bearer)', re.IGNORECASE),
            'registration': re.compile(r'\b(registration|attach|UE)', re.IGNORECASE),
        }
        return patterns
    
    def extract(self, content: str) -> Dict:
        """
        从配置内容中提取元数据
        
        Args:
            content: 配置文件内容
            
        Returns:
            元数据字典
        """
        metadata = {}
        
        # 提取项目信息
        if self.config.get('extract_project_info', True):
            project_info = self._extract_project_info(content)
            if project_info:
                metadata.update(project_info)
        
        # 提取版本信息
        if self.config.get('extract_version', True):
            version_info = self._extract_version_info(content)
            if version_info:
                metadata['version'] = version_info
        
        # 提取时间戳
        if self.config.get('extract_timestamp', True):
            timestamp = self._extract_timestamp(content)
            if timestamp:
                metadata['timestamp'] = timestamp
        
        # 提取5GC特定信息
        gsc_info = self._extract_5gc_info(content)
        if gsc_info:
            metadata['5gc_info'] = gsc_info
        
        # 提取网络配置信息
        network_info = self._extract_network_info(content)
        if network_info:
            metadata['network'] = network_info
        
        # 提取统计信息
        statistics = self._extract_statistics(content)
        metadata['statistics'] = statistics
        
        # 提取配置复杂度评估
        complexity = self._assess_complexity(content, statistics)
        metadata['complexity'] = complexity
        
        return metadata
    
    def _extract_project_info(self, content: str) -> Dict:
        """提取项目信息"""
        project_info = {}
        
        # 使用配置的模式
        for pattern in self.project_patterns:
            match = pattern.search(content)
            if match:
                if match.groups():
                    # 提取命名组或第一个组
                    key = self._extract_key_from_pattern(pattern.pattern)
                    project_info[key] = match.group(1)
                else:
                    project_info['project'] = match.group(0)
        
        # 额外的项目信息提取
        # 客户信息
        customer_pattern = re.compile(r'Customer[:\s]+([^\n]+)', re.IGNORECASE)
        match = customer_pattern.search(content)
        if match:
            project_info['customer'] = match.group(1).strip()
        
        # 站点信息
        site_pattern = re.compile(r'Site[:\s]+([^\n]+)', re.IGNORECASE)
        match = site_pattern.search(content)
        if match:
            project_info['site'] = match.group(1).strip()
        
        # 区域信息
        region_pattern = re.compile(r'Region[:\s]+([^\n]+)', re.IGNORECASE)
        match = region_pattern.search(content)
        if match:
            project_info['region'] = match.group(1).strip()
        
        return project_info
    
    def _extract_version_info(self, content: str) -> Optional[str]:
        """提取版本信息"""
        for pattern in self.version_patterns:
            match = pattern.search(content)
            if match:
                return match.group(1) if match.groups() else match.group(0)
        
        # 备用版本提取
        version_keywords = ['Version', 'Release', 'Build', 'Revision']
        for keyword in version_keywords:
            pattern = re.compile(rf'{keyword}[:\s]+([^\s,\n]+)', re.IGNORECASE)
            match = pattern.search(content)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_timestamp(self, content: str) -> Optional[str]:
        """提取时间戳"""
        for pattern in self.timestamp_patterns:
            match = pattern.search(content)
            if match:
                return match.group(0)
        
        # 备用时间戳格式
        additional_patterns = [
            r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}',  # ISO format
            r'\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2}',  # US format
            r'\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2}:\d{2}',  # EU format
        ]
        
        for pattern_str in additional_patterns:
            pattern = re.compile(pattern_str)
            match = pattern.search(content)
            if match:
                return match.group(0)
        
        return None
    
    def _extract_5gc_info(self, content: str) -> Dict:
        """提取5GC相关信息"""
        info = {
            'network_functions': {},
            'features': [],
            'interfaces': [],
            'identifiers': {}
        }
        
        # 网元识别和计数
        for nf_name, pattern in self.nf_patterns.items():
            matches = pattern.findall(content)
            if matches:
                info['network_functions'][nf_name] = {
                    'count': len(matches),
                    'instances': list(set(matches))[:5]  # 最多保存5个实例
                }
        
        # 功能特性识别
        for feature_name, pattern in self.feature_patterns.items():
            if pattern.search(content):
                info['features'].append(feature_name)
        
        # 接口识别
        interface_patterns = {
            'N1': r'\bN1\b',
            'N2': r'\bN2\b',
            'N3': r'\bN3\b',
            'N4': r'\bN4\b',
            'N6': r'\bN6\b',
            'N7': r'\bN7\b',
            'N8': r'\bN8\b',
            'N9': r'\bN9\b',
            'N10': r'\bN10\b',
            'N11': r'\bN11\b',
            'SBI': r'\b(SBI|sbi)\b',
            'Namf': r'\bNamf\b',
            'Nsmf': r'\bNsmf\b',
            'Nudm': r'\bNudm\b',
        }
        
        for interface_name, pattern_str in interface_patterns.items():
            pattern = re.compile(pattern_str, re.IGNORECASE)
            if pattern.search(content):
                info['interfaces'].append(interface_name)
        
        # 标识符提取
        # PLMN
        plmn_pattern = re.compile(r'PLMN[:\s]+([0-9]{5,6})')
        plmn_matches = plmn_pattern.findall(content)
        if plmn_matches:
            info['identifiers']['PLMN'] = list(set(plmn_matches))
        
        # TAC
        tac_pattern = re.compile(r'TAC[:\s]+(?:0x)?([0-9A-Fa-f]+)')
        tac_matches = tac_pattern.findall(content)
        if tac_matches:
            info['identifiers']['TAC'] = list(set(tac_matches))
        
        # DNN
        dnn_pattern = re.compile(r'DNN[:\s]+([^\s,]+(?:,[^\s,]+)*)')
        dnn_matches = dnn_pattern.findall(content)
        if dnn_matches:
            dnns = []
            for match in dnn_matches:
                dnns.extend(match.split(','))
            info['identifiers']['DNN'] = list(set(dnns))
        
        # 切片信息
        sst_pattern = re.compile(r'SST[:\s]+([0-9]+)')
        sst_matches = sst_pattern.findall(content)
        if sst_matches:
            info['identifiers']['SST'] = list(set(sst_matches))
        
        return info
    
    def _extract_network_info(self, content: str) -> Dict:
        """提取网络配置信息"""
        network_info = {
            'ip_addresses': [],
            'ports': [],
            'urls': [],
            'domains': []
        }
        
        # IP地址
        ip_pattern = re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b')
        ip_matches = ip_pattern.findall(content)
        if ip_matches:
            # 统计最常见的IP段
            ip_segments = ['.'.join(ip.split('.')[:2]) for ip in ip_matches]
            segment_counter = Counter(ip_segments)
            network_info['ip_addresses'] = {
                'total': len(set(ip_matches)),
                'samples': list(set(ip_matches))[:10],
                'common_segments': dict(segment_counter.most_common(5))
            }
        
        # 端口号
        port_pattern = re.compile(r'port[:\s]+([0-9]{1,5})', re.IGNORECASE)
        port_matches = port_pattern.findall(content)
        if port_matches:
            network_info['ports'] = list(set(port_matches))
        
        # URL
        url_pattern = re.compile(r'https?://[^\s]+')
        url_matches = url_pattern.findall(content)
        if url_matches:
            network_info['urls'] = list(set(url_matches))[:10]
        
        # 域名
        domain_pattern = re.compile(r'\b([a-z0-9]+(?:[-.][a-z0-9]+)*\.[a-z]{2,})\b', re.IGNORECASE)
        domain_matches = domain_pattern.findall(content)
        if domain_matches:
            network_info['domains'] = list(set(domain_matches))[:10]
        
        return network_info
    
    def _extract_statistics(self, content: str) -> Dict:
        """提取统计信息"""
        lines = content.split('\n')
        
        statistics = {
            'total_lines': len(lines),
            'non_empty_lines': sum(1 for line in lines if line.strip()),
            'comment_lines': sum(1 for line in lines if line.strip().startswith('#')),
            'size_bytes': len(content.encode('utf-8')),
            'size_mb': round(len(content.encode('utf-8')) / (1024 * 1024), 2)
        }
        
        # 配置项统计
        config_items = 0
        section_count = 0
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # 配置项（键值对）
            if '=' in line or ':' in line:
                config_items += 1
            
            # 配置节
            if line.startswith('[') and line.endswith(']'):
                section_count += 1
        
        statistics['config_items'] = config_items
        statistics['sections'] = section_count
        
        # 字符类型统计
        statistics['character_stats'] = {
            'alphabetic': sum(1 for c in content if c.isalpha()),
            'numeric': sum(1 for c in content if c.isdigit()),
            'whitespace': sum(1 for c in content if c.isspace()),
            'special': sum(1 for c in content if not c.isalnum() and not c.isspace())
        }
        
        return statistics
    
    def _assess_complexity(self, content: str, statistics: Dict) -> Dict:
        """评估配置复杂度"""
        complexity = {
            'level': 'low',  # low, medium, high
            'score': 0,
            'factors': []
        }
        
        score = 0
        factors = []
        
        # 基于大小的复杂度
        if statistics['size_mb'] > 10:
            score += 30
            factors.append('large_file_size')
        elif statistics['size_mb'] > 1:
            score += 10
            factors.append('medium_file_size')
        
        # 基于配置项数量
        if statistics['config_items'] > 1000:
            score += 30
            factors.append('many_config_items')
        elif statistics['config_items'] > 100:
            score += 10
            factors.append('moderate_config_items')
        
        # 基于网元数量
        if '5gc_info' in content:
            # 这里简化处理，实际应该从已提取的5gc_info中获取
            nf_count = content.count('AMF') + content.count('SMF') + content.count('UPF')
            if nf_count > 10:
                score += 20
                factors.append('multiple_network_functions')
        
        # 基于嵌套深度（简单估算）
        max_indent = 0
        for line in content.split('\n'):
            indent = len(line) - len(line.lstrip())
            max_indent = max(max_indent, indent)
        
        if max_indent > 20:
            score += 15
            factors.append('deep_nesting')
        
        # 确定复杂度级别
        if score >= 50:
            complexity['level'] = 'high'
        elif score >= 20:
            complexity['level'] = 'medium'
        else:
            complexity['level'] = 'low'
        
        complexity['score'] = score
        complexity['factors'] = factors
        
        return complexity
    
    def _extract_key_from_pattern(self, pattern: str) -> str:
        """从正则表达式模式中提取键名"""
        # 简单提取，假设模式中包含关键词
        keywords = ['PROJECT', 'Customer', 'Site', 'Region']
        for keyword in keywords:
            if keyword in pattern:
                return keyword.lower()
        return 'info'


if __name__ == "__main__":
    # 测试元数据提取
    extractor = MetadataExtractor("../config.yaml")
    
    test_content = """
    # 5GC Network Configuration
    # Project: Beijing-5GC-Phase2
    # Customer: China Mobile
    # Version: 2.1.0
    # Date: 2024-01-15 10:30:00
    
    [GLOBAL]
    site_id = BJ001
    region = North-China
    
    [AMF_CONFIG]
    amf_name = AMF_01
    amf_ip = 192.168.100.10
    plmn_id = 46000
    tac = 0x0001
    
    [SMF_CONFIG]
    smf_name = SMF_01
    n4_interface_ip = 192.168.100.20
    dnn = internet,ims,mms
    
    [SLICE_CONFIG]
    sst = 1
    sd = 0x000001
    
    [SECURITY]
    authentication = enabled
    encryption = AES256
    """
    
    metadata = extractor.extract(test_content)
    
    print("提取的元数据:")
    print("="*50)
    
    for key, value in metadata.items():
        if isinstance(value, dict):
            print(f"\n{key}:")
            for k, v in value.items():
                if isinstance(v, dict):
                    print(f"  {k}:")
                    for kk, vv in v.items():
                        print(f"    {kk}: {vv}")
                else:
                    print(f"  {k}: {v}")
        else:
            print(f"{key}: {value}")
