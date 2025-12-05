# 修复输出目录命名问题

## 问题描述

当前通过API上传文件时，输出目录结构为：
```
output/20251205_020503/tmp9mdv5gb8/  ← 使用临时文件名（随机）
```

期望的目录结构：
```
output/20251205_020503/用户上传的文件名/  ← 使用原始文件名
```

## 原因分析

### 当前处理流程

```python
# api/index.py
1. 接收用户上传：filename = "A-PCC-MM_Day1_1.33.xml"
2. 创建临时文件：tempfile.NamedTemporaryFile() → "/tmp/tmp9mdv5gb8.xml"
3. 调用处理器：preprocessor.process_file(temp_file_path)
4. 生成输出目录：使用 file_path.stem → "tmp9mdv5gb8"
```

**问题所在**：`preprocessor.py:164` 使用 `file_path.stem`（临时文件名）而不是原始文件名

```python
# preprocessor.py:164
file_output_dir = self.output_dir / file_path.stem  # ← 使用临时文件的stem
```

## 解决方案

### 方案1: 修改process_file方法（推荐）

添加可选参数 `original_filename` 来指定输出目录名。

#### 修改步骤

**1. 修改 preprocessor.py**

```python
# src/preprocessor.py

def process_file(self, file_path: str,
                desensitize: bool = True,
                convert_format: bool = True,
                chunk: bool = True,
                extract_metadata: bool = True,
                original_filename: Optional[str] = None) -> ProcessingResult:  # ← 新增参数
    """
    处理单个配置文件

    Args:
        file_path: 文件路径
        desensitize: 是否脱敏
        convert_format: 是否转换格式
        chunk: 是否分块
        extract_metadata: 是否提取元数据
        original_filename: 原始文件名（用于输出目录命名，可选）  # ← 新增说明

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
        logger.info(f"开始处理文件: {file_path} (大小: {file_size_mb:.2f} MB)")

        # 读取原始内容（保持格式）
        original_text = self.converter.read_file(str(file_path))
        detected_format = self.converter.detect_format(str(file_path))

        # 创建文件专属输出目录
        # 如果提供了原始文件名，使用原始文件名；否则使用当前文件名
        if original_filename:
            # 使用原始文件名（去除扩展名）
            output_dir_name = Path(original_filename).stem
        else:
            # 使用当前文件路径的文件名（去除扩展名）
            output_dir_name = file_path.stem

        file_output_dir = self.output_dir / output_dir_name  # ← 修改这里
        file_output_dir.mkdir(exist_ok=True)

        # ... 后续处理代码不变 ...
```

**2. 修改 api/index.py**

```python
# api/index.py

# 在 do_POST 方法中修改（约221行）

# 原代码：
result = preprocessor.process_file(
    temp_file_path,
    desensitize=options.get('desensitize', True),
    convert_format=options.get('convert_format', True),
    chunk=options.get('chunk', False),
    extract_metadata=options.get('extract_metadata', True)
)

# 修改后：
result = preprocessor.process_file(
    temp_file_path,
    desensitize=options.get('desensitize', True),
    convert_format=options.get('convert_format', True),
    chunk=options.get('chunk', False),
    extract_metadata=options.get('extract_metadata', True),
    original_filename=filename  # ← 新增：传递原始文件名
)
```

### 方案2: 创建符号链接/重命名临时文件（备选）

在创建临时文件时使用原始文件名：

```python
# api/index.py (修改 do_POST 方法，约180-186行)

# 原代码：
with tempfile.NamedTemporaryFile(mode='wb', suffix=original_suffix, delete=False) as temp_file:
    temp_file.write(decoded_bytes)
    temp_file_path = temp_file.name

# 修改后：
import tempfile
import shutil

# 使用原始文件名创建临时文件
temp_dir = tempfile.gettempdir()
# 保留原始文件名，但放在临时目录
safe_filename = Path(filename).name  # 获取安全的文件名
temp_file_path = Path(temp_dir) / safe_filename

# 写入文件
with open(temp_file_path, 'wb') as temp_file:
    temp_file.write(decoded_bytes)
```

