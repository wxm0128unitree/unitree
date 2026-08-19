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
            "owner_name": "测试管理员", "holder": "测试管理员", "status": "在库",
        })
        assert created.status_code == 200, created.text
        robot_id = created.json()["id"]

        edited = client.put(f"/api/robots/{robot_id}", headers=headers, json={
            "asset_code": "G1-TEST-001", "model": "G1-Pro", "owner_department": "研发部",
            "owner_name": "测试管理员", "holder": "测试管理员", "location": "一楼库房", "remark": "含充电器",
        })
        assert edited.status_code == 200
        assert edited.json()["owner_name"] == "测试管理员"

        changed = client.post(f"/api/robots/{robot_id}/status", headers=headers, json={
            "status": "借出", "location": "二楼实验室", "borrower": "王五",
            "purpose": "算法测试", "expected_return_at": "2030-01-02T12:00:00", "note": "测试借出", "holder": "任意值",
        })
        assert changed.status_code == 200, changed.text
        assert changed.json()["borrower"] == "王五"
        assert changed.json()["holder"] == "王五"

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
            'category': '拓展坞', 'subtype': '', 'model': 'G1 拓展坞', 'unit': '个',
            'initial_quantity': 20, 'location': '配件柜', 'asset_code': 'DOCK-G1', 'status': '在库',
            'owner_name': '测试管理员', 'holder': '测试管理员'
        })
        assert created.status_code == 200, created.text
        assert created.json()['asset_code'] == 'DOCK-G1'
        item_id = created.json()['id']
        borrowed = client.post(f'/api/inventory/items/{item_id}/action', headers=headers, json={
            'action': 'borrow', 'quantity': 20, 'borrower': '张三', 'purpose': '测试'
        })
        assert borrowed.json()['available_quantity'] == 0
        assert borrowed.json()['loaned_quantity'] == 20
        assert borrowed.json()['holder'] == '张三'
        assert client.post(f'/api/inventory/items/{item_id}/action', headers=headers,
            json={'action': 'borrow', 'quantity': 99}).status_code == 400
        assert client.post(f'/api/inventory/items/{item_id}/action', headers=headers,
            json={'action': 'borrow', 'quantity': 1}).status_code == 400
        returned = client.post(f'/api/inventory/items/{item_id}/action', headers=headers,
            json={'action': 'return', 'quantity': 20})
        assert returned.json()['available_quantity'] == 20
        assert returned.json()['holder'] == '测试管理员'
        migrated = client.post(f'/api/inventory/items/{item_id}/action', headers=headers, json={
            'action': 'migrate', 'quantity': 5, 'destination_department': '算法部'
        })
        assert migrated.json()['total_quantity'] == 15
        assert migrated.json()['available_quantity'] == 15
        emptied = client.post(f'/api/inventory/items/{item_id}/action', headers=headers, json={
            'action': 'migrate', 'quantity': 15, 'destination_department': '算法部'
        })
        assert emptied.status_code == 200
        assert all(x['id'] != item_id for x in client.get('/api/inventory/items', headers=headers).json())


def test_training_platform_stats_and_robot_migration():
    with TestClient(app) as client:
        headers = auth(client)
        created = client.post('/api/robots', headers=headers, json={
            'asset_code': 'PT-H-001', 'model': '实训台', 'device_branch': 'training_platform',
            'platform_type': 'humanoid', 'status': '在库', 'owner_name': '测试管理员', 'holder': '测试管理员'
        })
        assert created.status_code == 200, created.text
        robot_id = created.json()['id']
        stats = client.get('/api/stats', headers=headers).json()
        assert stats['by_model']['实训台']['total'] >= 1
        assert stats['by_model']['实训台']['in_stock'] >= 1
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
            'device_branch': 'training_platform', 'platform_type': 'quadruped', 'status': '在库',
            'owner_name': '测试管理员', 'holder': '测试管理员'
        })
        assert created.status_code == 200, created.text
        robot = created.json()
        assert robot['model'] == '实训台'
        assert robot['device_branch'] == 'training_platform'
        assert client.get('/api/stats', headers=headers).json()['by_model']['实训台']['total'] >= 1

        edited = client.put(f"/api/robots/{robot['id']}", headers=headers, json={
            'asset_code': robot['asset_code'], 'model': 'R1',
            'device_branch': 'training_platform', 'platform_type': 'quadruped',
            'owner_department': '实训中心', 'owner_name': '测试管理员', 'holder': '测试管理员', 'location': '3楼', 'remark': ''
        })
        assert edited.status_code == 200, edited.text
        assert edited.json()['model'] == '实训台'
        assert edited.json()['device_branch'] == 'training_platform'

        without_shape = client.post('/api/robots', headers=headers, json={
            'asset_code': 'PT-NO-SHAPE-001', 'model': '实训台',
            'device_branch': 'training_platform', 'status': '在库', 'owner_name': '测试管理员', 'holder': '测试管理员'
        })
        assert without_shape.status_code == 200
        assert without_shape.json()['platform_type'] == ''

        legacy_identity = client.post('/api/robots', headers=headers, json={
            'asset_code': 'PT-LEGACY-MODEL-001', 'model': '实训台', 'status': '在库',
            'owner_name': '测试管理员', 'holder': '测试管理员'
        })
        assert legacy_identity.status_code == 200
        assert legacy_identity.json()['device_branch'] == 'training_platform'


