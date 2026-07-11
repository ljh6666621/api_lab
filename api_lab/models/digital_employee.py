from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, ForeignKey

from core.database import Base


class DigitalEmployee(Base):
    """数字员工数据模型：存储数字员工的基本信息、角色设定、默认模型及状态。"""
    __tablename__ = "digital_employees"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, index=True, comment="员工名称")
    avatar = Column(String(500), nullable=True, comment="头像URL")
    description = Column(Text, nullable=True, comment="员工职责描述")
    role_key = Column(String(50), nullable=False, default="default", index=True, comment="角色key，对应prompts.ROLES")
    default_model_id = Column(Integer, ForeignKey("llm_models.id"), nullable=True, index=True, comment="默认模型ID，0或None表示系统默认")
    owner_id = Column(Integer, nullable=True, index=True, comment="所属用户/创建人ID")
    status = Column(Integer, nullable=False, default=1, index=True, comment="状态：1=启用，0=禁用")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")


class EmployeeTaskRun(Base):
    """数字员工任务执行记录：存储数字员工触发的各类任务（流水线、画像、NL2SQL）运行状态与结果。"""
    __tablename__ = "employee_task_runs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    employee_id = Column(Integer, nullable=False, index=True, comment="关联数字员工ID")
    user_id = Column(Integer, nullable=False, index=True, comment="触发用户ID")
    task_type = Column(String(50), nullable=False, comment="任务类型：pipeline_run/asset_profile/nl2sql_report")
    params = Column(JSON, nullable=True, comment="任务参数JSON")
    status = Column(String(30), nullable=False, default="queued", comment="状态：queued/running/success/failed")
    result = Column(JSON, nullable=True, comment="执行结果JSON")
    error_msg = Column(Text, nullable=True, comment="错误信息")
    started_at = Column(DateTime, default=datetime.utcnow, comment="开始执行时间")
    finished_at = Column(DateTime, nullable=True, comment="结束时间")
