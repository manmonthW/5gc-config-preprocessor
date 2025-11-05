"""
配置预处理主模块
整合脱敏、格式转换、分块等所有预处理功能
"""

import os
import json
import yaml
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import hashlib
from tqdm import tqdm

from desensitizer import ConfigDesensitizer
from format_converter import FormatConverter, ConfigFormat
from chunker import SmartChunker, ConfigChunk
from metadata_extractor import MetadataExtractor

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class ProcessingResult:
    """预处理结果"""
    success: bool
    file_path: str
    original_format: str
    processed_files: List[str]
    metadata: Dict
    statistics: Dict
    errors: List[str]
    processing_time: float

class ConfigPreProcessor:
    """配置文件预处理器主类"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        初始化预处理器
        
        Args:
            config_path: 配置文件路径
        """
        self.config = self._load_config(config_path)
        
        # 初始化各个组件
        self.desensitizer = ConfigDesensitizer(config_path)
        self.converter = FormatConverter(config_path)
        self.chunker = SmartChunker(config_path)
        self.metadata_extractor = MetadataExtractor(config_path)
        
        # 设置输出目录
        self.output_base = Path(self.config['output']['base_dir'])
        if self.config['output']['create_timestamp_folder']:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            self.output_dir = self.output_base / timestamp
        else:
            self.output_dir = self.output_base
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化统计信息
        self.statistics = {
            'files_processed': 0,
            'total_size_mb': 0,
            'processing_time_seconds': 0,
            'chunks_created': 0,
            'desensitization_count': 0
        }
    
    def _load_config(self, config_path: str) -> Dict:
        """加载配置文件"""
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def process_file(self, file_path: str, 
                    desensitize: bool = True,
                    convert_format: bool = True,
                    chunk: bool = True,
                    extract_metadata: bool = True) -> ProcessingResult:
        """
        处理单个配置文件
        
        Args:
            file_path: 文件路径
            desensitize: 是否脱敏
            convert_format: 是否转换格式
            chunk: 是否分块
            extract_metadata: 是否提取元数据
            
        Returns:
            处理结果
        """
        start_time = datetime.now()
        errors = []
        processed_files = []
        metadata = {}
        
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                raise FileNotFoundError(f"文件不存在: {file_path}")
            
            # 获取文件信息
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            logger.info(f"开始处理文件: {file_path} (大小: {file_size_mb:.2f} MB)")
            
            # 创建文件专属输出目录
            file_output_dir = self.output_dir / file_path.stem
            file_output_dir.mkdir(exist_ok=True)
            
            # Step 1: 格式检测和转换
            if convert_format:
                logger.info("Step 1: 格式转换...")
                unified = self.converter.process_file(str(file_path))
                original_format = unified['metadata']['original_format']
                
                # 保存统一格式
                unified_file = file_output_dir / f"{file_path.stem}_unified.json"
                self.converter.save_unified(unified, str(unified_file))
                processed_files.append(str(unified_file))
                logger.info(f"  ✓ 格式转换完成: {original_format} -> unified")
            else:
                # 直接读取文件
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                original_format = self.converter.detect_format(str(file_path)).value
                unified = {'config': {'content': content}}
            
            # Step 2: 元数据提取
            if extract_metadata:
                logger.info("Step 2: 元数据提取...")
                # 从原始文件提取
                with open(file_path, 'r', encoding='utf-8') as f:
                    raw_content = f.read()
                metadata = self.metadata_extractor.extract(raw_content)
                
                # 保存元数据
                metadata_file = file_output_dir / f"{file_path.stem}_metadata.json"
                with open(metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, ensure_ascii=False, indent=2)
                processed_files.append(str(metadata_file))
                logger.info(f"  ✓ 元数据提取完成: {len(metadata)} 个字段")
            
            # Step 3: 脱敏处理
            if desensitize:
                logger.info("Step 3: 脱敏处理...")
                # 获取要脱敏的内容
                if convert_format:
                    # 将统一格式转回文本进行脱敏
                    content = self._unified_to_text(unified)
                else:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                
                # 执行脱敏
                desensitized_content, desensitize_mapping = \
                    self.desensitizer.desensitize_text(content)
                
                # 保存脱敏后的内容
                desensitized_file = file_output_dir / f"{file_path.stem}_desensitized.txt"
                with open(desensitized_file, 'w', encoding='utf-8') as f:
                    f.write(desensitized_content)
                processed_files.append(str(desensitized_file))
                
                # 保存脱敏映射
                mapping_file = file_output_dir / f"{file_path.stem}_desensitize_mapping.json"
                with open(mapping_file, 'w', encoding='utf-8') as f:
                    json.dump(desensitize_mapping, f, ensure_ascii=False, indent=2)
                processed_files.append(str(mapping_file))
                
                desensitize_stats = self.desensitizer.get_statistics()
                logger.info(f"  ✓ 脱敏完成: {desensitize_stats['total_replacements']} 处替换")
                
                # 更新内容为脱敏后的版本
                content = desensitized_content
            else:
                if not convert_format:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
            
            # Step 4: 智能分块
            if chunk:
                logger.info("Step 4: 智能分块...")
                chunks = self.chunker.chunk_text(content)
                
                # 保存分块
                chunks_dir = file_output_dir / "chunks"
                self.chunker.save_chunks(chunks, str(chunks_dir))
                processed_files.append(str(chunks_dir))
                
                logger.info(f"  ✓ 分块完成: 生成 {len(chunks)} 个块")
                self.statistics['chunks_created'] += len(chunks)
            
            # Step 5: 生成处理报告
            logger.info("Step 5: 生成处理报告...")
            report = self._generate_report(
                file_path=str(file_path),
                original_format=original_format,
                metadata=metadata,
                processed_files=processed_files,
                statistics={
                    'file_size_mb': file_size_mb,
                    'chunks_created': len(chunks) if chunk else 0,
                    'desensitization': self.desensitizer.get_statistics() if desensitize else {}
                }
            )
            
            report_file = file_output_dir / f"{file_path.stem}_report.json"
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            processed_files.append(str(report_file))
            logger.info("  ✓ 报告生成完成")
            
            # 更新统计信息
            self.statistics['files_processed'] += 1
            self.statistics['total_size_mb'] += file_size_mb
            
            # 计算处理时间
            processing_time = (datetime.now() - start_time).total_seconds()
            self.statistics['processing_time_seconds'] += processing_time
            
            logger.info(f"✅ 文件处理完成: {file_path}")
            logger.info(f"   处理时间: {processing_time:.2f} 秒")
            logger.info(f"   输出目录: {file_output_dir}")
            
            return ProcessingResult(
                success=True,
                file_path=str(file_path),
                original_format=original_format,
                processed_files=processed_files,
                metadata=metadata,
                statistics=self.statistics,
                errors=errors,
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"处理文件失败: {e}")
            errors.append(str(e))
            
            return ProcessingResult(
                success=False,
                file_path=str(file_path),
                original_format="unknown",
                processed_files=processed_files,
                metadata=metadata,
                statistics=self.statistics,
                errors=errors,
                processing_time=(datetime.now() - start_time).total_seconds()
            )
    
    def process_directory(self, directory_path: str, 
                         pattern: str = "*",
                         recursive: bool = True) -> List[ProcessingResult]:
        """
        处理目录中的所有配置文件
        
        Args:
            directory_path: 目录路径
            pattern: 文件匹配模式
            recursive: 是否递归处理子目录
            
        Returns:
            处理结果列表
        """
        directory_path = Path(directory_path)
        if not directory_path.exists():
            raise ValueError(f"目录不存在: {directory_path}")
        
        # 查找所有匹配的文件
        if recursive:
            files = list(directory_path.rglob(pattern))
        else:
            files = list(directory_path.glob(pattern))
        
        logger.info(f"找到 {len(files)} 个文件待处理")
        
        results = []
        for file_path in tqdm(files, desc="处理文件"):
            if file_path.is_file():
                result = self.process_file(str(file_path))
                results.append(result)
        
        # 生成总体报告
        self._generate_summary_report(results)
        
        return results
    
    def _unified_to_text(self, unified: Dict) -> str:
        """将统一格式转回文本"""
        def dict_to_text(d, indent=0):
            lines = []
            indent_str = "  " * indent
            
            if isinstance(d, dict):
                for key, value in d.items():
                    if isinstance(value, dict):
                        lines.append(f"{indent_str}[{key}]")
                        lines.append(dict_to_text(value, indent + 1))
                    elif isinstance(value, list):
                        lines.append(f"{indent_str}{key} = {','.join(map(str, value))}")
                    else:
                        lines.append(f"{indent_str}{key} = {value}")
            else:
                lines.append(f"{indent_str}{d}")
            
            return '\n'.join(lines)
        
        return dict_to_text(unified.get('config', {}))
    
    def _generate_report(self, **kwargs) -> Dict:
        """生成处理报告"""
        return {
            'timestamp': datetime.now().isoformat(),
            'version': '1.0.0',
            **kwargs
        }
    
    def _generate_summary_report(self, results: List[ProcessingResult]):
        """生成汇总报告"""
        summary = {
            'total_files': len(results),
            'successful': sum(1 for r in results if r.success),
            'failed': sum(1 for r in results if not r.success),
            'total_processing_time': sum(r.processing_time for r in results),
            'total_size_mb': self.statistics['total_size_mb'],
            'total_chunks': self.statistics['chunks_created'],
            'files': []
        }
        
        for result in results:
            summary['files'].append({
                'file': result.file_path,
                'success': result.success,
                'format': result.original_format,
                'processing_time': result.processing_time,
                'errors': result.errors
            })
        
        summary_file = self.output_dir / "processing_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        logger.info(f"汇总报告已保存: {summary_file}")


