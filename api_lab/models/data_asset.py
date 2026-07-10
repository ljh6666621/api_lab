from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, func

from core.database import Base


class DataAsset(Base):
    """数据资产模型：记录数据资产的元信息，包括来源、字段结构、行数、标签等。"""

    __tablename__ = "data_assets"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    """资产 ID，主键自增。"""

    name = Column(String(200), nullable=False, index=True)
    """资产名称，必填，最长 200 字符。"""

    source_type = Column(String(50), nullable=False, default="manual")
    """资产来源类型：'pipeline' 流水线 / 'table' 数据库表 / 'manual' 手动录入，默认 'manual'。"""

    source_table = Column(String(200), nullable=True)
    """来源表名（数据库中真实表名）或 pipeline_runs 引用，可空。"""

    pipeline_id = Column(Integer, nullable=True)
    """关联的流水线 ID，可空（暂不加外键约束）。"""

    description = Column(Text, nullable=True)
    """资产描述说明，可空。"""

    owner_id = Column(Integer, nullable=True)
    """资产负责人用户 ID，可空。"""

    columns_info = Column(JSON, nullable=True)
    """字段信息 JSON：[{"name":"id","type":"INTEGER","comment":""}, ...]，可空。"""

    row_count = Column(Integer, nullable=False, default=0)
    """数据行数，默认 0。"""

    last_sync_at = Column(DateTime, nullable=True)
    """最近同步/画像生成时间，可空。"""

    tags = Column(String(500), nullable=True)
    """标签列表，逗号分隔字符串，最长 500 字符，可空。"""

    created_at = Column(DateTime, default=datetime.utcnow)
    """创建时间。"""

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    """更新时间。"""


class AssetProfile(Base):
    """资产画像模型：存储某次生成的数据资产统计画像与 LLM 自然语言报告。"""

    __tablename__ = "asset_profiles"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    """画像 ID，主键自增。"""

    asset_id = Column(Integer, nullable=False, index=True)
    """关联的数据资产 ID，必填。"""

    generated_at = Column(DateTime, nullable=False, default=func.now())
    """画像生成时间，默认当前时间。"""

    summary = Column(JSON, nullable=True)
    """画像统计摘要 JSON：包含缺失率、枚举分布、min/max/avg 等，可空。"""

    report_text = Column(Text, nullable=True)
    """LLM 生成的自然语言分析报告，可空。"""

    generated_by = Column(Integer, nullable=True)
    """触发画像生成的用户 ID，可空。"""
