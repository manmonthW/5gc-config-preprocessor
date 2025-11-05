"""
配置文件智能分块模块
用于将大型配置文件分割成可管理的块，同时保持配置的完整性
"""

import re
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import logging
import yaml
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class ConfigChunk:
    """配置块数据结构"""
    chunk_id: int
    start_line: int
    end_line: int
    content: str
    features: List[str]  # 包含的功能特征
    metadata: Dict
    overlap_start: Optional[int] = None
    overlap_end: Optional[int] = None

class SmartChunker:
    """智能配置文件分块器"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """初始化分块器"""
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        self.config = config.get('chunking', {})
        self.enabled = self.config.get('enabled', True)
        self.strategy = self.config.get('strategy', 'smart')
        self.chunk_size_lines = self.config.get('chunk_size_lines', 5000)
        self.chunk_size_kb = self.config.get('chunk_size_kb', 1024)
        self.overlap_lines = self.config.get('overlap_lines', 100)
        
        # 智能分块配置
        self.smart_config = self.config.get('smart_chunking', {})
        self.section_markers = self.smart_config.get('section_markers', [])
        self.preserve_blocks = self.smart_config.get('preserve_blocks', [])
        
        # 编译保留块模式
        self.preserve_patterns = []
        for block in self.preserve_blocks:
            if 'pattern' in block:
                self.preserve_patterns.append(
                    re.compile(block['pattern'], re.DOTALL | re.MULTILINE)
                )
    
    def chunk_text(self, text: str) -> List[ConfigChunk]:
        """
        对文本进行分块
        
        Args:
            text: 输入文本
            
        Returns:
            配置块列表
        """
        if not self.enabled:
            # 不分块，返回整个文本
            return [ConfigChunk(
                chunk_id=0,
                start_line=1,
                end_line=len(text.split('\n')),
                content=text,
                features=[],
                metadata={'strategy': 'disabled'}
            )]
        
        if self.strategy == 'smart':
            return self._smart_chunking(text)
        elif self.strategy == 'fixed_lines':
            return self._fixed_lines_chunking(text)
        elif self.strategy == 'fixed_size':
            return self._fixed_size_chunking(text)
        else:
            logger.warning(f"未知的分块策略: {self.strategy}，使用智能分块")
            return self._smart_chunking(text)
    
    def _smart_chunking(self, text: str) -> List[ConfigChunk]:
        """
        智能分块策略
        基于配置结构和语义边界进行分块
        """
        lines = text.split('\n')
        chunks = []
        
        # 1. 识别配置段落
        sections = self._identify_sections(lines)
        logger.info(f"识别到 {len(sections)} 个配置段落")
        
        # 2. 识别需要保留完整的块
        preserve_blocks = self._identify_preserve_blocks(lines)
        logger.info(f"识别到 {len(preserve_blocks)} 个需要保留完整的块")
        
        # 3. 基于段落和保留块进行分块
        current_chunk_lines = []
        current_chunk_start = 1
        current_features = set()
        chunk_id = 0
        
        for line_no, line in enumerate(lines, 1):
            # 检查是否在保留块内
            in_preserve_block = False
            for block_start, block_end in preserve_blocks:
                if block_start <= line_no <= block_end:
                    in_preserve_block = True
                    # 如果当前块会超过大小限制，先保存当前块
                    if (len(current_chunk_lines) > 0 and 
                        len(current_chunk_lines) + (block_end - block_start + 1) > self.chunk_size_lines):
                        # 保存当前块
                        chunk = self._create_chunk(
                            chunk_id, 
                            current_chunk_start,
                            line_no - 1,
                            current_chunk_lines,
                            list(current_features)
                        )
                        chunks.append(chunk)
                        chunk_id += 1
                        current_chunk_lines = []
                        current_chunk_start = line_no
                        current_features = set()
                    
                    # 添加整个保留块
                    for i in range(block_start - 1, block_end):
                        if i < len(lines):
                            current_chunk_lines.append(lines[i])
                            # 提取特征
                            features = self._extract_features(lines[i])
                            current_features.update(features)
                    
                    # 跳过已处理的行
                    line_no = block_end
                    break
            
            if not in_preserve_block:
                current_chunk_lines.append(line)
                
                # 提取特征
                features = self._extract_features(line)
                current_features.update(features)
                
                # 检查是否需要创建新块
                should_split = False
                
                # 条件1: 达到大小限制
                if len(current_chunk_lines) >= self.chunk_size_lines:
                    should_split = True
                
                # 条件2: 遇到主要段落标记
                for marker in self.section_markers:
                    if marker in line and len(current_chunk_lines) > self.chunk_size_lines // 2:
                        should_split = True
                        break
                
                if should_split:
                    # 创建块
                    chunk = self._create_chunk(
                        chunk_id,
                        current_chunk_start,
                        line_no,
                        current_chunk_lines,
                        list(current_features)
                    )
                    chunks.append(chunk)
                    chunk_id += 1
                    
                    # 添加重叠
                    overlap_start = max(0, len(current_chunk_lines) - self.overlap_lines)
                    current_chunk_lines = current_chunk_lines[overlap_start:]
                    current_chunk_start = line_no - len(current_chunk_lines) + 1
                    current_features = set()
                    
                    # 重新提取重叠部分的特征
                    for overlap_line in current_chunk_lines:
                        features = self._extract_features(overlap_line)
                        current_features.update(features)
        
        # 保存最后一个块
        if current_chunk_lines:
            chunk = self._create_chunk(
                chunk_id,
                current_chunk_start,
                len(lines),
                current_chunk_lines,
                list(current_features)
            )
            chunks.append(chunk)
        
        logger.info(f"智能分块完成，共生成 {len(chunks)} 个块")
        return chunks
    
    def _fixed_lines_chunking(self, text: str) -> List[ConfigChunk]:
        """
        固定行数分块策略
        """
        lines = text.split('\n')
        chunks = []
        chunk_id = 0
        
        for i in range(0, len(lines), self.chunk_size_lines - self.overlap_lines):
            start_line = i + 1
            end_line = min(i + self.chunk_size_lines, len(lines))
            
            chunk_lines = lines[i:end_line]
            features = []
            for line in chunk_lines:
                features.extend(self._extract_features(line))
            
            chunk = ConfigChunk(
                chunk_id=chunk_id,
                start_line=start_line,
                end_line=end_line,
                content='\n'.join(chunk_lines),
                features=list(set(features)),
                metadata={'strategy': 'fixed_lines'}
            )
            
            # 添加重叠信息
            if i > 0:
                chunk.overlap_start = max(1, start_line - self.overlap_lines)
            if end_line < len(lines):
                chunk.overlap_end = min(len(lines), end_line + self.overlap_lines)
            
            chunks.append(chunk)
            chunk_id += 1
        
        logger.info(f"固定行数分块完成，共生成 {len(chunks)} 个块")
        return chunks
    
    def _fixed_size_chunking(self, text: str) -> List[ConfigChunk]:
        """
        固定大小分块策略（按KB）
        """
        lines = text.split('\n')
        chunks = []
        chunk_id = 0
        current_chunk_lines = []
        current_size = 0
        current_start = 1
        target_size = self.chunk_size_kb * 1024  # 转换为字节
        
        for line_no, line in enumerate(lines, 1):
            line_size = len(line.encode('utf-8'))
            
            if current_size + line_size > target_size and current_chunk_lines:
                # 创建块
                features = []
                for chunk_line in current_chunk_lines:
                    features.extend(self._extract_features(chunk_line))
                
                chunk = ConfigChunk(
                    chunk_id=chunk_id,
                    start_line=current_start,
                    end_line=line_no - 1,
                    content='\n'.join(current_chunk_lines),
                    features=list(set(features)),
                    metadata={
                        'strategy': 'fixed_size',
                        'size_bytes': current_size
                    }
                )
                chunks.append(chunk)
                chunk_id += 1
                
                # 重置
                current_chunk_lines = []
                current_size = 0
                current_start = line_no
            
            current_chunk_lines.append(line)
            current_size += line_size
        
        # 保存最后一个块
        if current_chunk_lines:
            features = []
            for chunk_line in current_chunk_lines:
                features.extend(self._extract_features(chunk_line))
            
            chunk = ConfigChunk(
                chunk_id=chunk_id,
                start_line=current_start,
                end_line=len(lines),
                content='\n'.join(current_chunk_lines),
                features=list(set(features)),
                metadata={
                    'strategy': 'fixed_size',
                    'size_bytes': current_size
                }
            )
            chunks.append(chunk)
        
        logger.info(f"固定大小分块完成，共生成 {len(chunks)} 个块")
        return chunks
    
    def _identify_sections(self, lines: List[str]) -> List[Tuple[int, int, str]]:
        """
        识别配置段落
        
        Returns:
            段落列表 [(开始行, 结束行, 段落名)]
        """
        sections = []
        current_section = None
        section_start = 0
        
        for line_no, line in enumerate(lines, 1):
            # 检查段落标记
            for marker in self.section_markers:
                if marker in line:
                    # 保存前一个段落
                    if current_section:
                        sections.append((section_start, line_no - 1, current_section))
                    
                    # 开始新段落
                    current_section = self._extract_section_name(line, marker)
                    section_start = line_no
                    break
        
        # 保存最后一个段落
        if current_section:
            sections.append((section_start, len(lines), current_section))
        
        return sections
    
    def _identify_preserve_blocks(self, lines: List[str]) -> List[Tuple[int, int]]:
        """
        识别需要保留完整的配置块
        
        Returns:
            块列表 [(开始行, 结束行)]
        """
        blocks = []
        text = '\n'.join(lines)
        
        for pattern in self.preserve_patterns:
            for match in pattern.finditer(text):
                # 计算匹配的行号
                start_pos = match.start()
                end_pos = match.end()
                
                start_line = text[:start_pos].count('\n') + 1
                end_line = text[:end_pos].count('\n') + 1
                
                blocks.append((start_line, end_line))
        
        # 合并重叠的块
        blocks = self._merge_overlapping_blocks(blocks)
        
        return blocks
    
    def _merge_overlapping_blocks(self, blocks: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        """合并重叠的块"""
        if not blocks:
            return []
        
        blocks.sort(key=lambda x: x[0])
        merged = [blocks[0]]
        
        for current_start, current_end in blocks[1:]:
            last_start, last_end = merged[-1]
            
            if current_start <= last_end + 1:  # 重叠或相邻
                merged[-1] = (last_start, max(last_end, current_end))
            else:
                merged.append((current_start, current_end))
        
        return merged
    
    def _extract_features(self, line: str) -> List[str]:
        """
        从行中提取功能特征
        
        Args:
            line: 配置行
            
        Returns:
            特征列表
        """
        features = []
        
        # 功能关键词列表（根据5GC配置特点）
        feature_keywords = [
            'PLMN', 'TAC', 'AMF', 'SMF', 'UPF', 'NRF', 'UDM', 'AUSF',
            'NSSF', 'PCF', 'BSF', 'CHF', 'SEPP', 'SCP',
            'slice', 'DNN', 'APN', 'QoS', 'bearer', 'session',
            'roaming', 'handover', 'authentication', 'security',
            'charging', 'billing', 'policy', 'routing'
        ]
        
        line_lower = line.lower()
        for keyword in feature_keywords:
            if keyword.lower() in line_lower:
                features.append(keyword)
        
        return features
    
    def _extract_section_name(self, line: str, marker: str) -> str:
        """提取段落名称"""
        # 简单提取，可以根据实际格式优化
        parts = line.split(marker)
        if len(parts) > 1:
            return parts[1].strip()
        return marker
    
    def _create_chunk(self, chunk_id: int, start_line: int, end_line: int,
                     lines: List[str], features: List[str]) -> ConfigChunk:
        """创建配置块"""
        return ConfigChunk(
            chunk_id=chunk_id,
            start_line=start_line,
            end_line=end_line,
            content='\n'.join(lines),
            features=features,
            metadata={
                'strategy': self.strategy,
                'line_count': len(lines),
                'feature_count': len(features)
            }
        )
    
    def save_chunks(self, chunks: List[ConfigChunk], output_dir: str):
        """
        保存分块结果
        
        Args:
            chunks: 配置块列表
            output_dir: 输出目录
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 保存每个块
        for chunk in chunks:
            chunk_file = output_path / f"chunk_{chunk.chunk_id:04d}.txt"
            with open(chunk_file, 'w', encoding='utf-8') as f:
                f.write(chunk.content)
            
            # 保存块元数据
            meta_file = output_path / f"chunk_{chunk.chunk_id:04d}_meta.yaml"
            with open(meta_file, 'w', encoding='utf-8') as f:
                yaml.dump({
                    'chunk_id': chunk.chunk_id,
                    'start_line': chunk.start_line,
                    'end_line': chunk.end_line,
                    'features': chunk.features,
                    'metadata': chunk.metadata,
                    'overlap_start': chunk.overlap_start,
                    'overlap_end': chunk.overlap_end
                }, f, allow_unicode=True)
        
        # 保存索引文件
        index_file = output_path / "chunks_index.yaml"
        with open(index_file, 'w', encoding='utf-8') as f:
            index_data = {
                'total_chunks': len(chunks),
                'chunks': []
            }
            
            for chunk in chunks:
                index_data['chunks'].append({
                    'id': chunk.chunk_id,
                    'lines': f"{chunk.start_line}-{chunk.end_line}",
                    'features': chunk.features,
                    'size': len(chunk.content)
                })
            
            yaml.dump(index_data, f, allow_unicode=True)
        
        logger.info(f"已保存 {len(chunks)} 个块到: {output_dir}")
    
    def merge_chunks(self, chunks: List[ConfigChunk]) -> str:
        """
        合并配置块
        
        Args:
            chunks: 配置块列表
            
        Returns:
            合并后的文本
        """
        # 按块ID排序
        sorted_chunks = sorted(chunks, key=lambda x: x.chunk_id)
        
        merged_lines = []
        last_end_line = 0
        
        for chunk in sorted_chunks:
            lines = chunk.content.split('\n')
            
            # 处理重叠
            if chunk.overlap_start and chunk.overlap_start <= last_end_line:
                # 跳过重叠部分
                skip_lines = last_end_line - chunk.start_line + 1
                lines = lines[skip_lines:]
            
            merged_lines.extend(lines)
            last_end_line = chunk.end_line
        
        return '\n'.join(merged_lines)


