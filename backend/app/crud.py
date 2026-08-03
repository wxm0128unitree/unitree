"""
业务逻辑层
封装设备状态变更、操作日志记录等核心业务
"""
from sqlalchemy.orm import Session
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from app import models, schemas
from fastapi import HTTPException
from typing import List, Optional
from datetime import datetime


def get_robot_by_code(db: Session, asset_code: str) -> Optional[models.Robot]:
    return db.query(models.Robot).filter(models.Robot.asset_code == asset_code).first()


VALID_DEVICE_BRANCHES = {"standard_robot", "training_platform"}
VALID_PLATFORM_TYPES = {"humanoid", "quadruped"}
VALID_STATUSES = {"在库", "借出", "维修中"}
INDIVIDUAL_INVENTORY_CATEGORIES = {"电池", "遥控器"}


def _normalize_robot_identity(data: dict) -> dict:
    """统一成品机器人/实训台身份，实训台不再区分形态。"""
    normalized = dict(data)
    normalized["asset_code"] = (normalized.get("asset_code") or "").strip()
    normalized["model"] = (normalized.get("model") or "").strip()
    branch = (normalized.get("device_branch") or "standard_robot").strip()
    platform_type = (normalized.get("platform_type") or "").strip()
    if branch not in VALID_DEVICE_BRANCHES:
        raise HTTPException(status_code=400, detail="设备分支不正确")
    if branch == "training_platform" or normalized["model"] == "实训台":
        branch = "training_platform"
        normalized["model"] = "实训台"
        # 兼容保留历史人形/四足值；新记录使用空值，不再要求或展示形态。
        platform_type = platform_type if platform_type in VALID_PLATFORM_TYPES else ""
    else:
        if not normalized["model"]:
            raise HTTPException(status_code=400, detail="机器人型号不能为空")
        platform_type = ""
    normalized["device_branch"] = branch
    normalized["platform_type"] = platform_type
    return normalized


def list_robots(
    db: Session,
    model: Optional[str] = None,
    status: Optional[str] = None,
    keyword: Optional[str] = None,
    holder: Optional[str] = None,
    include_archived: bool = False,
    visible_to: Optional[str] = None,
) -> List[models.Robot]:
    """列出设备，支持筛选"""
    q = db.query(models.Robot)
    if visible_to:
        q = q.filter(models.Robot.owner_name == visible_to)
    if not include_archived:
        q = q.filter(models.Robot.is_archived == 0, models.Robot.lifecycle_status == "active")
    if model and model != "全部":
        q = q.filter(models.Robot.model == model)
    if status and status != "全部":
        q = q.filter(models.Robot.status == status)
    if holder and holder != "全部":
        like = f"%{holder.strip()}%"
        q = q.filter(or_(models.Robot.holder.like(like), models.Robot.owner_name.like(like), models.Robot.borrower.like(like)))
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
    data = _normalize_robot_identity(payload.model_dump())
    if not data["asset_code"]:
        raise HTTPException(status_code=400, detail="资产编号不能为空")
    if get_robot_by_code(db, data["asset_code"]):
        raise HTTPException(status_code=400, detail=f"资产编号 {data['asset_code']} 已存在")
    data["owner_name"] = (data.get("owner_name") or "").strip()
    data["holder"] = (data.get("holder") or "").strip()
    if not data["owner_name"]:
        raise HTTPException(status_code=400, detail="负责人不能为空")
    if not data["holder"]:
        raise HTTPException(status_code=400, detail="持有人不能为空")
    if not db.query(models.User).filter(models.User.name == data["owner_name"], models.User.is_active == 1).first():
        raise HTTPException(status_code=400, detail="负责人必须是启用的内部账号")
    if data["status"] == "借出":
        if not (data.get("borrower") or "").strip():
            raise HTTPException(status_code=400, detail="借出设备必须填写借用人")
        data["borrower"] = data["borrower"].strip()
        data["holder"] = data["borrower"]
    if data["status"] == "在库" and not db.query(models.User).filter(
        models.User.name == data["holder"], models.User.is_active == 1).first():
        raise HTTPException(status_code=400, detail="在库设备的持有人必须是内部人员")
    if payload.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail="状态只能是在库、借出或维修中")
    robot = models.Robot(**data)
    db.add(robot)
    try:
        db.flush()
        # 设备与首条审计日志在同一事务中提交，避免只写入设备却没有日志。
        db.add(models.OperationLog(
            robot_id=robot.id, operator=operator, action="入库",
            before_status="", after_status=robot.status,
            before_location="", after_location=robot.location or "", note="设备创建",
        ))
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"资产编号 {data['asset_code']} 已存在")
    db.refresh(robot)
    return robot


