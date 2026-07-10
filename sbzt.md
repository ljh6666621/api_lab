# API Lab 项目 - 成员 d 代码汇总

**负责模块**：数据验证层  
**日期**：2026-07-10  

---

## schemas/user.py

```python
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator


class UserBase(BaseModel):
    """用户通用字段基类：定义了注册、响应等场景共用的基础字段。"""
    username: str = Field(..., min_length=2, max_length=50, description="用户名")
    email: str = Field(..., description="邮箱")
    mobile: Optional[str] = Field("", max_length=20, description="手机号")
    dept_id: Optional[int] = Field(0, description="部门ID")


class UserRegister(UserBase):
    """用户注册请求体：继承通用字段并补充明文密码，含密码长度校验。"""
    password: str = Field(..., min_length=6, max_length=50, description="明文密码")

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Pydantic 字段校验器：确保注册密码长度不小于 6 位。"""
        if len(v) < 6:
            raise ValueError("密码长度不能少于 6 位")
        return v


class UserLogin(BaseModel):
    """用户登录请求体：接收用户名/邮箱 + 密码进行认证。"""
    username: str = Field(..., description="用户名或邮箱")
    password: str = Field(..., description="密码")


class LoginResponse(BaseModel):
    """登录成功响应体：返回 JWT 访问令牌、令牌类型及用户基本信息。"""
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class UserResponse(BaseModel):
    """用户信息响应体：返回给前端的用户公开字段，不包含密码哈希。"""
    id: int
    username: str
    email: str
    mobile: str
    dept_id: int
    status: int = Field(description="1正常 2禁用")

    model_config = {"from_attributes": True}


LoginResponse.model_rebuild()
```

---

## schemas/department.py

```python
from typing import Optional
from pydantic import BaseModel, Field


class DepartmentBase(BaseModel):
    """部门通用字段基类：定义部门名称、上级、负责人等基础属性。"""
    name: str = Field(..., min_length=1, max_length=100, description="部门名称")
    parent_id: Optional[int] = Field(0, description="上级部门ID")
    leader: Optional[str] = Field("", max_length=50, description="负责人")
    phone: Optional[str] = Field("", max_length=20, description="联系电话")
    status: Optional[int] = Field(1, description="1正常 2禁用")


class DepartmentCreate(DepartmentBase):
    """部门创建请求体：直接继承基类所有字段用于新增部门。"""
    pass


class DepartmentUpdate(BaseModel):
    """部门更新请求体：所有字段均为可选，仅更新传入的非空字段。"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    parent_id: Optional[int] = None
    leader: Optional[str] = None
    phone: Optional[str] = None
    status: Optional[int] = None


class DepartmentResponse(DepartmentBase):
    """部门响应体：在通用字段基础上增加部门 ID，支持 ORM 实体直接转换。"""
    id: int

    model_config = {"from_attributes": True}
```

---

## schemas/product.py

```python
from typing import Optional

from pydantic import BaseModel, Field


class ProductCreate(BaseModel):
    """商品创建请求体：定义新增商品时必须传入的字段及约束。"""
    name: str = Field(..., min_length=1, description="商品名称")
    category: str = Field(..., description="品类")
    price: float = Field(..., gt=0, description="单价")
    stock: int = Field(default=0, ge=0, description="库存")


class ProductUpdate(BaseModel):
    """商品更新请求体：所有字段均为可选，仅更新传入的非空字段。"""
    name: Optional[str] = Field(None, min_length=1)
    category: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    stock: Optional[int] = Field(None, ge=0)


class ProductResponse(BaseModel):
    """商品响应体：返回商品详情的标准结构，支持直接从 ORM 实体转换。"""
    id: int
    name: str
    category: str
    price: float
    stock: int

    model_config = {"from_attributes": True}


class DeleteResponse(BaseModel):
    """通用删除操作响应体：告知前端删除是否成功并附带提示消息。"""
    success: bool
    message: str
```