if __name__ == "__main__":
    # 测试分块模块
    chunker = SmartChunker("../config.yaml")
    
    # 创建测试配置文件
    test_config = """# 5GC Network Function Configuration
# Version: 1.0.0
# Date: 2024-01-15

############### SECTION AMF Configuration ###############
BEGIN AMF_CONFIG
amf_name = AMF_01
amf_id = 0x01
region_id = 0x02
set_id = 0x001
plmn_list = 46000,46001,46002
supported_tac = 0x0001,0x0002

[AMF_NETWORK]
n2_interface_ip = 192.168.100.10
n2_interface_port = 38412
sbi_interface_ip = 192.168.200.10
sbi_interface_port = 8080

[AMF_SECURITY]
encryption_algorithm = AES256
integrity_algorithm = SHA256
key_management = enabled
END AMF_CONFIG

############### SECTION SMF Configuration ###############
BEGIN SMF_CONFIG
smf_name = SMF_01
smf_id = 0x02
dnn_list = internet,ims,mms

[SMF_NETWORK]
n4_interface_ip = 192.168.100.20
n4_interface_port = 8805
sbi_interface_ip = 192.168.200.20
sbi_interface_port = 8080

[SMF_SESSION]
max_sessions = 100000
session_timeout = 3600
idle_timeout = 300
END SMF_CONFIG

############### SECTION UPF Configuration ###############
BEGIN UPF_CONFIG
upf_name = UPF_01
upf_id = 0x03

[UPF_NETWORK]
n3_interface_ip = 192.168.100.30
n3_interface_port = 2152
n4_interface_ip = 192.168.100.31
n4_interface_port = 8805
n6_interface_ip = 10.0.0.1
n6_interface_gateway = 10.0.0.254

[UPF_DATAPATH]
forwarding_mode = fast_path
buffer_size = 65536
max_throughput = 10Gbps
END UPF_CONFIG
""" * 20  # 复制20次以创建大文件
    
    # 测试智能分块
    print("测试智能分块策略")
    print("="*50)
    chunks = chunker.chunk_text(test_config)
    
    print(f"生成块数: {len(chunks)}")
    for i, chunk in enumerate(chunks[:3]):  # 只显示前3个块
        print(f"\n块 {chunk.chunk_id}:")
        print(f"  行范围: {chunk.start_line}-{chunk.end_line}")
        print(f"  特征: {chunk.features[:5]}...")  # 只显示前5个特征
        print(f"  内容长度: {len(chunk.content)} 字符")
    
    # 保存分块结果
    chunker.save_chunks(chunks, "./output/chunks")
    
    # 测试合并
    print("\n测试块合并")
    print("="*50)
    merged = chunker.merge_chunks(chunks)
    print(f"原始长度: {len(test_config)}")
    print(f"合并后长度: {len(merged)}")
    print(f"长度差异: {abs(len(test_config) - len(merged))}")
