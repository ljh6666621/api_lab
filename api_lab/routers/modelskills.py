from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from core.database import get_db
from core.security import get_current_user
from models import model_skill as model_orm
from models.user import User
from schemas.model_skill import (
    LLMModelCreate,
    LLMModelUpdate,
    LLMModelResponse,
    SkillCreate,
    SkillUpdate,
    SkillResponse,
    SkillBindingCreate,
    SkillBindingResponse,
    SkillTestRequest,
)
from services.model_skill import ModelRepository, SkillRepository, SkillEngine

router = APIRouter(prefix="/modelskills", tags=["模型与技能管理"])


@router.post("/models", response_model=LLMModelResponse, status_code=status.HTTP_201_CREATED)
def create_model(
    body: LLMModelCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    新增大语言模型配置接口（需登录）。
    若设置 is_default=True，会自动把其他模型重置为非默认，确保同一时间只有一个默认模型。
    API Key 在入库前会进行 Fernet 对称加密，不存储明文。
    """
    model = ModelRepository.create(db, body)
    return model


@router.get("/models", response_model=dict)
def list_models(
    skip: int = Query(0, ge=0, description="分页偏移量，从 0 开始"),
    limit: int = Query(100, ge=1, le=500, description="每页条数"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    大语言模型配置列表接口（需登录）。
    返回总数与分页明细，API Key 返回掩码后格式（****xxxx），不暴露明文或密文。
    """
    models = ModelRepository.list(db, skip=skip, limit=limit)
    return {
        "total": len(models),
        "items": [LLMModelResponse.model_validate(m) for m in models],
    }


@router.get("/models/{model_id}", response_model=LLMModelResponse)
def get_model(
    model_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取单个大语言模型配置详情（需登录）。
    若指定 ID 的模型不存在，返回 HTTP 404。
    """
    model = ModelRepository.get(db, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="指定的 LLM 模型不存在")
    return model


@router.put("/models/{model_id}", response_model=LLMModelResponse)
def update_model(
    model_id: int,
    body: LLMModelUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    更新大语言模型配置接口（需登录）。
    只更新请求体中显式传的字段（非 None），若更新 api_key 则会重新加密存储。
    模型不存在返回 404。
    """
    model = ModelRepository.update(db, model_id, body)
    if not model:
        raise HTTPException(status_code=404, detail="指定的 LLM 模型不存在")
    return model


@router.delete("/models/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_model(
    model_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    删除大语言模型配置接口（需登录）。
    成功删除返回 204 无内容，模型不存在返回 404。
    """
    ok = ModelRepository.delete(db, model_id)
    if not ok:
        raise HTTPException(status_code=404, detail="指定的 LLM 模型不存在")


@router.post("/skills", response_model=SkillResponse, status_code=status.HTTP_201_CREATED)
def create_skill(
    body: SkillCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    新增自定义技能接口（需登录）。
    技能名称（name）在数据库中唯一，重复插入会报唯一键冲突。
    parameters_schema 为符合 OpenAI function calling 的 JSON 对象。
    """
    existing = db.query(model_orm.Skill).filter(model_orm.Skill.name == body.name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"技能名称 {body.name} 已存在")
    skill = SkillRepository.create(db, body)
    return skill


@router.get("/skills", response_model=dict)
def list_skills(
    skip: int = Query(0, ge=0, description="分页偏移量"),
    limit: int = Query(100, ge=1, le=500, description="每页条数"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    自定义技能列表接口（需登录）。
    返回总条数与分页明细，仅包含用户自定义的技能（不包含内置技能）。
    """
    skills = SkillRepository.list(db, skip=skip, limit=limit)
    return {
        "total": len(skills),
        "items": [SkillResponse.model_validate(s) for s in skills],
    }


@router.get("/skills/builtins", response_model=dict)
def list_builtin_skills(
    current_user: User = Depends(get_current_user),
):
    """
    内置技能列表接口（需登录）。
    返回平台预先集成的 4 个内置技能：
    run_nl2sql（自然语言转 SQL）、run_pipeline（执行流水线）、
    gen_asset_profile（生成资产画像）、query_user（搜索用户）。
    """
    builtins = SkillRepository.list_builtin()
    return {"total": len(builtins), "items": builtins}


@router.get("/skills/{skill_id}", response_model=SkillResponse)
def get_skill(
    skill_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取单个自定义技能详情（需登录）。
    技能不存在返回 404。
    """
    skill = SkillRepository.get(db, skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="指定的技能不存在")
    return skill


@router.put("/skills/{skill_id}", response_model=SkillResponse)
def update_skill(
    skill_id: int,
    body: SkillUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    更新自定义技能接口（需登录）。
    只更新请求体中显式传的字段（非 None），技能不存在返回 404。
    """
    if body.name is not None:
        conflict = (
            db.query(model_orm.Skill)
            .filter(model_orm.Skill.name == body.name, model_orm.Skill.id != skill_id)
            .first()
        )
        if conflict:
            raise HTTPException(status_code=400, detail=f"技能名称 {body.name} 已被占用")
    skill = SkillRepository.update(db, skill_id, body)
    if not skill:
        raise HTTPException(status_code=404, detail="指定的技能不存在")
    return skill


@router.delete("/skills/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_skill(
    skill_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    删除自定义技能接口（需登录）。
    成功删除返回 204 无内容，技能不存在返回 404。
    """
    ok = SkillRepository.delete(db, skill_id)
    if not ok:
        raise HTTPException(status_code=404, detail="指定的技能不存在")


@router.post("/skills/test", response_model=dict)
def test_skill(
    body: SkillTestRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    技能测试/手动调用接口（需登录）。
    传入技能名称与参数字典，引擎按优先级调用内置技能或自定义技能，返回执行结果 JSON。
    常用于调试 LLM function calling 效果，或后台手动触发某个技能。
    """
    result = SkillEngine.call_skill(db, body.name, body.args)
    return result


@router.post("/bindings", response_model=SkillBindingResponse, status_code=status.HTTP_201_CREATED)
def create_binding(
    body: SkillBindingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    新增员工-技能绑定接口（需登录）。
    将指定自定义技能绑定到指定员工 ID，员工在对话时即可在 tools 中看到该技能。
    同一 employee_id + skill_id 组合全局唯一（数据库唯一约束）。
    员工或技能不存在返回 400。
    """
    employee = db.query(User).filter(User.id == body.employee_id).first()
    if not employee:
        raise HTTPException(status_code=400, detail="指定的员工不存在")
    skill = SkillRepository.get(db, body.skill_id)
    if not skill:
        raise HTTPException(status_code=400, detail="指定的技能不存在")
    existing = (
        db.query(model_orm.SkillBinding)
        .filter(
            model_orm.SkillBinding.employee_id == body.employee_id,
            model_orm.SkillBinding.skill_id == body.skill_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="该员工与技能的绑定关系已存在")
    binding = model_orm.SkillBinding(
        employee_id=body.employee_id,
        skill_id=body.skill_id,
    )
    db.add(binding)
    db.commit()
    db.refresh(binding)
    return binding


@router.get("/bindings", response_model=dict)
def list_bindings(
    employee_id: Optional[int] = Query(None, ge=1, description="可选，按员工 ID 过滤绑定列表"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    技能绑定列表接口（需登录）。
    可传 employee_id 过滤指定员工拥有的绑定；不传则返回全量绑定。
    返回总条数与绑定明细列表。
    """
    query = db.query(model_orm.SkillBinding)
    if employee_id is not None:
        query = query.filter(model_orm.SkillBinding.employee_id == employee_id)
    bindings = query.order_by(model_orm.SkillBinding.id).all()
    return {
        "total": len(bindings),
        "items": [SkillBindingResponse.model_validate(b) for b in bindings],
    }


@router.delete("/bindings/{binding_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_binding(
    binding_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    删除员工-技能绑定接口（需登录）。
    按绑定 ID 删除，成功返回 204，不存在返回 404。
    """
    binding = (
        db.query(model_orm.SkillBinding)
        .filter(model_orm.SkillBinding.id == binding_id)
        .first()
    )
    if not binding:
        raise HTTPException(status_code=404, detail="指定的技能绑定不存在")
    db.delete(binding)
    db.commit()