def update_robot_status(
    db: Session, robot_id: int, payload: schemas.RobotUpdate, operator: str = "admin",
) -> models.Robot:
    """核心动作：修改设备状态（借出/归还/维修/转移）"""
    robot = db.query(models.Robot).filter(
        models.Robot.id == robot_id, models.Robot.is_archived == 0,
        models.Robot.lifecycle_status == "active",
    ).first()
    if not robot:
        raise HTTPException(status_code=404, detail="设备不存在")

    if payload.status.strip() not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail="状态只能是在库、借出或维修中")

    # 记录变更前状态
    before = {"status": robot.status, "location": robot.location}

    # 更新状态
    new_status = payload.status.strip()
    requested_holder = payload.holder.strip()
    if new_status == "借出":
        if not payload.borrower.strip():
            raise HTTPException(status_code=400, detail="借出必须填写借用人")
        new_holder = payload.borrower.strip()
    elif new_status == "在库":
        new_holder = requested_holder or (robot.owner_name if before["status"] == "借出" else robot.holder)
        if not db.query(models.User).filter(models.User.name == new_holder, models.User.is_active == 1).first():
            raise HTTPException(status_code=400, detail="在库设备的持有人必须是内部人员")
    else:
        new_holder = requested_holder or robot.holder
    if not new_holder:
        raise HTTPException(status_code=400, detail="持有人不能为空")
    robot.status = new_status
    robot.holder = new_holder
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


def get_stats(db: Session, visible_to: Optional[str] = None) -> dict:
    """首页统计：总数量、各状态数量"""
    active = (models.Robot.is_archived == 0) & (models.Robot.lifecycle_status == "active")
    q = db.query(models.Robot).filter(active)
    if visible_to:
        q = q.filter(models.Robot.owner_name == visible_to)
    rows = q.all()
    total = len(rows)
    in_stock = sum(r.status == "在库" for r in rows)
    borrowed = sum(r.status == "借出" for r in rows)
    in_repair = sum(r.status == "维修中" for r in rows)
    by_model = {}
    training = {"total": 0, "in_stock": 0, "borrowed": 0, "in_repair": 0}
    for robot in rows:
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
    page: int = 1, page_size: int = 50, visible_to: Optional[str] = None,
):
    """查询操作日志并返回分页结果。"""
    q = db.query(models.OperationLog)
    if visible_to:
        q = q.join(models.Robot).filter(models.Robot.owner_name == visible_to)
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
    robot = db.query(models.Robot).filter(
        models.Robot.id == robot_id, models.Robot.is_archived == 0,
        models.Robot.lifecycle_status == "active",
    ).first()
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


def edit_robot(db: Session, robot_id: int, payload: schemas.RobotEdit, operator: str, allow_owner_change: bool = False):
    robot = db.query(models.Robot).filter(
        models.Robot.id == robot_id, models.Robot.is_archived == 0,
        models.Robot.lifecycle_status == "active",
    ).first()
    if not robot:
        raise HTTPException(status_code=404, detail="设备不存在")
    duplicate = db.query(models.Robot).filter(models.Robot.asset_code == payload.asset_code.strip(), models.Robot.id != robot_id).first()
    if duplicate:
        raise HTTPException(status_code=400, detail=f"资产编号 {payload.asset_code} 已存在")
    identity = _normalize_robot_identity({
        "asset_code": payload.asset_code,
        "model": payload.model,
        "device_branch": payload.device_branch if payload.device_branch is not None else robot.device_branch,
        "platform_type": payload.platform_type if payload.platform_type is not None else robot.platform_type,
    })
    changed = []
    if not payload.holder.strip():
        raise HTTPException(status_code=400, detail="持有人不能为空")
    if robot.status == "借出" and robot.borrower and payload.holder.strip() != robot.borrower:
        raise HTTPException(status_code=400, detail="借出状态下持有人必须与借用人一致")
    if robot.status == "在库" and not db.query(models.User).filter(
        models.User.name == payload.holder.strip(), models.User.is_active == 1).first():
        raise HTTPException(status_code=400, detail="在库设备的持有人必须是内部人员")
    fields = ["asset_code", "model", "device_branch", "platform_type", "holder", "location", "remark"]
    if allow_owner_change:
        if not db.query(models.User).filter(models.User.name == payload.owner_name.strip(), models.User.is_active == 1).first():
            raise HTTPException(status_code=400, detail="负责人必须是启用的内部账号")
        fields.extend(["owner_department", "owner_name"])
    for field in fields:
        value = identity[field] if field in identity else getattr(payload, field).strip()
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
    robot = db.query(models.Robot).filter(
        models.Robot.id == robot_id, models.Robot.is_archived == 0,
        models.Robot.lifecycle_status == "active",
    ).first()
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
    robot = db.query(models.Robot).filter(
        models.Robot.id == robot_id, models.Robot.lifecycle_status == "active",
        models.Robot.is_archived == 0,
    ).first()
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


