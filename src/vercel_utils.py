#!/usr/bin/env python3
"""
Vercel Serverless 环境工具模块
用于检测环境和处理内存文件
"""
import os
import io
import zipfile
import base64
from typing import Dict, Optional, Tuple
from pathlib import Path


def is_vercel_environment() -> bool:
    """
    检测是否在 Vercel Serverless 环境中运行

    Returns:
        bool: True 表示在 Vercel 环境
    """
    # 检测多个 Vercel 环境变量
    vercel_indicators = [
        os.environ.get('VERCEL') == '1',
        os.environ.get('VERCEL_URL') is not None,
        os.environ.get('VERCEL_ENV') is not None,
        os.environ.get('NOW_REGION') is not None,  # Vercel (原 Now.sh) 的另一个标识
    ]

    return any(vercel_indicators)


def create_zip_in_memory(files: Dict[str, bytes], base_filename: str = "output") -> bytes:
    """
    在内存中创建 ZIP 文件

    Args:
        files: 文件字典 {文件名: 文件内容(bytes)}
        base_filename: ZIP 内部基础目录名

    Returns:
        bytes: ZIP 文件的二进制内容
    """
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for filename, content in files.items():
            # 确保内容是 bytes
            if isinstance(content, str):
                content = content.encode('utf-8')

            # 添加到 ZIP，保持原始文件名结构
            zip_file.writestr(filename, content)

    zip_buffer.seek(0)
    return zip_buffer.getvalue()


def encode_to_base64(content: bytes) -> str:
    """
    将二进制内容编码为 base64 字符串

    Args:
        content: 二进制内容

    Returns:
        str: base64 编码的字符串
    """
    return base64.b64encode(content).decode('ascii')


def prepare_vercel_response(
    files: Dict[str, bytes],
    original_filename: str,
    success: bool = True,
    message: str = "File processed successfully"
) -> Dict:
    """
    准备 Vercel 环境的响应数据

    Args:
        files: 处理后的文件字典 {文件名: 内容}
        original_filename: 原始文件名
        success: 是否成功
        message: 处理消息

    Returns:
        dict: 包含 base64 编码内容的响应字典
    """
    if not success:
        return {
            'success': False,
            'error': message
        }

    # 如果只有一个文件，直接返回
    if len(files) == 1:
        filename, content = list(files.items())[0]

        # 确保是 bytes
        if isinstance(content, str):
            content = content.encode('utf-8')

        return {
            'success': True,
            'filename': filename,
            'content_base64': encode_to_base64(content),
            'message': message,
            'file_count': 1
        }

    # 多个文件，打包成 ZIP
    zip_content = create_zip_in_memory(files, Path(original_filename).stem)
    zip_filename = f"{Path(original_filename).stem}_processed.zip"

    return {
        'success': True,
        'filename': zip_filename,
        'content_base64': encode_to_base64(zip_content),
        'message': message,
        'file_count': len(files),
        'files_included': list(files.keys())
    }


def read_file_to_memory(file_path: str) -> bytes:
    """
    读取文件到内存

    Args:
        file_path: 文件路径

    Returns:
        bytes: 文件内容
    """
    with open(file_path, 'rb') as f:
        return f.read()


def get_file_extension(filename: str) -> str:
    """
    获取文件扩展名

    Args:
        filename: 文件名

    Returns:
        str: 扩展名（小写，不含点）
    """
    return Path(filename).suffix.lower().lstrip('.')


def determine_content_type(filename: str) -> str:
    """
    根据文件名确定 MIME 类型

    Args:
        filename: 文件名

    Returns:
        str: MIME 类型
    """
    ext = get_file_extension(filename)

    content_types = {
        'yaml': 'application/x-yaml',
        'yml': 'application/x-yaml',
        'json': 'application/json',
        'xml': 'application/xml',
        'txt': 'text/plain',
        'ini': 'text/plain',
        'zip': 'application/zip',
    }

    return content_types.get(ext, 'application/octet-stream')


class MemoryFileWriter:
    """
    内存文件写入器
    用于在内存中模拟文件写入操作
    """

    def __init__(self):
        self.files: Dict[str, io.BytesIO] = {}

    def open(self, filename: str, mode: str = 'w') -> io.BytesIO:
        """
        打开一个内存文件用于写入

        Args:
            filename: 文件名
            mode: 打开模式 ('w', 'wb', 'a', 'ab')

        Returns:
            io.BytesIO: 内存缓冲区
        """
        if filename not in self.files:
            self.files[filename] = io.BytesIO()

        # 如果是追加模式，seek 到末尾
        if 'a' in mode:
            self.files[filename].seek(0, 2)
        else:
            # 否则清空现有内容
            self.files[filename] = io.BytesIO()

        return self.files[filename]

    def write(self, filename: str, content: bytes):
        """
        直接写入内容到内存文件

        Args:
            filename: 文件名
            content: 内容
        """
        buffer = self.open(filename, 'wb')
        if isinstance(content, str):
            content = content.encode('utf-8')
        buffer.write(content)
        buffer.seek(0)

    def get_files(self) -> Dict[str, bytes]:
        """
        获取所有文件内容

        Returns:
            dict: {文件名: 内容(bytes)}
        """
        result = {}
        for filename, buffer in self.files.items():
            buffer.seek(0)
            result[filename] = buffer.read()
        return result

    def get_file(self, filename: str) -> Optional[bytes]:
        """
        获取单个文件内容

        Args:
            filename: 文件名

        Returns:
            bytes: 文件内容，如果不存在返回 None
        """
        if filename in self.files:
            buffer = self.files[filename]
            buffer.seek(0)
            return buffer.read()
        return None

    def clear(self):
        """清空所有文件"""
        self.files.clear()

    def file_count(self) -> int:
        """获取文件数量"""
        return len(self.files)


if __name__ == '__main__':
    # 测试代码
    print("=== Vercel 环境检测 ===")
    print(f"是否在 Vercel 环境: {is_vercel_environment()}")

    print("\n=== 内存文件写入测试 ===")
    writer = MemoryFileWriter()

    # 写入测试文件
    writer.write('test1.txt', b'Hello World')
    writer.write('test2.json', '{"key": "value"}'.encode())

    print(f"文件数量: {writer.file_count()}")
    print(f"文件列表: {list(writer.get_files().keys())}")

    print("\n=== ZIP 打包测试 ===")
    files = writer.get_files()
    zip_content = create_zip_in_memory(files, 'test')
    print(f"ZIP 大小: {len(zip_content)} bytes")

    print("\n=== Vercel 响应准备测试 ===")
    response = prepare_vercel_response(files, 'test.yaml', success=True)
    print(f"响应包含字段: {list(response.keys())}")
    print(f"文件名: {response['filename']}")
    print(f"Base64 长度: {len(response['content_base64'])}")
