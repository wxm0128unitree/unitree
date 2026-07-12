"""
数据库模型定义
严格按照开发手册设计：两张表
1. 设备主表 (Robot) - 存储设备当前状态
2. 操作日志表 (OperationLog) - 审计追踪
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Robot(Base):
    """设备主表"""
    __tablename__ = "robots"

    id = Column(Integer, primary_key=True, index=True)
    asset_code = Column(String(64), unique=True, nullable=False, index=True)  # 资产编号
    model = Column(String(32), nullable=False, index=True)  # 型号
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
    last_inventory_at = Column(DateTime, nullable=True)
    last_inventory_by = Column(String(64), default="")
    last_inventory_location = Column(String(128), default="")
    inventory_note = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

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
    created_at = Column(DateTime, default=datetime.now, index=True)

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
    created_at = Column(DateTime, default=datetime.now)
