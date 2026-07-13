import os
import tempfile
from pathlib import Path

DB_FILE = Path(tempfile.gettempdir()) / "unitree_api_tests.db"
if DB_FILE.exists():
    DB_FILE.unlink()
os.environ["DB_PATH"] = str(DB_FILE)
os.environ["JWT_SECRET"] = "test-secret-test-secret-test-secret-123456"
os.environ["ADMIN_NAME"] = "测试管理员"
os.environ["ADMIN_PHONE"] = "13800000000"
os.environ["ADMIN_PASSWORD"] = "test-password"
os.environ["BACKUP_ROOT"] = str(Path(tempfile.gettempdir()) / "unitree_backups")

from fastapi.testclient import TestClient
from app.main import app


def auth(client):
    response = client.post("/api/auth/login", json={"phone": "13800000000", "password": "test-password"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_api_marks_generated_timestamps_as_utc():
    with TestClient(app) as client:
        headers = auth(client)
        users = client.get("/api/users", headers=headers).json()
        assert users[0]["created_at"].endswith("+00:00")
        assert users[0]["last_login_at"].endswith("+00:00")


def test_protected_reads_and_full_robot_lifecycle():
    with TestClient(app) as client:
        for path in ("/api/robots", "/api/stats", "/api/logs"):
            assert client.get(path).status_code == 401
        assert client.post("/api/admin/init").status_code == 404
        headers = auth(client)
        created = client.post("/api/robots", headers=headers, json={
            "asset_code": "G1-TEST-001", "model": "G1", "owner_department": "研发部",
            "owner_name": "张三", "holder": "张三", "status": "在库",
        })
        assert created.status_code == 200, created.text
        robot_id = created.json()["id"]

        edited = client.put(f"/api/robots/{robot_id}", headers=headers, json={
            "asset_code": "G1-TEST-001", "model": "G1-Pro", "owner_department": "研发部",
            "owner_name": "李四", "location": "一楼库房", "remark": "含充电器",
        })
        assert edited.status_code == 200
        assert edited.json()["owner_name"] == "李四"

        changed = client.post(f"/api/robots/{robot_id}/status", headers=headers, json={
            "status": "借出", "location": "二楼实验室", "borrower": "王五",
            "purpose": "算法测试", "expected_return_at": "2030-01-02T12:00:00", "note": "测试借出",
        })
        assert changed.status_code == 200, changed.text
        assert changed.json()["borrower"] == "王五"

        checked = client.post(f"/api/robots/{robot_id}/inventory", headers=headers,
            json={"location": "二楼实验室", "note": "设备正常"})
        assert checked.status_code == 200
        assert checked.json()["last_inventory_by"] == "测试管理员"

        assert client.delete(f"/api/robots/{robot_id}", headers=headers).status_code == 200
        assert client.get("/api/robots", headers=headers).json() == []
        archived = client.get("/api/robots?include_archived=true", headers=headers).json()
        assert archived[0]["is_archived"] == 1
        assert client.post(f"/api/robots/{robot_id}/restore", headers=headers).status_code == 200

        logs = client.get("/api/logs?action=盘点&page_size=1", headers=headers).json()
        assert logs["total"] == 1
        assert logs["items"][0]["action"] == "盘点"
        assert client.get("/api/export/robots.csv", headers=headers).status_code == 200
        assert client.get("/api/export/logs.csv", headers=headers).status_code == 200


def test_admin_user_management_and_disabled_login():
    with TestClient(app) as client:
        headers = auth(client)
        created = client.post("/api/users", headers=headers, json={
            "name": "普通用户", "phone": "13900000000", "password": "password1", "is_admin": 0,
        })
        assert created.status_code == 200, created.text
        user_id = created.json()["id"]
        assert client.put(f"/api/users/{user_id}", headers=headers, json={"is_active": 0}).status_code == 200
        denied = client.post("/api/auth/login", json={"phone": "13900000000", "password": "password1"})
        assert denied.status_code == 403


def test_backup_path_traversal_is_rejected():
    from app.backup import resolve_backup
    try:
        resolve_backup("manual", "../secret.db")
        assert False, "path traversal should fail"
    except ValueError:
        pass


def test_portable_backup_round_trip():
    from app import models
    from app.backup import _run_portable_backup, _restore_portable_backup
    from app.database import engine
    snapshot = Path(tempfile.gettempdir()) / "unitree_portable_backup.json"
    _run_portable_backup(snapshot)
    with engine.begin() as conn:
        before = conn.execute(models.User.__table__.count() if hasattr(models.User.__table__, "count") else models.User.__table__.select()).fetchall()
        conn.execute(models.OperationLog.__table__.delete())
        conn.execute(models.Robot.__table__.delete())
        conn.execute(models.User.__table__.delete())
    _restore_portable_backup(snapshot)
    with engine.connect() as conn:
        after = conn.execute(models.User.__table__.select()).fetchall()
    assert len(after) == len(before)