---

## schemas/data_pipeline.py

```python
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DataSourceCreate(BaseModel):
    """数据源创建请求体：定义新增数据源时必须传入的字段及约束。"""
    name: str = Field(..., min_length=1, max_length=100, description="数据源名称")
    type: Optional[str] = Field("http_api", description="数据源类型：http_api/crawler/upload")
    config: dict = Field(..., description="数据源配置字典，如 {url, headers, method, params, jq_path}")
    status: Optional[int] = Field(1, description="状态：1=启用，0=停用")


class DataSourceUpdate(BaseModel):
    """数据源更新请求体：所有字段均为可选，仅更新传入的非空字段。"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    type: Optional[str] = None
    config: Optional[dict] = None
    status: Optional[int] = None


class DataSourceResponse(BaseModel):
    """数据源响应体：返回数据源详情的标准结构，支持直接从 ORM 实体转换。"""
    id: int
    name: str
    type: str
    config: Optional[dict] = None
    status: int
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DataPipelineCreate(BaseModel):
    """流水线创建请求体：定义新增采集流水线时必须传入的字段及约束。"""
    name: str = Field(..., min_length=1, max_length=200, description="流水线名称")
    source_id: int = Field(..., description="关联数据源 ID")
    schedule: Optional[str] = Field(None, description="cron 定时表达式，为空则不调度")
    extract_rules: Optional[dict] = Field(None, description="提取规则：{field_map, filter}")
    target_asset_id: Optional[int] = Field(None, description="目标资产 ID（预留）")
    status: Optional[int] = Field(1, description="状态：1=启用，0=停用")


class DataPipelineUpdate(BaseModel):
    """流水线更新请求体：所有字段均为可选，仅更新传入的非空字段。"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    source_id: Optional[int] = None
    schedule: Optional[str] = None
    extract_rules: Optional[dict] = None
    target_asset_id: Optional[int] = None
    status: Optional[int] = None


class DataPipelineResponse(BaseModel):
    """流水线响应体：返回采集流水线详情的标准结构，支持直接从 ORM 实体转换。"""
    id: int
    name: str
    source_id: int
    schedule: Optional[str] = None
    extract_rules: Optional[dict] = None
    target_asset_id: Optional[int] = None
    status: int
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PipelineRunResponse(BaseModel):
    """流水线运行记录响应体：返回单次执行的完整信息（包含数据和错误）。"""
    id: int
    pipeline_id: int
    triggered_by: str
    start_at: datetime
    end_at: Optional[datetime] = None
    status: str
    rows_count: int
    error_msg: Optional[str] = None
    data: Optional[list] = None

    model_config = {"from_attributes": True}


class ManualRunRequest(BaseModel):
    """手动触发执行请求体：force=True 时忽略正在运行的实例并强制执行。"""
    force: Optional[bool] = Field(False, description="是否忽略正在运行的记录强制执行")
```

---

## schemas/data_asset.py