**注意**：方案2可能存在文件名冲突问题（如果同时上传相同文件名）。

### 方案3: 使用唯一前缀+原始文件名

```python
# api/index.py

import tempfile
from datetime import datetime

# 生成唯一的临时文件名
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
safe_filename = Path(filename).name
unique_filename = f"{timestamp}_{safe_filename}"

temp_dir = Path(tempfile.gettempdir())
temp_file_path = temp_dir / unique_filename

with open(temp_file_path, 'wb') as temp_file:
    temp_file.write(decoded_bytes)
```

**优点**：避免文件名冲突，同时保留原始文件名信息

## 完整修改代码

### 文件1: src/preprocessor.py

找到 `process_file` 方法定义（约125行），修改如下：

```python
def process_file(self, file_path: str,
                desensitize: bool = True,
                convert_format: bool = True,
                chunk: bool = True,
                extract_metadata: bool = True,
                original_filename: Optional[str] = None) -> ProcessingResult:
    """
    处理单个配置文件

    Args:
        file_path: 文件路径
        desensitize: 是否脱敏
        convert_format: 是否转换格式
        chunk: 是否分块
        extract_metadata: 是否提取元数据
        original_filename: 原始文件名（可选，用于输出目录命名）

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
        if original_filename:
            output_dir_name = Path(original_filename).stem
        else:
            output_dir_name = file_path.stem

        file_output_dir = self.output_dir / output_dir_name
        file_output_dir.mkdir(exist_ok=True)

        # 后续代码保持不变...
```

### 文件2: api/index.py

找到 `process_file` 调用处（约221行），修改如下：

```python
# Process the file
result = preprocessor.process_file(
    temp_file_path,
    desensitize=options.get('desensitize', True),
    convert_format=options.get('convert_format', True),
    chunk=options.get('chunk', False),
    extract_metadata=options.get('extract_metadata', True),
    original_filename=filename  # ← 添加这一行
)
```

## 测试验证

### 1. 重新构建Docker镜像

```bash
docker-compose build app
docker-compose up -d
```

### 2. 测试API

```bash
# 上传文件测试
curl -X POST http://localhost:9000/api \
  -H "Content-Type: application/json" \
  -d '{
    "file_content": "'$(base64 test.yaml)'",
    "filename": "my-config-file.yaml",
    "options": {
      "desensitize": true,
      "convert_format": true,
      "chunk": true,
      "extract_metadata": true
    }
  }'
```

### 3. 检查输出目录

```bash
# 应该看到如下结构：
ls output/20251205_XXXXXX/

# 期望输出：
my-config-file/  ← 使用了原始文件名
```

## 向后兼容性

修改后的代码**完全向后兼容**：

- ✅ 如果调用时不提供 `original_filename`，行为与之前完全相同
- ✅ 本地使用 `quick_start.py` 不受影响
- ✅ 只有通过API上传时才会使用新功能

## 额外改进建议

### 1. 文件名安全处理

```python
def sanitize_filename(filename: str) -> str:
    """
    清理文件名，移除不安全字符
    """
    # 移除路径分隔符和其他危险字符
    safe_chars = re.sub(r'[^\w\s\-\.]', '_', filename)
    # 限制长度
    return safe_chars[:200]

# 在 preprocessor.py 中使用：
if original_filename:
    output_dir_name = sanitize_filename(Path(original_filename).stem)
```

### 2. 日志改进

```python
# 在 preprocessor.py 中
if original_filename:
    logger.info(f"原始文件名: {original_filename}")
    logger.info(f"临时文件路径: {file_path}")
logger.info(f"输出目录: {file_output_dir}")
```

## 总结

- **推荐方案**: 方案1（修改process_file方法）
- **修改文件**: 2个（preprocessor.py, api/index.py）
- **修改行数**: 约10行
- **向后兼容**: 是
- **风险等级**: 低
