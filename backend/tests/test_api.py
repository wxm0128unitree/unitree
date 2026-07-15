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


def test_quantity_inventory_borrow_return_and_migration():
    with TestClient(app) as client:
        headers = auth(client)
        created = client.post('/api/inventory/items', headers=headers, json={
            'category': '电池', 'subtype': '', 'model': 'G1 电池', 'unit': '块',
            'initial_quantity': 20, 'location': '电池柜'
        })
        assert created.status_code == 200, created.text
        item_id = created.json()['id']
        borrowed = client.post(f'/api/inventory/items/{item_id}/action', headers=headers, json={
            'action': 'borrow', 'quantity': 3, 'borrower': '张三', 'purpose': '测试'
        })
        assert borrowed.json()['available_quantity'] == 17
        assert borrowed.json()['loaned_quantity'] == 3
        assert client.post(f'/api/inventory/items/{item_id}/action', headers=headers,
            json={'action': 'borrow', 'quantity': 99}).status_code == 400
        assert client.post(f'/api/inventory/items/{item_id}/action', headers=headers,
            json={'action': 'borrow', 'quantity': 1}).status_code == 400
        returned = client.post(f'/api/inventory/items/{item_id}/action', headers=headers,
            json={'action': 'return', 'quantity': 2})
        assert returned.json()['available_quantity'] == 19
        migrated = client.post(f'/api/inventory/items/{item_id}/action', headers=headers, json={
            'action': 'migrate', 'quantity': 5, 'destination_department': '算法部'
        })
        assert migrated.json()['total_quantity'] == 15
        assert migrated.json()['available_quantity'] == 14


def test_training_platform_stats_and_robot_migration():
    with TestClient(app) as client:
        headers = auth(client)
        created = client.post('/api/robots', headers=headers, json={
            'asset_code': 'PT-H-001', 'model': '实训台', 'device_branch': 'training_platform',
            'platform_type': 'humanoid', 'status': '在库'
        })
        assert created.status_code == 200, created.text
        robot_id = created.json()['id']
        stats = client.get('/api/stats', headers=headers).json()
        assert stats['training_platforms']['humanoid'] >= 1
        migrated = client.post(f'/api/robots/{robot_id}/migrate', headers=headers,
            json={'destination_department': '其他部门', 'destination_holder': '李四', 'reason': '项目迁移'})
        assert migrated.status_code == 200
        assert migrated.json()['lifecycle_status'] == 'migrated'
        assert client.post(f'/api/robots/{robot_id}/status', headers=headers,
            json={'status': '借出', 'location': '外部'}).status_code == 404
        assert client.post(f'/api/robots/{robot_id}/inventory', headers=headers,
            json={'location': '外部', 'note': '不应允许'}).status_code == 404
        active_ids = [r['id'] for r in client.get('/api/robots', headers=headers).json()]
        assert robot_id not in active_ids
        assert client.post(f'/api/robots/{robot_id}/undo-migration', headers=headers).status_code == 200


def test_training_platform_identity_is_normalized_and_survives_editing():
    with TestClient(app) as client:
        headers = auth(client)
        created = client.post('/api/robots', headers=headers, json={
            'asset_code': 'PT-Q-LOGIC-001', 'model': 'G1',
            'device_branch': 'training_platform', 'platform_type': 'quadruped', 'status': '在库'
        })
        assert created.status_code == 200, created.text
        robot = created.json()
        assert robot['model'] == '实训台'
        assert robot['device_branch'] == 'training_platform'
        assert client.get('/api/stats', headers=headers).json()['training_platforms']['quadruped'] >= 1

        edited = client.put(f"/api/robots/{robot['id']}", headers=headers, json={
            'asset_code': robot['asset_code'], 'model': 'R1',
            'device_branch': 'training_platform', 'platform_type': 'quadruped',
            'owner_department': '实训中心', 'owner_name': '', 'location': '3楼', 'remark': ''
        })
        assert edited.status_code == 200, edited.text
        assert edited.json()['model'] == '实训台'
        assert edited.json()['device_branch'] == 'training_platform'

        invalid = client.post('/api/robots', headers=headers, json={
            'asset_code': 'PT-BAD-001', 'model': '实训台',
            'device_branch': 'training_platform', 'platform_type': '', 'status': '在库'
        })
        assert invalid.status_code == 400
