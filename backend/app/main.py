"""
FastAPI 路由定义
严格遵循开发手册：极简、去流程化、以状态为中心
"""
from fastapi import FastAPI, Depends, Query, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional, List
import os
import csv
import io
from datetime import datetime

from app.database import get_db, init_db, SessionLocal, single_process_bootstrap
from app import schemas, crud
from app import models
from app import backup as backup_mod
from app.auth import (
    hash_password, verify_password, create_access_token,
    get_current_user, get_current_admin, get_optional_user,
)

app = FastAPI(
    title="\u5b87\u6811\u673a\u5668\u4eba\u8bbe\u5907\u7ba1\u7406\u7cfb\u7edf",
    description="\u53bb\u6d41\u7a0b\u5316\u3001\u4ee5\u72b6\u6001\u4e3a\u4e2d\u5fc3\u7684\u8bbe\u5907\u51fa\u5165\u5e93\u7ba1\u7406",
    version="3.0.0",
)

# CORS：默认允许所有（部署后可设 CORS_ORIGINS 收紧）
ALLOWED_ORIGINS = os.environ.get("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS if ALLOWED_ORIGINS != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态前端路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# 可通过 FRONTEND_DIST 环境变量强制指定前端目录（容器场景）
FRONTEND_DIST = os.environ.get(
    "FRONTEND_DIST",
    os.path.join(BASE_DIR, "frontend", "dist")
)
FRONTEND_ASSETS = os.path.join(FRONTEND_DIST, "assets")
FRONTEND_INDEX = os.path.join(FRONTEND_DIST, "index.html")

_static_mounted = False


def _bootstrap_admin():
    """数据库为空时自动创建默认管理员（可通过环境变量自定义）"""
    db = SessionLocal()
    try:
        if db.query(models.User).count() > 0:
            return
        admin = models.User(
            name=os.environ.get("ADMIN_NAME", "\u738b\u66e6\u660e"),  # 王曦明
            phone=os.environ.get("ADMIN_PHONE", "13083401281"),
            password_hash=hash_password(os.environ.get("ADMIN_PASSWORD", "111111")),
            is_admin=1,
        )
        db.add(admin)
        try:
            db.commit()
            print(f"[INFO] Bootstrap admin created: {admin.name} / {admin.phone}")
        except IntegrityError:
            db.rollback()
            print("[INFO] Bootstrap admin was created by another worker")
    finally:
        db.close()


@app.on_event("startup")
def on_startup():
    global _static_mounted
    init_db()
    # 多 worker 下，只有抢到 SQLite 写锁的那个进程执行 bootstrap
    if single_process_bootstrap():
        _bootstrap_admin()
    else:
        print("[INFO] Bootstrap not needed (users already exist or other worker holds lock)")
    if os.path.exists(FRONTEND_ASSETS):
        app.mount("/assets", StaticFiles(directory=FRONTEND_ASSETS), name="assets")
    if os.path.exists(FRONTEND_INDEX):
        _static_mounted = True
        print(f"[INFO] Frontend mounted from {FRONTEND_DIST}")


# ========== 健康检查（供负载均衡 / 监控 / Docker 使用） ==========

@app.get("/api/health", tags=["\u7cfb\u7edf"])
def api_health():
    return {"status": "ok", "version": app.version}


@app.get("/api/bootstrap", tags=["\u7cfb\u7edf"])
def api_bootstrap():
    """前端启动时调用，告知当前是否已经初始化"""
    db = SessionLocal()
    try:
        return {
            "initialized": db.query(models.User).count() > 0,
            "allow_register": os.environ.get("ALLOW_REGISTER", "1") == "1",
        }
    finally:
        db.close()


# ========== 鉴权 API ==========


@app.post("/api/admin/init", tags=["\u7cfb\u7edf"])
def api_admin_init(
    db: Session = Depends(get_db), x_init_token: Optional[str] = Header(None),
):
    """\u624b\u52a8\u521d\u59cb\u5316\u7ba1\u7406\u5458\u8d26\u53f7\uff08\u4ec5\u5f53\u6570\u636e\u5e93\u4e3a\u7a7a\u65f6\u751f\u6548\uff09"""
    expected = os.environ.get("ADMIN_INIT_TOKEN")
    if not expected or x_init_token != expected:
        raise HTTPException(status_code=404, detail="not found")
    existing = db.query(models.User).first()
    if existing:
        return {"ok": False, "message": "\u6570\u636e\u5e93\u5df2\u6709\u7528\u6237\uff0c\u8df3\u8fc7\u521d\u59cb\u5316"}
    user = models.User(
        name=os.environ.get("ADMIN_NAME", "\u738b\u66e6\u660e"),
        phone=os.environ.get("ADMIN_PHONE", "13083401281"),
        password_hash=hash_password(os.environ.get("ADMIN_PASSWORD", "111111")),
        is_admin=1,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"ok": True, "message": f"\u7ba1\u7406\u5458\u521b\u5efa\u6210\u529f: {user.name} / {user.phone}"}



@app.post("/api/auth/register", response_model=schemas.Token, tags=["\u8ba4\u8bc1"])
def api_register(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    """注册新用户；可通过环境变量 ALLOW_REGISTER=0 关闭该入口"""
    if os.environ.get("ALLOW_REGISTER", "1") != "1":
        raise HTTPException(status_code=403, detail="\u6ce8\u518c\u5df2\u5173\u95ed\uff0c\u8bf7\u8054\u7cfb\u7ba1\u7406\u5458")
    existing = db.query(models.User).filter(models.User.phone == payload.phone).first()
    if existing:
        raise HTTPException(status_code=400, detail="\u8be5\u624b\u673a\u53f7\u5df2\u6ce8\u518c")
    user = models.User(
        name=payload.name,
        phone=payload.phone,
        password_hash=hash_password(payload.password),
        is_admin=0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(user)
    return schemas.Token(
        access_token=token,
        user=schemas.UserOut.model_validate(user),
    )


@app.post("/api/auth/login", response_model=schemas.Token, tags=["\u8ba4\u8bc1"])
def api_login(payload: schemas.UserLogin, db: Session = Depends(get_db)):
    """登录，返回 JWT"""
    user = db.query(models.User).filter(models.User.phone == payload.phone).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="\u624b\u673a\u53f7\u6216\u5bc6\u7801\u4e0d\u6b63\u786e")
    if user.is_active != 1:
        raise HTTPException(status_code=403, detail="账号已停用，请联系管理员")
    user.last_login_at = models.utc_now()
    db.commit()
    db.refresh(user)
    token = create_access_token(user)
    return schemas.Token(
        access_token=token,
        user=schemas.UserOut.model_validate(user),
    )


@app.get("/api/auth/me", response_model=schemas.UserOut, tags=["\u8ba4\u8bc1"])
def api_me(current_user: models.User = Depends(get_current_user)):
    """获取当前登录用户信息"""
    return current_user


# ========== 设备 API ==========

@app.get("/api/robots", response_model=List[schemas.RobotOut], tags=["\u8bbe\u5907"])
def api_list_robots(
    model: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    holder: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    include_archived: bool = Query(False),
):
    if include_archived and current_user.is_admin != 1:
        raise HTTPException(status_code=403, detail="只有管理员可以查看归档设备")
    return crud.list_robots(db, model=model, status=status, keyword=keyword, holder=holder,
                            include_archived=include_archived)


@app.post("/api/robots", response_model=schemas.RobotOut, tags=["\u8bbe\u5907"])
def api_create_robot(
    payload: schemas.RobotCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return crud.create_robot(db, payload, operator=current_user.name)


@app.get("/api/robots/{robot_id}", response_model=schemas.RobotOut, tags=["\u8bbe\u5907"])
def api_get_robot(
    robot_id: int, db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    r = db.query(models.Robot).filter(models.Robot.id == robot_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="\u8bbe\u5907\u4e0d\u5b58\u5728")
    if r.is_archived and current_user.is_admin != 1:
        raise HTTPException(status_code=404, detail="设备不存在")
    return r


@app.put("/api/robots/{robot_id}", response_model=schemas.RobotOut, tags=["设备"])
def api_edit_robot(
    robot_id: int, payload: schemas.RobotEdit, db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return crud.edit_robot(db, robot_id, payload, current_user.name)


@app.post("/api/robots/{robot_id}/status", response_model=schemas.RobotOut, tags=["\u8bbe\u5907"])
def api_update_status(
    robot_id: int,
    payload: schemas.RobotUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return crud.update_robot_status(
        db, robot_id, payload, operator=current_user.name,
    )


@app.delete("/api/robots/{robot_id}", tags=["\u8bbe\u5907"])
def api_delete_robot(
    robot_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin),
):
    """归档设备（仅管理员），保留全部日志并可恢复。"""
    return crud.delete_robot(db, robot_id, operator=current_user.name)


@app.post("/api/robots/{robot_id}/restore", response_model=schemas.RobotOut, tags=["设备"])
def api_restore_robot(
    robot_id: int, db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin),
):
    return crud.restore_robot(db, robot_id, current_user.name)


@app.post("/api/robots/{robot_id}/migrate", response_model=schemas.RobotOut, tags=["设备"])
def api_migrate_robot(robot_id: int, payload: schemas.RobotMigration, db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin)):
    return crud.migrate_robot(db, robot_id, payload, current_user.name)


@app.post("/api/robots/{robot_id}/undo-migration", response_model=schemas.RobotOut, tags=["设备"])
def api_undo_robot_migration(robot_id: int, db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin)):
    return crud.undo_robot_migration(db, robot_id, current_user.name)


@app.post("/api/robots/{robot_id}/inventory", response_model=schemas.RobotOut, tags=["设备"])
def api_inventory_robot(
    robot_id: int, payload: schemas.InventoryUpdate, db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return crud.inventory_robot(db, robot_id, payload, current_user.name)


# ========== 统计 & 日志 ==========

@app.get("/api/stats", response_model=schemas.RobotStats, tags=["\u7edf\u8ba1"])
def api_stats(
    db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user),
):
    return crud.get_stats(db)


@app.get("/api/logs", response_model=schemas.LogPage, tags=["\u65e5\u5fd7"])
def api_logs(
    robot_id: Optional[int] = Query(None),
    operator: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    keyword: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    items, total = crud.list_logs(db, robot_id=robot_id, operator=operator, action=action,
        date_from=date_from, date_to=date_to, keyword=keyword, page=page, page_size=page_size)
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@app.get("/api/export/robots.csv", tags=["导出"])
def api_export_robots(
    include_archived: bool = Query(False), db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if include_archived and current_user.is_admin != 1:
        raise HTTPException(status_code=403, detail="只有管理员可以导出归档设备")
    robots = crud.list_robots(db, include_archived=include_archived)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["资产编号", "型号", "状态", "归属部门", "资产负责人", "当前借用人", "当前位置",
                     "借用用途", "借出时间", "预计归还", "维修描述", "备注", "是否归档", "最近盘点时间", "盘点人"])
    for r in robots:
        writer.writerow([r.asset_code, r.model, r.status, r.owner_department, r.owner_name, r.borrower,
            r.location, r.purpose, r.borrowed_at or "", r.expected_return_at or "", r.repair_description,
            r.remark, "是" if r.is_archived else "否", r.last_inventory_at or "", r.last_inventory_by])
    data = "\ufeff" + output.getvalue()
    return StreamingResponse(iter([data.encode("utf-8")]), media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=robots.csv"})


@app.get("/api/export/logs.csv", tags=["导出"])
def api_export_logs(
    db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user),
):
    items, _ = crud.list_logs(db, page=1, page_size=10000)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["时间", "设备ID", "操作人", "操作", "原状态", "新状态", "原位置", "新位置", "备注"])
    for row in items:
        writer.writerow([row.created_at, row.robot_id, row.operator, row.action, row.before_status,
            row.after_status, row.before_location, row.after_location, row.note])
    data = "\ufeff" + output.getvalue()
    return StreamingResponse(iter([data.encode("utf-8")]), media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=operation_logs.csv"})


# ========== 数量库存 ============

@app.get("/api/inventory/items", response_model=List[schemas.InventoryItemOut], tags=["数量库存"])
def api_inventory_items(category: Optional[str] = Query(None), db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)):
    return crud.list_inventory_items(db, category)


@app.post("/api/inventory/items", response_model=schemas.InventoryItemOut, tags=["数量库存"])
def api_create_inventory_item(payload: schemas.InventoryItemCreate, db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)):
    return crud.create_inventory_item(db, payload, current_user.name)


@app.post("/api/inventory/items/{item_id}/action", response_model=schemas.InventoryItemOut, tags=["数量库存"])
def api_inventory_action(item_id: int, payload: schemas.InventoryAction, db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)):
    return crud.inventory_action(db, item_id, payload, current_user.name)