def test_regular_user_only_sees_owned_devices_and_logs():
    with TestClient(app) as client:
        admin_headers = auth(client)
        user = client.post('/api/users', headers=admin_headers, json={
            'name': '持有人甲', 'phone': '13700000001', 'password': 'password1', 'is_admin': 0,
        })
        assert user.status_code == 200, user.text
        mine = client.post('/api/robots', headers=admin_headers, json={
            'asset_code': 'OWNED-001', 'model': 'G1', 'holder': '外部保管人', 'owner_name': '持有人甲',
            'status': '借出', 'borrower': '外部保管人',
        }).json()
        other = client.post('/api/robots', headers=admin_headers, json={
            'asset_code': 'OTHER-001', 'model': 'R1', 'holder': '测试管理员', 'owner_name': '测试管理员',
        }).json()
        login = client.post('/api/auth/login', json={'phone': '13700000001', 'password': 'password1'})
        user_headers = {'Authorization': f"Bearer {login.json()['access_token']}"}
        visible = client.get('/api/robots', headers=user_headers).json()
        assert [r['id'] for r in visible] == [mine['id']]
        assert client.get(f"/api/robots/{other['id']}", headers=user_headers).status_code == 404
        assert client.get('/api/stats', headers=user_headers).json()['total'] == 1
        assert all(row['robot_id'] == mine['id'] for row in client.get('/api/logs', headers=user_headers).json()['items'])
        holder_names = {x['name'] for x in client.get('/api/holders', headers=user_headers).json()}
        assert holder_names == {'持有人甲', '外部保管人'}


def test_inventory_edit_delete_and_auto_archive_at_zero():
    with TestClient(app) as client:
        headers = auth(client)
        created = client.post('/api/inventory/items', headers=headers, json={
            'category': '遥控器', 'model': 'RC-ZERO', 'unit': '个', 'initial_quantity': 1,
            'asset_code': 'RC-001', 'status': '在库', 'owner_name': '测试管理员', 'holder': '测试管理员',
        })
        item_id = created.json()['id']
        edited = client.put(f'/api/inventory/items/{item_id}', headers=headers, json={
            'category': '遥控器', 'subtype': '', 'model': 'RC-ZERO', 'asset_code': 'RC-001',
            'status': '维修中', 'unit': '个', 'location': '维修柜', 'owner_department': '',
            'owner_name': '测试管理员', 'holder': '维修人员', 'remark': '待检修',
        })
        assert edited.status_code == 200, edited.text
        assert edited.json()['status'] == '维修中'
        assert client.delete(f'/api/inventory/items/{item_id}', headers=headers).status_code == 200
        assert all(item['id'] != item_id for item in client.get('/api/inventory/items', headers=headers).json())

        deletable = client.post('/api/inventory/items', headers=headers, json={
            'category': '拓展坞', 'model': 'DOCK-DELETE', 'initial_quantity': 2,
            'owner_name': '测试管理员', 'holder': '测试管理员',
        }).json()
        assert client.delete(f"/api/inventory/items/{deletable['id']}", headers=headers).status_code == 200


