# 目录命名修复验证报告

## 修复状态

✅ **修复成功！** 输出目录现在使用用户上传的原始文件名，而不是随机临时文件名。

---

## 修改内容

### 1. 修改 `src/preprocessor.py`

**位置**: `process_file` 方法签名和目录创建逻辑

**修改内容**:
- 添加了 `original_filename: Optional[str] = None` 参数
- 在创建输出目录时，优先使用 `original_filename` 而不是临时文件名

```python
def process_file(self, file_path: str,
                desensitize: bool = True,
                convert_format: bool = True,
                chunk: bool = True,
                extract_metadata: bool = True,
                original_filename: Optional[str] = None) -> ProcessingResult:
    # ...

    # 创建文件专属输出目录
    if original_filename:
        output_dir_name = Path(original_filename).stem
    else:
        output_dir_name = file_path.stem

    file_output_dir = self.output_dir / output_dir_name
    file_output_dir.mkdir(exist_ok=True)
```

### 2. 修改 `api/index.py`

**位置**: `do_POST` 方法中调用 `process_file` 的地方 (约227行)

**修改内容**:
- 添加了 `original_filename=filename` 参数传递

```python
result = preprocessor.process_file(
    temp_file_path,
    desensitize=options.get('desensitize', True),
    convert_format=options.get('convert_format', True),
    chunk=options.get('chunk', False),
    extract_metadata=options.get('extract_metadata', True),
    original_filename=filename  # ← 新增此行
)
```

---

## 测试验证

### 测试环境
- **Docker容器**: config_preprocessor_app
- **API端口**: 9000
- **测试时间**: 2025-12-05 02:53:57

### 测试用例

**上传文件信息**:
- 原始文件: `test-upload.yaml`
- 上传文件名: `my-test-config.yaml`
- 文件内容: 简单的YAML配置文件

**API请求**:
```python
{
  "file_content": "<base64 encoded>",
  "filename": "my-test-config.yaml",
  "options": {
    "desensitize": true,
    "convert_format": true,
    "chunk": false,
    "extract_metadata": true
  }
}
```

### 测试结果

#### ✅ 成功指标

1. **API响应**:
   - 状态码: 200
   - 处理状态: Success
   - 处理时间: 0.05秒

2. **输出目录结构**:

**修复前** (使用临时文件名):
```
output/
└── 20251205_020503/
    └── tmpXXXXXX/              ← 随机临时文件名
        ├── tmpXXXXXX_unified.json
        ├── tmpXXXXXX_metadata.json
        └── ...
```

**修复后** (使用原始文件名):
```
output/
└── 20251205_025357/
    └── my-test-config/         ← 使用用户上传的文件名
        ├── tmpaefearhx_unified.json
        ├── tmpaefearhx_metadata.json
        ├── tmpaefearhx_desensitized.txt
        ├── tmpaefearhx_desensitize_mapping.json
        └── tmpaefearhx_report.json
```

3. **API返回的输出目录**:
```
/app/output/20251205_025357/my-test-config
                            ^^^^^^^^^^^^^^
                            使用了原始文件名 "my-test-config"
```

#### 📊 详细验证

```bash
# 容器内目录结构
docker exec config_preprocessor_app sh -c "ls -la /app/output/20251205_025357/"

结果:
drwxr-xr-x 1 processor processor 4096 Dec  5 02:53 my-test-config
```

```bash
# 目录内生成的文件
docker exec config_preprocessor_app sh -c "ls -la /app/output/20251205_025357/my-test-config/"

结果:
-rw-r--r-- 1 processor processor  217 Dec  5 02:53 tmpaefearhx_desensitize_mapping.json
-rw-r--r-- 1 processor processor  158 Dec  5 02:53 tmpaefearhx_desensitized.txt
-rw-r--r-- 1 processor processor  758 Dec  5 02:53 tmpaefearhx_metadata.json
-rw-r--r-- 1 processor processor 1575 Dec  5 02:53 tmpaefearhx_report.json
-rw-r--r-- 1 processor processor 1377 Dec  5 02:53 tmpaefearhx_unified.json
```

---

## 向后兼容性验证

### ✅ 本地文件处理 (不受影响)

当直接使用 `quick_start.py` 处理本地文件时:
```bash
python quick_start.py -i config.yaml
```

**行为**:
- `original_filename` 参数为 `None`
- 使用原有逻辑: `file_path.stem`
- 输出目录: `output/TIMESTAMP/config/`

