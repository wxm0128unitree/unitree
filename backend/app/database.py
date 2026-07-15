"""
数据库配置
- 本地开发：SQLite 文件（默认 ./robot_inventory.db）
- 线上部署：Turso (libSQL) — 设置 DATABASE_URL=libsql://xxx.turso.io
"""
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import SQLAlchemyError
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
    _migrate_existing_database()
    _normalize_legacy_training_platforms()


def _migrate_existing_database():
    """为没有 Alembic 的旧部署补齐新增列；每次启动可安全重复执行。"""
    migrations = {
        "robots": {
            "device_branch": "VARCHAR(32) NOT NULL DEFAULT 'standard_robot'",
            "platform_type": "VARCHAR(32) DEFAULT ''",
            "lifecycle_status": "VARCHAR(16) NOT NULL DEFAULT 'active'",
            "owner_department": "VARCHAR(64) DEFAULT ''",
            "owner_name": "VARCHAR(32) DEFAULT ''",
            "borrower": "VARCHAR(32) DEFAULT ''",
            "purpose": "VARCHAR(128) DEFAULT ''",
            "borrowed_at": "TIMESTAMP NULL",
            "expected_return_at": "TIMESTAMP NULL",
            "repair_description": "TEXT DEFAULT ''",
            "is_archived": "INTEGER NOT NULL DEFAULT 0",
            "archived_at": "TIMESTAMP NULL",
            "migrated_at": "TIMESTAMP NULL",
            "destination_department": "VARCHAR(64) DEFAULT ''",
            "destination_holder": "VARCHAR(32) DEFAULT ''",
            "migration_reason": "TEXT DEFAULT ''",
            "last_inventory_at": "TIMESTAMP NULL",
            "last_inventory_by": "VARCHAR(64) DEFAULT ''",
            "last_inventory_location": "VARCHAR(128) DEFAULT ''",
            "inventory_note": "TEXT DEFAULT ''",
        },
        "users": {
            "is_active": "INTEGER NOT NULL DEFAULT 1",
            "last_login_at": "TIMESTAMP NULL",
        },
    }
    tables = set(inspect(engine).get_table_names())
    for table, columns in migrations.items():
        if table not in tables:
            continue
        for name, definition in columns.items():
            try:
                with engine.begin() as conn:
                    existing = {c["name"] for c in inspect(conn).get_columns(table)}
                    if name in existing:
                        continue
                    conn.exec_driver_sql(
                        f'ALTER TABLE "{table}" ADD COLUMN "{name}" {definition}'
                    )
            except SQLAlchemyError as exc:
                # 多 worker 首次部署可能同时迁移；另一进程已添加该列时视为成功。
                message = str(exc).lower()
                if "duplicate column" not in message and "already exists" not in message:
                    raise


def _normalize_legacy_training_platforms():
    """只修复可明确识别的旧分类值，不删除、不覆盖无法判断的数据。"""
    if "robots" not in set(inspect(engine).get_table_names()):
        return
    with engine.begin() as conn:
        conn.exec_driver_sql(
            "UPDATE robots SET device_branch = 'training_platform' "
            "WHERE device_branch IN ('training', 'training_table', '实训台')"
        )
        conn.exec_driver_sql(
            "UPDATE robots SET platform_type = 'humanoid', device_branch = 'training_platform' "
            "WHERE platform_type IN ('human', '人形', '人形实训台') OR model = '人形实训台'"
        )
        conn.exec_driver_sql(
            "UPDATE robots SET platform_type = 'quadruped', device_branch = 'training_platform' "
            "WHERE platform_type IN ('quadruped_robot', '四足', '四足实训台') OR model = '四足实训台'"
        )
        conn.exec_driver_sql(
            "UPDATE robots SET device_branch = 'training_platform' "
            "WHERE model = '实训台'"
        )


def single_process_bootstrap():
    """多进程下只让一个进程执行 bootstrap"""
    try:
        if engine.dialect.name == "postgresql":
            with engine.begin() as conn:
                conn.exec_driver_sql("SELECT pg_advisory_xact_lock(82736491)")
                count = conn.exec_driver_sql("SELECT COUNT(*) FROM users").scalar() or 0
                return count == 0
        conn = engine.connect()
        conn.exec_driver_sql("BEGIN IMMEDIATE")
        try:
            count = conn.exec_driver_sql("SELECT COUNT(*) FROM users").scalar() or 0
            return count == 0
        finally:
            conn.exec_driver_sql("COMMIT")
            conn.close()
    except Exception as e:
        print(f"[WARN] bootstrap lock failed: {e}")
        return False
