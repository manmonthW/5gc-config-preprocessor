#!/usr/bin/env python3
"""
配置预处理模块快速启动脚本
提供命令行接口和使用示例
"""

import sys
import argparse
import logging
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from preprocessor import ConfigPreProcessor
from desensitizer import ConfigDesensitizer
from format_converter import FormatConverter
from chunker import SmartChunker

def setup_logging(verbose: bool = False):
    """设置日志"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def create_sample_config():
    """创建示例配置文件"""
    sample_config = """# 5GC Network Configuration Sample
# Project: Beijing-Mobile-5GC
# Customer: China Mobile
# Version: 1.0.0
# Date: 2024-01-15 10:30:00

############### Global Configuration ###############
[GLOBAL]
site_id = BJ001
region = North-China
deployment_type = distributed
redundancy = active-standby

############### AMF Configuration ###############
[AMF_CONFIG]
amf_name = AMF_BJ_01
amf_id = 0x0001
plmn_id = 46000
region_id = 0x02
set_id = 0x001

# Network Configuration
amf_ip = 192.168.100.10
amf_port = 38412
sbi_ip = 192.168.200.10
sbi_port = 8080

# Security Settings
security_algorithm = AES256
integrity_check = enabled
admin_password = Admin@123456
api_key = sk-1234567890abcdef

# Subscriber Data
test_imsi = 460001234567890
test_phone = 13812345678

############### SMF Configuration ###############
[SMF_CONFIG]
smf_name = SMF_BJ_01
smf_id = 0x0002
supported_dnn = internet,ims,mms

# Network Configuration
n4_interface_ip = 192.168.100.20
n4_interface_port = 8805
pfcp_heartbeat = 60

# Session Management
max_sessions = 100000
session_timeout = 3600
idle_timeout = 300

# QoS Configuration
default_qos_profile = standard
max_bandwidth_mbps = 1000

############### UPF Configuration ###############
[UPF_CONFIG]
upf_name = UPF_BJ_01
upf_id = 0x0003

# Data Path Configuration
n3_interface_ip = 192.168.100.30
n3_interface_port = 2152
n6_gateway = 10.0.0.254
forwarding_mode = enhanced

# Performance Settings
buffer_size = 65536
max_throughput = 10Gbps
packet_detection_rules = enabled

############### NRF Configuration ###############
[NRF_CONFIG]
nrf_name = NRF_BJ_01
nrf_fqdn = nrf.5gc.mnc000.mcc460.3gppnetwork.org
nrf_ip = 192.168.200.100
nrf_port = 8080

# Service Discovery
service_discovery = enabled
heartbeat_interval = 10
registration_ttl = 3600

############### Slice Configuration ###############
[SLICE_CONFIG]
slice_1_sst = 1
slice_1_sd = 0x000001
slice_1_name = eMBB

slice_2_sst = 2
slice_2_sd = 0x000002
slice_2_name = URLLC

