# ============ 阶段 1: 前端构建 ============
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

# 复制前端依赖文件
COPY frontend/package*.json ./

# 安装所有依赖（包括 devDependencies，构建需要）
RUN npm ci

# 复制前端源码并构建
COPY frontend/ ./
RUN npm run build

# ============ 阶段 2: Python 运行环境 ============
FROM python:3.12-slim

WORKDIR /app/backend

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制requirements.txt并安装Python依赖
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制后端应用程序代码
COPY backend/ ./

# 准备数据目录并复制前端产物
RUN mkdir -p /app/data/static /app/data/logs
# Vite 配置中 outDir 是 ../data/static，所以构建产物在 /app/data/static
COPY --from=frontend-builder /app/data/static /app/data/static

# 创建配置文件（如果不存在）
RUN touch /app/backend/configs/config.txt

# 设置权限
RUN chmod +x app/mail_api.py

# 暴露端口
EXPOSE 5001

# 设置健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5001/ || exit 1

# 启动命令
ENV PYTHONPATH=/app/backend
CMD ["python", "-m", "app.mail_api", "web"]
