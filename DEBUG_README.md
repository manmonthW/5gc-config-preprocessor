# 5GC配置预处理器 - 调试系统

## 🔧 调试功能概述

本项目集成了完整的调试和日志系统，帮助快速定位和解决问题。调试系统设计为独立模块，便于在发布时分离。

## 📁 调试系统结构

```
debug/
├── __init__.py          # 调试模块入口
├── config.py            # 调试配置管理
├── logger.py            # 日志记录系统
├── tools.py             # 调试工具集
└── release.py           # 发布管理工具
```

## 🚀 快速开始

### 1. 启用调试模式

调试模式默认启用，可通过环境变量控制：

```bash
export DEBUG=true
export LOG_LEVEL=DEBUG
export LOG_TO_FILE=true
export LOG_TO_CONSOLE=true
export DETAILED_ERRORS=true
```

### 2. 访问调试端点

- **主要API**: `https://your-app.vercel.app/api`
- **调试信息**: `https://your-app.vercel.app/api/debug`
- **测试端点**: `https://your-app.vercel.app/api/hello`

### 3. 查看调试信息

在浏览器中访问 `/api/debug` 可以看到：
- 系统配置信息
- 自动化测试结果
- 预处理器导入状态
- Python环境信息

## 📊 调试功能详情

### 🎯 API错误跟踪

每个API请求都会生成唯一的请求ID，并记录：
- 请求参数和选项
- 处理步骤和时间
- 错误类型和堆栈跟踪
- 文件处理详情

```json
{
  "request_id": "20241106_143022_123456",
  "error": "处理失败原因",
  "details": {
    "error_type": "ValueError",
    "traceback": "完整错误堆栈",
    "file_info": "文件相关信息"
  }
}
```

### 📝 日志系统

日志自动记录到：
- **控制台输出**: 实时查看
- **文件日志**: `debug/logs/` 目录
- **结构化格式**: JSON格式便于分析

日志级别：
- `DEBUG`: 详细调试信息
- `INFO`: 一般信息
- `WARNING`: 警告信息
- `ERROR`: 错误信息
- `CRITICAL`: 严重错误

### 🧪 自动化测试

内置测试工具自动检查：
- 预处理器模块导入
- 配置文件存在性
- Base64编码解码
- API请求模拟
- 目录结构完整性

## 🛠️ 使用调试工具

### 命令行调试

```bash
# 进入调试目录
cd debug

# 运行快速测试
python tools.py --test

# 生成调试报告
python tools.py --report

# 创建测试数据
python tools.py --create-test-data
```

### Python代码调试

```python
from debug import api_logger, log_function_call

# 记录函数调用
@log_function_call
def my_function():
    api_logger.debug("调试信息")
    api_logger.error("错误信息", exception=e)
```

## 🔍 问题定位指南

### 1. YAML文件处理失败

**症状**: 上传YAML文件后返回"处理失败"

**调试步骤**:
1. 检查浏览器控制台错误信息
2. 访问 `/api/debug` 查看系统状态
3. 查看请求ID对应的日志
4. 检查文件编码和格式

**常见原因**:
- 文件编码不是UTF-8
- YAML语法错误
- 文件过大
- 预处理器模块导入失败

### 2. API导入错误

**症状**: API返回预处理器不可用

**调试信息**:
```json
{
  "mode": "demo",
  "debug_info": {
    "import_error": "No module named 'preprocessor'",
    "python_path": [...],
    "src_dir": "/path/to/src"
  }
}
```

**解决方案**:
1. 检查src目录是否存在
2. 确认预处理器模块完整性
3. 检查Python路径配置

### 3. Base64编码问题

**症状**: "Invalid base64 file content"

**调试步骤**:
1. 检查文件是否正确选择
2. 查看控制台Base64长度信息
3. 测试文件大小限制

## 📋 错误信息解读

### 前端错误显示

新的错误显示包含：
- **请求ID**: 用于日志追踪
- **错误类型**: 具体的异常类型
- **处理时间**: 失败前的处理时长
- **文件信息**: 文件名、大小、类型
- **技术详情**: 可展开的堆栈跟踪
- **故障排除建议**: 针对性的解决建议

### 后端日志格式

```json
{
  "timestamp": "2024-11-06T14:30:22.123456",
  "level": "ERROR",
  "module": "api",
  "message": "POST request processing failed",
  "data": {
    "request_id": "20241106_143022_123456",
    "exception": {
      "type": "ValueError",
      "message": "Error details",
      "traceback": "..."
    }
  }
}
```

## 🚀 发布时分离调试代码

### 创建发布版本

```bash
cd debug
python release.py --create-release --output-dir ../release_version
```

### 功能说明

发布工具会自动：
- 移除整个 `debug/` 目录
- 清理API文件中的调试代码
- 设置生产环境变量
- 生成发布信息文件

### 备份和恢复

```bash
# 备份调试文件
python release.py --backup-debug

# 恢复调试文件
python release.py --restore-debug

# 完全移除调试文件（会先备份）
python release.py --remove-debug
```

## ⚙️ 配置选项

### 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `DEBUG` | `true` | 是否启用调试模式 |
| `LOG_LEVEL` | `DEBUG` | 日志级别 |
| `LOG_TO_FILE` | `true` | 是否写入日志文件 |
| `LOG_TO_CONSOLE` | `true` | 是否输出到控制台 |
| `DETAILED_ERRORS` | `true` | 是否显示详细错误 |

### 运行时配置

```python
from debug import debug_config

# 检查调试状态
if debug_config.enabled:
    print("调试模式已启用")

# 获取配置信息
config_info = debug_config.get_debug_info()
```

## 💡 最佳实践

### 1. 开发阶段
- 保持调试模式启用
- 定期查看日志文件
- 使用调试端点监控系统状态

### 2. 测试阶段
- 运行完整调试测试套件
- 验证错误处理流程
- 测试边界条件

### 3. 发布准备
- 运行发布工具创建生产版本
- 验证调试代码已完全移除
- 测试生产环境功能

### 4. 问题追踪
- 记录请求ID用于日志关联
- 保存完整的错误信息
- 定期清理日志文件

## 🆘 常见问题

**Q: 为什么看不到日志文件？**
A: 检查 `LOG_TO_FILE` 环境变量，确认 `debug/logs/` 目录权限

**Q: 调试端点返回404？**
A: 确认 `api/debug.py` 文件存在，检查Vercel部署状态

**Q: 前端显示的错误信息不够详细？**
A: 检查 `DETAILED_ERRORS` 设置，查看浏览器控制台

**Q: 如何在生产环境临时启用调试？**
A: 设置环境变量 `DEBUG=true` 重新部署

---

📞 **需要帮助？** 查看具体的错误信息和请求ID，可以快速定位问题根源！