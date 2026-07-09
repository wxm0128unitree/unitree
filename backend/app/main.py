"""
FastAPI 路由定义
严格遵循开发手册：极简、去流程化、以状态为中心
"""
from fastapi import FastAPI, Depends, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Optional, List
import os

from app.database import get_db, init_db, SessionLocal, single_process_bootstrap
from app import schemas, crud
from app import models
from app.auth import (
    hash_password, verify_password, create_access_token,
    get_current_user, get_optional_user,
)

app = FastAPI(
    title="\u5b87\u6811\u673a\u5668\u4eba\u8bbe\u5907\u7ba1\u7406\u7cfb\u7edf",
    description="\u53bb\u6d41\u7a0b\u5316\u3001\u4ee5\u72b6\u6001\u4e3a\u4e2d\u5fc3\u7684\u8bbe\u5907\u51fa\u5165\u5e93\u7ba1\u7406",
    version="2.1.0",
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
        db.commit()
        print(f"[INFO] Bootstrap admin created: {admin.name} / {admin.phone}")
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
):
    return crud.list_robots(db, model=model, status=status, keyword=keyword, holder=holder)


@app.post("/api/robots", response_model=schemas.RobotOut, tags=["\u8bbe\u5907"])
def api_create_robot(
    payload: schemas.RobotCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return crud.create_robot(db, payload, operator=current_user.name)


@app.get("/api/robots/{robot_id}", response_model=schemas.RobotOut, tags=["\u8bbe\u5907"])
def api_get_robot(robot_id: int, db: Session = Depends(get_db)):
    r = db.query(models.Robot).filter(models.Robot.id == robot_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="\u8bbe\u5907\u4e0d\u5b58\u5728")
    return r


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
    current_user: models.User = Depends(get_current_user),
):
    return crud.delete_robot(db, robot_id, operator=current_user.name)


# ========== 统计 & 日志 ==========

@app.get("/api/stats", response_model=schemas.RobotStats, tags=["\u7edf\u8ba1"])
def api_stats(db: Session = Depends(get_db)):
    return crud.get_stats(db)


@app.get("/api/logs", response_model=List[schemas.OperationLogOut], tags=["\u65e5\u5fd7"])
def api_logs(
    robot_id: Optional[int] = Query(None),
    limit: int = Query(200, le=1000),
    db: Session = Depends(get_db),
):
    return crud.list_logs(db, robot_id=robot_id, limit=limit)


# ========== 用户管理（管理员） ==========

@app.get("/api/users", response_model=List[schemas.UserOut], tags=["\u7528\u6237"])
def api_list_users(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """列出所有用户"""
    return db.query(models.User).order_by(models.User.created_at).all()


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
