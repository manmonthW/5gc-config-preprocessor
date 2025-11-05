# Contributing to 5GC Config Preprocessor

感谢您对 5GC Config Preprocessor 项目的关注！我们欢迎所有形式的贡献。

## 📋 目录
- [行为准则](#行为准则)
- [如何贡献](#如何贡献)
- [报告Bug](#报告bug)
- [建议新功能](#建议新功能)
- [提交代码](#提交代码)
- [开发环境设置](#开发环境设置)
- [代码规范](#代码规范)
- [测试指南](#测试指南)
- [文档贡献](#文档贡献)

## 行为准则

本项目采用[贡献者契约](https://www.contributor-covenant.org/)行为准则。参与项目即表示您同意遵守其条款。

## 如何贡献

### 报告Bug

发现Bug？请通过GitHub Issues报告：

1. 使用 [Bug Report Template](.github/ISSUE_TEMPLATE/bug_report.md)
2. 提供详细的复现步骤
3. 包含错误信息和日志
4. 说明环境信息（OS、Python版本等）

### 建议新功能

有好的想法？我们很乐意听到：

1. 使用 [Feature Request Template](.github/ISSUE_TEMPLATE/feature_request.md)
2. 解释功能的使用场景
3. 提供可能的实现方案

### 提交代码

#### 1. Fork仓库
```bash
# Fork项目到您的GitHub账号
# 然后克隆到本地
git clone https://github.com/YOUR_USERNAME/5gc-config-preprocessor.git
cd 5gc-config-preprocessor
```

#### 2. 创建分支
```bash
# 基于main创建feature分支
git checkout -b feature/your-feature-name

# 或修复bug
git checkout -b fix/bug-description
```

#### 3. 开发环境设置
```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装开发依赖
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

#### 4. 进行更改
- 遵循现有代码风格
- 添加必要的测试
- 更新相关文档

#### 5. 运行测试
```bash
# 运行所有测试
pytest tests/

# 运行特定测试
pytest tests/test_desensitizer.py

# 检查代码覆盖率
pytest --cov=src --cov-report=html
```

#### 6. 代码检查
```bash
# 代码格式化
black src/ tests/

# 代码检查
flake8 src/ tests/
pylint src/

# 类型检查
mypy src/
```

#### 7. 提交更改
```bash
# 添加更改
git add .

# 提交（使用规范的提交信息）
git commit -m "feat: add new desensitization rule for XXX"
```

#### 8. 推送并创建PR
```bash
# 推送到您的fork
git push origin feature/your-feature-name
```

然后在GitHub上创建Pull Request。

## 代码规范

### Python代码风格

我们遵循 [PEP 8](https://www.python.org/dev/peps/pep-0008/) 规范：

```python
# 良好的示例
class ConfigProcessor:
    """配置处理器类"""
    
    def __init__(self, config_path: str):
        """
        初始化处理器
        
        Args:
            config_path: 配置文件路径
        """
        self.config = self._load_config(config_path)
    
    def process_file(self, file_path: str) -> ProcessingResult:
        """处理单个文件"""
        # 实现细节
        pass
```

### 提交信息规范

使用 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

```
<type>(<scope>): <subject>

<body>

<footer>
```

类型（type）：
- `feat`: 新功能
- `fix`: Bug修复
- `docs`: 文档更新
- `style`: 代码格式（不影响代码运行的变动）
- `refactor`: 重构
- `perf`: 性能优化
- `test`: 测试
- `chore`: 构建过程或辅助工具的变动

示例：
```
feat(desensitizer): add support for email desensitization

- Add email pattern recognition
- Update configuration schema
- Add unit tests for email processing

Closes #123
```

## 测试指南

### 编写测试

每个新功能都应该包含相应的测试：

```python
# tests/test_new_feature.py
import unittest
from src.module import NewFeature

class TestNewFeature(unittest.TestCase):
    def setUp(self):
        self.feature = NewFeature()
    
    def test_basic_functionality(self):
        """测试基本功能"""
        result = self.feature.process("input")
        self.assertEqual(result, "expected_output")
    
    def test_edge_case(self):
        """测试边界情况"""
        # 测试实现
        pass
```

### 测试覆盖率

我们的目标是保持80%以上的测试覆盖率：

```bash
# 生成覆盖率报告
pytest --cov=src --cov-report=html --cov-report=term

# 查看HTML报告
open htmlcov/index.html
```

## 文档贡献

### 更新文档

文档同样重要！请确保：

1. 新功能有相应的文档
2. API更改更新了文档
3. 示例代码是可运行的
4. README保持最新

### 文档格式

使用Markdown格式，遵循以下规范：

```markdown
# 一级标题

## 二级标题

### 三级标题

**粗体文本**用于强调

`代码` 用反引号包裹

​```python
# 代码块使用三个反引号
def example():
    pass
​```
```

## 开发流程

### 1. Issue讨论
在开始大的改动前，先创建Issue讨论

### 2. 设计文档
对于重大功能，提供设计文档

### 3. 迭代开发
分小步提交，便于review

### 4. Code Review
所有PR都需要至少一个维护者的review

### 5. CI/CD
确保所有CI检查通过

## 发布流程

### 版本号规范

遵循 [Semantic Versioning](https://semver.org/):
- MAJOR.MINOR.PATCH
- 例如：1.2.3

### 发布检查清单

- [ ] 所有测试通过
- [ ] 文档已更新
- [ ] CHANGELOG已更新
- [ ] 版本号已更新
- [ ] 创建Git tag

## 获取帮助

### 资源

- [项目文档](README.md)
- [API文档](docs/api.md)
- [FAQ](docs/faq.md)

### 联系方式

- GitHub Issues: 技术问题
- Email: support@example.com
- Slack: #5gc-config-preprocessor

## 贡献者

感谢所有贡献者！

<!-- ALL-CONTRIBUTORS-LIST:START -->
<!-- ALL-CONTRIBUTORS-LIST:END -->

## 许可证

通过贡献代码，您同意您的贡献将按照 [MIT License](LICENSE) 许可。

---

**感谢您的贡献！** 🎉