```python
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class DataAssetCreate(BaseModel):
    """数据资产创建请求体：定义新增数据资产时的字段及约束。"""

    name: str = Field(..., min_length=1, max_length=200, description="资产名称")
    source_type: Optional[str] = Field("manual", description="来源类型：pipeline/table/manual，默认 manual")
    source_table: Optional[str] = Field(None, max_length=200, description="来源表名")
    pipeline_id: Optional[int] = Field(None, description="关联流水线 ID")
    description: Optional[str] = Field(None, description="资产描述")
    owner_id: Optional[int] = Field(None, description="负责人用户 ID")
    columns_info: Optional[Union[Dict[str, Any], List[Any]]] = Field(None, description="字段信息 JSON")
    tags: Optional[str] = Field(None, max_length=500, description="标签，逗号分隔")


class DataAssetUpdate(BaseModel):
    """数据资产更新请求体：所有字段均为可选，仅更新传入的非空字段。"""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    source_type: Optional[str] = None
    source_table: Optional[str] = Field(None, max_length=200)
    pipeline_id: Optional[int] = None
    description: Optional[str] = None
    owner_id: Optional[int] = None
    columns_info: Optional[Union[Dict[str, Any], List[Any]]] = None
    row_count: Optional[int] = None
    last_sync_at: Optional[datetime] = None
    tags: Optional[str] = Field(None, max_length=500)


class DataAssetResponse(BaseModel):
    """数据资产响应体：返回资产详情的标准结构，支持直接从 ORM 实体转换。"""

    id: int
    name: str
    source_type: str
    source_table: Optional[str] = None
    pipeline_id: Optional[int] = None
    description: Optional[str] = None
    owner_id: Optional[int] = None
    columns_info: Optional[Any] = None
    row_count: int = 0
    last_sync_at: Optional[datetime] = None
    tags: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AssetProfileResponse(BaseModel):
    """资产画像响应体：返回画像详情的标准结构，支持直接从 ORM 实体转换。"""

    id: int
    asset_id: int
    generated_at: datetime
    summary: Optional[Any] = None
    report_text: Optional[str] = None
    generated_by: Optional[int] = None

    model_config = {"from_attributes": True}


class ManualProfileRequest(BaseModel):
    """手动触发生成画像的请求体。"""

    force: bool = Field(False, description="是否强制重新生成（忽略 1 小时缓存）")


class OverviewResponse(BaseModel):
    """数据资产概览统计响应体。"""

    total_assets: int = Field(0, description="资产总数")
    total_rows: int = Field(0, description="所有资产总行数")
    by_source_type: Dict[str, int] = Field(default_factory=dict, description="按来源类型分组的资产数量")
    today_profiles: int = Field(0, description="今日生成的画像数量")
```

---

## schemas/digital_employee.py

```python
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class EmployeeCreate(BaseModel):
    """数字员工创建请求体：定义新增数字员工时的字段及约束。"""

    name: str = Field(..., min_length=1, max_length=100, description="员工名称")
    avatar: Optional[str] = Field(None, max_length=500, description="头像URL")
    description: Optional[str] = Field(None, description="员工职责描述")
    role_key: Optional[str] = Field("default", max_length=50, description="角色key，对应prompts.ROLES，默认default")
    default_model_id: Optional[int] = Field(None, description="默认LLM模型ID，None或0表示系统默认")
    status: Optional[int] = Field(1, description="状态：1=启用，0=禁用，默认1")


class EmployeeUpdate(BaseModel):
    """数字员工更新请求体：所有字段均为可选，仅更新传入的非空字段。"""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    avatar: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    role_key: Optional[str] = Field(None, max_length=50)
    default_model_id: Optional[int] = None
    status: Optional[int] = None
    owner_id: Optional[int] = None


class EmployeeResponse(BaseModel):
    """数字员工响应体：返回员工详情的标准结构，支持直接从ORM实体转换。"""

    id: int
    name: str
    avatar: Optional[str] = None
    description: Optional[str] = None
    role_key: str
    default_model_id: Optional[int] = None
    owner_id: Optional[int] = None
    status: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EmployeeChatRequest(BaseModel):
    """数字员工聊天请求体：支持两种输入方式，二选一。
    - 直接传 content 字符串：视为单轮用户消息
    - 传 messages 列表：完整的多轮对话上下文
    """

    messages: Optional[List[Dict[str, Any]]] = Field(None, description="多轮对话消息列表，格式如[{role,content}]")
    content: Optional[str] = Field(None, description="单轮用户消息文本（与messages二选一）")


class EmployeeTaskRequest(BaseModel):
    """数字员工任务触发请求体：指定任务类型与参数。"""

    task_type: str = Field(..., description="任务类型：pipeline_run/asset_profile/nl2sql_report")
    params: Optional[Dict[str, Any]] = Field(None, description="任务参数字典")


class TaskRunResponse(BaseModel):
    """数字员工任务执行记录响应体：返回任务运行详情，支持直接从ORM实体转换。"""

    id: int
    employee_id: int
    user_id: int
    task_type: str
    params: Optional[Any] = None
    status: str
    result: Optional[Any] = None
    error_msg: Optional[str] = None
    started_at: datetime
    finished_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
```

