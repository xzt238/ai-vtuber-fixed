# 咕咕嘎嘎 AI-VTuber Docker镜像
# 基于Python 3.11 slim镜像

FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV DEBIAN_FRONTEND=noninteractive

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    wget \
    curl \
    unzip \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgcc-s1 \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .
COPY requirements-build.txt .

# 安装Python依赖
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 创建必要的目录
RUN mkdir -p /app/cache \
    /app/logs \
    /app/memory \
    /app/models \
    /app/GPT-SoVITS/GPT_weights_v3 \
    /app/GPT-SoVITS/SoVITS_weights_v3

# 设置权限
RUN chmod +x /app/scripts/*.sh || true

# 暴露端口
EXPOSE 12393 12394

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:12393/ || exit 1

# 启动命令
CMD ["python", "-m", "app.main"]