@app.get("/api/inventory/stats", tags=["数量库存"])
def api_inventory_stats(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return crud.inventory_stats(db)


@app.get("/api/inventory/transactions", response_model=List[schemas.InventoryTransactionOut], tags=["数量库存"])
def api_inventory_transactions(limit: int = Query(200, ge=1, le=1000), db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)):
    return db.query(models.InventoryTransaction).order_by(models.InventoryTransaction.created_at.desc()).limit(limit).all()


# ========== 用户管理（管理员） ==========

@app.put("/api/users/me", response_model=schemas.UserOut, tags=["用户"])
def api_update_me(
    payload: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """修改当前登录用户的信息（名字或密码）"""
    if payload.name is not None:
        current_user.name = payload.name.strip()
    if payload.password is not None:
        current_user.password_hash = hash_password(payload.password)
    db.commit()
    db.refresh(current_user)
    return schemas.UserOut.model_validate(current_user)


@app.get("/api/users", response_model=List[schemas.UserOut], tags=["用户"])
def api_list_users(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin),
):
    """列出所有用户（仅管理员）"""
    return db.query(models.User).order_by(models.User.created_at).all()


@app.post("/api/users", response_model=schemas.UserOut, tags=["用户"])
def api_create_user(
    payload: schemas.AdminUserCreate, db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin),
):
    if db.query(models.User).filter(models.User.phone == payload.phone).first():
        raise HTTPException(status_code=400, detail="该手机号已注册")
    user = models.User(name=payload.name, phone=payload.phone,
        password_hash=hash_password(payload.password), is_admin=payload.is_admin, is_active=1)
    db.add(user); db.commit(); db.refresh(user)
    return user


