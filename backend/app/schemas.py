"""
Pydantic 数据校验模型（API 请求/响应）
"""
import re
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime


# ========== 设备相关 ==========


class RobotBase(BaseModel):
    asset_code: str = Field(..., max_length=64, description="资产编号")
    model: str = Field(..., max_length=32, description="型号")
    status: str = Field(default="在库", description="状态")
    location: str = Field(default="", max_length=128, description="去向/持有人/故障原因")
    holder: str = Field(default="", max_length=32, description="设备归属人（谁提单/名下）")
    owner_department: str = Field(default="", max_length=64, description="资产归属部门")
    owner_name: str = Field(default="", max_length=32, description="资产负责人")
    borrower: str = Field(default="", max_length=32, description="当前借用人")
    purpose: str = Field(default="", max_length=128, description="借用用途")
    borrowed_at: Optional[datetime] = None
    expected_return_at: Optional[datetime] = None
    repair_description: str = Field(default="", max_length=1000)
    remark: Optional[str] = ""


class RobotCreate(RobotBase):
    pass


class RobotUpdate(BaseModel):
    """修改状态请求体"""
    status: str = Field(..., description="新状态：在库/借出/维修中")
    location: str = Field(default="", max_length=128, description="去向信息")
    note: Optional[str] = Field(default="", description="备注")
    borrower: str = Field(default="", max_length=32)
    purpose: str = Field(default="", max_length=128)
    expected_return_at: Optional[datetime] = None
    repair_description: str = Field(default="", max_length=1000)


class RobotEdit(BaseModel):
    asset_code: str = Field(..., min_length=1, max_length=64)
    model: str = Field(..., min_length=1, max_length=32)
    owner_department: str = Field(default="", max_length=64)
    owner_name: str = Field(default="", max_length=32)
    location: str = Field(default="", max_length=128)
    remark: str = Field(default="", max_length=2000)


class InventoryUpdate(BaseModel):
    location: str = Field(default="", max_length=128)
    note: str = Field(default="", max_length=1000)

class RobotOut(RobotBase):
    id: int
    created_at: datetime
    updated_at: datetime
    is_archived: int = 0
    archived_at: Optional[datetime] = None
    last_inventory_at: Optional[datetime] = None
    last_inventory_by: str = ""
    last_inventory_location: str = ""
    inventory_note: str = ""

    class Config:
        from_attributes = True


class RobotStats(BaseModel):
    """统计信息"""
    total: int
    in_stock: int
    borrowed: int
    in_repair: int


class OperationLogOut(BaseModel):
    id: int
    robot_id: int
    operator: str
    action: str
    before_status: Optional[str]
    after_status: Optional[str]
    before_location: Optional[str]
    after_location: Optional[str]
    note: Optional[str]
    created_at: datetime
    asset_code: Optional[str] = None

    class Config:
        from_attributes = True


# ========== 用户/认证相关 ==========

PHONE_RE = re.compile(r"^1[3-9]\d{9}$")


class UserCreate(BaseModel):
    """注册请求"""
    name: str = Field(..., min_length=1, max_length=32, description="真实姓名")
    phone: str = Field(..., description="11 位手机号，作为登录账号")
    password: str = Field(..., min_length=6, max_length=64, description="密码，至少 6 位")

    @field_validator("phone")
    @classmethod
    def _check_phone(cls, v: str) -> str:
        v = v.strip()
        if not PHONE_RE.match(v):
            raise ValueError("手机号格式不正确（11 位，1 开头）")
        return v

    @field_validator("name")
    @classmethod
    def _check_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("姓名不能为空")
        return v


class UserLogin(BaseModel):
    """登录请求"""
    phone: str = Field(..., description="手机号")
    password: str = Field(..., description="密码")


class UserOut(BaseModel):
    id: int
    name: str
    phone: str
    is_admin: int
    is_active: int = 1
    last_login_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True




class UserUpdate(BaseModel):
    """修改用户信息请求体"""
    name: Optional[str] = Field(default=None, min_length=1, max_length=32)
    password: Optional[str] = Field(default=None, min_length=6, max_length=64)


class AdminUserCreate(UserCreate):
    is_admin: int = Field(default=0, ge=0, le=1)


class AdminUserUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=32)
    password: Optional[str] = Field(default=None, min_length=6, max_length=64)
    is_admin: Optional[int] = Field(default=None, ge=0, le=1)
    is_active: Optional[int] = Field(default=None, ge=0, le=1)


class LogPage(BaseModel):
    items: list[OperationLogOut]
    total: int
    page: int
    page_size: int


class Token(BaseModel):
    """登录响应"""
    access_token: str
    token_type: str = "bearer"
    user: UserOut
