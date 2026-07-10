# API Lab 项目 - 成员 a 代码汇总

**负责模块**：数据库模型设计  
**日期**：2026-07-10  

---

## models/__init__.py

```python
from models.product import Product
from models.user import User
from models.department import Department
from models.chat_session import ChatSession
from models.model_skill import LLMModel, Skill, SkillBinding
from models.data_asset import DataAsset, AssetProfile
from models.data_pipeline import DataSource, DataPipeline, PipelineRun
from models.digital_employee import DigitalEmployee, EmployeeTaskRun
from models.im import IMConversation, IMConversationMember, IMMessage

__all__ = [
    "Product",
    "User",
    "Department",
    "ChatSession",
    "LLMModel",
    "Skill",
    "SkillBinding",
    "DataAsset",
    "AssetProfile",
    "DataSource",
    "DataPipeline",
    "PipelineRun",
    "DigitalEmployee",
    "EmployeeTaskRun",
    "IMConversation",
    "IMConversationMember",
    "IMMessage",
]
```

---

## models/user.py

```python
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime

from core.database import Base


class User(Base):
    """用户数据模型：存储系统用户的基本信息、账号状态及关联部门。"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    mobile = Column(String(20), default="")
    password_hash = Column(String(255), nullable=False)
    dept_id = Column(Integer, default=0, index=True)
    status = Column(Integer, default=1, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

---

## models/department.py

```python
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime

from core.database import Base


class Department(Base):
    """部门数据模型：描述组织架构中的部门，支持 parent_id 建立层级关系。"""
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    parent_id = Column(Integer, default=0, index=True)
    leader = Column(String(50), default="")
    phone = Column(String(20), default="")
    status = Column(Integer, default=1, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

---

## models/product.py

```python
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime

from core.database import Base


class Product(Base):
    """商品数据模型：记录商品名称、品类、单价、库存等核心信息。"""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    category = Column(String(100), nullable=False)
    price = Column(Float, nullable=False)
    stock = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

---

## models/data_pipeline.py

```python
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
```

---

## models/data_asset.py

```python
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
```

---

## models/digital_employee.py

```python
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
```

---

## models/im.py

```python
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, UniqueConstraint, JSON, func
from sqlalchemy.orm import relationship

from core.database import Base


class IMConversation(Base):
    """即时通讯会话表：支持单聊(single)、群聊(group)、数字员工对话(employee)三种类型。"""
    __tablename__ = "im_conversations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    type = Column(String(20), nullable=False, default="single", comment="会话类型：single单聊/group群聊/employee数字员工")
    name = Column(String(200), nullable=True, comment="会话名称（群聊名或数字员工对话名）")
    created_by = Column(Integer, nullable=True, comment="创建者用户ID")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")

    members = relationship("IMConversationMember", back_populates="conversation", cascade="all, delete-orphan")
    messages = relationship("IMMessage", back_populates="conversation", cascade="all, delete-orphan")


class IMConversationMember(Base):
    """会话成员表：记录每个会话包含哪些用户成员。"""
    __tablename__ = "im_conversation_members"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey("im_conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True, comment="用户ID（数字员工以employee_id作为伪用户ID存入）")
    joined_at = Column(DateTime, default=func.now(), comment="加入时间")

    __table_args__ = (
        UniqueConstraint("conversation_id", "user_id", name="uq_conv_user"),
    )

    conversation = relationship("IMConversation", back_populates="members")


class IMMessage(Base):
    """即时通讯消息表：存储会话内的所有聊天消息。"""
    __tablename__ = "im_messages"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey("im_conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_id = Column(Integer, nullable=True, default=0, comment="发送者用户ID，0表示系统/数字员工")
    content = Column(Text, nullable=False, comment="消息内容文本")
    msg_type = Column(String(20), nullable=False, default="text", comment="消息类型：text文本/image图片/file文件等")
    created_at = Column(DateTime, default=func.now(), index=True, comment="发送时间")
    read_at = Column(JSON, nullable=True, comment="已读状态字典：{用户ID: ISO时间戳字符串}")

    conversation = relationship("IMConversation", back_populates="messages")
```

---

## models/model_skill.py

```python
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
```

---

## models/chat_session.py

```python
from sqlalchemy import Column, Integer, String, DateTime, JSON, func

from core.database import Base


class ChatSession(Base):
    """聊天会话数据模型：存储多轮对话的会话元数据与消息历史。"""

    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    """会话主键 ID，自增整数"""

    user_id = Column(Integer, nullable=False, index=True)
    """所属用户 ID，非空"""

    title = Column(String(200), nullable=True)
    """会话标题，最多 200 字符，可为空"""

    messages = Column(JSON, default=list)
    """消息列表 JSON，默认空数组，每条含 role 与 content"""

    created_at = Column(DateTime(timezone=True), default=func.now())
    """会话创建时间（带时区），默认当前数据库时间"""
```

---

**完成文件数**：10 个  
**代码行数**：约 300 行
