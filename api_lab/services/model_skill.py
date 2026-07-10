from typing import Optional, Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from core.config import DEFAULT_MODEL_ID
from core.crypto import encrypt_secret, decrypt_secret
from core.database import SessionLocal, get_db
from models import model_skill as model_orm
from models.user import User
from schemas import model_skill as schema


def _extract_value(args: dict, key: str, default: Any = None) -> Any:
    """从 args 字典中安全提取值，支持多种键名风格。"""
    if key in args:
        return args[key]
    for k, v in args.items():
        if k.lower() == key.lower():
            return v
    return default


def _run_nl2sql(db: Session, args: dict) -> dict:
    """内置技能执行函数：自然语言转 SQL 并返回查询结果与总结。"""
    from services.llm_service import generate_nl2sql_with_answer

    try:
        question = str(_extract_value(args, "question", ""))
        if not question:
            return {"ok": False, "error": "缺少 question 参数"}
        result = generate_nl2sql_with_answer(content=question)
        return {"ok": True, **result}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _run_pipeline(db: Session, args: dict) -> dict:
    """内置技能执行函数：执行指定 ID 的数据流水线（占位，待 A 模块对接）。"""
    pipeline_id = _extract_value(args, "pipeline_id")
    if pipeline_id is None:
        return {"ok": False, "error": "缺少 pipeline_id 参数"}
    return {"status": "queued", "pipeline_id": pipeline_id}


def _run_gen_asset_profile(db: Session, args: dict) -> dict:
    """内置技能执行函数：生成指定资产的画像信息（占位，未来对接资产画像模块）。"""
    asset_id = _extract_value(args, "asset_id")
    if asset_id is None:
        return {"ok": False, "error": "缺少 asset_id 参数"}
    return {"asset_id": asset_id, "status": "started"}


def _run_query_user(db: Session, args: dict) -> dict:
    """内置技能执行函数：按用户名或邮箱模糊搜索用户列表。"""
    query_str = str(_extract_value(args, "query", ""))
    if not query_str:
        return {"ok": False, "error": "缺少 query 参数"}
    like_pattern = f"%{query_str}%"
    users = (
        db.query(User)
        .filter(or_(User.username.like(like_pattern), User.email.like(like_pattern)))
        .all()
    )
    items = []
    for u in users:
        items.append({
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "mobile": u.mobile,
            "dept_id": u.dept_id,
            "status": u.status,
        })
    return {"ok": True, "total": len(items), "items": items}