def _inventory_item_query(db: Session, visible_to: Optional[str] = None):
    q = db.query(models.InventoryItem).filter(models.InventoryItem.is_archived == 0)
    return q.filter(models.InventoryItem.owner_name == visible_to) if visible_to else q


def _validate_inventory_data(db: Session, data: dict, item_id: Optional[int] = None):
    category = (data.get("category") or "").strip()
    code = (data.get("asset_code") or "").strip()
    owner = (data.get("owner_name") or "").strip()
    holder = (data.get("holder") or "").strip()
    status = (data.get("status") or "").strip()
    if status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail="状态只能是在库、借出或维修中")
    if not owner:
        raise HTTPException(status_code=400, detail="负责人不能为空")
    if not holder:
        raise HTTPException(status_code=400, detail="当前持有人不能为空")
    if not db.query(models.User).filter(models.User.name == owner, models.User.is_active == 1).first():
        raise HTTPException(status_code=400, detail="负责人必须是启用的内部账号")
    if status == "在库" and not db.query(models.User).filter(
        models.User.name == holder, models.User.is_active == 1).first():
        raise HTTPException(status_code=400, detail="在库配件的持有人必须是内部人员")
    if code:
        q = db.query(models.InventoryItem).filter(
            models.InventoryItem.asset_code == code,
            models.InventoryItem.is_archived == 0,
        )
        if item_id is not None:
            q = q.filter(models.InventoryItem.id != item_id)
        if q.first():
            raise HTTPException(status_code=400, detail=f"配件编号 {code} 已存在")
    return category, code, owner, holder, status


def create_inventory_item(db: Session, payload: schemas.InventoryItemCreate, operator: str):
    data = payload.model_dump(exclude={"initial_quantity"})
    category, code, owner, holder, status = _validate_inventory_data(db, data)
    quantity = payload.initial_quantity
    if category in INDIVIDUAL_INVENTORY_CATEGORIES:
        if quantity != 1:
            raise HTTPException(status_code=400, detail="电池和遥控器必须逐件创建，数量固定为 1")
    else:
        duplicate = db.query(models.InventoryItem).filter(
            models.InventoryItem.category == category,
            models.InventoryItem.subtype == payload.subtype.strip(),
            models.InventoryItem.model == payload.model.strip(),
            models.InventoryItem.owner_name == owner,
            models.InventoryItem.holder == holder,
            models.InventoryItem.is_archived == 0,
        ).first()
        if duplicate:
            raise HTTPException(status_code=400, detail="该持有人名下已有相同分类、类型和型号的配件")
    data.update(category=category, asset_code=code, owner_name=owner, holder=holder, status=status)
    available = quantity if status == "在库" else 0
    loaned = quantity if status == "借出" else 0
    item = models.InventoryItem(**data, total_quantity=quantity, available_quantity=available, loaned_quantity=loaned)
    db.add(item); db.flush()
    if payload.initial_quantity:
        db.add(models.InventoryTransaction(inventory_item_id=item.id, action="stock_in", quantity=payload.initial_quantity,
            before_total=0, after_total=payload.initial_quantity, before_available=0, after_available=payload.initial_quantity,
            operator=operator, note="初始库存"))
    db.commit(); db.refresh(item); return item


def edit_inventory_item(db: Session, item_id: int, payload: schemas.InventoryItemEdit, allow_owner_change: bool = False):
    item = db.query(models.InventoryItem).filter(models.InventoryItem.id == item_id, models.InventoryItem.is_archived == 0).first()
    if not item: raise HTTPException(status_code=404, detail="库存项目不存在")
    data = payload.model_dump()
    if not allow_owner_change:
        data["owner_name"] = item.owner_name
    category, code, owner, holder, status = _validate_inventory_data(db, data, item_id=item_id)
    if category not in INDIVIDUAL_INVENTORY_CATEGORIES:
        duplicate = db.query(models.InventoryItem).filter(
            models.InventoryItem.category == category,
            models.InventoryItem.subtype == payload.subtype.strip(),
            models.InventoryItem.model == payload.model.strip(),
            models.InventoryItem.owner_name == owner,
            models.InventoryItem.holder == holder,
            models.InventoryItem.id != item_id,
            models.InventoryItem.is_archived == 0,
        ).first()
        if duplicate:
            raise HTTPException(status_code=400, detail="该持有人名下已有相同分类、类型和型号的配件")
    data.update(category=category, asset_code=code, owner_name=owner, holder=holder, status=status)
    for field, value in data.items():
        setattr(item, field, value.strip() if isinstance(value, str) else value)
    if item.status == "在库":
        item.available_quantity, item.loaned_quantity = item.total_quantity, 0
    elif item.status == "借出":
        item.available_quantity, item.loaned_quantity = 0, item.total_quantity
    else:
        item.available_quantity, item.loaned_quantity = 0, 0
    db.commit(); db.refresh(item); return item