############### Monitoring ###############
[MONITORING]
metrics_enabled = true
metrics_endpoint = https://monitoring.example.com/metrics
alert_email = ops@example.com
log_level = INFO
"""
    
    with open("sample_5gc_config.txt", "w", encoding="utf-8") as f:
        f.write(sample_config)
    
    print("✅ 创建示例配置文件: sample_5gc_config.txt")
    return "sample_5gc_config.txt"

def process_single_file(args):
    """处理单个文件"""
    print(f"\n{'='*60}")
    print(f"开始处理文件: {args.input}")
    print(f"{'='*60}\n")
    
    # 初始化预处理器
    preprocessor = ConfigPreProcessor(args.config)
    
    # 处理文件
    result = preprocessor.process_file(
        args.input,
        desensitize=not args.no_desensitize,
        convert_format=not args.no_convert,
        chunk=not args.no_chunk,
        extract_metadata=not args.no_metadata
    )
    
    # 显示结果
    if result.success:
        print("\n✅ 预处理成功！")
        print(f"处理时间: {result.processing_time:.2f} 秒")
        print(f"原始格式: {result.original_format}")
        print(f"\n生成的文件 ({len(result.processed_files)} 个):")
        for file in result.processed_files:
            print(f"  📄 {file}")
        
        if result.metadata:
            print(f"\n元数据:")
            for key, value in result.metadata.items():
                if isinstance(value, dict):
                    print(f"  {key}:")
                    for k, v in value.items():
                        print(f"    - {k}: {v}")
                else:
                    print(f"  {key}: {value}")
        
        if result.statistics:
            print(f"\n统计信息:")
            for key, value in result.statistics.items():
                print(f"  {key}: {value}")
    else:
        print("\n❌ 预处理失败！")
        print(f"错误信息:")
        for error in result.errors:
            print(f"  - {error}")

def process_directory(args):
    """处理目录"""
    print(f"\n{'='*60}")
    print(f"开始处理目录: {args.input}")
    print(f"文件模式: {args.pattern}")
    print(f"递归处理: {args.recursive}")
    print(f"{'='*60}\n")
    
    # 初始化预处理器
    preprocessor = ConfigPreProcessor(args.config)
    
    # 处理目录
    results = preprocessor.process_directory(
        args.input,
        pattern=args.pattern,
        recursive=args.recursive
    )
    
    # 显示汇总
    successful = sum(1 for r in results if r.success)
    failed = sum(1 for r in results if not r.success)
    
    print(f"\n{'='*60}")
    print(f"处理完成！")
    print(f"成功: {successful} 个文件")
    print(f"失败: {failed} 个文件")
    print(f"总处理时间: {sum(r.processing_time for r in results):.2f} 秒")
    print(f"{'='*60}")

def test_desensitizer():
    """测试脱敏功能"""
    print("\n" + "="*60)
    print("测试脱敏功能")
    print("="*60 + "\n")
    
    desensitizer = ConfigDesensitizer("config.yaml")
    
    test_text = """
    # 测试配置
    server_ip = 192.168.1.100
    customer = China Mobile
    admin_password = MySecret123
    test_phone = 13812345678
    test_imsi = 460001234567890
    api_url = https://api.customer.com/v1/service
    """
    
    print("原始文本:")
    print(test_text)
    
    result, mapping = desensitizer.desensitize_text(test_text)
    
    print("\n脱敏后文本:")
    print(result)
    
    print("\n脱敏映射:")
    for category, items in mapping.items():
        if items:
            print(f"  {category}: {len(items)} 项")

def test_converter():
    """测试格式转换功能"""
    print("\n" + "="*60)
    print("测试格式转换功能")
    print("="*60 + "\n")
    
    converter = FormatConverter("config.yaml")
    
    # 创建测试XML文件
    xml_content = """<?xml version="1.0"?>
    <config>
        <network>
            <ip>192.168.1.100</ip>
            <port>8080</port>
        </network>
    </config>"""
    
    with open("test.xml", "w") as f:
        f.write(xml_content)
    
    # 测试格式检测
    format_type = converter.detect_format("test.xml")
    print(f"检测到格式: {format_type.value}")
    
    # 测试转换
    unified = converter.process_file("test.xml")
    print(f"转换成功！")
    print(f"配置结构: {list(unified['config'].keys())}")
    
    # 清理
    Path("test.xml").unlink()

def test_chunker():
    """测试分块功能"""
    print("\n" + "="*60)
    print("测试分块功能")
    print("="*60 + "\n")
    
    chunker = SmartChunker("config.yaml")
    
    # 创建大文本
    test_text = "Line {}\n" * 10000
    test_text = test_text.format(*range(10000))
    
    chunks = chunker.chunk_text(test_text)
    print(f"生成 {len(chunks)} 个块")
    
    for i, chunk in enumerate(chunks[:3]):
        print(f"\n块 {chunk.chunk_id}:")
        print(f"  行范围: {chunk.start_line}-{chunk.end_line}")
        print(f"  内容长度: {len(chunk.content)} 字符")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="5GC配置文件预处理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 处理单个文件
  python quick_start.py -i sample_5gc_config.txt
  
  # 处理目录
  python quick_start.py -i ./configs/ -d
  
  # 只进行脱敏
  python quick_start.py -i config.txt --no-convert --no-chunk
  
  # 创建示例文件
  python quick_start.py --create-sample
  
  # 运行测试
  python quick_start.py --test
        """
    )
    
    parser.add_argument('-i', '--input', 
                       help='输入文件或目录路径')
    parser.add_argument('-c', '--config', 
                       default='config.yaml',
                       help='配置文件路径 (默认: config.yaml)')
    parser.add_argument('-d', '--directory', 
                       action='store_true',
                       help='处理目录而不是单个文件')
    parser.add_argument('-p', '--pattern', 
                       default='*.txt',
                       help='文件匹配模式 (默认: *.txt)')
    parser.add_argument('-r', '--recursive', 
                       action='store_true',
                       help='递归处理子目录')
    parser.add_argument('-v', '--verbose', 
                       action='store_true',
                       help='显示详细日志')
    
    # 处理选项
    parser.add_argument('--no-desensitize', 
                       action='store_true',
                       help='跳过脱敏处理')
    parser.add_argument('--no-convert', 
                       action='store_true',
                       help='跳过格式转换')
    parser.add_argument('--no-chunk', 
                       action='store_true',
                       help='跳过分块处理')
    parser.add_argument('--no-metadata', 
                       action='store_true',
                       help='跳过元数据提取')
    
    # 特殊命令
    parser.add_argument('--create-sample', 
                       action='store_true',
                       help='创建示例配置文件')
    parser.add_argument('--test', 
                       action='store_true',
                       help='运行功能测试')
    
    args = parser.parse_args()
    
    # 设置日志
    setup_logging(args.verbose)
    
    # 执行命令
    if args.create_sample:
        sample_file = create_sample_config()
        print(f"\n提示: 现在可以运行以下命令处理示例文件:")
        print(f"  python quick_start.py -i {sample_file}")
    
    elif args.test:
        print("\n运行功能测试...")
        test_desensitizer()
        test_converter()
        test_chunker()
        print("\n✅ 所有测试完成！")
    
    elif args.input:
        if args.directory:
            process_directory(args)
        else:
            process_single_file(args)
    
    else:
        print("欢迎使用5GC配置预处理工具！\n")
        print("快速开始:")
        print("1. 创建示例文件: python quick_start.py --create-sample")
        print("2. 处理示例文件: python quick_start.py -i sample_5gc_config.txt")
        print("\n更多帮助: python quick_start.py --help")

if __name__ == "__main__":
    main()
