"""
数据库配置
- 本地开发：SQLite 文件（默认 ./robot_inventory.db）
- 线上部署：Turso (libSQL) — 设置 DATABASE_URL=libsql://xxx.turso.io
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_DB_PATH = os.path.join(BASE_DIR, "robot_inventory.db")
DB_PATH = os.environ.get("DB_PATH", DEFAULT_DB_PATH)
DATABASE_URL = os.environ.get("DATABASE_URL")

# libsql:// → Turso / 远端 SQLite
# 默认本地：sqlite:///
if DATABASE_URL and DATABASE_URL.startswith("libsql"):
    SQLALCHEMY_DATABASE_URL = "sqlite:///"  # 占位符，用 creator 自定义连接
    USE_LIBSQL = True
elif DATABASE_URL and DATABASE_URL.startswith("postgres"):
    # 用 psycopg3 (新版本) 替代 psycopg2，更快且 Python 3.12 兼容
    SQLALCHEMY_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
    USE_LIBSQL = False
elif DATABASE_URL:
    SQLALCHEMY_DATABASE_URL = DATABASE_URL
    USE_LIBSQL = False
else:
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"
    USE_LIBSQL = False

# Turso 配置
TURSO_URL = os.environ.get("DATABASE_URL") if USE_LIBSQL else None
TURSO_AUTH_TOKEN = os.environ.get("DATABASE_AUTH_TOKEN", "")


def _libsql_creator():
    """给 SQLAlchemy 用的连接工厂：每次请求新连接走 libsql"""
    import libsql
    return libsql.connect(
        database=":memory:",
        sync_url=TURSO_URL,
        auth_token=TURSO_AUTH_TOKEN,
    )


def _sqlite_args():
    if USE_LIBSQL:
        return {}
    if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
        # 确保目录存在
        _dir = os.path.dirname(SQLALCHEMY_DATABASE_URL.replace("sqlite:///", ""))
        if _dir:
            os.makedirs(_dir, exist_ok=True)
        return {"check_same_thread": False, "timeout": 30}
    return {}


engine_kwargs = {
    "echo": False,
    "pool_pre_ping": True,
}
if USE_LIBSQL:
    engine_kwargs["creator"] = _libsql_creator
elif SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False, "timeout": 30}
    # 确保目录存在
    _dir = os.path.dirname(SQLALCHEMY_DATABASE_URL.replace("sqlite:///", ""))
    if _dir:
        os.makedirs(_dir, exist_ok=True)

engine = create_engine(SQLALCHEMY_DATABASE_URL, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """初始化数据库（checkfirst=True → IF NOT EXISTS，安全幂等）"""
    from app import models  # noqa
    Base.metadata.create_all(bind=engine, checkfirst=True)


def single_process_bootstrap():
    """多进程下只让一个进程执行 bootstrap"""
    try:
        conn = engine.connect()
        conn.exec_driver_sql("BEGIN IMMEDIATE")
        try:
            from app import models
            count = conn.exec_driver_sql(
                "SELECT COUNT(*) FROM users"
            ).scalar() or 0
            return count == 0
        finally:
            conn.exec_driver_sql("COMMIT")
            conn.close()
    except Exception as e:
        print(f"[WARN] bootstrap lock failed: {e}")
        return False