def delete_inventory_item(db: Session, item_id: int):
    item = db.query(models.InventoryItem).filter(models.InventoryItem.id == item_id, models.InventoryItem.is_archived == 0).first()
    if not item: raise HTTPException(status_code=404, detail="库存项目不存在")
    if item.loaned_quantity > 0: raise HTTPException(status_code=400, detail="仍有配件借出，归还后才能删除")
    item.is_archived = 2
    db.commit()
    return {"ok": True}


def list_inventory_items(db: Session, category: Optional[str] = None, status: Optional[str] = None,
    holder: Optional[str] = None, keyword: Optional[str] = None, visible_to: Optional[str] = None):
    q = _inventory_item_query(db, visible_to)
    if category:
        if category in {"夹爪", "三指灵巧手"}:
            q = q.filter(models.InventoryItem.category == "灵巧手", models.InventoryItem.subtype == category)
        else:
            q = q.filter(models.InventoryItem.category == category)
    if status and status != "全部": q = q.filter(models.InventoryItem.status == status)
    if holder and holder != "全部": q = q.filter(models.InventoryItem.holder.like(f"%{holder.strip()}%"))
    if keyword:
        like = f"%{keyword.strip()}%"
        q = q.filter(or_(models.InventoryItem.asset_code.like(like), models.InventoryItem.model.like(like),
            models.InventoryItem.owner_name.like(like), models.InventoryItem.owner_department.like(like),
            models.InventoryItem.holder.like(like), models.InventoryItem.location.like(like)))
    return q.order_by(models.InventoryItem.category, models.InventoryItem.owner_name, models.InventoryItem.model,
        models.InventoryItem.asset_code).all()


def inventory_action(db: Session, item_id: int, payload: schemas.InventoryAction, operator: str):
    item = db.query(models.InventoryItem).filter(models.InventoryItem.id == item_id, models.InventoryItem.is_archived == 0).with_for_update().first()
    if not item: raise HTTPException(status_code=404, detail="库存项目不存在")
    if item.category in INDIVIDUAL_INVENTORY_CATEGORIES:
        raise HTTPException(status_code=400, detail="电池和遥控器为逐件管理，请直接修改状态")
    action, qty = payload.action, payload.quantity
    before_total, before_available = item.total_quantity, item.available_quantity
    if action == "stock_in": item.total_quantity += qty; item.available_quantity += qty
    elif action == "borrow":
        if not payload.borrower.strip(): raise HTTPException(status_code=400, detail="借出必须填写借用人")
        if qty != item.available_quantity or item.loaned_quantity:
            raise HTTPException(status_code=400, detail="同一配件记录必须整体借出；分给不同持有人时请分别建档")
        item.available_quantity = 0; item.loaned_quantity = qty
        item.status = "借出"; item.holder = payload.borrower.strip()
    elif action == "return":
        if qty != item.loaned_quantity:
            raise HTTPException(status_code=400, detail="同一配件记录必须整体归还")
        item.available_quantity = item.total_quantity; item.loaned_quantity = 0
        item.status = "在库"; item.holder = item.owner_name
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
    db.add(tx)
    if item.total_quantity == 0 and item.loaned_quantity == 0:
        item.is_archived = 2
    db.commit(); db.refresh(item); return item


def inventory_stats(db: Session, visible_to: Optional[str] = None):
    items = list_inventory_items(db, visible_to=visible_to)
    categories = {}
    for item in items:
        key = item.subtype if item.category == "灵巧手" and item.subtype else item.category
        row = categories.setdefault(key, {"total": 0, "available": 0, "loaned": 0})
        row["total"] += item.total_quantity; row["available"] += item.available_quantity; row["loaned"] += item.loaned_quantity
    return {"total": sum(x.total_quantity for x in items), "available": sum(x.available_quantity for x in items),
            "loaned": sum(x.loaned_quantity for x in items), "categories": categories}
