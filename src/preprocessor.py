"""
配置预处理主模块
整合脱敏、格式转换、分块等所有预处理功能
"""

import os
import json
import yaml
import shutil
import logging
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
try:
    from tqdm import tqdm
except ImportError:  # pragma: no cover - fallback when tqdm unavailable
    def tqdm(iterable, **kwargs):
        return iterable

from desensitizer import ConfigDesensitizer
from format_converter import FormatConverter
from chunker import SmartChunker
from metadata_extractor import MetadataExtractor
from utils import resolve_config_path

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
    message: str = ""
    output_directory: str = ""
    preferred_output_root: str = ""
    mirrored_output_directory: Optional[str] = None
    mirrored_files: Optional[List[str]] = None
    used_output_fallback: bool = False
    mirror_error: Optional[str] = None
    # Vercel Serverless 支持：内存文件存储
    memory_files: Optional[Dict[str, bytes]] = None  # {filename: content}

class ConfigPreProcessor:
    """配置文件预处理器主类"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        初始化预处理器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = resolve_config_path(config_path)
        self.config = self._load_config(self.config_path)
        
        # 初始化各个组件
        config_path_str = str(self.config_path)
        self.desensitizer = ConfigDesensitizer(config_path_str)
        self.converter = FormatConverter(config_path_str)
        self.chunker = SmartChunker(config_path_str)
        self.metadata_extractor = MetadataExtractor(config_path_str)
        
        # 设置输出目录（在只读环境中回退到临时目录）
        output_settings = self.config.get('output', {})
        base_dir = output_settings.get('base_dir', './output')
        use_timestamp = output_settings.get('create_timestamp_folder', True)
        self.preferred_output_base = self._resolve_output_base(base_dir)
        self.output_base, self.output_dir, self.using_output_fallback = self._prepare_output_directory(
            self.preferred_output_base,
            use_timestamp
        )
        
        # 初始化统计信息
        self.statistics = {
            'files_processed': 0,
            'total_size_mb': 0,
            'processing_time_seconds': 0,
            'chunks_created': 0,
            'desensitization_count': 0
        }
    
    def _load_config(self, config_path: Path) -> Dict:
        """加载配置文件"""
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _resolve_output_base(self, base_dir: str) -> Path:
        """解析配置的输出根目录"""
        resolved_base = Path(base_dir)
        if not resolved_base.is_absolute():
            resolved_base = self.config_path.parent / resolved_base
        return resolved_base
    
    def _prepare_output_directory(self, preferred_base: Path, use_timestamp: bool):
        """为处理结果准备输出目录，必要时回退到临时目录"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S') if use_timestamp else None
        target_dir = preferred_base / timestamp if timestamp else preferred_base
        
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            return preferred_base, target_dir, False
        except (PermissionError, OSError) as exc:
            fallback_base = Path(tempfile.gettempdir()) / "config_preprocessor_output"
            fallback_dir = fallback_base / timestamp if timestamp else fallback_base
            fallback_dir.mkdir(parents=True, exist_ok=True)
            logger.warning(
                "Output directory %s is not writable (%s). Falling back to %s",
                target_dir,
                exc,
                fallback_dir
            )
            return fallback_base, fallback_dir, True
    
    def process_file(self, file_path: str,
                    desensitize: bool = True,
                    convert_format: bool = True,
                    chunk: bool = True,
                    extract_metadata: bool = True,
                    original_filename: Optional[str] = None,
                    memory_mode: bool = False) -> ProcessingResult:
        """
        处理单个配置文件

        Args:
            file_path: 文件路径
            desensitize: 是否脱敏
            convert_format: 是否转换格式
            chunk: 是否分块
            extract_metadata: 是否提取元数据
            original_filename: 原始文件名（可选，用于输出目录命名）
            memory_mode: Vercel Serverless 模式 - 不写磁盘，内存返回 (默认False)

        Returns:
            处理结果
        """
        start_time = datetime.now()
        errors = []
        processed_files = []
        metadata = {}
        
        file_output_dir: Optional[Path] = None
        
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                raise FileNotFoundError(f"文件不存在: {file_path}")
            
            # 获取文件信息
            file_size_mb = file_path.stat().st_size / (1024 * 1024)

            # 确定显示名称
            display_name = original_filename if original_filename else file_path.name
            logger.info(f"开始处理文件: {display_name} (大小: {file_size_mb:.2f} MB)")

            # 读取原始内容（保持格式）
            original_text = self.converter.read_file(str(file_path))
            detected_format = self.converter.detect_format(str(file_path))

            # 创建文件专属输出目录
            # 如果提供了原始文件名，使用原始文件名；否则使用当前文件名
            if original_filename:
                output_dir_name = Path(original_filename).stem
            else:
                output_dir_name = file_path.stem

            file_output_dir = self.output_dir / output_dir_name
            file_output_dir.mkdir(exist_ok=True)

            unified = None

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
                original_format = detected_format.value
            
            # Step 2: 元数据提取
            if extract_metadata:
                logger.info("Step 2: 元数据提取...")
                metadata = self.metadata_extractor.extract(original_text)
                
                # 保存元数据
                metadata_file = file_output_dir / f"{file_path.stem}_metadata.json"
                with open(metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, ensure_ascii=False, indent=2)
                processed_files.append(str(metadata_file))
                logger.info(f"  ✓ 元数据提取完成: {len(metadata)} 个字段")
            
            # Step 3: 脱敏处理
            if desensitize:
                logger.info("Step 3: 脱敏处理...")

                # 执行脱敏（基于原始文本，保持格式）
                desensitized_content, desensitize_mapping = \
                    self.desensitizer.desensitize_text(original_text)

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

                content_for_chunking = desensitized_content
            else:
                content_for_chunking = original_text
            
            # Step 4: 智能分块
            if chunk:
                logger.info("Step 4: 智能分块...")
                chunks = self.chunker.chunk_text(content_for_chunking)
                
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
            
            mirror_info = self._mirror_output_if_needed(file_output_dir, processed_files)
            if mirror_info.get('mirrored'):
                logger.info("✅ 输出目录已同步到项目 output: %s", mirror_info.get('mirror_dir'))
            elif mirror_info.get('error'):
                logger.warning("⚠️ 输出目录同步失败: %s", mirror_info['error'])
            
            logger.info(f"✅ 文件处理完成: {file_path}")
            logger.info(f"   处理时间: {processing_time:.2f} 秒")
            logger.info(f"   输出目录: {file_output_dir}")

            # Vercel Serverless 模式：读取所有文件到内存
            memory_files = None
            if memory_mode:
                logger.info("🔄 Vercel 模式：读取文件到内存...")
                memory_files = {}
                for file_path_str in processed_files:
                    file_path_obj = Path(file_path_str)

                    # 处理目录（chunks）
                    if file_path_obj.is_dir():
                        # 读取目录下所有文件
                        for chunk_file in file_path_obj.rglob('*'):
                            if chunk_file.is_file():
                                relative_name = chunk_file.relative_to(file_output_dir)
                                with open(chunk_file, 'rb') as f:
                                    memory_files[str(relative_name)] = f.read()
                    # 处理单个文件
                    elif file_path_obj.is_file():
                        filename = file_path_obj.name
                        with open(file_path_obj, 'rb') as f:
                            memory_files[filename] = f.read()

                logger.info(f"  ✓ 已读取 {len(memory_files)} 个文件到内存")

            return ProcessingResult(
                success=True,
                file_path=str(file_path),
                original_format=original_format,
                processed_files=processed_files,
                metadata=metadata,
                statistics=self.statistics,
                errors=errors,
                processing_time=processing_time,
                message=f"Processing completed successfully in {processing_time:.2f} seconds",
                output_directory=str(file_output_dir),
                preferred_output_root=str(self.preferred_output_base),
                mirrored_output_directory=mirror_info.get('mirror_dir'),
                mirrored_files=mirror_info.get('mirror_files'),
                used_output_fallback=self.using_output_fallback,
                mirror_error=mirror_info.get('error'),
                memory_files=memory_files  # Vercel 模式返回内存文件
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
                processing_time=(datetime.now() - start_time).total_seconds(),
                message=f"Processing failed: {str(e)}",
                output_directory=str(file_output_dir) if file_output_dir else str(self.output_dir),
                preferred_output_root=str(self.preferred_output_base),
                used_output_fallback=self.using_output_fallback
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
    
    def _mirror_output_if_needed(self, source_dir: Path, processed_files: List[str]) -> Dict[str, Any]:
        """在临时目录写入时尝试同步到项目 output 目录"""
        if not self.using_output_fallback or not source_dir:
            return {'mirrored': False}
        
        mirror_info = {'mirrored': False}
        try:
            relative_dir = source_dir.relative_to(self.output_base)
        except ValueError:
            relative_dir = source_dir.name
        
        target_dir = self.preferred_output_base / relative_dir
        
        try:
            target_dir.parent.mkdir(parents=True, exist_ok=True)
            if target_dir.exists():
                shutil.rmtree(target_dir)
            shutil.copytree(source_dir, target_dir)
            
            mirrored_files = []
            for file_path in processed_files:
                try:
                    rel = Path(file_path).relative_to(self.output_base)
                except ValueError:
                    continue
                mirrored_files.append(str(self.preferred_output_base / rel))
            
            mirror_info.update({
                'mirrored': True,
                'mirror_dir': str(target_dir),
                'mirror_files': mirrored_files
            })
        except Exception as exc:
            mirror_info['error'] = str(exc)
        
        return mirror_info
    
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