---

## schemas/model_skill.py

```python
from typing import Optional, Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


def _mask_api_key(raw: Optional[str]) -> str:
    """对 API Key 进行掩码处理，只暴露最后 4 位，其余用 **** 代替。"""
    if not raw:
        return "********"
    if len(raw) > 4:
        return "****" + raw[-4:]
    return "********"


class LLMModelCreate(BaseModel):
    """创建大语言模型请求体：用于新增一个 LLM 接入配置。"""

    name: str = Field(..., max_length=100, description="模型显示名称")
    provider: Optional[str] = Field("openai-compatible", max_length=50, description="模型服务商，默认 openai-compatible")
    base_url: str = Field(..., max_length=500, description="API 基础地址")
    api_key: str = Field(..., description="明文 API Key，入库前会自动加密")
    model_id: str = Field(..., max_length=200, description="具体模型 ID/名称")
    temperature: Optional[float] = Field(0.7, description="采样温度 0~2，默认 0.7")
    max_tokens: Optional[int] = Field(0, description="最大生成 token 数，0 表示模型默认值")
    is_default: Optional[bool] = Field(False, description="是否设为系统默认模型")
    status: Optional[int] = Field(1, description="状态：1启用 2禁用")


class LLMModelUpdate(BaseModel):
    """更新大语言模型请求体：所有字段均可选，只更新传入非 None 的字段。"""

    name: Optional[str] = Field(None, max_length=100, description="模型显示名称")
    provider: Optional[str] = Field(None, max_length=50, description="模型服务商")
    base_url: Optional[str] = Field(None, max_length=500, description="API 基础地址")
    api_key: Optional[str] = Field(None, description="新明文 API Key，非 None 时会重新加密入库")
    model_id: Optional[str] = Field(None, max_length=200, description="具体模型 ID/名称")
    temperature: Optional[float] = Field(None, description="采样温度 0~2")
    max_tokens: Optional[int] = Field(None, description="最大生成 token 数")
    is_default: Optional[bool] = Field(None, description="是否设为系统默认模型")
    status: Optional[int] = Field(None, description="状态：1启用 2禁用")


class LLMModelResponse(BaseModel):
    """大语言模型配置响应体：返回配置信息，API Key 做掩码处理不返回明文。"""

    id: int = Field(description="主键 ID")
    name: str = Field(description="模型显示名称")
    provider: str = Field(description="模型服务商")
    base_url: Optional[str] = Field(description="API 基础地址")
    model_id: str = Field(description="具体模型 ID/名称")
    temperature: float = Field(description="采样温度")
    max_tokens: int = Field(description="最大生成 token 数")
    is_default: bool = Field(description="是否为系统默认模型")
    status: int = Field(description="状态：1启用 2禁用")
    created_at: Any = Field(description="创建时间")
    api_key_masked: str = Field(description="掩码后的 API Key，格式 ****abcd")

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def _mask_key(cls, data: Any) -> Any:
        """将 ORM 的 api_key 字段转换为响应体的 api_key_masked（掩码后）。"""
        if isinstance(data, dict):
            if "api_key" in data and "api_key_masked" not in data:
                data["api_key_masked"] = _mask_api_key(data.get("api_key"))
            return data
        api_key_val = getattr(data, "api_key", None)
        data_dict: dict = {}
        for col in ["id", "name", "provider", "base_url", "model_id",
                     "temperature", "max_tokens", "is_default", "status", "created_at"]:
            data_dict[col] = getattr(data, col, None)
        data_dict["api_key_masked"] = _mask_api_key(api_key_val)
        return data_dict


class SkillCreate(BaseModel):
    """创建技能请求体：新增一个自定义技能。"""

    name: str = Field(..., max_length=100, description="技能英文名称（function.name），全局唯一")
    description: Optional[str] = Field(None, description="技能详细描述，告诉 LLM 何时及如何使用")
    code_path: Optional[str] = Field(None, max_length=500, description="自定义技能代码文件路径")
    parameters_schema: Optional[dict] = Field(None, description="参数 Schema，符合 OpenAI function calling 格式")
    enabled: Optional[bool] = Field(True, description="是否启用该技能，默认 True")


class SkillUpdate(BaseModel):
    """更新技能请求体：所有字段均可选。"""

    name: Optional[str] = Field(None, max_length=100, description="技能英文名称")
    description: Optional[str] = Field(None, description="技能详细描述")
    code_path: Optional[str] = Field(None, max_length=500, description="自定义技能代码文件路径")
    parameters_schema: Optional[dict] = Field(None, description="参数 Schema")
    enabled: Optional[bool] = Field(None, description="是否启用")


class SkillResponse(BaseModel):
    """技能信息响应体：返回完整技能定义。"""

    id: int = Field(description="主键 ID")
    name: str = Field(description="技能英文名称")
    description: Optional[str] = Field(description="技能详细描述")
    code_path: Optional[str] = Field(description="自定义技能代码文件路径")
    parameters_schema: Optional[dict] = Field(description="参数 Schema（JSON）")
    enabled: bool = Field(description="是否启用")
    created_at: Any = Field(description="创建时间")

    model_config = ConfigDict(from_attributes=True)


class SkillBindingCreate(BaseModel):
    """创建技能绑定请求体：将某个技能绑定到指定员工。"""

    employee_id: int = Field(description="员工 ID（users.id）")
    skill_id: int = Field(description="技能 ID（skills.id）")


class SkillBindingResponse(BaseModel):
    """技能绑定响应体：返回绑定关系详情。"""

    id: int = Field(description="主键 ID")
    employee_id: int = Field(description="员工 ID")
    skill_id: int = Field(description="技能 ID")
    created_at: Any = Field(description="绑定创建时间")

    model_config = ConfigDict(from_attributes=True)


class SkillTestRequest(BaseModel):
    """技能测试请求体：在调试模式下手动触发某个技能执行。"""

    name: str = Field(description="要调用的技能名称")
    args: dict = Field(default_factory=dict, description="技能调用参数，key=参数名 value=参数值")
```