def test_responsible_account_controls_access_not_current_holder():
    with TestClient(app) as client:
        admin_headers = auth(client)
        client.post('/api/users', headers=admin_headers, json={
            'name': '内部负责人', 'phone': '13700000011', 'password': 'password1', 'is_admin': 0,
        })
        client.post('/api/users', headers=admin_headers, json={
            'name': '内部持有人', 'phone': '13700000012', 'password': 'password1', 'is_admin': 0,
        })
        robot = client.post('/api/robots', headers=admin_headers, json={
            'asset_code': 'RESP-001', 'model': 'G1', 'owner_name': '内部负责人',
            'holder': '内部持有人', 'status': '在库',
        }).json()
        owner_login = client.post('/api/auth/login', json={'phone':'13700000011','password':'password1'}).json()
        holder_login = client.post('/api/auth/login', json={'phone':'13700000012','password':'password1'}).json()
        owner_headers={'Authorization':f"Bearer {owner_login['access_token']}"}
        holder_headers={'Authorization':f"Bearer {holder_login['access_token']}"}
        assert client.get(f"/api/robots/{robot['id']}", headers=owner_headers).status_code == 200
        assert client.get(f"/api/robots/{robot['id']}", headers=holder_headers).status_code == 404
        edited = client.put(f"/api/robots/{robot['id']}", headers=owner_headers, json={
            'asset_code': 'RESP-001', 'model': 'G1', 'device_branch': 'standard_robot',
            'platform_type': '', 'owner_department': '不得修改', 'owner_name': '内部持有人',
            'holder': '内部持有人', 'location': '负责人更新的位置', 'remark': '负责人可编辑',
        })
        assert edited.status_code == 200, edited.text
        assert edited.json()['location'] == '负责人更新的位置'
        assert edited.json()['owner_name'] == '内部负责人'

        borrowed=client.post(f"/api/robots/{robot['id']}/status", headers=owner_headers, json={
            'status':'借出','borrower':'外部人员','holder':'其他值','location':'外部单位'
        })
        assert borrowed.status_code == 200, borrowed.text
        assert borrowed.json()['holder'] == borrowed.json()['borrower'] == '外部人员'
        returned=client.post(f"/api/robots/{robot['id']}/status", headers=owner_headers, json={
            'status':'在库','holder':'','location':''
        })
        assert returned.status_code == 200, returned.text
        assert returned.json()['holder'] == '内部负责人'
        assert returned.json()['borrower'] == ''


def test_inventory_is_owner_scoped_and_individual_codes_are_global():
    with TestClient(app) as client:
        admin_headers=auth(client)
        client.post('/api/users', headers=admin_headers, json={
            'name':'配件负责人','phone':'13700000021','password':'password1','is_admin':0,
        })
        battery=client.post('/api/inventory/items', headers=admin_headers, json={
            'category':'电池','model':'G1电池','asset_code':'1','initial_quantity':1,
            'owner_name':'配件负责人','holder':'外部保管人','status':'维修中',
        })
        assert battery.status_code == 200, battery.text
        duplicate=client.post('/api/inventory/items', headers=admin_headers, json={
            'category':'遥控器','model':'G1遥控器','asset_code':'1','initial_quantity':1,
            'owner_name':'测试管理员','holder':'测试管理员','status':'在库',
        })
        assert duplicate.status_code == 400
        bulk_battery=client.post('/api/inventory/items', headers=admin_headers, json={
            'category':'电池','model':'G1电池','asset_code':'2','initial_quantity':2,
            'owner_name':'测试管理员','holder':'测试管理员','status':'在库',
        })
        assert bulk_battery.status_code == 400
        login=client.post('/api/auth/login', json={'phone':'13700000021','password':'password1'}).json()
        user_headers={'Authorization':f"Bearer {login['access_token']}"}
        visible=client.get('/api/inventory/items?category=电池',headers=user_headers).json()
        assert [x['id'] for x in visible] == [battery.json()['id']]
        assert client.delete(f"/api/inventory/items/{battery.json()['id']}",headers=user_headers).status_code == 403

        bulk = client.post('/api/inventory/items', headers=admin_headers, json={
            'category':'Pico','model':'Pico 4','initial_quantity':3,
            'owner_name':'配件负责人','holder':'配件负责人','status':'在库',
        }).json()
        edited = client.put(f"/api/inventory/items/{bulk['id']}", headers=user_headers, json={
            'category':'Pico','subtype':'','model':'Pico 4','asset_code':'','status':'在库',
            'unit':'个','location':'普通用户更新的位置','owner_department':'不得修改',
            'owner_name':'测试管理员','holder':'配件负责人','remark':'普通用户可编辑资料',
        })
        assert edited.status_code == 200, edited.text
        assert edited.json()['location'] == '普通用户更新的位置'
        assert edited.json()['owner_name'] == '配件负责人'
        increased = client.post(f"/api/inventory/items/{bulk['id']}/action", headers=user_headers,
            json={'action':'stock_in','quantity':2})
        assert increased.status_code == 200, increased.text
        assert increased.json()['total_quantity'] == 5
        reduced = client.post(f"/api/inventory/items/{bulk['id']}/action", headers=user_headers,
            json={'action':'scrap','quantity':4})
        assert reduced.status_code == 200, reduced.text
        assert reduced.json()['total_quantity'] == 1
        forbidden_zero = client.post(f"/api/inventory/items/{bulk['id']}/action", headers=user_headers,
            json={'action':'scrap','quantity':1})
        assert forbidden_zero.status_code == 403
        assert client.get(f"/api/inventory/items?category=Pico", headers=user_headers).json()[0]['total_quantity'] == 1


