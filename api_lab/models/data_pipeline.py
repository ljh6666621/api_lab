from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, Text
from sqlalchemy.orm import relationship

from core.database import Base


class DataSource(Base):
    """
    数据源模型：定义数据采集的来源配置，支持 HTTP API、爬虫、文件上传等多种类型。
    config 字段以 JSON 格式存储各类型特定参数（URL、Headers、方法、参数、提取路径等）。
    """
    __tablename__ = "data_sources"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, index=True, comment="数据源名称")
    type = Column(String(50), nullable=False, default="http_api", comment="数据源类型：http_api/crawler/upload")
    config = Column(JSON, nullable=True, comment="数据源配置 JSON，如 {url, headers, method, params, jq_path, extract_map}")
    status = Column(Integer, nullable=False, default=1, comment="状态：1=启用，0=停用")
    created_by = Column(Integer, nullable=True, comment="创建人用户 ID")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    pipelines = relationship("DataPipeline", back_populates="source", cascade="all, delete-orphan")


class DataPipeline(Base):
    """
    数据采集流水线模型：关联数据源与采集规则，支持定时调度与字段映射。
    schedule 字段存储 cron 表达式，extract_rules 定义字段重命名和过滤规则。
    """
    __tablename__ = "pipelines"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(200), nullable=False, index=True, comment="流水线名称")
    source_id = Column(Integer, ForeignKey("data_sources.id"), nullable=False, comment="关联数据源 ID")
    schedule = Column(String(100), nullable=True, comment="cron 定时表达式，为空则不自动调度")
    extract_rules = Column(JSON, nullable=True, comment="提取规则 JSON，如 {field_map: {...}, filter: {...}}")
    target_asset_id = Column(Integer, nullable=True, comment="目标资产 ID，预留 B 模块同步使用")
    status = Column(Integer, nullable=False, default=1, comment="状态：1=启用，0=停用")
    created_by = Column(Integer, nullable=True, comment="创建人用户 ID")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    source = relationship("DataSource", back_populates="pipelines")
    runs = relationship("PipelineRun", back_populates="pipeline", cascade="all, delete-orphan")


class PipelineRun(Base):
    """
    流水线运行记录模型：每次管道执行（手动/定时/上传）生成一条记录，
    包含执行状态、耗时、采集条数、错误信息以及最终数据结果。
    """
    __tablename__ = "pipeline_runs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    pipeline_id = Column(Integer, ForeignKey("pipelines.id"), nullable=False, comment="关联流水线 ID")
    triggered_by = Column(String(50), nullable=False, default="manual", comment="触发方式：manual/scheduler/user_<id>/upload")
    start_at = Column(DateTime, default=datetime.utcnow, comment="开始执行时间")
    end_at = Column(DateTime, nullable=True, comment="执行结束时间")
    status = Column(String(30), nullable=False, default="running", comment="执行状态：running/success/failed")
    rows_count = Column(Integer, nullable=False, default=0, comment="采集到的数据行数")
    error_msg = Column(Text, nullable=True, comment="错误信息（执行失败时记录")
    data = Column(JSON, nullable=True, comment="采集结果数据列表 JSON")

    pipeline = relationship("DataPipeline", back_populates="runs")