# 创建元数据提取器模块
class MetadataExtractor:
    """元数据提取器"""
    
    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        self.config = config.get('metadata', {})
        self.project_patterns = [re.compile(p) for p in self.config.get('project_patterns', [])]
        self.version_patterns = [re.compile(p) for p in self.config.get('version_patterns', [])]
        self.timestamp_patterns = [re.compile(p) for p in self.config.get('timestamp_patterns', [])]
    
    def extract(self, content: str) -> Dict:
        """提取元数据"""
        import re
        metadata = {}
        
        # 提取项目信息
        for pattern in self.project_patterns:
            match = pattern.search(content)
            if match:
                metadata['project'] = match.group(1) if match.groups() else match.group(0)
                break
        
        # 提取版本信息
        for pattern in self.version_patterns:
            match = pattern.search(content)
            if match:
                metadata['version'] = match.group(1) if match.groups() else match.group(0)
                break
        
        # 提取时间戳
        for pattern in self.timestamp_patterns:
            match = pattern.search(content)
            if match:
                metadata['timestamp'] = match.group(0)
                break
        
        # 提取基本统计
        lines = content.split('\n')
        metadata['statistics'] = {
            'total_lines': len(lines),
            'non_empty_lines': sum(1 for line in lines if line.strip()),
            'comment_lines': sum(1 for line in lines if line.strip().startswith('#')),
            'size_bytes': len(content.encode('utf-8'))
        }
        
        return metadata