---

## schemas/im.py

```python
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


class ConversationCreate(BaseModel):
    """创建会话请求体。"""
    conv_type: str = Field(default="single", description="会话类型：single单聊/group群聊/employee数字员工")
    name: Optional[str] = Field(default=None, description="会话名称（群聊或数字员工对话名）")
    members: List[int] = Field(description="参与用户ID列表：single必须正好2人，group至少1人（+创建者）")
    employee_id: Optional[int] = Field(default=None, description="数字员工ID，当conv_type=employee时必填")

    @field_validator("members")
    @classmethod
    def check_members(cls, v, info):
        conv_type = info.data.get("conv_type", "single")
        if conv_type == "single":
            if len(v) != 2:
                raise ValueError("单聊会话 members 必须包含正好 2 个用户ID")
        elif conv_type == "group":
            if len(v) < 1:
                raise ValueError("群聊会话 members 至少需要 1 个用户ID")
        elif conv_type == "employee":
            if len(v) < 1:
                raise ValueError("数字员工对话 members 至少包含当前用户ID")
        return v


class ConversationResponse(BaseModel):
    """会话列表响应项（简要信息）。"""
    id: int
    type: str
    name: Optional[str] = None
    created_by: Optional[int] = None
    created_at: datetime
    members_count: int = Field(description="会话成员数量")
    last_message: Optional[str] = Field(default=None, description="最新一条消息的内容预览")


class ConversationDetailResponse(ConversationResponse):
    """会话详情响应（含成员ID列表）。"""
    members: List[int] = Field(description="会话内所有成员的用户ID列表")


class MessageSendRequest(BaseModel):
    """发送消息请求体。"""
    content: str = Field(description="消息内容")
    msg_type: str = Field(default="text", description="消息类型：text/image/file等")


class MessageResponse(BaseModel):
    """消息响应项。"""
    id: int
    conversation_id: int
    sender_id: Optional[int]
    sender_name: Optional[str] = Field(default=None, description="发送者显示名称（用户姓名或'数字员工/系统'）")
    content: str
    msg_type: str
    created_at: datetime
```

