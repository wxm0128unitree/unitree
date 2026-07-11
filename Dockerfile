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

# 系统依赖：curl 健康检查、tzdata 让 supercronic 用东八区
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        tzdata \
    && rm -rf /var/lib/apt/lists/*

# 装 supercronic（小体积、单二进制、容器友好的 cron）
ARG SUPERCRONIC_VERSION=v0.2.33
RUN ARCH=$(dpkg --print-architecture) && \
    case "$ARCH" in \
        amd64) SC_ARCH=amd64 ;; \
        arm64) SC_ARCH=arm64 ;; \
        armhf) SC_ARCH=armv7 ;; \
        *) echo "unsupported arch $ARCH" && exit 1 ;; \
    esac && \
    curl -fsSL "https://github.com/aptible/supercronic/releases/download/${SUPERCRONIC_VERSION}/supercronic-linux-${SC_ARCH}" \
        -o /usr/local/bin/supercronic && \
    chmod +x /usr/local/bin/supercronic && \
    supercronic -version || true

# 装后端依赖
COPY backend/requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

# 复制后端代码
COPY backend/ /app/

# 从前端构建阶段复制 dist
COPY --from=frontend-build /web/dist /app/frontend/dist

# 数据卷：SQLite / 上传文件 / 持久化；backup 目录放 /data/backups
RUN mkdir -p /data/backups/daily /data/backups/weekly /data/backups/manual
ENV DB_PATH=/data/robot_inventory.db \
    FRONTEND_DIST=/app/frontend/dist \
    ALLOW_REGISTER=1 \
    ADMIN_NAME="王曦明" \
    ADMIN_PHONE=13083401281 \
    ADMIN_PASSWORD=111111 \
    BACKUP_ROOT=/data/backups \
    BACKUP_KEEP_DAILY=30 \
    BACKUP_KEEP_WEEKLY=12 \
    TZ=Asia/Shanghai

# 自动备份 crontab：
#   每天凌晨 3 点 跑一次 daily 备份
#   每周一凌晨 4 点跑一次 weekly 备份
# supercronic 时区用上面 ENV TZ=Asia/Shanghai
RUN printf '0 3 * * * cd /app && /usr/local/bin/python -m app.backup daily >> /data/backups/backup.log 2>&1\n' \
           '0 4 * * 1 cd /app && /usr/local/bin/python -m app.backup weekly >> /data/backups/backup.log 2>&1\n' \
       > /etc/crontab.backup

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8000/api/health || exit 1

# 同时启动 uvicorn 和 supercronic：
#   - uvicorn 4 worker 是数据库 backend
#   - supercronic 负责每日定时备份
# 用一个 shell 启动脚本同时拉起两者，任意一个挂掉容器退出
RUN printf '#!/bin/sh\nset -e\n\
echo "[INFO] starting supercronic for daily backups..."\n\
/usr/local/bin/supercronic /etc/crontab.backup >> /data/backups/crond.log 2>&1 &\n\
SUPER_PID=$!\n\
echo "[INFO] starting uvicorn..."\n\
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4\n' > /entrypoint.sh && \
    chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]
