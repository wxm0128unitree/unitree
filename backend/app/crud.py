"""
业务逻辑层
封装设备状态变更、操作日志记录等核心业务
"""
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app import models, schemas
from fastapi import HTTPException
from typing import List, Optional
from datetime import datetime


def get_robot_by_code(db: Session, asset_code: str) -> Optional[models.Robot]:
    return db.query(models.Robot).filter(models.Robot.asset_code == asset_code).first()


def list_robots(
    db: Session,
    model: Optional[str] = None,
    status: Optional[str] = None,
    keyword: Optional[str] = None,
    holder: Optional[str] = None,
    include_archived: bool = False,
) -> List[models.Robot]:
    """列出设备，支持筛选"""
    q = db.query(models.Robot)
    if not include_archived:
        q = q.filter(models.Robot.is_archived == 0)
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
            (models.Robot.holder.like(like)) |
            (models.Robot.owner_name.like(like)) |
            (models.Robot.owner_department.like(like)) |
            (models.Robot.borrower.like(like))
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
    robot = db.query(models.Robot).filter(models.Robot.id == robot_id, models.Robot.is_archived == 0).first()
    if not robot:
        raise HTTPException(status_code=404, detail="设备不存在")

    if not payload.status or not payload.status.strip():
        raise HTTPException(status_code=400, detail="状态不能为空")
    if len(payload.status) > 32:
        raise HTTPException(status_code=400, detail="状态长度不能超过 32 个字符")

    # 记录变更前状态
    before = {"status": robot.status, "location": robot.location}

    # 更新状态
    robot.status = payload.status.strip()
    robot.location = payload.location.strip() if payload.status != "在库" else ""
    robot.borrower = payload.borrower.strip() if payload.status == "借出" else ""
    robot.purpose = payload.purpose.strip() if payload.status == "借出" else ""
    robot.expected_return_at = payload.expected_return_at if payload.status == "借出" else None
    robot.repair_description = payload.repair_description.strip() if payload.status == "维修中" else ""
    if payload.status == "借出" and before["status"] != "借出":
        robot.borrowed_at = datetime.now()
    elif payload.status != "借出":
        robot.borrowed_at = None

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
    active = models.Robot.is_archived == 0
    total = db.query(models.Robot).filter(active).count()
    in_stock = db.query(models.Robot).filter(active, models.Robot.status == "在库").count()
    borrowed = db.query(models.Robot).filter(active, models.Robot.status == "借出").count()
    in_repair = db.query(models.Robot).filter(active, models.Robot.status == "维修中").count()
    return {"total": total, "in_stock": in_stock, "borrowed": borrowed, "in_repair": in_repair}


def list_logs(
    db: Session, robot_id: Optional[int] = None, operator: Optional[str] = None,
    action: Optional[str] = None, date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None, keyword: Optional[str] = None,
    page: int = 1, page_size: int = 50,
):
    """查询操作日志并返回分页结果。"""
    q = db.query(models.OperationLog)
    if robot_id:
        q = q.filter(models.OperationLog.robot_id == robot_id)
    if operator:
        q = q.filter(models.OperationLog.operator == operator)
    if action:
        q = q.filter(models.OperationLog.action == action)
    if date_from:
        q = q.filter(models.OperationLog.created_at >= date_from)
    if date_to:
        q = q.filter(models.OperationLog.created_at <= date_to)
    if keyword:
        like = f"%{keyword}%"
        q = q.filter(or_(models.OperationLog.note.like(like), models.OperationLog.after_location.like(like)))
    total = q.count()
    items = q.order_by(models.OperationLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return items, total


def delete_robot(db: Session, robot_id: int, operator: str = "admin"):
    robot = db.query(models.Robot).filter(models.Robot.id == robot_id, models.Robot.is_archived == 0).first()
    if not robot:
        raise HTTPException(status_code=404, detail="设备不存在")
    robot.is_archived = 1
    robot.archived_at = datetime.now()
    db.add(models.OperationLog(robot_id=robot.id, operator=operator, action="归档", before_status=robot.status,
        after_status=robot.status, before_location=robot.location, after_location=robot.location, note="设备已归档"))
    db.commit()
    return {"ok": True, "operator": operator}


def restore_robot(db: Session, robot_id: int, operator: str = "admin"):
    robot = db.query(models.Robot).filter(models.Robot.id == robot_id, models.Robot.is_archived == 1).first()
    if not robot:
        raise HTTPException(status_code=404, detail="归档设备不存在")
    robot.is_archived = 0
    robot.archived_at = None
    db.add(models.OperationLog(robot_id=robot.id, operator=operator, action="恢复", before_status=robot.status,
        after_status=robot.status, before_location=robot.location, after_location=robot.location, note="设备已恢复"))
    db.commit()
    db.refresh(robot)
    return robot


def edit_robot(db: Session, robot_id: int, payload: schemas.RobotEdit, operator: str):
    robot = db.query(models.Robot).filter(models.Robot.id == robot_id, models.Robot.is_archived == 0).first()
    if not robot:
        raise HTTPException(status_code=404, detail="设备不存在")
    duplicate = db.query(models.Robot).filter(models.Robot.asset_code == payload.asset_code.strip(), models.Robot.id != robot_id).first()
    if duplicate:
        raise HTTPException(status_code=400, detail=f"资产编号 {payload.asset_code} 已存在")
    changed = []
    for field in ("asset_code", "model", "owner_department", "owner_name", "location", "remark"):
        value = getattr(payload, field).strip()
        if getattr(robot, field) != value:
            changed.append(field)
            setattr(robot, field, value)
    if changed:
        db.add(models.OperationLog(robot_id=robot.id, operator=operator, action="资料编辑",
            before_status=robot.status, after_status=robot.status, before_location=robot.location,
            after_location=robot.location, note="更新字段：" + "、".join(changed)))
    db.commit()
    db.refresh(robot)
    return robot


def inventory_robot(db: Session, robot_id: int, payload: schemas.InventoryUpdate, operator: str):
    robot = db.query(models.Robot).filter(models.Robot.id == robot_id, models.Robot.is_archived == 0).first()
    if not robot:
        raise HTTPException(status_code=404, detail="设备不存在")
    robot.last_inventory_at = datetime.now()
    robot.last_inventory_by = operator
    robot.last_inventory_location = payload.location.strip()
    robot.inventory_note = payload.note.strip()
    db.add(models.OperationLog(robot_id=robot.id, operator=operator, action="盘点",
        before_status=robot.status, after_status=robot.status, before_location=robot.location,
        after_location=payload.location.strip() or robot.location, note=payload.note.strip()))
    db.commit()
    db.refresh(robot)
    return robot
