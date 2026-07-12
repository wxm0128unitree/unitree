"""
自动备份脚本
==========
支持两种数据库：
  - SQLite（本地 / Docker / 嵌入式）：使用 sqlite3 的 .backup 命令，热备份、不会损坏
  - PostgreSQL（Render / 托管 PG）：使用 pg_dump 导出 SQL

备份目录布局：
  /data/backups/
      daily/         # 每天一次（保留 30 天）
          robot_2026-07-10_030000.db
      weekly/        # 每周一次（保留 12 周）
          robot_2026-W28.db
      manual/        # 管理员手动触发
          robot_2026-07-10_143012.db

用法：
  # 手动跑一次
  python -m app.backup

  # Docker 中由 cron 每日凌晨 3 点触发
  0 3 * * * cd /app && python -m app.backup >> /var/log/backup.log 2>&1

环境变量：
  BACKUP_ROOT      备份根目录，默认 /data/backups
  BACKUP_KEEP_DAILY   每日备份保留天数，默认 30
  BACKUP_KEEP_WEEKLY  每周备份保留周数，默认 12
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path


# 与 database.py 同样的检测逻辑，避免循环 import
def _detect_db_kind() -> str:
    url = os.environ.get("DATABASE_URL", "")
    if url.startswith("libsql"):
        return "libsql"
    if url.startswith("postgres"):
        return "postgres"
    return "sqlite"


def _sqlite_db_path() -> Path:
    """拿 SQLite 文件路径；与 database.py 保持一致"""
    root = Path(__file__).resolve().parent.parent.parent  # backend/app/.. -> backend/..
    default = root / "robot_inventory.db"
    return Path(os.environ.get("DB_PATH", str(default)))


def _backup_root() -> Path:
    root = Path(os.environ.get("BACKUP_ROOT", str(Path(tempfile.gettempdir()) / "unitree-backups")))
    root.mkdir(parents=True, exist_ok=True)
    return root


def _timestamp(fmt: str) -> str:
    return datetime.now().strftime(fmt)


def _run_sqlite_backup(src_db: Path, dst_file: Path) -> None:
    """通过 sqlite3 .backup 做一致性的热备份。
    .backup 命令会等所有读事务结束再拷，不损坏 WAL/Journal。
    """
    import sqlite3

    dst_file.parent.mkdir(parents=True, exist_ok=True)
    src_uri = f"file:{src_db}?mode=ro"
    with sqlite3.connect(src_uri, uri=True) as src:
        with sqlite3.connect(str(dst_file)) as dst:
            src.backup(dst)
    print(f"[OK] SQLite backup -> {dst_file}")


def _run_pg_backup(dst_file: Path) -> None:
    """通过 pg_dump 导出 SQL。
    psycopg3 已在 requirements 里，但 pg_dump 是 PostgreSQL 自带命令，
    Docker python:3.12-slim 默认没有，所以这里走 subprocess 优先，
    失败则降级到 SQLAlchemy 逐表 SELECT .. format_insert。
    """
    dst_file.parent.mkdir(parents=True, exist_ok=True)
    url = os.environ["DATABASE_URL"]
    # 把 SQLAlchemy URL 还原成 libpq URL（去掉 +psycopg 后缀）
    libpq_url = url.replace("postgresql+psycopg://", "postgresql://", 1)

    pg_dump_bin = shutil.which("pg_dump")
    if pg_dump_bin:
        env = os.environ.copy()
        # pg_dump 自动从 URI 解析；不需要额外参数
        with open(dst_file, "wb") as f:
            r = subprocess.run(
                [pg_dump_bin, "--no-owner", "--no-privileges", libpq_url],
                stdout=f, stderr=subprocess.PIPE, env=env,
            )
        if r.returncode == 0:
            print(f"[OK] pg_dump backup -> {dst_file}")
            return
        print(f"[WARN] pg_dump failed ({r.returncode}): {r.stderr.decode(errors='ignore')[:300]}")

    # 降级：用 psycopg 自带的 pg_dump 兼容路径（psycopg3 的 Copy 导出能力较弱，
    # 这里直接走 SQLAlchemy + 每张表 SELECT INTO OUTFILE 之类不可移植，
    # 所以最稳还是再尝试一次 pg_dump，或者用 pg_dump 远程模式）
    raise RuntimeError(
        "PostgreSQL 备份需要安装 pg_dump 客户端。"
        "Dockerfile 中加入 'apt-get install -y postgresql-client' 后重试。"
    )


def _run_libsql_backup(dst_file: Path) -> None:
    """libsql/Turso：调用 .backup 命令将其导出到本地文件。"""
    import libsql

    dst_file.parent.mkdir(parents=True, exist_ok=True)
    url = os.environ["DATABASE_URL"]
    token = os.environ.get("DATABASE_AUTH_TOKEN", "")
    conn = libsql.connect(database=":memory:", sync_url=url, auth_token=token)
    try:
        with open(dst_file, "wb") as f:
            for chunk in conn.execute("SELECT 1"):
                pass
        # libsql 没有直接的 .backup API；最稳的方式：逐表 SELECT 转 SQL
        # 这里采用一个折中：调用 .dump（如果 libsql 支持），否则抛错
        try:
            dump = conn.execute("PRAGMA wal_checkpoint(FULL)")
        except Exception:
            pass
        with open(dst_file, "wb") as f:
            f.write(_dump_libsql_via_select(conn))
        print(f"[OK] libsql backup -> {dst_file}")
    finally:
        conn.close()


def _json_value(value):
    return value.isoformat() if isinstance(value, datetime) else value


def _run_portable_backup(dst_file: Path) -> None:
    """使用 SQLAlchemy 生成 PostgreSQL/libSQL/SQLite 均可恢复的完整 JSON 快照。"""
    from app.database import engine
    from app import models
    dst_file.parent.mkdir(parents=True, exist_ok=True)
    tables = [models.User.__table__, models.Robot.__table__, models.OperationLog.__table__]
    payload = {"format": "unitree-backup", "version": 1, "created_at": datetime.now().isoformat(), "tables": {}}
    with engine.connect() as conn:
        for table in tables:
            rows = conn.execute(table.select()).mappings().all()
            payload["tables"][table.name] = [
                {key: _json_value(value) for key, value in dict(row).items()} for row in rows
            ]
    temp = dst_file.with_suffix(dst_file.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    json.loads(temp.read_text(encoding="utf-8"))
    temp.replace(dst_file)


def _dump_libsql_via_select(conn) -> bytes:
    """退化路径：用 SELECT 拿所有表数据，生成 INSERT SQL。
    适合数据量小的内部工具；Turso 上的生产大库建议用其自带导出功能。"""
    out = []
    out.append(b"-- libsql backup via SELECT\nBEGIN TRANSACTION;\n")
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )]
    for t in tables:
        cols = [r[1] for r in conn.execute(f"PRAGMA table_info({t})")]
        col_list = ",".join(f'"{c}"' for c in cols)
        for row in conn.execute(f"SELECT {col_list} FROM {t}"):
            vals = ",".join("NULL" if v is None else f"'{str(v).replace(chr(39), chr(39)*2)}'" for v in row)
            out.append(f"INSERT INTO {t} ({col_list}) VALUES ({vals});\n".encode())
    out.append(b"COMMIT;\n")
    return b"".join(out)


def _prune_old_files(directory: Path, keep: int, pattern: str = "robot_*") -> int:
    """保留最新的 N 个备份，删除更早的。返回删除数量。"""
    if not directory.exists():
        return 0
    files = sorted(directory.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    removed = 0
    for old in files[keep:]:
        try:
            old.unlink()
            removed += 1
        except OSError as e:
            print(f"[WARN] failed to delete old backup {old}: {e}")
    return removed


def daily_backup() -> Path:
    root = _backup_root()
    kind = _detect_db_kind()
    day = _timestamp("%Y-%m-%d_%H%M%S")
    if kind == "sqlite":
        ext = "db"
        target = root / "daily" / f"robot_{day}.{ext}"
        _run_sqlite_backup(_sqlite_db_path(), target)
    elif kind in {"postgres", "libsql"}:
        target = root / "daily" / f"robot_{day}.json"
        _run_portable_backup(target)
    else:
        raise RuntimeError(f"unsupported DB kind: {kind}")

    keep_daily = int(os.environ.get("BACKUP_KEEP_DAILY", "30"))
    removed = _prune_old_files(root / "daily", keep_daily, f"robot_*.{target.suffix[1:]}")
    if removed:
        print(f"[OK] pruned {removed} old daily backup(s), kept latest {keep_daily}")
    return target


def weekly_backup() -> Path:
    root = _backup_root()
    kind = _detect_db_kind()
    iso_week = datetime.now().strftime("%G-W%V")
    if kind == "sqlite":
        target = root / "weekly" / f"robot_{iso_week}.db"
        _run_sqlite_backup(_sqlite_db_path(), target)
    elif kind in {"postgres", "libsql"}:
        target = root / "weekly" / f"robot_{iso_week}.json"
        _run_portable_backup(target)
    else:
        raise RuntimeError(f"unsupported DB kind: {kind}")

    keep_weekly = int(os.environ.get("BACKUP_KEEP_WEEKLY", "12"))
    removed = _prune_old_files(root / "weekly", keep_weekly, f"robot_*.{target.suffix[1:]}")
    if removed:
        print(f"[OK] pruned {removed} old weekly backup(s), kept latest {keep_weekly}")
    return target


def manual_backup() -> Path:
    root = _backup_root()
    kind = _detect_db_kind()
    ts = _timestamp("%Y-%m-%d_%H%M%S")
    if kind == "sqlite":
        target = root / "manual" / f"robot_{ts}.db"
        _run_sqlite_backup(_sqlite_db_path(), target)
    elif kind in {"postgres", "libsql"}:
        target = root / "manual" / f"robot_{ts}.json"
        _run_portable_backup(target)
    else:
        raise RuntimeError(f"unsupported DB kind: {kind}")
    return target


def resolve_backup(kind: str, name: str) -> Path:
    """只允许访问备份根目录下的已知分类，阻止路径穿越。"""
    if kind not in {"daily", "weekly", "manual"}:
        raise ValueError("备份分类无效")
    if not name or Path(name).name != name:
        raise ValueError("备份文件名无效")
    target = (_backup_root() / kind / name).resolve()
    root = _backup_root().resolve()
    if root not in target.parents or not target.is_file():
        raise FileNotFoundError("备份文件不存在")
    return target


def restore_backup(kind: str, name: str) -> Path:
    """从管理员选定的备份恢复；恢复前自动生成一份安全备份。"""
    source = resolve_backup(kind, name)
    if source.suffix.lower() == ".json":
        safety = manual_backup()
        _restore_portable_backup(source)
        return safety
    if _detect_db_kind() != "sqlite" or source.suffix.lower() != ".db":
        raise ValueError("备份格式与当前数据库不兼容")
    import sqlite3
    with sqlite3.connect(f"file:{source}?mode=ro", uri=True) as check:
        if check.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise ValueError("备份完整性校验失败")
        required = {row[0] for row in check.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {"robots", "operation_logs", "users"}.issubset(required):
            raise ValueError("备份缺少必要数据表")
    safety = manual_backup()
    _run_sqlite_backup(source, _sqlite_db_path())
    return safety


def _restore_portable_backup(source: Path) -> None:
    from app.database import engine
    from app import models
    payload = json.loads(source.read_text(encoding="utf-8"))
    if payload.get("format") != "unitree-backup" or payload.get("version") != 1:
        raise ValueError("备份格式或版本无效")
    expected = {"users", "robots", "operation_logs"}
    if set(payload.get("tables", {})) != expected:
        raise ValueError("备份缺少必要数据表")
    tables = {t.name: t for t in [models.User.__table__, models.Robot.__table__, models.OperationLog.__table__]}
    converted = {}
    for name, rows in payload["tables"].items():
        table = tables[name]
        columns = {c.name: c for c in table.columns}
        converted[name] = []
        for row in rows:
            if not isinstance(row, dict) or not set(row).issubset(columns):
                raise ValueError(f"备份表 {name} 包含无效字段")
            clean = {}
            for key, value in row.items():
                if value is not None and columns[key].type.python_type is datetime:
                    value = datetime.fromisoformat(value)
                clean[key] = value
            converted[name].append(clean)
    with engine.begin() as conn:
        conn.execute(tables["operation_logs"].delete())
        conn.execute(tables["robots"].delete())
        conn.execute(tables["users"].delete())
        for name in ("users", "robots", "operation_logs"):
            if converted[name]:
                conn.execute(tables[name].insert(), converted[name])
        if engine.dialect.name == "postgresql":
            for name in ("users", "robots", "operation_logs"):
                conn.exec_driver_sql(
                    f"SELECT setval(pg_get_serial_sequence('{name}', 'id'), COALESCE((SELECT MAX(id) FROM {name}), 1), true)"
                )


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    cmd = argv[0] if argv else "daily"
    start = time.time()
    try:
        if cmd == "daily":
            f = daily_backup()
        elif cmd == "weekly":
            f = weekly_backup()
        elif cmd == "manual":
            f = manual_backup()
        else:
            print(f"unknown command: {cmd}", file=sys.stderr)
            return 2
        print(f"[OK] backup finished in {time.time() - start:.1f}s -> {f}")
        return 0
    except Exception as e:
        print(f"[ERROR] backup failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