def test_holder_search_and_accessory_subtype_detail_filter():
    with TestClient(app) as client:
        headers=auth(client)
        client.post('/api/inventory/items',headers=headers,json={
            'category':'灵巧手','subtype':'夹爪','model':'G1夹爪','initial_quantity':2,
            'owner_name':'测试管理员','holder':'外部保管甲','status':'维修中',
        })
        client.post('/api/inventory/items',headers=headers,json={
            'category':'灵巧手','subtype':'三指灵巧手','model':'Dex3','initial_quantity':1,
            'owner_name':'测试管理员','holder':'测试管理员','status':'在库',
        })
        grippers=client.get('/api/inventory/items?category=夹爪',headers=headers).json()
        assert grippers and all(x['subtype']=='夹爪' for x in grippers)
        filtered=client.get('/api/inventory/items?holder=外部保管甲',headers=headers).json()
        assert filtered and all(x['holder']=='外部保管甲' for x in filtered)
        holder_search=client.get('/api/holders?keyword=外部保管甲',headers=headers).json()
        assert holder_search[0]['name']=='外部保管甲'


def test_individual_accessories_support_unnumbered_batch_stock_in_and_later_status_split():
    with TestClient(app) as client:
        headers = auth(client)
        created = client.post('/api/inventory/items', headers=headers, json={
            'category': '电池', 'model': 'G1批量电池', 'initial_quantity': 5,
            'asset_code': '', 'status': '在库', 'owner_name': '测试管理员',
            'holder': '测试管理员', 'location': '电池柜A区',
        })
        assert created.status_code == 200, created.text
        rows = client.get('/api/inventory/items?category=电池&keyword=G1批量电池', headers=headers).json()
        assert len(rows) == 5
        assert all(row['total_quantity'] == 1 and row['asset_code'] == '' for row in rows)
        assert all(row['owner_name'] == '测试管理员' and row['status'] == '在库' for row in rows)

        first = rows[0]
        repaired = client.put(f"/api/inventory/items/{first['id']}", headers=headers, json={
            'category': '电池', 'subtype': '', 'model': 'G1批量电池', 'asset_code': '',
            'status': '维修中', 'unit': '块', 'location': '维修柜', 'owner_department': '',
            'owner_name': '测试管理员', 'holder': '维修人员', 'remark': '批量入库后单件转维修',
        })
        assert repaired.status_code == 200, repaired.text
        rows = client.get('/api/inventory/items?category=电池&keyword=G1批量电池', headers=headers).json()
        assert sum(row['status'] == '在库' for row in rows) == 4
        assert sum(row['status'] == '维修中' for row in rows) == 1

        numbered_batch = client.post('/api/inventory/items', headers=headers, json={
            'category': '遥控器', 'model': '禁止重复编号批量', 'initial_quantity': 2,
            'asset_code': 'RC-BATCH', 'status': '在库', 'owner_name': '测试管理员',
            'holder': '测试管理员',
        })
        assert numbered_batch.status_code == 400


def test_custom_accessory_category_is_created_and_included_in_stats():
    with TestClient(app) as client:
        headers = auth(client)
        created = client.post('/api/inventory/items', headers=headers, json={
            'category': '定制工具', 'model': '赛事工具包', 'initial_quantity': 3,
            'status': '在库', 'owner_name': '测试管理员', 'holder': '测试管理员',
        })
        assert created.status_code == 200, created.text
        rows = client.get('/api/inventory/items?category=定制工具', headers=headers).json()
        assert len(rows) == 1 and rows[0]['total_quantity'] == 3
        stats = client.get('/api/inventory/stats', headers=headers).json()
        assert stats['categories']['定制工具']['total'] == 3


