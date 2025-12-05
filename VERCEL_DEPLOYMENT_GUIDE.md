# Vercel Serverless 部署指南

## 📋 目录

- [概述](#概述)
- [核心特性](#核心特性)
- [架构设计](#架构设计)
- [部署步骤](#部署步骤)
- [环境检测机制](#环境检测机制)
- [API 使用](#api-使用)
- [前端集成](#前端集成)
- [测试验证](#测试验证)
- [故障排除](#故障排除)

---

## 📖 概述

本项目已完成 **Vercel Serverless Function** 适配，支持：

✅ **双模式运行**
- **本地模式**: 继续写入文件到 `output/`，返回文件路径
- **Vercel 模式**: 无文件写入，内存处理，返回 base64 编码内容

✅ **自动环境检测**
- 自动识别 Vercel 环境（通过环境变量）
- 无需手动配置，开箱即用

✅ **完整功能支持**
- 格式转换（XML/YAML/JSON/INI）
- 智能脱敏
- 元数据提取
- 智能分块（可选）

✅ **智能输出**
- 单文件：直接 base64 返回
- 多文件：自动打包为 ZIP

---

## 🌟 核心特性

### 1. 环境隔离

```python
# 自动检测环境
is_vercel = is_vercel_environment()

if is_vercel:
    # Vercel 模式：内存处理
    result = preprocessor.process_file(file_path, memory_mode=True)
else:
    # 本地模式：磁盘写入
    result = preprocessor.process_file(file_path, memory_mode=False)
```

### 2. 内存模式处理

```python
# Vercel 环境下的处理流程
1. 上传文件 → /tmp/
2. 处理文件 → /tmp/ (仍然写入，但不返回路径)
3. 读取到内存 → memory_files = {filename: content}
4. 打包（如需要） → ZIP in memory
5. 返回 base64 → JSON response
```

### 3. 响应格式

**Vercel 环境响应** (单文件):
```json
{
  "success": true,
  "filename": "config_desensitized.txt",
  "content_base64": "VGhpcyBpcyBiYXNlNjQgY29udGVudA==",
  "message": "File processed successfully",
  "file_count": 1,
  "metadata": {...},
  "statistics": {...},
  "processing_time": 2.45,
  "is_vercel_response": true
}
```

**Vercel 环境响应** (多文件):
```json
{
  "success": true,
  "filename": "config_processed.zip",
  "content_base64": "UEsDBBQAAAAI...",
  "message": "File processed successfully",
  "file_count": 5,
  "files_included": [
    "config_unified.json",
    "config_metadata.json",
    "config_desensitized.txt",
    "config_desensitize_mapping.json",
    "config_report.json"
  ],
  "metadata": {...},
  "is_vercel_response": true
}
```

**本地环境响应** (原有格式):
```json
{
  "success": true,
  "message": "Processing completed successfully",
  "processed_files": [
    "/path/to/output/config_unified.json",
    "/path/to/output/config_metadata.json"
  ],
  "output_directory": "/path/to/output/20251205_150000/config",
  "metadata": {...},
  "is_vercel_response": false
}
```

---

## 🏗️ 架构设计

### 代码结构

```
config_preprocessor/
├── src/
│   ├── preprocessor.py         # 核心处理器（支持 memory_mode）
│   ├── vercel_utils.py         # NEW: Vercel 工具模块
│   ├── desensitizer.py
│   ├── format_converter.py
│   ├── chunker.py
│   └── metadata_extractor.py
├── api/
│   └── index.py                # UPDATED: Vercel 环境检测和响应
├── public/
│   ├── vercel-upload-example.html  # NEW: 完整 Web 示例
│   └── download-example.js         # NEW: JavaScript 代码片段
└── vercel.json                 # Vercel 配置文件
```

### 修改摘要

#### 1. 新增文件

**`src/vercel_utils.py`** - Vercel 工具模块
```python
- is_vercel_environment()        # 环境检测
- prepare_vercel_response()      # 响应准备
- create_zip_in_memory()         # 内存 ZIP
- encode_to_base64()             # Base64 编码
- MemoryFileWriter              # 内存文件写入器
```

#### 2. 修改文件

**`src/preprocessor.py`**
```python
@dataclass
class ProcessingResult:
    # ... 原有字段 ...
    memory_files: Optional[Dict[str, bytes]] = None  # NEW

def process_file(self, ..., memory_mode: bool = False):
    # ... 原有逻辑 ...

    # NEW: 如果 memory_mode=True，读取所有文件到内存
    if memory_mode:
        memory_files = {}
        for file_path in processed_files:
            with open(file_path, 'rb') as f:
                memory_files[filename] = f.read()

    return ProcessingResult(..., memory_files=memory_files)
```

**`api/index.py`**
```python
# NEW: 导入 Vercel 工具
from vercel_utils import is_vercel_environment, prepare_vercel_response

def do_POST(self):
    # NEW: 检测环境
    is_vercel = is_vercel_environment()

    # NEW: 传递 memory_mode
    result = preprocessor.process_file(
        temp_file_path,
        memory_mode=is_vercel
    )

    # NEW: Vercel 环境返回 base64
    if is_vercel and result.memory_files:
        response_data = prepare_vercel_response(
            files=result.memory_files,
            original_filename=filename,
            success=result.success
        )
        self.send_success_response(response_data)
        return

    # 本地环境：原有逻辑
    response_data = {...}  # 返回文件路径
```

---

## 🚀 部署步骤

### 前置要求

- GitHub 账号
- Vercel 账号（免费）
- Git 已安装

### 步骤 1: 准备代码

```bash
# 确保所有改动已提交
git status
git add .
git commit -m "Add Vercel Serverless support"
git push origin main
```

### 步骤 2: 连接 Vercel

1. 访问 [Vercel Dashboard](https://vercel.com/dashboard)
2. 点击 **New Project**
3. 选择 **Import Git Repository**
4. 授权 GitHub 并选择 `5gc-config-preprocessor` 仓库

### 步骤 3: 配置项目

**Framework Preset**: Other（或 None）

**Build & Development Settings**:
- Build Command: （留空）
- Output Directory: `public`
- Install Command: `pip install -r requirements.txt`

**Environment Variables**:
无需额外配置（Vercel 自动设置 `VERCEL=1`）

### 步骤 4: 部署

点击 **Deploy** 按钮

等待部署完成（约 1-2 分钟）

### 步骤 5: 验证部署

访问分配的 URL：`https://your-project.vercel.app/api`

应该看到 API 信息响应

---

## 🔍 环境检测机制

### 检测逻辑

```python
def is_vercel_environment() -> bool:
    """
    检测是否在 Vercel Serverless 环境中运行
    """
    vercel_indicators = [
        os.environ.get('VERCEL') == '1',           # Vercel 标准环境变量
        os.environ.get('VERCEL_URL') is not None,  # Vercel 项目 URL
        os.environ.get('VERCEL_ENV') is not None,  # Vercel 环境类型
        os.environ.get('NOW_REGION') is not None,  # Vercel 区域
    ]

    return any(vercel_indicators)
```

### 验证环境

**本地测试**:
```bash
# 不设置环境变量，应该返回 False
python -c "from src.vercel_utils import is_vercel_environment; print(is_vercel_environment())"
# 输出: False
```

**模拟 Vercel 环境**:
```bash
# 设置 VERCEL=1
export VERCEL=1  # Linux/macOS
set VERCEL=1     # Windows

python -c "from src.vercel_utils import is_vercel_environment; print(is_vercel_environment())"
# 输出: True
```

---

## 📡 API 使用

### 端点信息

- **URL**: `https://your-project.vercel.app/api`
- **方法**: `POST`
- **Content-Type**: `application/json`

### 请求格式

```json
{
  "file_content": "<base64-encoded-file-content>",
  "filename": "config.yaml",
  "options": {
    "desensitize": true,
    "convert_format": true,
    "chunk": false,
    "extract_metadata": true
  }
}
```

### 响应格式

#### 成功响应 (Vercel):

```json
{
  "success": true,
  "filename": "config_processed.zip",
  "content_base64": "UEsDBBQAAAAI...",
  "message": "File processed successfully",
  "file_count": 5,
  "files_included": ["config_unified.json", "..."],
  "metadata": {...},
  "statistics": {...},
  "processing_time": 2.45,
  "is_vercel_response": true
}
```

#### 错误响应:

```json
{
  "success": false,
  "error": "Invalid base64 file content"
}
```

### cURL 示例

```bash
curl -X POST https://your-project.vercel.app/api \
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

### Python 示例

```python
import base64
import requests

# 读取文件
with open('config.yaml', 'rb') as f:
    file_content = base64.b64encode(f.read()).decode('utf-8')

# 发送请求
response = requests.post(
    'https://your-project.vercel.app/api',
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

if result['success']:
    # 下载文件
    import base64
    content = base64.b64decode(result['content_base64'])
    with open(result['filename'], 'wb') as f:
        f.write(content)
    print(f"✅ 下载完成: {result['filename']}")
else:
    print(f"❌ 错误: {result['error']}")
```

---

## 🌐 前端集成

### 方法 1: 原生 JavaScript

```javascript
// 见 public/download-example.js

async function uploadAndProcessFile(file) {
    // 1. 读取文件为 base64
    const base64Content = await fileToBase64(file);

    // 2. 发送请求
    const response = await fetch('/api', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            file_content: base64Content,
            filename: file.name,
            options: {
                desensitize: true,
                convert_format: true,
                chunk: false,
                extract_metadata: true
            }
        })
    });

    const result = await response.json();

    // 3. 下载文件
    if (result.success) {
        downloadFile(result.content_base64, result.filename);
    }
}

function downloadFile(base64Content, filename) {
    const link = document.createElement('a');
    link.href = 'data:application/octet-stream;base64,' + base64Content;
    link.download = filename;
    link.click();
}
```

### 方法 2: React

```jsx
import React, { useState } from 'react';

function FileUploader() {
    const [processing, setProcessing] = useState(false);

    const handleUpload = async (event) => {
        const file = event.target.files[0];
        if (!file) return;

        setProcessing(true);

        try {
            const base64 = await fileToBase64(file);

            const response = await fetch('/api', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    file_content: base64,
                    filename: file.name,
                    options: {
                        desensitize: true,
                        convert_format: true,
                        chunk: false,
                        extract_metadata: true
                    }
                })
            });

            const result = await response.json();

            if (result.success) {
                // 触发下载
                const link = document.createElement('a');
                link.href = `data:application/octet-stream;base64,${result.content_base64}`;
                link.download = result.filename;
                link.click();

                alert('处理成功！');
            }
        } catch (error) {
            alert(`错误: ${error.message}`);
        } finally {
            setProcessing(false);
        }
    };

    return (
        <div>
            <input
                type="file"
                onChange={handleUpload}
                disabled={processing}
                accept=".xml,.yaml,.yml,.json,.ini,.txt"
            />
            {processing && <p>处理中...</p>}
        </div>
    );
}

async function fileToBase64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => {
            const base64 = reader.result.split(',')[1];
            resolve(base64);
        };
        reader.onerror = reject;
        reader.readAsDataURL(file);
    });
}
```

### 方法 3: 完整 HTML 页面

见 `public/vercel-upload-example.html` - 包含：
- ✅ 拖拽上传
- ✅ 进度显示
- ✅ 选项配置
- ✅ 结果展示
- ✅ 自动下载

---

## 🧪 测试验证

### 1. 本地测试

```bash
# 启动本地服务器
python start_server.py

# 访问测试页面
open http://localhost:8000/vercel-upload-example.html

# 上传文件测试
# 应该返回本地路径 (is_vercel_response: false)
```

### 2. Vercel 环境测试

```bash
# 访问 Vercel 部署的 URL
open https://your-project.vercel.app/vercel-upload-example.html

# 上传文件测试
# 应该下载文件 (is_vercel_response: true)
```

### 3. 功能测试清单

- [ ] 上传 XML 文件
- [ ] 上传 YAML 文件
- [ ] 上传 JSON 文件
- [ ] 测试脱敏功能
- [ ] 测试格式转换
- [ ] 测试元数据提取
- [ ] 测试分块功能（大文件）
- [ ] 测试多文件输出（ZIP 下载）
- [ ] 验证环境检测（本地 vs Vercel）
- [ ] 验证错误处理

### 4. 性能测试

```bash
# 小文件 (< 1MB)
# 预期处理时间: < 5秒

# 中等文件 (1-5MB)
# 预期处理时间: 5-30秒

# 大文件 (> 5MB)
# 预期处理时间: 30-120秒
# 注意: Vercel Serverless 有 10 秒执行时间限制（Hobby 计划）
```

---

## 🛠️ 故障排除

### 问题 1: 环境检测失败

**症状**: 本地环境被误判为 Vercel

**解决**:
```bash
# 检查环境变量
echo $VERCEL
# 应该为空

# 取消设置
unset VERCEL  # Linux/macOS
set VERCEL=   # Windows
```

### 问题 2: 文件下载失败

**症状**: 浏览器没有触发下载

**解决**:
```javascript
// 确保 base64 内容正确
console.log(result.content_base64.substring(0, 50));

// 检查文件名
console.log(result.filename);

// 尝试手动下载
const link = document.createElement('a');
link.href = `data:application/octet-stream;base64,${result.content_base64}`;
link.download = result.filename;
document.body.appendChild(link);
link.click();
document.body.removeChild(link);
```

### 问题 3: 处理超时

**症状**: Vercel 返回 504 Gateway Timeout

**原因**: Vercel Hobby 计划有 10 秒执行时间限制

**解决**:
```python
# 禁用耗时操作
result = preprocessor.process_file(
    file_path,
    chunk=False,  # 禁用分块
    memory_mode=True
)
```

或升级到 Vercel Pro 计划（60 秒限制）

### 问题 4: 内存不足

**症状**: 处理大文件时崩溃

**原因**: Vercel Serverless 内存限制（1024MB）

**解决**:
```python
# 限制文件大小
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

if file_size > MAX_FILE_SIZE:
    return {
        'success': False,
        'error': 'File too large. Maximum size: 50MB'
    }
```

### 问题 5: CORS 错误

**症状**: 前端无法访问 API

**解决**: 确保 `api/index.py` 中设置了 CORS 头
```python
self.send_header('Access-Control-Allow-Origin', '*')
self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
self.send_header('Access-Control-Allow-Headers', 'Content-Type')
```

---

## 📚 相关文档

- [本地部署指南](LOCAL_DEPLOYMENT.md)
- [Docker 部署指南](DOCKER_DEPLOYMENT.md)
- [输出文件说明](OUTPUT_FILES_EXPLANATION.md)
- [API 文档](API_DOCUMENTATION.md)

---

## 🎯 最佳实践

### 1. 文件大小控制

```javascript
// 前端限制文件大小
const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB

if (file.size > MAX_FILE_SIZE) {
    alert('文件过大！最大支持 50MB');
    return;
}
```

### 2. 错误处理

```javascript
try {
    const result = await uploadAndProcessFile(file);
    if (result.success) {
        downloadFile(result.content_base64, result.filename);
    } else {
        throw new Error(result.error);
    }
} catch (error) {
    console.error('处理失败:', error);
    alert(`错误: ${error.message}`);
}
```

### 3. 进度反馈

```javascript
// 显示处理状态
setStatus('info', '正在上传文件...');
const result = await uploadAndProcessFile(file);
setStatus('info', '正在处理文件...');
// ... 处理逻辑 ...
setStatus('success', '处理完成！');
```

### 4. 日志记录

```python
# 后端日志
if DEBUG_AVAILABLE:
    api_logger.info(f"Vercel mode: {is_vercel}")
    api_logger.info(f"Memory files: {len(memory_files)}")
    api_logger.info(f"Processing time: {processing_time}s")
```

---

## 🔐 安全建议

1. **文件类型验证**
```python
ALLOWED_EXTENSIONS = {'.xml', '.yaml', '.yml', '.json', '.ini', '.txt'}

file_ext = Path(filename).suffix.lower()
if file_ext not in ALLOWED_EXTENSIONS:
    return {'success': False, 'error': 'Invalid file type'}
```

2. **内容大小限制**
```python
MAX_CONTENT_SIZE = 100 * 1024 * 1024  # 100MB

if len(file_content) > MAX_CONTENT_SIZE:
    return {'success': False, 'error': 'Content too large'}
```

3. **速率限制** (使用 Vercel 内置功能)

4. **输入验证**
```python
import re

# 文件名安全检查
safe_filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
```

---

## 📊 性能优化

### 1. 减少处理时间

```python
# 禁用不必要的功能
result = preprocessor.process_file(
    file_path,
    chunk=False,         # 跳过分块
    convert_format=True,  # 保留转换
    memory_mode=True
)
```

### 2. 压缩响应

```python
import gzip

# 压缩 base64 内容（前端需解压）
compressed = gzip.compress(content)
base64_content = base64.b64encode(compressed).decode()
```

### 3. 缓存优化

```python
# 使用 Vercel Edge Cache
self.send_header('Cache-Control', 'public, max-age=3600')
```

---

**最后更新**: 2025-12-05
**维护者**: Claude Code
**版本**: 2.0.0 (Vercel Support)
