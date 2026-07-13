"""
数据库模型定义
严格按照开发手册设计：两张表
1. 设备主表 (Robot) - 存储设备当前状态
2. 操作日志表 (OperationLog) - 审计追踪
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base


def utc_now():
    """数据库统一保存无时区标记的 UTC，API 输出时再补 UTC 标记。"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Robot(Base):
    """设备主表"""
    __tablename__ = "robots"

    id = Column(Integer, primary_key=True, index=True)
    asset_code = Column(String(64), unique=True, nullable=False, index=True)  # 资产编号
    model = Column(String(32), nullable=False, index=True)  # 型号
    device_branch = Column(String(32), nullable=False, default="standard_robot", index=True)
    platform_type = Column(String(32), default="", index=True)
    lifecycle_status = Column(String(16), nullable=False, default="active", index=True)
    status = Column(String(16), nullable=False, default="在库", index=True)
    location = Column(String(128), default="")  # 去向/持有人/故障原因（动态）
    holder = Column(String(32), default="", index=True)  # 设备归属：谁提单/名下
    owner_department = Column(String(64), default="", index=True)  # 资产归属部门
    owner_name = Column(String(32), default="", index=True)  # 资产负责人
    borrower = Column(String(32), default="", index=True)  # 当前借用人
    purpose = Column(String(128), default="")  # 借用用途
    borrowed_at = Column(DateTime, nullable=True)
    expected_return_at = Column(DateTime, nullable=True, index=True)
    repair_description = Column(Text, default="")
    remark = Column(Text, default="")  # 备注
    is_archived = Column(Integer, nullable=False, default=0, index=True)
    archived_at = Column(DateTime, nullable=True)
    migrated_at = Column(DateTime, nullable=True)
    destination_department = Column(String(64), default="")
    destination_holder = Column(String(32), default="")
    migration_reason = Column(Text, default="")
    last_inventory_at = Column(DateTime, nullable=True)
    last_inventory_by = Column(String(64), default="")
    last_inventory_location = Column(String(128), default="")
    inventory_note = Column(Text, default="")
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    logs = relationship("OperationLog", back_populates="robot", cascade="all, delete-orphan")


class OperationLog(Base):
    """操作日志表"""
    __tablename__ = "operation_logs"

    id = Column(Integer, primary_key=True, index=True)
    robot_id = Column(Integer, ForeignKey("robots.id"), nullable=False)
    operator = Column(String(64), default="admin")  # 操作人
    action = Column(String(32), nullable=False)  # 操作类型：入库/借出/归还/维修/转移
    before_status = Column(String(16))
    after_status = Column(String(16))
    before_location = Column(String(128))
    after_location = Column(String(128))
    note = Column(Text, default="")
    created_at = Column(DateTime, default=utc_now, index=True)

    robot = relationship("Robot", back_populates="logs")


class User(Base):
    """用户表"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(32), nullable=False)  # 真实姓名
    phone = Column(String(20), unique=True, nullable=False, index=True)  # 账号（手机号）
    password_hash = Column(String(255), nullable=False)  # bcrypt 哈希
    is_admin = Column(Integer, default=0)  # 1=管理员, 0=普通用户
    is_active = Column(Integer, nullable=False, default=1)  # 1=启用, 0=停用
    last_login_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)


class InventoryItem(Base):
    """按数量管理的配件库存。"""
    __tablename__ = "inventory_items"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(32), nullable=False, index=True)
    subtype = Column(String(32), default="", index=True)
    model = Column(String(64), nullable=False, index=True)
    unit = Column(String(16), nullable=False, default="个")
    total_quantity = Column(Integer, nullable=False, default=0)
    available_quantity = Column(Integer, nullable=False, default=0)
    loaned_quantity = Column(Integer, nullable=False, default=0)
    location = Column(String(128), default="")
    owner_department = Column(String(64), default="")
    owner_name = Column(String(32), default="")
    remark = Column(Text, default="")
    is_archived = Column(Integer, nullable=False, default=0, index=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    transactions = relationship("InventoryTransaction", back_populates="item", cascade="all, delete-orphan")


class InventoryTransaction(Base):
    __tablename__ = "inventory_transactions"

    id = Column(Integer, primary_key=True, index=True)
    inventory_item_id = Column(Integer, ForeignKey("inventory_items.id"), nullable=False, index=True)
    action = Column(String(24), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    before_total = Column(Integer, nullable=False)
    after_total = Column(Integer, nullable=False)
    before_available = Column(Integer, nullable=False)
    after_available = Column(Integer, nullable=False)
    borrower = Column(String(32), default="")
    purpose = Column(String(128), default="")
    destination_department = Column(String(64), default="")
    destination_holder = Column(String(32), default="")
    expected_return_at = Column(DateTime, nullable=True)
    operator = Column(String(64), nullable=False)
    note = Column(Text, default="")
    created_at = Column(DateTime, default=utc_now, index=True)

    item = relationship("InventoryItem", back_populates="transactions")