class ModelRepository:
    """大语言模型配置仓储：封装 LLMModel 的 CRUD 及配置获取逻辑。"""

    @staticmethod
    def create(db: Session, data: schema.LLMModelCreate) -> model_orm.LLMModel:
        """
        新增 LLM 模型配置。
        若 is_default=True，则先将其他所有模型的 is_default 置为 False，确保唯一默认模型。
        API Key 入库前会通过 encrypt_secret 对称加密。
        """
        if data.is_default:
            db.query(model_orm.LLMModel).update(
                {model_orm.LLMModel.is_default: False},
                synchronize_session=False,
            )
        model = model_orm.LLMModel(
            name=data.name,
            provider=data.provider or "openai-compatible",
            base_url=data.base_url,
            api_key=encrypt_secret(data.api_key),
            model_id=data.model_id,
            temperature=data.temperature if data.temperature is not None else 0.7,
            max_tokens=data.max_tokens if data.max_tokens is not None else 0,
            is_default=bool(data.is_default),
            status=data.status if data.status is not None else 1,
        )
        db.add(model)
        db.commit()
        db.refresh(model)
        return model

    @staticmethod
    def get(db: Session, model_id: int) -> Optional[model_orm.LLMModel]:
        """按主键 ID 查询单个 LLM 模型配置。"""
        return db.query(model_orm.LLMModel).filter(model_orm.LLMModel.id == model_id).first()

    @staticmethod
    def list(db: Session, skip: int = 0, limit: int = 100) -> list[model_orm.LLMModel]:
        """分页查询 LLM 模型配置列表，默认前 100 条。"""
        return (
            db.query(model_orm.LLMModel)
            .order_by(model_orm.LLMModel.id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def update(
        db: Session,
        model_id: int,
        data: schema.LLMModelUpdate,
    ) -> Optional[model_orm.LLMModel]:
        """
        更新 LLM 模型配置，只更新 data 中非 None 的字段。
        若 is_default 被设为 True，则先清除其他模型的默认标记。
        若 api_key 被提供，则重新加密后存储。
        """
        model = ModelRepository.get(db, model_id)
        if not model:
            return None
        if data.is_default:
            db.query(model_orm.LLMModel).filter(model_orm.LLMModel.id != model_id).update(
                {model_orm.LLMModel.is_default: False},
                synchronize_session=False,
            )
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if value is None:
                continue
            if field == "api_key":
                setattr(model, field, encrypt_secret(value))
            else:
                setattr(model, field, value)
        db.commit()
        db.refresh(model)
        return model

    @staticmethod
    def delete(db: Session, model_id: int) -> bool:
        """按 ID 删除 LLM 模型配置，成功返回 True，未找到返回 False。"""
        model = ModelRepository.get(db, model_id)
        if not model:
            return False
        db.delete(model)
        db.commit()
        return True

    @staticmethod
    def get_default(db: Session) -> Optional[model_orm.LLMModel]:
        """
        获取当前系统默认模型。
        优先级：is_default=True 的模型 > 配置项 DEFAULT_MODEL_ID 指定的 ID > 列表第一个。
        全部无结果返回 None。
        """
        default = (
            db.query(model_orm.LLMModel)
            .filter(model_orm.LLMModel.is_default.is_(True))
            .first()
        )
        if default:
            return default
        if DEFAULT_MODEL_ID and DEFAULT_MODEL_ID > 0:
            by_id = (
                db.query(model_orm.LLMModel)
                .filter(model_orm.LLMModel.id == DEFAULT_MODEL_ID)
                .first()
            )
            if by_id:
                return by_id
        all_models = ModelRepository.list(db, skip=0, limit=1)
        return all_models[0] if all_models else None

    @staticmethod
    def get_runtime_config(db: Session, model_id: Optional[int] = None) -> dict:
        """
        获取可直接用于 LLM 调用的运行时配置字典。
        返回字段：base_url, api_key（已解密明文）, model_id, temperature, max_tokens。
        若未找到任何模型配置则返回空字典 {}。
        """
        model: Optional[model_orm.LLMModel] = None
        if model_id:
            model = ModelRepository.get(db, model_id)
        if not model:
            model = ModelRepository.get_default(db)
        if not model:
            return {}
        return {
            "base_url": model.base_url or "",
            "api_key": decrypt_secret(model.api_key) or "",
            "model_id": model.model_id,
            "temperature": model.temperature or 0.7,
            "max_tokens": model.max_tokens or 0,
        }


class SkillRepository:
    """技能仓储：内置技能注册 + 自定义技能（Skill ORM）CRUD。"""

    _BUILTINS: dict[str, dict] = {
        "run_nl2sql": {
            "description": "将用户的自然语言问题转换为 SQL 查询，并执行数据库查询返回结果及自然语言总结。适用于用户问查询类问题。",
            "parameters_schema": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "用户用自然语言描述的查询问题，如'查询销售额最高的前5个产品'",
                    },
                    "asset_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "可选，限定查询的资产/数据表 ID 列表",
                        "default": [],
                    },
                },
                "required": ["question"],
            },
            "callable": _run_nl2sql,
        },
        "run_pipeline": {
            "description": "启动并排队执行一条指定 ID 的数据处理流水线。适用于触发数据清洗、同步、报表生成等后台任务。",
            "parameters_schema": {
                "type": "object",
                "properties": {
                    "pipeline_id": {
                        "type": "integer",
                        "description": "要启动的流水线 ID（整数主键）",
                    },
                },
                "required": ["pipeline_id"],
            },
            "callable": _run_pipeline,
        },
        "gen_asset_profile": {
            "description": "为指定的资产生成或更新画像信息（如标签、统计特征、元数据摘要等），返回任务启动状态。",
            "parameters_schema": {
                "type": "object",
                "properties": {
                    "asset_id": {
                        "type": "integer",
                        "description": "需要生成画像的资产 ID（整数主键）",
                    },
                },
                "required": ["asset_id"],
            },
            "callable": _run_gen_asset_profile,
        },
        "query_user": {
            "description": "在系统用户库中按用户名或邮箱进行模糊搜索，返回匹配到的用户列表，用于找人场景。",
            "parameters_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词，可以是用户名的一部分或邮箱的一部分",
                    },
                },
                "required": ["query"],
            },
            "callable": _run_query_user,
        },
    }

    @staticmethod
    def get_builtin(name: str) -> Optional[dict]:
        """按名称获取内置技能定义，找不到返回 None。"""
        return SkillRepository._BUILTINS.get(name)

    @staticmethod
    def list_builtin() -> list[dict]:
        """列出所有内置技能的元信息（不包含 callable 内部函数引用）。"""
        result = []
        for name, info in SkillRepository._BUILTINS.items():
            result.append({
                "name": name,
                "description": info.get("description", ""),
                "parameters_schema": info.get("parameters_schema"),
            })
        return result

    @staticmethod
    def create(db: Session, data: schema.SkillCreate) -> model_orm.Skill:
        """新增自定义技能入库。"""
        skill = model_orm.Skill(
            name=data.name,
            description=data.description,
            code_path=data.code_path,
            parameters_schema=data.parameters_schema,
            enabled=bool(data.enabled) if data.enabled is not None else True,
        )
        db.add(skill)
        db.commit()
        db.refresh(skill)
        return skill

    @staticmethod
    def get(db: Session, skill_id: int) -> Optional[model_orm.Skill]:
        """按 ID 查询自定义技能。"""
        return db.query(model_orm.Skill).filter(model_orm.Skill.id == skill_id).first()

    @staticmethod
    def list(db: Session, skip: int = 0, limit: int = 100) -> list[model_orm.Skill]:
        """列出所有自定义技能（分页）。"""
        return (
            db.query(model_orm.Skill)
            .order_by(model_orm.Skill.id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def update(
        db: Session,
        skill_id: int,
        data: schema.SkillUpdate,
    ) -> Optional[model_orm.Skill]:
        """更新自定义技能，只更新非 None 字段。"""
        skill = SkillRepository.get(db, skill_id)
        if not skill:
            return None
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if value is None:
                continue
            setattr(skill, field, value)
        db.commit()
        db.refresh(skill)
        return skill

    @staticmethod
    def delete(db: Session, skill_id: int) -> bool:
        """按 ID 删除自定义技能。"""
        skill = SkillRepository.get(db, skill_id)
        if not skill:
            return False
        db.delete(skill)
        db.commit()
        return True


class SkillEngine:
    """技能执行引擎：负责组装 function calling tools 列表与实际调用技能。"""

    @staticmethod
    def build_tools(db: Session, employee_id: Optional[int] = None) -> list[dict]:
        """
        组装 OpenAI function calling 格式的 tools 数组。
        包含：所有 enabled 的内置技能 + 员工绑定的启用中自定义技能。
        返回：[{"type":"function","function":{name, description, parameters}},...]
        """
        tools: list[dict] = []
        for name, info in SkillRepository._BUILTINS.items():
            tools.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": info.get("description", ""),
                    "parameters": info.get("parameters_schema") or {},
                },
            })
        custom_skills_q = db.query(model_orm.Skill).filter(model_orm.Skill.enabled.is_(True))
        if employee_id is not None:
            custom_skills_q = custom_skills_q.join(
                model_orm.SkillBinding,
                model_orm.SkillBinding.skill_id == model_orm.Skill.id,
            ).filter(model_orm.SkillBinding.employee_id == employee_id)
        for skill in custom_skills_q.all():
            tools.append({
                "type": "function",
                "function": {
                    "name": skill.name,
                    "description": skill.description or "",
                    "parameters": skill.parameters_schema or {"type": "object", "properties": {}},
                },
            })
        return tools

    @staticmethod
    def call_skill(db: Session, name: str, args: dict) -> dict:
        """
        按名称调用技能并返回执行结果字典。
        调用优先级：内置技能（_BUILTINS）> 自定义技能（Skill ORM）。
        自定义技能：有 code_path 则返回占位（后续动态加载），无 code_path 则报错。
        未找到返回 {"error":"unknown skill"}。
        """
        builtin = SkillRepository.get_builtin(name)
        if builtin is not None:
            func = builtin["callable"]
            try:
                return func(db, args or {})
            except Exception as e:
                return {"ok": False, "error": str(e)}
        custom = (
            db.query(model_orm.Skill).filter(model_orm.Skill.name == name).first()
        )
        if custom:
            if custom.code_path:
                return {"status": "not_implemented_custom_code", "skill": name, "code_path": custom.code_path}
            return {"error": "custom skill missing code_path"}
        return {"error": "unknown skill"}
