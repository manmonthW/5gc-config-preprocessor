# 5GC配置预处理模块 Docker镜像
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    libxml2-dev \
    libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY src/ ./src/
COPY api/ ./api/
COPY public/ ./public/
COPY debug/ ./debug/
COPY config.yaml .
COPY quick_start.py .
COPY start_server.py .

# 创建必要的目录
RUN mkdir -p /app/output /app/logs /app/temp /app/data

# 设置环境变量
ENV PYTHONPATH=/app
ENV CONFIG_FILE=/app/config.yaml
ENV OUTPUT_DIR=/app/output
ENV LOG_LEVEL=INFO

# 创建非root用户
RUN useradd -m -u 1000 processor && \
    chown -R processor:processor /app

# 切换到非root用户
USER processor

# 暴露端口（API服务）
EXPOSE 8000

# 默认启动API服务器
CMD ["python", "start_server.py"]