@app.put("/api/users/{user_id}", response_model=schemas.UserOut, tags=["用户"])
def api_admin_update_user(
    user_id: int, payload: schemas.AdminUserUpdate, db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.id == current_user.id and payload.is_active == 0:
        raise HTTPException(status_code=400, detail="不能停用当前登录账号")
    was_admin = user.is_admin == 1 and user.is_active == 1
    if was_admin and payload.is_admin == 0:
        admins = db.query(models.User).filter(models.User.is_admin == 1, models.User.is_active == 1).count()
        if admins <= 1:
            raise HTTPException(status_code=400, detail="必须至少保留一名启用的管理员")
    if was_admin and payload.is_active == 0:
        admins = db.query(models.User).filter(models.User.is_admin == 1, models.User.is_active == 1).count()
        if admins <= 1:
            raise HTTPException(status_code=400, detail="必须至少保留一名启用的管理员")
    if payload.name is not None: user.name = payload.name.strip()
    if payload.password is not None: user.password_hash = hash_password(payload.password)
    if payload.is_admin is not None: user.is_admin = payload.is_admin
    if payload.is_active is not None: user.is_active = payload.is_active
    db.commit(); db.refresh(user)
    return user



# ========== 备份 API（仅管理员） ==========

@app.post("/api/backup/run", tags=["系统"])
def api_backup_run(
    current_user: models.User = Depends(get_current_admin),
):
    """手动触发一次备份。
    返回备份文件路径和大小。"""
    try:
        target = backup_mod.manual_backup()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"备份失败: {e}")
    return {"ok": True, "path": str(target), "size": target.stat().st_size}


