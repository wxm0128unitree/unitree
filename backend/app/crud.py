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
        q = q.filter(models.Robot.is_archived == 0, models.Robot.lifecycle_status == "active")
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
        robot.borrowed_at = models.utc_now()
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
    active = (models.Robot.is_archived == 0) & (models.Robot.lifecycle_status == "active")
    total = db.query(models.Robot).filter(active).count()
    in_stock = db.query(models.Robot).filter(active, models.Robot.status == "在库").count()
    borrowed = db.query(models.Robot).filter(active, models.Robot.status == "借出").count()
    in_repair = db.query(models.Robot).filter(active, models.Robot.status == "维修中").count()
    rows = db.query(models.Robot).filter(active).all()
    by_model = {}
    training = {"humanoid": 0, "quadruped": 0}
    for robot in rows:
        if robot.device_branch == "training_platform":
            training[robot.platform_type or "other"] = training.get(robot.platform_type or "other", 0) + 1
        else:
            entry = by_model.setdefault(robot.model, {"total": 0, "in_stock": 0, "borrowed": 0, "in_repair": 0})
            entry["total"] += 1
            if robot.status == "在库": entry["in_stock"] += 1
            elif robot.status == "借出": entry["borrowed"] += 1
            elif robot.status == "维修中": entry["in_repair"] += 1
    return {"total": total, "in_stock": in_stock, "borrowed": borrowed, "in_repair": in_repair,
            "by_model": by_model, "training_platforms": training}


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
    robot.archived_at = models.utc_now()
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
    for field in ("asset_code", "model", "device_branch", "platform_type", "owner_department", "owner_name", "location", "remark"):
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
    robot.last_inventory_at = models.utc_now()
    robot.last_inventory_by = operator
    robot.last_inventory_location = payload.location.strip()
    robot.inventory_note = payload.note.strip()
    db.add(models.OperationLog(robot_id=robot.id, operator=operator, action="盘点",
        before_status=robot.status, after_status=robot.status, before_location=robot.location,
        after_location=payload.location.strip() or robot.location, note=payload.note.strip()))
    db.commit()
    db.refresh(robot)
    return robot


def migrate_robot(db: Session, robot_id: int, payload: schemas.RobotMigration, operator: str):
    robot = db.query(models.Robot).filter(models.Robot.id == robot_id, models.Robot.lifecycle_status == "active").first()
    if not robot: raise HTTPException(status_code=404, detail="设备不存在或已迁移")
    robot.lifecycle_status = "migrated"
    robot.migrated_at = models.utc_now()
    robot.destination_department = payload.destination_department.strip()
    robot.destination_holder = payload.destination_holder.strip()
    robot.migration_reason = payload.reason.strip()
    db.add(models.OperationLog(robot_id=robot.id, operator=operator, action="迁移",
        before_status=robot.status, after_status="已迁移", before_location=robot.location,
        after_location=robot.destination_department, note=payload.reason))
    db.commit(); db.refresh(robot); return robot


def undo_robot_migration(db: Session, robot_id: int, operator: str):
    robot = db.query(models.Robot).filter(models.Robot.id == robot_id, models.Robot.lifecycle_status == "migrated").first()
    if not robot: raise HTTPException(status_code=404, detail="迁移记录不存在")
    robot.lifecycle_status = "active"; robot.migrated_at = None
    robot.destination_department = ""; robot.destination_holder = ""; robot.migration_reason = ""
    db.add(models.OperationLog(robot_id=robot.id, operator=operator, action="撤销迁移",
        before_status="已迁移", after_status=robot.status, before_location="", after_location=robot.location, note="管理员撤销迁移"))
    db.commit(); db.refresh(robot); return robot


def create_inventory_item(db: Session, payload: schemas.InventoryItemCreate, operator: str):
    duplicate = db.query(models.InventoryItem).filter(models.InventoryItem.category == payload.category,
        models.InventoryItem.subtype == payload.subtype, models.InventoryItem.model == payload.model,
        models.InventoryItem.is_archived == 0).first()
    if duplicate: raise HTTPException(status_code=400, detail="相同分类、子类型和型号的库存项目已存在")
    data = payload.model_dump(exclude={"initial_quantity"})
    item = models.InventoryItem(**data, total_quantity=payload.initial_quantity, available_quantity=payload.initial_quantity)
    db.add(item); db.flush()
    if payload.initial_quantity:
        db.add(models.InventoryTransaction(inventory_item_id=item.id, action="stock_in", quantity=payload.initial_quantity,
            before_total=0, after_total=payload.initial_quantity, before_available=0, after_available=payload.initial_quantity,
            operator=operator, note="初始库存"))
    db.commit(); db.refresh(item); return item


def list_inventory_items(db: Session, category: Optional[str] = None):
    q = db.query(models.InventoryItem).filter(models.InventoryItem.is_archived == 0)
    if category: q = q.filter(models.InventoryItem.category == category)
    return q.order_by(models.InventoryItem.category, models.InventoryItem.model).all()


def inventory_action(db: Session, item_id: int, payload: schemas.InventoryAction, operator: str):
    item = db.query(models.InventoryItem).filter(models.InventoryItem.id == item_id, models.InventoryItem.is_archived == 0).with_for_update().first()
    if not item: raise HTTPException(status_code=404, detail="库存项目不存在")
    action, qty = payload.action, payload.quantity
    before_total, before_available = item.total_quantity, item.available_quantity
    if action == "stock_in": item.total_quantity += qty; item.available_quantity += qty
    elif action == "borrow":
        if qty > item.available_quantity: raise HTTPException(status_code=400, detail="出库数量超过当前库存")
        item.available_quantity -= qty; item.loaned_quantity += qty
    elif action == "return":
        if qty > item.loaned_quantity: raise HTTPException(status_code=400, detail="归还数量超过当前借出数量")
        item.available_quantity += qty; item.loaned_quantity -= qty
    elif action == "migrate":
        if not payload.destination_department.strip(): raise HTTPException(status_code=400, detail="迁移必须填写接收部门")
        if qty > item.available_quantity: raise HTTPException(status_code=400, detail="迁移数量超过当前库存")
        item.available_quantity -= qty; item.total_quantity -= qty
    elif action == "scrap":
        if qty > item.available_quantity: raise HTTPException(status_code=400, detail="报废数量超过当前库存")
        item.available_quantity -= qty; item.total_quantity -= qty
    else: raise HTTPException(status_code=400, detail="不支持的库存操作")
    tx = models.InventoryTransaction(inventory_item_id=item.id, action=action, quantity=qty,
        before_total=before_total, after_total=item.total_quantity, before_available=before_available,
        after_available=item.available_quantity, borrower=payload.borrower.strip(), purpose=payload.purpose.strip(),
        destination_department=payload.destination_department.strip(), destination_holder=payload.destination_holder.strip(),
        expected_return_at=payload.expected_return_at, operator=operator, note=payload.note.strip())
    db.add(tx); db.commit(); db.refresh(item); return item


def inventory_stats(db: Session):
    items = list_inventory_items(db)
    categories = {}
    for item in items:
        key = item.subtype if item.category == "灵巧手" and item.subtype else item.category
        row = categories.setdefault(key, {"total": 0, "available": 0, "loaned": 0})
        row["total"] += item.total_quantity; row["available"] += item.available_quantity; row["loaned"] += item.loaned_quantity
    return {"total": sum(x.total_quantity for x in items), "available": sum(x.available_quantity for x in items),
            "loaned": sum(x.loaned_quantity for x in items), "categories": categories}
