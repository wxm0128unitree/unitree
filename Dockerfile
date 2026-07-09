# ============ Stage 1: 构建前端 ============
FROM node:20-alpine AS frontend-build
WORKDIR /web

# 装前端依赖
COPY frontend/package*.json ./
RUN npm install --no-audit --no-fund

# 复制前端源码并构建
COPY frontend/ ./
# 允许在容器内访问后端默认地址（如果用户在反代后，nginx 转发，前端无需特殊配置）
RUN npm run build

# ============ Stage 2: 跑后端 ============
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 系统依赖（curl 用于健康检查）
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# 装后端依赖
COPY backend/requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

# 复制后端代码
COPY backend/ /app/

# 从前端构建阶段复制 dist
COPY --from=frontend-build /web/dist /app/frontend/dist

# 数据卷：SQLite / 上传文件 / 持久化
RUN mkdir -p /data
ENV DB_PATH=/data/robot_inventory.db \
    FRONTEND_DIST=/app/frontend/dist \
    ALLOW_REGISTER=1 \
    ADMIN_NAME="王曦明" \
    ADMIN_PHONE=13083401281 \
    ADMIN_PASSWORD=111111

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8000/api/health || exit 1

# 用 4 个 worker + uvicorn（生产级）
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