def test_quantity_accessory_can_be_split_across_stock_borrowed_and_repair_states():
    with TestClient(app) as client:
        headers = auth(client)
        created = client.post('/api/inventory/items', headers=headers, json={
            'category': '拓展坞', 'model': '状态拆分测试', 'initial_quantity': 5,
            'status': '在库', 'owner_name': '测试管理员', 'holder': '测试管理员',
        })
        assert created.status_code == 200, created.text
        source_id = created.json()['id']
        borrowed = client.post(f'/api/inventory/items/{source_id}/action', headers=headers, json={
            'action': 'borrow', 'quantity': 2, 'borrower': '赛事一队',
        })
        assert borrowed.status_code == 200, borrowed.text
        assert borrowed.json()['status'] == '借出' and borrowed.json()['total_quantity'] == 2

        rows = client.get('/api/inventory/items?keyword=状态拆分测试', headers=headers).json()
        stock = next(row for row in rows if row['status'] == '在库')
        repaired = client.post(f"/api/inventory/items/{stock['id']}/action", headers=headers, json={
            'action': 'repair', 'quantity': 1,
        })
        assert repaired.status_code == 200, repaired.text
        assert repaired.json()['status'] == '维修中'

        returned = client.post(f"/api/inventory/items/{borrowed.json()['id']}/action", headers=headers, json={
            'action': 'return', 'quantity': 1,
        })
        assert returned.status_code == 200, returned.text
        rows = client.get('/api/inventory/items?keyword=状态拆分测试', headers=headers).json()
        totals = {status: sum(row['total_quantity'] for row in rows if row['status'] == status)
                  for status in ('在库', '借出', '维修中')}
        assert totals == {'在库': 3, '借出': 1, '维修中': 1}

        repair_row = next(row for row in rows if row['status'] == '维修中')
        restored = client.post(f"/api/inventory/items/{repair_row['id']}/action", headers=headers, json={
            'action': 'restore', 'quantity': 1,
        })
        assert restored.status_code == 200, restored.text
        rows = client.get('/api/inventory/items?keyword=状态拆分测试', headers=headers).json()
        assert sum(row['total_quantity'] for row in rows if row['status'] == '在库') == 4
        assert sum(row['total_quantity'] for row in rows if row['status'] == '借出') == 1


def test_device_number_finds_complete_operation_history_and_filtered_export():
    with TestClient(app) as client:
        headers = auth(client)
        robot = client.post('/api/robots', headers=headers, json={
            'asset_code': 'TRACE-OLD-001', 'model': 'G1', 'status': '在库',
            'owner_name': '测试管理员', 'holder': '测试管理员',
        })
        assert robot.status_code == 200, robot.text
        robot_id = robot.json()['id']
        unrelated = client.post('/api/robots', headers=headers, json={
            'asset_code': 'TRACE-OTHER-999', 'model': 'R1', 'status': '在库',
            'owner_name': '测试管理员', 'holder': '测试管理员',
        })
        assert unrelated.status_code == 200, unrelated.text

        borrowed = client.post(f'/api/robots/{robot_id}/status', headers=headers, json={
            'status': '借出', 'location': '赛事现场', 'borrower': '赛事组', 'note': '领用',
        })
        assert borrowed.status_code == 200, borrowed.text
        returned = client.post(f'/api/robots/{robot_id}/status', headers=headers, json={
            'status': '在库', 'holder': '测试管理员', 'note': '归还验收',
        })
        assert returned.status_code == 200, returned.text
        renamed = client.put(f'/api/robots/{robot_id}', headers=headers, json={
            'asset_code': 'TRACE-NEW-001', 'model': 'G1', 'owner_department': '',
            'owner_name': '测试管理员', 'holder': '测试管理员', 'location': '', 'remark': '',
        })
        assert renamed.status_code == 200, renamed.text

        current = client.get('/api/logs?asset_code=TRACE-NEW-001&page_size=200', headers=headers)
        assert current.status_code == 200, current.text
        current_rows = current.json()['items']
        assert len(current_rows) == 4
        assert {row['robot_id'] for row in current_rows} == {robot_id}
        assert {row['action'] for row in current_rows} == {'入库', '借出', '归还', '资料编辑'}
        assert any('设备编号：TRACE-OLD-001 → TRACE-NEW-001' in (row['note'] or '') for row in current_rows)

        dedicated = client.get('/api/logs/device/TRACE-NEW-001?page_size=200', headers=headers)
        assert dedicated.status_code == 200, dedicated.text
        assert len(dedicated.json()['items']) == 4
        old_dedicated = client.get('/api/logs/device/TRACE-OLD-001?page_size=200', headers=headers)
        assert old_dedicated.status_code == 200, old_dedicated.text
        assert len(old_dedicated.json()['items']) == 4
        assert client.get('/api/logs/device/NEW-001', headers=headers).status_code == 404

        partial = client.get('/api/logs?asset_code=NEW-001&page_size=200', headers=headers).json()['items']
        assert len(partial) == 4
        old_rows = client.get('/api/logs?asset_code=TRACE-OLD-001&page_size=200', headers=headers).json()['items']
        assert len(old_rows) == 3
        assert all(row['asset_code'] == 'TRACE-OLD-001' for row in old_rows)

        exported = client.get('/api/export/logs.csv?asset_code=TRACE-NEW-001', headers=headers)
        assert exported.status_code == 200
        csv_text = exported.content.decode('utf-8-sig')
        assert 'TRACE-NEW-001' in csv_text
        assert 'TRACE-OTHER-999' not in csv_text


