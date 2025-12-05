# Docker 本地部署指南

## 部署概述

该应用已成功部署在本地Docker环境中，包含以下服务：

- **API服务**: 5GC配置预处理核心服务
- **Web界面**: Nginx静态文件服务

## 服务访问地址

- **API服务**: http://localhost:9000/api
- **Web界面**: http://localhost:9001

## 快速开始

### 1. 启动服务

```bash
# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

### 2. 停止服务

```bash
# 停止所有服务
docker-compose down

# 停止并删除数据卷
docker-compose down -v
```

### 3. 重启服务

```bash
# 重启所有服务
docker-compose restart

# 重启特定服务
docker-compose restart app
```

## API 使用示例

### 1. 获取API信息

```bash
curl --noproxy localhost http://localhost:9000/api
```

### 2. 处理配置文件

```bash
# 准备测试文件
echo "amf_ip = 192.168.1.100" > test_config.txt

# 将文件内容转换为base64
FILE_CONTENT=$(cat test_config.txt | base64)

# 调用API处理
curl --noproxy localhost -X POST http://localhost:9000/api \
  -H "Content-Type: application/json" \
  -d "{
    \"file_content\": \"$FILE_CONTENT\",
    \"filename\": \"test_config.txt\",
    \"options\": {
      \"desensitize\": true,
      \"convert_format\": true,
      \"chunk\": false,
      \"extract_metadata\": true
    }
  }"
```

## 目录结构

```
config_preprocessor/
├── input/           # 输入文件目录（挂载到容器）
├── output/          # 输出文件目录（挂载到容器）
├── logs/            # 日志目录（挂载到容器）
├── public/          # Web静态文件
├── src/             # 源代码
├── api/             # API服务
├── docker-compose.yml
├── Dockerfile
└── start_server.py  # API服务启动脚本
```

## 配置说明

### 端口配置

当前配置：
- API服务: 主机端口 9000 -> 容器端口 8000
- Web服务: 主机端口 9001 -> 容器端口 80

如需修改端口，编辑 `docker-compose.yml` 文件中的 `ports` 配置。

### 环境变量

可在 `docker-compose.yml` 中配置以下环境变量：

- `LOG_LEVEL`: 日志级别（默认: INFO）
- `MAX_WORKERS`: 最大工作线程数（默认: 4）
- `PORT`: API服务端口（默认: 8000）

## 常见问题

### 1. 端口被占用

如果端口被占用，修改 `docker-compose.yml` 中的端口映射：

```yaml
ports:
  - "新端口:8000"  # 修改主机端口
```

### 2. 查看容器日志

```bash
# 查看所有容器日志
docker-compose logs

# 查看特定服务日志
docker-compose logs app
docker-compose logs web

# 实时跟踪日志
docker-compose logs -f app
```

### 3. 重新构建镜像

当修改代码后需要重新构建镜像：

```bash
# 重新构建并启动
docker-compose up -d --build

# 只重新构建特定服务
docker-compose build app
docker-compose up -d
```

### 4. 清理Docker资源

```bash
# 停止并删除容器
docker-compose down

# 删除未使用的镜像
docker image prune -a

# 删除未使用的卷
docker volume prune
```

## 健康检查

API服务配置了健康检查，每30秒检查一次服务状态。

查看健康状态：
```bash
docker-compose ps
```

状态显示为 `Up X seconds (healthy)` 表示服务正常。

## 性能优化

### 1. 调整工作线程

编辑 `docker-compose.yml`：

```yaml
environment:
  - MAX_WORKERS=8  # 根据CPU核心数调整
```

### 2. 限制容器资源

```yaml
services:
  app:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

## 生产部署建议

1. **使用具体的镜像标签**，不要使用 `latest`
2. **配置日志轮转**，避免日志文件过大
3. **设置重启策略**: `restart: always`
4. **配置反向代理**（Nginx/Traefik）处理SSL
5. **启用认证机制**保护API接口
6. **配置监控和告警**

## 维护命令

```bash
# 更新镜像
docker-compose pull
docker-compose up -d

# 备份数据
docker-compose exec app tar czf /tmp/backup.tar.gz /app/output

# 恢复数据
docker cp backup.tar.gz config_preprocessor_app:/tmp/
docker-compose exec app tar xzf /tmp/backup.tar.gz -C /
```

## 技术支持

- 查看项目文档: README.md
- 查看API文档: http://localhost:9000/api
- 问题反馈: 项目GitHub Issues

---

**部署时间**: 2025-12-05
**版本**: 1.0.0
