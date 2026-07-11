from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    Text,
    JSON,
    UniqueConstraint,
    func,
)

from core.database import Base


class LLMModel(Base):
    """大语言模型配置：存储可用的 LLM 接入参数，包括 API 端点、密钥、默认参数等。"""

    __tablename__ = "llm_models"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        doc="主键 ID，自增",
    )
    name = Column(
        String(100),
        nullable=False,
        doc="模型显示名称，用于前端展示和区分",
    )
    provider = Column(
        String(50),
        default="openai-compatible",
        doc="模型服务商，默认 openai-compatible，兼容 OpenAI 协议",
    )
    base_url = Column(
        String(500),
        doc="API 基础地址，如 https://api.openai.com/v1",
    )
    api_key = Column(
        Text,
        doc="加密后存储的 API 密钥，使用 core.crypto.encrypt_secret 加密",
    )
    model_id = Column(
        String(200),
        nullable=False,
        doc="具体模型 ID/名称，如 gpt-4o-mini、qwen-plus 等",
    )
    temperature = Column(
        Float,
        default=0.7,
        doc="采样温度，0~2 之间，值越大随机性越高",
    )
    max_tokens = Column(
        Integer,
        default=0,
        doc="最大生成长度（token 数），0 表示使用模型默认值",
    )
    is_default = Column(
        Boolean,
        default=False,
        doc="是否为当前系统默认模型，同一时间仅一个为 True",
    )
    status = Column(
        Integer,
        default=1,
        doc="状态：1=启用，2=禁用",
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        doc="创建时间，数据库服务器时间",
    )


class Skill(Base):
    """技能定义：描述一个可被 LLM 调用的工具/能力，包括代码路径和参数 Schema。"""

    __tablename__ = "skills"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        doc="主键 ID，自增",
    )
    name = Column(
        String(100),
        unique=True,
        nullable=False,
        doc="技能名称（英文），全局唯一，作为 LLM function calling 的 function.name",
    )
    description = Column(
        Text,
        doc="技能详细描述，告诉 LLM 该技能能做什么，何时调用",
    )
    code_path = Column(
        String(500),
        nullable=True,
        doc="自定义技能代码文件路径，指向可执行的 Python 函数；内置技能可为空",
    )
    parameters_schema = Column(
        JSON,
        nullable=True,
        doc="参数 Schema（JSON），符合 OpenAI function calling 的 parameters 格式",
    )
    enabled = Column(
        Boolean,
        default=True,
        doc="是否启用该技能，禁用后不会出现在 tools 列表中",
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        doc="创建时间，数据库服务器时间",
    )


class SkillBinding(Base):
    """技能绑定：将某个技能绑定到具体员工（用户），实现技能的人员级权限控制。"""

    __tablename__ = "skill_bindings"
    __table_args__ = (
        UniqueConstraint("employee_id", "skill_id", name="uq_employee_skill"),
    )

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        doc="主键 ID，自增",
    )
    employee_id = Column(
        Integer,
        nullable=False,
        doc="员工 ID（对应 users.id），被绑定技能的用户",
    )
    skill_id = Column(
        Integer,
        nullable=False,
        doc="技能 ID（对应 skills.id），被绑定的技能",
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        doc="绑定创建时间，数据库服务器时间",
    )
