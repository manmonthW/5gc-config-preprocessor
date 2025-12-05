# Vercel 快速开始指南

## 🚀 5 分钟部署到 Vercel

这是最快的开始使用 Vercel Serverless 版本的方法。

---

## ✅ 前置检查

- [ ] 已注册 GitHub 账号
- [ ] 已注册 Vercel 账号（[免费注册](https://vercel.com/signup)）
- [ ] 代码已推送到 GitHub

---

## 📦 步骤 1: 推送代码到 GitHub

```bash
# 如果还没有推送
git add .
git commit -m "Add Vercel Serverless support"
git push origin main
```

---

## 🔗 步骤 2: 连接 Vercel

1. 访问 [Vercel Dashboard](https://vercel.com/dashboard)
2. 点击 **New Project**
3. 点击 **Import Git Repository**
4. 选择 GitHub 并授权
5. 选择仓库 `5gc-config-preprocessor`
6. 点击 **Import**

---

## ⚙️ 步骤 3: 配置项目

**Framework Preset**: `Other`

**Root Directory**: `.` (默认)

**Build Settings**:
- Build Command: `(留空)`
- Output Directory: `public`
- Install Command: `pip install -r requirements.txt`

**点击 Deploy**

---

## ✨ 步骤 4: 等待部署

等待 1-2 分钟，Vercel 会自动：
1. 安装 Python 依赖
2. 部署 Serverless Function
3. 部署静态文件

---

## 🎉 步骤 5: 测试部署

部署完成后，你会得到一个 URL，例如：
```
https://5gc-config-preprocessor.vercel.app
```

### 测试 API

访问：`https://your-url.vercel.app/api`

应该看到：
```json
{
  "message": "5GC Config Preprocessor API",
  "version": "1.0.0",
  "debug_available": false
}
```

### 测试 Web 界面

访问：`https://your-url.vercel.app/vercel-upload-example.html`

上传一个配置文件试试！

---

## 📝 快速 API 测试

### 方法 1: cURL

```bash
# 准备测试文件
echo "network: {name: test}" > test.yaml

# 发送请求
curl -X POST https://your-url.vercel.app/api \
  -H "Content-Type: application/json" \
  -d "{
    \"file_content\": \"$(base64 -w 0 test.yaml 2>/dev/null || base64 test.yaml)\",
    \"filename\": \"test.yaml\",
    \"options\": {
      \"desensitize\": true,
      \"convert_format\": true,
      \"chunk\": false,
      \"extract_metadata\": true
    }
  }"
```

### 方法 2: Python

```python
import base64
import requests

# 读取文件
with open('test.yaml', 'rb') as f:
    content = base64.b64encode(f.read()).decode()

# 发送请求
response = requests.post(
    'https://your-url.vercel.app/api',
    json={
        'file_content': content,
        'filename': 'test.yaml',
        'options': {
            'desensitize': True,
            'convert_format': True,
            'chunk': False,
            'extract_metadata': True
        }
    }
)

result = response.json()
print(result)

# 下载文件
if result['success']:
    import base64
    content = base64.b64decode(result['content_base64'])
    with open(result['filename'], 'wb') as f:
        f.write(content)
    print(f"✅ 已下载: {result['filename']}")
```

### 方法 3: JavaScript (浏览器)

```javascript
// 打开浏览器控制台，粘贴以下代码

fetch('/api', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        file_content: btoa('network: {name: test}'),
        filename: 'test.yaml',
        options: {
            desensitize: true,
            convert_format: true,
            chunk: false,
            extract_metadata: true
        }
    })
})
.then(r => r.json())
.then(result => {
    console.log(result);

    if (result.success) {
        // 下载文件
        const link = document.createElement('a');
        link.href = 'data:application/octet-stream;base64,' + result.content_base64;
        link.download = result.filename;
        link.click();
    }
});
```

---

## 🔍 验证 Vercel 环境

确认响应中包含：
```json
{
  "success": true,
  "is_vercel_response": true,  // ← 应该是 true
  "filename": "...",
  "content_base64": "..."
}
```

如果 `is_vercel_response` 是 `true`，说明 Vercel 模式正常工作！

---

## 🛠️ 下一步

### 自定义域名

1. 在 Vercel Dashboard 中打开项目
2. 点击 **Settings** → **Domains**
3. 添加你的域名
4. 配置 DNS 记录（Vercel 会提供详细说明）

### 环境变量

如需配置：
1. 打开 **Settings** → **Environment Variables**
2. 添加变量
3. 重新部署

### 监控和日志

1. 点击项目 → **Deployments**
2. 选择一个部署
3. 查看 **Functions** 日志

---

## ⚡ 快速命令

```bash
# 查看部署状态
vercel ls

# 本地预览（安装 Vercel CLI）
npm i -g vercel
vercel dev

# 手动部署
vercel --prod
```

---

## 📚 相关文档

- **完整部署指南**: [VERCEL_DEPLOYMENT_GUIDE.md](VERCEL_DEPLOYMENT_GUIDE.md)
- **本地部署**: [LOCAL_DEPLOYMENT.md](LOCAL_DEPLOYMENT.md)
- **Docker 部署**: [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md)

---

## 🐛 常见问题

### Q: 部署失败了怎么办？

A: 检查 Vercel 的构建日志：
1. 打开项目
2. 点击失败的部署
3. 查看 **Build Logs**

常见问题：
- 缺少依赖：确保 `requirements.txt` 完整
- Python 版本：Vercel 使用 Python 3.9
- 文件路径：使用绝对路径或相对于项目根目录的路径

### Q: API 返回 404？

A: 检查 `vercel.json` 配置：
```json
{
  "routes": [
    {
      "src": "/api",
      "dest": "/api/index.py"
    }
  ]
}
```

### Q: 处理超时？

A: Vercel 免费计划限制：
- 最大执行时间: 10 秒
- 最大内存: 1024MB

解决方法：
- 禁用耗时操作（如分块）
- 升级到 Pro 计划（60秒）
- 限制文件大小

---

## 🎯 成功标志

- ✅ API 可访问
- ✅ 上传文件成功
- ✅ 自动下载处理结果
- ✅ `is_vercel_response: true`
- ✅ 文件内容正确

---

**准备时间**: 5 分钟
**部署时间**: 1-2 分钟
**难度**: ⭐ (极简单)

开始享受 Serverless 的便利吧！🚀
