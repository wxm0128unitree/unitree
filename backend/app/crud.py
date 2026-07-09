"""
业务逻辑层
封装设备状态变更、操作日志记录等核心业务
"""
from sqlalchemy.orm import Session
from app import models, schemas
from fastapi import HTTPException
from typing import List, Optional


def get_robot_by_code(db: Session, asset_code: str) -> Optional[models.Robot]:
    return db.query(models.Robot).filter(models.Robot.asset_code == asset_code).first()


def list_robots(
    db: Session,
    model: Optional[str] = None,
    status: Optional[str] = None,
    keyword: Optional[str] = None,
    holder: Optional[str] = None,
) -> List[models.Robot]:
    """列出设备，支持筛选"""
    q = db.query(models.Robot)
    if model and model != "全部":
        q = q.filter(models.Robot.model == model)
    if status and status != "全部":
        q = q.filter(models.Robot.status == status)
    if holder and holder != "全部":
        q = q.filter(models.Robot.holder == holder)
    if keyword:
        like = f"%{keyword}%"
        q = q.filter(
            (models.Robot.asset_code.like(like)) |
            (models.Robot.location.like(like)) |
            (models.Robot.holder.like(like))
        )
    return q.order_by(models.Robot.model, models.Robot.asset_code).all()


def create_robot(db: Session, payload: schemas.RobotCreate, operator: str = "admin") -> models.Robot:
    """新增设备"""
    if get_robot_by_code(db, payload.asset_code):
        raise HTTPException(status_code=400, detail=f"资产编号 {payload.asset_code} 已存在")
    if not payload.model or not payload.model.strip():
        raise HTTPException(status_code=400, detail="型号不能为空")
    if len(payload.model) > 32:
        raise HTTPException(status_code=400, detail="型号长度不能超过 32 个字符")
    if payload.status and len(payload.status) > 32:
        raise HTTPException(status_code=400, detail="状态长度不能超过 32 个字符")
    robot = models.Robot(**payload.model_dump())
    db.add(robot)
    db.commit()
    db.refresh(robot)
    # 入库操作也写一条日志（方便追溯）
    db.add(models.OperationLog(
        robot_id=robot.id,
        operator=operator,
        action="入库",
        before_status="",
        after_status=robot.status,
        before_location="",
        after_location=robot.location or "",
        note="\u8bbe\u5907\u521b\u5efa",
    ))
    db.commit()
    return robot


def update_robot_status(
    db: Session, robot_id: int, payload: schemas.RobotUpdate, operator: str = "admin",
) -> models.Robot:
    """核心动作：修改设备状态（借出/归还/维修/转移）"""
    robot = db.query(models.Robot).filter(models.Robot.id == robot_id).first()
    if not robot:
        raise HTTPException(status_code=404, detail="设备不存在")

    if not payload.status or not payload.status.strip():
        raise HTTPException(status_code=400, detail="状态不能为空")
    if len(payload.status) > 32:
        raise HTTPException(status_code=400, detail="状态长度不能超过 32 个字符")

    # 记录变更前状态
    before = {"status": robot.status, "location": robot.location}

    # 更新状态
    robot.status = payload.status
    robot.location = payload.location if payload.status != "在库" else ""

    # 写入日志
    action = _infer_action(before["status"], payload.status)
    log = models.OperationLog(
        robot_id=robot.id,
        operator=operator,
        action=action,
        before_status=before["status"],
        after_status=robot.status,
        before_location=before["location"],
        after_location=robot.location,
        note=payload.note or "",
    )
    db.add(log)
    db.commit()
    db.refresh(robot)
    return robot


def _infer_action(before: str, after: str) -> str:
    """根据状态前后变化推断操作类型"""
    if before == "在库" and after == "借出":
        return "借出"
    if before == "借出" and after == "在库":
        return "归还"
    if after == "维修中":
        return "送修"
    if before == "维修中" and after == "在库":
        return "修好入库"
    if before == "借出" and after == "借出":
        return "转移"
    if before == "在库" and after == "在库":
        return "信息更新"
    return "状态变更"


def get_stats(db: Session) -> dict:
    """首页统计：总数量、各状态数量"""
    total = db.query(models.Robot).count()
    in_stock = db.query(models.Robot).filter(models.Robot.status == "在库").count()
    borrowed = db.query(models.Robot).filter(models.Robot.status == "借出").count()
    in_repair = db.query(models.Robot).filter(models.Robot.status == "维修中").count()
    return {"total": total, "in_stock": in_stock, "borrowed": borrowed, "in_repair": in_repair}


def list_logs(db: Session, robot_id: Optional[int] = None, limit: int = 200):
    """查询操作日志"""
    q = db.query(models.OperationLog)
    if robot_id:
        q = q.filter(models.OperationLog.robot_id == robot_id)
    return q.order_by(models.OperationLog.created_at.desc()).limit(limit).all()


def delete_robot(db: Session, robot_id: int, operator: str = "admin"):
    robot = db.query(models.Robot).filter(models.Robot.id == robot_id).first()
    if not robot:
        raise HTTPException(status_code=404, detail="设备不存在")
    # 级联删除会自动清理 logs（外键 cascade），但追加一条删除日志（用专门的保留表会更稳，
    # 此版本先不放进保留表，简化）
    db.delete(robot)
    db.commit()
    return {"ok": True, "operator": operator}