@app.get("/api/backup/list", tags=["系统"])
def api_backup_list(
    current_user: models.User = Depends(get_current_admin),
):
    """列出所有备份文件（按 daily/weekly/manual 分组），仅管理员。"""
    root = backup_mod._backup_root()
    out = {"daily": [], "weekly": [], "manual": []}
    for kind in out.keys():
        d = root / kind
        if not d.exists():
            continue
        for f in sorted(d.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            if f.is_file():
                st = f.stat()
                out[kind].append({
                    "name": f.name,
                    "size": st.st_size,
                    "mtime": int(st.st_mtime),
                })
    return out


@app.post("/api/backup/restore", tags=["系统"])
def api_backup_restore(
    kind: str = Query(...), name: str = Query(...), confirm: str = Query(...),
    current_user: models.User = Depends(get_current_admin),
):
    if confirm != "RESTORE":
        raise HTTPException(status_code=400, detail="恢复确认文字不正确")
    try:
        safety = backup_mod.restore_backup(kind, name)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"ok": True, "safety_backup": safety.name, "message": "恢复完成，请重新登录并核对数据"}


@app.get("/api/backup/download", tags=["系统"])
def api_backup_download(
    kind: str = Query(...), name: str = Query(...),
    current_user: models.User = Depends(get_current_admin),
):
    try:
        target = backup_mod.resolve_backup(kind, name)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return FileResponse(target, filename=target.name, media_type="application/octet-stream")


# ========== 静态前端（SPA fallback） ==========

def _frontend_ready():
    return _static_mounted and os.path.exists(FRONTEND_INDEX)


@app.get("/", include_in_schema=False)
def serve_index():
    if _frontend_ready():
        return FileResponse(FRONTEND_INDEX)
    return {
        "error": "frontend_not_built",
        "message": "\u524d\u7aef\u672a\u6784\u5efa",
        "api_docs": "/docs",
    }


@app.get("/{path:path}", include_in_schema=False)
def serve_spa(path: str):
    if path.startswith(("api/", "docs", "openapi", "redoc")):
        raise HTTPException(status_code=404, detail="not found")
    if _frontend_ready():
        full = os.path.join(FRONTEND_DIST, path)
        if os.path.exists(full) and os.path.isfile(full):
            return FileResponse(full)
        return FileResponse(FRONTEND_INDEX)
    return {"error": "frontend_not_built", "path": path}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
