#!/usr/bin/env python3
"""
启动HTTP API服务器
"""

import sys
import os
from pathlib import Path
from http.server import HTTPServer

# 添加路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir / 'src'))
sys.path.insert(0, str(current_dir / 'api'))
sys.path.insert(0, str(current_dir / 'debug'))

# 导入handler
from api.index import handler

def run_server(port=8000):
    """运行HTTP服务器"""
    server_address = ('', port)
    httpd = HTTPServer(server_address, handler)

    print(f"🚀 5GC配置预处理API服务器启动")
    print(f"📡 监听端口: {port}")
    print(f"🌐 访问地址: http://localhost:{port}/api")
    print(f"📝 API文档: http://localhost:{port}/api (GET请求)")
    print(f"✨ 按Ctrl+C停止服务器\n")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 服务器已停止")
        httpd.server_close()

if __name__ == '__main__':
    # 从环境变量获取端口，默认8000
    port = int(os.environ.get('PORT', 8000))
    run_server(port)