def create_metadata_extractor_file():
    """创建独立的元数据提取器文件"""
    metadata_code = '''"""
元数据提取模块
用于从配置文件中提取项目信息、版本、时间戳等元数据
"""

import re
import yaml
from typing import Dict, List, Any
from datetime import datetime
import logging

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
        
        # 提取统计信息
        statistics = self._extract_statistics(content)
        metadata['statistics'] = statistics
        
        return metadata
    
    def _extract_project_info(self, content: str) -> Dict:
        """提取项目信息"""
        project_info = {}
        
        for pattern in self.project_patterns:
            match = pattern.search(content)
            if match:
                if match.groups():
                    # 提取命名组或第一个组
                    if match.lastindex:
                        key = pattern.pattern.split(':')[0].split()[-1].lower()
                        project_info[key] = match.group(1)
                else:
                    project_info['project'] = match.group(0)
        
        return project_info
    
    def _extract_version_info(self, content: str) -> str:
        """提取版本信息"""
        for pattern in self.version_patterns:
            match = pattern.search(content)
            if match:
                return match.group(1) if match.groups() else match.group(0)
        
        return None
    
    def _extract_timestamp(self, content: str) -> str:
        """提取时间戳"""
        for pattern in self.timestamp_patterns:
            match = pattern.search(content)
            if match:
                return match.group(0)
        
        return None
    
    def _extract_5gc_info(self, content: str) -> Dict:
        """提取5GC相关信息"""
        info = {
            'network_functions': [],
            'features': [],
            'interfaces': []
        }
        
        # 网元识别
        nf_keywords = [
            'AMF', 'SMF', 'UPF', 'NRF', 'UDM', 'AUSF', 'NSSF', 
            'PCF', 'BSF', 'CHF', 'SEPP', 'SCP', 'NEF', 'NRF'
        ]
        
        content_upper = content.upper()
        for nf in nf_keywords:
            if nf in content_upper:
                info['network_functions'].append(nf)
        
        # 功能特性识别
        feature_keywords = [
            'slice', 'roaming', 'handover', 'QoS', 'charging',
            'authentication', 'security', 'policy', 'session'
        ]
        
        content_lower = content.lower()
        for feature in feature_keywords:
            if feature.lower() in content_lower:
                info['features'].append(feature)
        
        # 接口识别
        interface_patterns = [
            r'N[1-9]\d*',  # N1, N2, N3, etc.
            r'S[1-9]\d*',  # S1, S5, S8, etc.
            r'Rx', r'Gx', r'Gy',  # Diameter interfaces
        ]
        
        for pattern_str in interface_patterns:
            pattern = re.compile(pattern_str)
            matches = pattern.findall(content)
            info['interfaces'].extend(matches)
        
        # 去重
        info['network_functions'] = list(set(info['network_functions']))
        info['features'] = list(set(info['features']))
        info['interfaces'] = list(set(info['interfaces']))
        
        return info
    
    def _extract_statistics(self, content: str) -> Dict:
        """提取统计信息"""
        lines = content.split('\\n')
        
        statistics = {
            'total_lines': len(lines),
            'non_empty_lines': sum(1 for line in lines if line.strip()),
            'comment_lines': sum(1 for line in lines if line.strip().startswith('#')),
            'size_bytes': len(content.encode('utf-8')),
            'size_mb': round(len(content.encode('utf-8')) / (1024 * 1024), 2)
        }
        
        # 配置项统计
        config_items = 0
        for line in lines:
            if '=' in line or ':' in line:
                if not line.strip().startswith('#'):
                    config_items += 1
        
        statistics['config_items'] = config_items
        
        return statistics
'''
    
    with open('/home/claude/config_preprocessor/src/metadata_extractor.py', 'w', encoding='utf-8') as f:
        f.write(metadata_code)
    
    return "metadata_extractor.py created"

# 创建元数据提取器文件
create_metadata_extractor_file()


if __name__ == "__main__":
    # 使用示例
    preprocessor = ConfigPreProcessor("config.yaml")
    
    # 处理单个文件
    result = preprocessor.process_file(
        "sample_config.txt",
        desensitize=True,
        convert_format=True,
        chunk=True,
        extract_metadata=True
    )
    
    if result.success:
        print("✅ 预处理成功！")
        print(f"处理时间: {result.processing_time:.2f} 秒")
        print(f"输出文件: {len(result.processed_files)} 个")
        print("\n生成的文件:")
        for file in result.processed_files:
            print(f"  - {file}")
    else:
        print("❌ 预处理失败！")
        print(f"错误: {result.errors}")