**结论**: 完全向后兼容，行为不变

### ✅ API上传 (使用新功能)

当通过API上传文件时:
```python
preprocessor.process_file(
    temp_file_path="/tmp/tmpXXXX.yaml",
    original_filename="user-uploaded.yaml"
)
```

**行为**:
- `original_filename` 参数有值
- 使用新逻辑: `Path(original_filename).stem`
- 输出目录: `output/TIMESTAMP/user-uploaded/`

**结论**: 新功能正常工作

---

## 与预期的对比

### 用户需求
> "我在本地docker中使用上传文件处理之后输出时间戳目录下的目录名字为随机字符，改用用户上传的文件名作为时间戳下下一级目录名"

### 实现结果

| 项目 | 修复前 | 修复后 | 状态 |
|------|--------|--------|------|
| 时间戳目录 | `20251205_020503` | `20251205_025357` | ✅ 正常 |
| 文件专属目录 | `tmp9mdv5gb8` (随机) | `my-test-config` (原始文件名) | ✅ 符合需求 |
| 输出文件 | 正常生成 | 正常生成 | ✅ 功能正常 |
| 向后兼容 | N/A | 本地文件处理不受影响 | ✅ 完全兼容 |

---

## 文件说明

### 为什么输出文件名仍使用临时文件名前缀？

目录内的文件 (如 `tmpaefearhx_unified.json`) 仍使用临时文件名前缀，这是**正常且符合设计**的:

1. **目录命名**: 使用 `original_filename.stem` → `my-test-config`
2. **文件命名**: 使用实际处理的文件路径 `file_path.stem` → `tmpaefearhx`

**原因**:
- 文件命名基于实际处理的文件对象 (临时文件)
- 这样可以避免文件名冲突
- 如果需要，可以进一步修改文件命名逻辑

**用户需求**: 用户只要求修改"时间戳下下一级目录名"，不包括文件名

---

## 额外改进建议 (可选)

如果需要让输出文件也使用原始文件名:

### 方案: 修改文件保存逻辑

在 `preprocessor.py` 中，所有保存文件的地方，将:
```python
output_file = file_output_dir / f"{file_path.stem}_unified.json"
```

改为:
```python
base_name = Path(original_filename).stem if original_filename else file_path.stem
output_file = file_output_dir / f"{base_name}_unified.json"
```

**影响范围**: 需要修改约10-15处文件保存逻辑

**风险**: 低，但增加代码复杂度

---

## 部署状态

### Docker镜像
- **镜像名称**: `5gc-config-preprocessor:latest`
- **构建时间**: 2025-12-05 10:50:58
- **构建状态**: ✅ 成功

### 容器状态
- **容器名称**: `config_preprocessor_app`
- **运行状态**: ✅ Running
- **端口映射**: `9000:8000`
- **健康检查**: ✅ Passed

### API状态
- **访问地址**: `http://localhost:9000/api`
- **GET请求**: ✅ 正常返回API信息
- **POST请求**: ✅ 正常处理文件上传

---

## 测试建议

### 1. 测试不同文件名

```bash
# 测试中文文件名
filename: "配置文件.yaml"
预期输出目录: output/TIMESTAMP/配置文件/

# 测试带空格的文件名
filename: "my config file.yaml"
预期输出目录: output/TIMESTAMP/my config file/

# 测试特殊字符
filename: "config-v1.2.3.yaml"
预期输出目录: output/TIMESTAMP/config-v1.2.3/
```

### 2. 测试大文件

使用之前的 `A-PCC-MM_Day1_1.33.xml` (3.2MB) 测试:
```bash
预期输出目录: output/TIMESTAMP/A-PCC-MM_Day1_1.33/
```

---

## 结论

✅ **目录命名修复已成功实现并通过测试**

**主要成果**:
1. ✅ 输出目录使用用户上传的原始文件名
2. ✅ 完全向后兼容现有功能
3. ✅ Docker镜像已更新并部署
4. ✅ API测试通过，功能正常

**用户可见效果**:
- 修复前: `output/20251205_020503/tmp9mdv5gb8/`
- 修复后: `output/20251205_025357/my-test-config/`

**推荐操作**:
可以直接在生产环境使用，或继续测试其他场景（中文文件名、大文件等）。

---

**验证完成时间**: 2025-12-05 10:54:00
**验证人**: Claude Code
