"""
生产模式启动脚本（无 Docker 时的备选方案）
用法：
    cd backend
    python run_prod.py
"""
import os
import sys
import secrets
import uvicorn
from pathlib import Path

ROOT = Path(__file__).parent.parent


def auto_secret() -> str:
    """若 JWT_SECRET 未设置，自动生成并写入 .env（仅第一次）"""
    env_file = ROOT / ".env"
    env_file_existed = env_file.exists()

    if not os.environ.get("JWT_SECRET"):
        secret_path = ROOT / ".jwt_secret"
        if secret_path.exists():
            os.environ["JWT_SECRET"] = secret_path.read_text().strip()
        else:
            secret = secrets.token_urlsafe(64)
            secret_path.write_text(secret)
            os.environ["JWT_SECRET"] = secret
            print(f"[INFO] JWT_SECRET auto-generated and saved to {secret_path}")

    if not env_file_existed and not env_file.exists():
        env_file.write_text(f"JWT_SECRET={os.environ['JWT_SECRET']}\n"
                            f"ADMIN_NAME=王曦明\nADMIN_PHONE=13083401281\nADMIN_PASSWORD=111111\n"
                            f"ALLOW_REGISTER=1\nDB_PATH={os.environ.get('DB_PATH', './data/robot_inventory.db')}\n"
                            f"\n# 复制本文件可编辑；首次启动将自动创建本文件\n")


def main():
    auto_secret()

    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    workers = int(os.environ.get("WORKERS", "4"))

    os.environ.setdefault("DB_PATH", os.path.join(ROOT, "data", "robot_inventory.db"))
    os.makedirs(os.path.dirname(os.environ["DB_PATH"]), exist_ok=True)

    os.environ.setdefault("FRONTEND_DIST", str(ROOT / "frontend" / "dist"))

    print("=" * 60)
    print(" 宇树机器人出入库管理系统 - 生产模式")
    print(f" 监听: http://{host}:{port}")
    print(f" 进程: {workers} workers")
    print(f" 数据库: {os.environ['DB_PATH']}")
    print(f" 前端:  {os.environ['FRONTEND_DIST']}")
    print("=" * 60)

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        workers=workers,
        log_level="info",
        proxy_headers=True,    # 关键：让 uvicorn 信任 Caddy/Nginx 转发的真实 IP / 协议
        forwarded_allow_ips="*",  # 内网反代，不需要严格限制
    )


if __name__ == "__main__":
    main()