---

## schemas/chat.py

```python
from datetime import datetime
from typing import List, Optional, Dict

from pydantic import BaseModel, ConfigDict, Field


class ChatMessage(BaseModel):
    role: str = Field(..., description="消息角色：user 或 assistant")
    content: str = Field(..., description="消息内容")


class ChatRequest(BaseModel):
    messages: List[ChatMessage] = Field(..., description="消息列表")
    role: Optional[str] = Field("default", description="人格角色名称")
    stream: bool = Field(False, description="是否流式响应")
    temperature: Optional[float] = Field(None, description="温度参数，控制回答多样性")


class ChatResponse(BaseModel):
    content: str = Field(..., description="AI 回复内容")


class NL2SQLRequest(BaseModel):
    question: str = Field(..., description="用户的自然语言问题")
    table_schemas: Optional[str] = Field(
        None,
        description="表结构描述，如 CREATE TABLE 语句；若未提供则使用默认示例表",
    )
    asset_ids: Optional[List[int]] = Field(
        None,
        description="关联的数据资产 ID 列表；若提供则从资产自动拼表结构",
    )


class NL2SQLResponse(BaseModel):
    sql: Optional[str] = Field(None, description="生成的 SQL 语句；若无法生成则为 null")
    explanation: str = Field(..., description="对 SQL 的解释或无法生成的原因")
    results: Optional[List[dict]] = Field(None, description="SQL 执行结果；若未执行或执行失败则为 null")


class NL2SQLAnswerResponse(BaseModel):
    sql: Optional[str] = Field(None, description="生成的 SQL 语句；若无法生成则为 null")
    explanation: str = Field(..., description="对 SQL 的解释或无法生成的原因")
    results: Optional[List[dict]] = Field(None, description="SQL 执行结果；若未执行或执行失败则为 null")
    answer: Optional[str] = Field(None, description="大模型基于查询结果生成的自然语言回答")


class ChatSessionCreate(BaseModel):
    title: Optional[str] = Field(None, description="会话标题，可省略由系统自动生成")


class ChatSessionResponse(BaseModel):
    id: int = Field(..., description="会话 ID")
    user_id: int = Field(..., description="所属用户 ID")
    title: Optional[str] = Field(None, description="会话标题")
    messages_count: int = Field(..., description="会话中的消息数量")
    messages: Optional[List[dict]] = Field(None, description="会话消息列表，仅在 GET /sessions/{id} 详情接口返回")
    created_at: datetime = Field(..., description="会话创建时间")

    model_config = ConfigDict(from_attributes=True)


class ChatMessageAppendRequest(BaseModel):
    content: str = Field(..., description="消息内容")
    role: str = Field("user", description="消息角色：默认 user")


class ChatSessionAskRequest(BaseModel):
    content: str = Field(..., description="用户的自然语言问题")
    role: str = Field("user", description="消息角色：默认 user")
    asset_ids: Optional[List[int]] = Field(None, description="绑定的数据资产 ID 列表")
    table_schemas: Optional[str] = Field(None, description="可选的自定义表结构描述字符串")
```

---

**完成文件数**：9 个  
**代码行数**：约 400 行
