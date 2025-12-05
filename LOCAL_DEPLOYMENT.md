# 本地部署指南 (非Docker)

本文档介绍如何在本地Windows/Linux/macOS系统上部署5GC配置预处理器，无需Docker。

---

## 📋 前置要求

### 1. Python环境

**必需版本**: Python 3.8 或更高版本

**检查Python版本**:
```bash
python --version
# 或
python3 --version
```

如果未安装Python，请从 [python.org](https://www.python.org/downloads/) 下载安装。

### 2. 安装依赖包

```bash
# 克隆或下载项目
git clone https://github.com/manmonthW/5gc-config-preprocessor.git
cd config_preprocessor

# 安装所有依赖
pip install -r requirements.txt
```

**依赖包列表**:
- `pyyaml` - YAML文件处理
- `xmltodict` - XML转JSON
- `chardet` - 字符编码检测
- `lxml` - XML解析加速

---

## 🚀 部署方式

### 方式1: 命令行模式 (推荐用于批处理)

**适用场景**: 本地文件处理、批量处理、脚本自动化

#### 基本使用

```bash
python quick_start.py -i <配置文件路径>
```

#### 完整参数说明

```bash
python quick_start.py \
  -i input_file.xml \              # 输入文件
  -o output_dir \                   # 输出目录(可选)
  --no-desensitize \                # 禁用脱敏(可选)
  --no-convert \                    # 禁用格式转换(可选)
  --no-chunk \                      # 禁用分块(可选)
  --no-metadata                     # 禁用元数据提取(可选)
```

#### 使用示例

**1. 处理单个配置文件**:
```bash
python quick_start.py -i config.yaml
```

**2. 只做脱敏处理**:
```bash
python quick_start.py -i config.xml --no-convert --no-chunk --no-metadata
```

**3. 指定输出目录**:
```bash
python quick_start.py -i config.json -o D:\output\myproject
```

**4. 批量处理多个文件**:
```bash
# Windows批处理
for %%f in (*.xml) do python quick_start.py -i %%f

# Linux/macOS
for file in *.xml; do python quick_start.py -i "$file"; done
```

#### 输出位置

默认输出目录: `output/YYYYMMDD_HHMMSS/文件名/`

例如:
```
output/
└── 20251205_150000/
    └── config/
        ├── config_unified.json
        ├── config_metadata.json
        ├── config_desensitized.txt
        └── ...
```

---

### 方式2: API服务器模式 (推荐用于Web应用)

**适用场景**: 提供HTTP API、前端调用、远程访问

#### 启动API服务器

```bash
python start_server.py
```

**默认配置**:
- 端口: `8000`
- 访问地址: `http://localhost:8000/api`

#### 自定义端口

**方法1: 环境变量**
```bash
# Windows
set PORT=9000
python start_server.py

# Linux/macOS
PORT=9000 python start_server.py
```

**方法2: 修改start_server.py**
```python
# 编辑 start_server.py
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 9000))  # 改为9000
    run_server(port)
```

#### API使用示例

**1. 获取API信息** (GET请求):
```bash
curl http://localhost:8000/api
```

**2. 上传并处理文件** (POST请求):

**使用curl**:
```bash
# Windows (PowerShell)
$content = [Convert]::ToBase64String([IO.File]::ReadAllBytes("config.yaml"))
$json = @{
    file_content = $content
    filename = "config.yaml"
    options = @{
        desensitize = $true
        convert_format = $true
        chunk = $false
        extract_metadata = $true
    }
} | ConvertTo-Json

Invoke-RestMethod -Uri http://localhost:8000/api -Method POST -Body $json -ContentType "application/json"

# Linux/macOS
curl -X POST http://localhost:8000/api \
  -H "Content-Type: application/json" \
  -d "{
    \"file_content\": \"$(base64 -w 0 config.yaml)\",
    \"filename\": \"config.yaml\",
    \"options\": {
      \"desensitize\": true,
      \"convert_format\": true,
      \"chunk\": false,
      \"extract_metadata\": true
    }
  }"
```

**使用Python脚本**:
```python
import base64
import requests

# 读取文件
with open('config.yaml', 'rb') as f:
    file_content = base64.b64encode(f.read()).decode('utf-8')

# 发送请求
response = requests.post(
    'http://localhost:8000/api',
    json={
        'file_content': file_content,
        'filename': 'config.yaml',
        'options': {
            'desensitize': True,
            'convert_format': True,
            'chunk': False,
            'extract_metadata': True
        }
    }
)

result = response.json()
print(f"处理状态: {result['success']}")
print(f"输出目录: {result['output_directory']}")
```

---

### 方式3: Web界面模式

**适用场景**: 图形化操作、非技术人员使用

#### 方法A: 使用内置Web服务器

**1. 启动API服务器**:
```bash
python start_server.py
```

**2. 启动Web服务器** (新终端):
```bash
# 进入public目录
cd public

# 启动简单HTTP服务器
# Python 3.x
python -m http.server 8080

# Python 2.x
python -m SimpleHTTPServer 8080
```

**3. 访问Web界面**:
打开浏览器访问: `http://localhost:8080`

#### 方法B: 使用nginx (推荐用于生产环境)

**1. 安装nginx**:
- Windows: 下载 [nginx for Windows](https://nginx.org/en/download.html)
- Linux: `sudo apt-get install nginx`
- macOS: `brew install nginx`

**2. 配置nginx**:

创建配置文件 `nginx-local.conf`:
```nginx
events {
    worker_connections 1024;
}

http {
    include       mime.types;
    default_type  application/octet-stream;

    server {
        listen 8080;
        server_name localhost;

        # 静态文件
        location / {
            root E:/xconfig/config_preprocessor/public;  # 修改为你的路径
            index index.html;
        }

        # API代理
        location /api {
            proxy_pass http://localhost:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
    }
}
```

**3. 启动nginx**:
```bash
# Windows
nginx.exe -c E:\path\to\nginx-local.conf

# Linux/macOS
nginx -c /path/to/nginx-local.conf
```

**4. 访问**:
- Web界面: `http://localhost:8080`
- API接口: `http://localhost:8080/api`

---

### 方式4: 集成到Python程序

**适用场景**: 嵌入到现有Python应用、自定义业务逻辑

```python
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, 'E:/xconfig/config_preprocessor/src')

from preprocessor import ConfigPreProcessor

# 初始化预处理器
preprocessor = ConfigPreProcessor('config.yaml')

# 处理文件
result = preprocessor.process_file(
    'input.xml',
    desensitize=True,
    convert_format=True,
    chunk=True,
    extract_metadata=True
)

if result.success:
    print(f"处理成功！")
    print(f"输出目录: {result.output_directory}")
    print(f"生成文件: {len(result.processed_files)} 个")

    # 访问处理结果
    print(f"\n元数据:")
    print(f"- 网络功能: {result.metadata.get('5gc_info', {}).get('network_functions', {})}")

    print(f"\n脱敏统计:")
    stats = result.statistics.get('desensitization', {})
    print(f"- 总替换数: {stats.get('total_replacements', 0)}")
else:
    print(f"处理失败: {result.message}")
```

---

## 🔧 高级配置

### 1. 修改配置文件

编辑 `config.yaml`:

```yaml
# 输出目录设置
output:
  base_directory: "output"  # 修改输出根目录
  use_timestamp: true       # 是否使用时间戳子目录

# 文件处理设置
file_processing:
  max_file_size_mb: 500     # 最大文件大小
  supported_formats:
    - yaml
    - json
    - xml
    - txt

# 脱敏设置
desensitization:
  patterns:
    ip_addresses: true      # IP地址脱敏
    passwords: true         # 密码脱敏
    imsi: true             # IMSI脱敏
    # ... 更多设置

# 性能设置
performance:
  memory_limit_mb: 2048     # 内存限制
  enable_parallel: true     # 启用并行处理
  max_workers: 4            # 最大工作线程数

# 分块设置
chunking:
  enabled: true
  chunk_size_lines: 5000    # 每块行数
  chunk_size_kb: 1024       # 每块大小(KB)
```

### 2. 日志配置

**查看日志**:
```bash
# 日志文件位置
ls logs/

# 查看最新日志
cat logs/preprocessor_YYYYMMDD.log
```

**修改日志级别** (在代码中):
```python
# src/utils/logger.py
import logging

# 修改为DEBUG可查看更详细日志
logging.basicConfig(level=logging.DEBUG)
```

### 3. 性能优化

**优化内存占用**:
```yaml
# config.yaml
performance:
  memory_limit_mb: 1024     # 降低内存限制

chunking:
  chunk_size_lines: 2000    # 减小分块大小
```

**提升处理速度**:
```yaml
performance:
  enable_parallel: true
  max_workers: 8            # 增加工作线程(根据CPU核心数)
```

---

## 🖥️ 后台运行

### Windows

**方法1: 使用PowerShell后台任务**
```powershell
# 启动后台任务
Start-Process python -ArgumentList "start_server.py" -WindowStyle Hidden

# 查看运行中的Python进程
Get-Process python

# 停止服务
Stop-Process -Name python
```

**方法2: 创建Windows服务** (使用NSSM)

1. 下载 [NSSM](https://nssm.cc/download)
2. 安装服务:
```cmd
nssm install ConfigPreprocessor "C:\Python39\python.exe" "E:\xconfig\config_preprocessor\start_server.py"
nssm start ConfigPreprocessor
```

### Linux/macOS

**方法1: 使用nohup**
```bash
# 后台启动
nohup python start_server.py > server.log 2>&1 &

# 查看进程
ps aux | grep start_server.py

# 停止服务
kill <PID>
```

**方法2: 使用systemd** (Linux)

创建 `/etc/systemd/system/config-preprocessor.service`:
```ini
[Unit]
Description=5GC Config Preprocessor API
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/config_preprocessor
ExecStart=/usr/bin/python3 start_server.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

启动服务:
```bash
sudo systemctl daemon-reload
sudo systemctl start config-preprocessor
sudo systemctl enable config-preprocessor  # 开机自启
sudo systemctl status config-preprocessor
```

**方法3: 使用screen/tmux**
```bash
# 创建screen会话
screen -S preprocessor

# 启动服务
python start_server.py

# 按 Ctrl+A 然后按 D 脱离会话

# 恢复会话
screen -r preprocessor
```

---

## 📱 远程访问配置

### 1. 允许外部访问

**修改start_server.py**:
```python
def run_server(port=8000, host='0.0.0.0'):  # 改为0.0.0.0
    server_address = (host, port)
    httpd = HTTPServer(server_address, handler)
    # ...
```

### 2. 防火墙设置

**Windows**:
```cmd
# 允许端口8000
netsh advfirewall firewall add rule name="Config Preprocessor" dir=in action=allow protocol=TCP localport=8000
```

**Linux**:
```bash
# UFW
sudo ufw allow 8000/tcp

# iptables
sudo iptables -A INPUT -p tcp --dport 8000 -j ACCEPT
```

### 3. 内网穿透 (可选)

使用 [ngrok](https://ngrok.com/) 实现外网访问:
```bash
# 安装ngrok
# 下载: https://ngrok.com/download

# 启动隧道
ngrok http 8000
```

---

## 🔒 安全建议

### 1. 访问控制

**添加简单认证** (修改api/index.py):
```python
def do_POST(self):
    # 检查Authorization header
    auth = self.headers.get('Authorization')
    if auth != 'Bearer your-secret-token':
        self.send_error_response(401, 'Unauthorized')
        return

    # 原有处理逻辑...
```

### 2. HTTPS支持

使用 [Let's Encrypt](https://letsencrypt.org/) 或自签名证书

### 3. 限制访问来源

**使用nginx限制IP**:
```nginx
location /api {
    allow 192.168.1.0/24;
    deny all;
    proxy_pass http://localhost:8000;
}
```

---

## 🧪 测试部署

### 1. 测试命令行模式

```bash
# 测试处理功能
python quick_start.py -i test-upload.yaml

# 检查输出
ls output/
```

### 2. 测试API模式

```bash
# 启动服务器
python start_server.py

# 新开终端，测试API
curl http://localhost:8000/api

# 应该返回API信息
```

### 3. 性能测试

```bash
# 测试大文件处理
python quick_start.py -i large_file.xml

# 查看处理时间和内存占用
```

---

## ❓ 常见问题

### Q1: 提示模块未找到

**问题**: `ModuleNotFoundError: No module named 'yaml'`

**解决**:
```bash
pip install pyyaml
# 或安装所有依赖
pip install -r requirements.txt
```

### Q2: 端口被占用

**问题**: `OSError: [Errno 48] Address already in use`

**解决**:
```bash
# 查找占用端口的进程
# Windows
netstat -ano | findstr :8000

# Linux/macOS
lsof -i :8000

# 修改端口
PORT=9000 python start_server.py
```

### Q3: Windows控制台显示乱码

**问题**: 中文显示为乱码或问号

**解决**:
```cmd
# 设置控制台编码为UTF-8
chcp 65001

# 或使用输出重定向
python quick_start.py -i config.xml > output.log 2>&1
```

### Q4: 文件权限问题

**问题**: `PermissionError: [Errno 13] Permission denied`

**解决**:
```bash
# 检查output目录权限
chmod 755 output/

# 或指定有权限的输出目录
python quick_start.py -i config.xml -o ~/my_output
```

---

## 📊 部署方式对比

| 特性 | 命令行模式 | API服务器 | Web界面 | 集成模式 |
|------|-----------|----------|---------|---------|
| 易用性 | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| 批量处理 | ✅ 优秀 | ⚠️ 一般 | ❌ 不支持 | ✅ 优秀 |
| 远程访问 | ❌ | ✅ | ✅ | ❌ |
| 资源占用 | 低 | 中 | 中 | 低 |
| 适用场景 | 脚本自动化 | Web应用 | 手动操作 | 二次开发 |
| 启动速度 | 即时 | 需常驻 | 需常驻 | 即时 |

---

## 🎯 推荐配置

### 个人本地使用
```bash
# 使用命令行模式
python quick_start.py -i config.xml
```

### 团队内网共享
```bash
# 启动API服务器 + Web界面
python start_server.py
# 访问: http://your-ip:8000
```

### 生产环境部署
```bash
# 使用nginx + systemd服务
# 配置HTTPS + 访问控制
```

---

## 📚 相关文档

- [Docker部署指南](DOCKER_DEPLOYMENT.md)
- [输出文件说明](OUTPUT_FILES_EXPLANATION.md)
- [文件大小限制](FILE_SIZE_LIMITS.md)
- [API使用文档](api/README.md)

---

**最后更新**: 2025-12-05
**维护者**: Claude Code