def test_existing_operation_logs_are_backfilled_without_data_loss(tmp_path, monkeypatch):
    from sqlalchemy import create_engine
    from app import database

    migration_engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    with migration_engine.begin() as conn:
        conn.exec_driver_sql("CREATE TABLE robots (id INTEGER PRIMARY KEY, asset_code VARCHAR(64) NOT NULL)")
        conn.exec_driver_sql(
            "CREATE TABLE operation_logs (id INTEGER PRIMARY KEY, robot_id INTEGER NOT NULL, "
            "operator VARCHAR(64), action VARCHAR(32), note TEXT)"
        )
        conn.exec_driver_sql("INSERT INTO robots (id, asset_code) VALUES (7, 'LEGACY-007')")
        conn.exec_driver_sql(
            "INSERT INTO operation_logs (id, robot_id, operator, action, note) "
            "VALUES (11, 7, '旧操作人', '入库', '旧日志不得丢失')"
        )
    monkeypatch.setattr(database, 'engine', migration_engine)
    database._migrate_existing_database()
    with migration_engine.connect() as conn:
        row = conn.exec_driver_sql(
            "SELECT id, robot_id, asset_code, operator, action, note FROM operation_logs WHERE id = 11"
        ).mappings().one()
    assert dict(row) == {
        'id': 11, 'robot_id': 7, 'asset_code': 'LEGACY-007', 'operator': '旧操作人',
        'action': '入库', 'note': '旧日志不得丢失',
    }


def test_device_history_is_available_to_owner_and_current_holder_only():
    with TestClient(app) as client:
        admin_headers = auth(client)
        for name, phone in [('追溯负责人', '13700000031'), ('当前持有人', '13700000032'), ('无关人员', '13700000033')]:
            response = client.post('/api/users', headers=admin_headers, json={
                'name': name, 'phone': phone, 'password': 'password1', 'is_admin': 0,
            })
            assert response.status_code == 200, response.text
        robot = client.post('/api/robots', headers=admin_headers, json={
            'asset_code': 'HISTORY-ACCESS-001', 'model': 'G1', 'status': '在库',
            'owner_name': '追溯负责人', 'holder': '当前持有人',
        })
        assert robot.status_code == 200, robot.text

        def user_headers(phone):
            login = client.post('/api/auth/login', json={'phone': phone, 'password': 'password1'})
            return {'Authorization': f"Bearer {login.json()['access_token']}"}

        owner_result = client.get('/api/logs/device/history-access-001', headers=user_headers('13700000031'))
        holder_result = client.get('/api/logs/device/HISTORY-ACCESS-001', headers=user_headers('13700000032'))
        denied_result = client.get('/api/logs/device/HISTORY-ACCESS-001', headers=user_headers('13700000033'))
        assert owner_result.status_code == 200 and owner_result.json()['total'] == 1
        assert holder_result.status_code == 200 and holder_result.json()['total'] == 1
        assert denied_result.status_code == 404
