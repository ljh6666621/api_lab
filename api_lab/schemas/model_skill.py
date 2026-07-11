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
