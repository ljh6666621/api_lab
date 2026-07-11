from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import desc
from sqlalchemy.orm import Session

from models.digital_employee import DigitalEmployee, EmployeeTaskRun
from prompts import roles as prompts


class EmployeeRepository:
    """数字员工仓储：封装 DigitalEmployee 模型的 CRUD 与分页查询静态方法。"""

    @staticmethod
    def create(db: Session, data: Dict[str, Any]) -> DigitalEmployee:
        """创建新数字员工。

        :param db: 数据库会话
        :param data: 员工字段字典
        :return: 新建的 DigitalEmployee 实体
        """
        emp = DigitalEmployee(**data)
        db.add(emp)
        db.commit()
        db.refresh(emp)
        return emp

    @staticmethod
    def get(db: Session, emp_id: int) -> Optional[DigitalEmployee]:
        """按 ID 获取单个数字员工。

        :param db: 数据库会话
        :param emp_id: 员工 ID
        :return: 匹配的 DigitalEmployee 或 None
        """
        return db.query(DigitalEmployee).filter(DigitalEmployee.id == emp_id).first()

    @staticmethod
    def list(db: Session, skip: int = 0, limit: int = 100) -> List[DigitalEmployee]:
        """分页查询数字员工列表（按 ID 升序）。

        :param db: 数据库会话
        :param skip: 偏移量
        :param limit: 每页条数
        :return: 数字员工列表
        """
        return db.query(DigitalEmployee).order_by(DigitalEmployee.id).offset(skip).limit(limit).all()

    @staticmethod
    def list_enabled(db: Session) -> List[DigitalEmployee]:
        """查询所有启用中（status=1）的数字员工列表。

        :param db: 数据库会话
        :return: 启用状态的数字员工列表
        """
        return db.query(DigitalEmployee).filter(DigitalEmployee.status == 1).order_by(DigitalEmployee.id).all()

    @staticmethod
    def update(db: Session, emp_id: int, data: Dict[str, Any]) -> Optional[DigitalEmployee]:
        """按 ID 局部更新数字员工字段。

        :param db: 数据库会话
        :param emp_id: 目标员工 ID
        :param data: 待更新字段字典
        :return: 更新后的 DigitalEmployee 实体，或 None
        """
        emp = EmployeeRepository.get(db, emp_id)
        if not emp:
            return None
        for key, value in data.items():
            if hasattr(emp, key):
                setattr(emp, key, value)
        db.commit()
        db.refresh(emp)
        return emp

    @staticmethod
    def delete(db: Session, emp_id: int) -> bool:
        """按 ID 删除数字员工。

        :param db: 数据库会话
        :param emp_id: 目标员工 ID
        :return: 删除成功 True，不存在 False
        """
        emp = EmployeeRepository.get(db, emp_id)
        if not emp:
            return False
        db.delete(emp)
        db.commit()
        return True

    @staticmethod
    def list_task_runs_by_employee(
        db: Session, emp_id: int, skip: int = 0, limit: int = 100
    ) -> List[EmployeeTaskRun]:
        """查询指定员工的历史任务记录（按 started_at 倒序）。

        :param db: 数据库会话
        :param emp_id: 员工 ID
        :param skip: 偏移量
        :param limit: 每页条数
        :return: EmployeeTaskRun 列表
        """
        return (
            db.query(EmployeeTaskRun)
            .filter(EmployeeTaskRun.employee_id == emp_id)
            .order_by(desc(EmployeeTaskRun.started_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def list_task_runs_by_user(
        db: Session, user_id: int, skip: int = 0, limit: int = 100
    ) -> List[EmployeeTaskRun]:
        """查询指定用户发起的所有任务记录（按 started_at 倒序）。

        :param db: 数据库会话
        :param user_id: 用户 ID
        :param skip: 偏移量
        :param limit: 每页条数
        :return: EmployeeTaskRun 列表
        """
        return (
            db.query(EmployeeTaskRun)
            .filter(EmployeeTaskRun.user_id == user_id)
            .order_by(desc(EmployeeTaskRun.started_at))
            .offset(skip)
            .limit(limit)
            .all()
        )


def _build_system_prompt(emp: DigitalEmployee) -> str:
    """根据数字员工的角色与描述拼接系统提示词。

    :param emp: DigitalEmployee 实体
    :return: 组装后的 system prompt 字符串
    """
    role_info = prompts.ROLES.get(emp.role_key)
    if role_info is None:
        role_str = f"你是数字员工 {emp.name}"
    else:
        role_str = role_info.get("description", "") or ""
    emp_desc = emp.description or ""
    return (
        f"你是企业智能协同平台的数字员工 {emp.name}。\n"
        f"职责：{emp_desc}\n"
        f"角色设定：{role_str}\n"
        f"回答请简洁、专业。"
    )


def _apply_runtime_cfg_to_chat(runtime_cfg: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """从 runtime_cfg 中抽取 chat_completion 支持的关键字参数（model/temperature/max_tokens）。"""
    kwargs: Dict[str, Any] = {}
    if not runtime_cfg:
        return kwargs
    if runtime_cfg.get("model_id"):
        kwargs["model"] = runtime_cfg["model_id"]
    if runtime_cfg.get("temperature") is not None:
        kwargs["temperature"] = runtime_cfg["temperature"]
    if runtime_cfg.get("max_tokens"):
        kwargs["max_tokens"] = runtime_cfg["max_tokens"]
    return kwargs


def chat_with_employee(
    db: Session,
    emp_id: int,
    user_messages: List[Dict[str, Any]],
    user_id: Optional[int] = None,
) -> str:
    """与数字员工进行对话：拼接系统提示词、组装工具、调用LLM并处理 tool_calls 占位。

    :param db: 数据库会话
    :param emp_id: 数字员工 ID
    :param user_messages: 用户侧消息列表（不含 system）
    :param user_id: 可选调用用户 ID
    :return: assistant 回复字符串（带调工具占位）
    :raises ValueError: 员工不存在时抛出
    """
    emp = EmployeeRepository.get(db, emp_id)
    if emp is None:
        raise ValueError("数字员工不存在")

    system_prompt = _build_system_prompt(emp)

    runtime_cfg: Optional[Dict[str, Any]] = None
    try:
        from services.model_skill import ModelRepository

        runtime_cfg = ModelRepository.get_runtime_config(db, emp.default_model_id)
    except (ImportError, Exception):
        runtime_cfg = None

    tools: Optional[List[Dict[str, Any]]] = None
    try:
        from services.model_skill import SkillEngine

        tools = SkillEngine.build_tools(db, employee_id=emp_id)
        if not tools:
            tools = None
    except (ImportError, Exception):
        tools = None

    trimmed_user_msgs = user_messages[-20:] if len(user_messages) > 20 else user_messages
    messages: List[Dict[str, Any]] = [{"role": "system", "content": system_prompt}] + list(trimmed_user_msgs)

    chat_kwargs = _apply_runtime_cfg_to_chat(runtime_cfg)

    if tools:
        try:
            from services.llm_service import get_client

            client = get_client()
            response = client.chat.completions.create(
                model=chat_kwargs.get("model") or _fallback_model_id(runtime_cfg),
                messages=messages,
                tools=tools,
                max_tokens=chat_kwargs.get("max_tokens") or _fallback_max_tokens(),
                temperature=chat_kwargs.get("temperature") if chat_kwargs.get("temperature") is not None else _fallback_temperature(),
            )
        except Exception as e:
            raise ValueError(f"调用大模型失败: {e}")
    else:
        try:
            from services.llm_service import chat_completion

            response = chat_completion(messages, **chat_kwargs)
        except Exception as e:
            raise ValueError(f"调用大模型失败: {e}")

    message = response.choices[0].message
    content = (getattr(message, "content", None) or "").strip()

    tool_calls = getattr(message, "tool_calls", None)
    if tool_calls:
        parts: List[str] = []
        for tc in tool_calls:
            tc_func = getattr(tc, "function", None)
            if tc_func is None:
                continue
            name = getattr(tc_func, "name", "") or ""
            args_raw = getattr(tc_func, "arguments", "") or "{}"
            try:
                args_obj = json.loads(args_raw)
                args_str = ", ".join(f"{k}={json.dumps(v, ensure_ascii=False)}" for k, v in args_obj.items())
            except Exception:
                args_str = args_raw
            parts.append(f"{name}({args_str})")
        if parts:
            content = content + " [调工具:" + ", ".join(parts) + "]"

    return content


def _fallback_model_id(runtime_cfg: Optional[Dict[str, Any]]) -> str:
    if runtime_cfg and runtime_cfg.get("model_id"):
        return runtime_cfg["model_id"]
    try:
        from core.llm_config import llm_config

        return llm_config.LLM_MODEL_ID
    except Exception:
        return "gpt-4o-mini"


def _fallback_max_tokens() -> int:
    try:
        from core.llm_config import llm_config

        return llm_config.LLM_MAX_TOKENS or 2048
    except Exception:
        return 2048


def _fallback_temperature() -> float:
    try:
        from core.llm_config import llm_config

        return float(llm_config.LLM_TEMPERATURE) if llm_config.LLM_TEMPERATURE is not None else 0.7
    except Exception:
        return 0.7


def run_employee_task(
    db: Session,
    emp_id: int,
    user_id: int,
    task_type: str,
    params: Optional[Dict[str, Any]] = None,
) -> EmployeeTaskRun:
    """由数字员工触发后台任务（流水线执行 / 资产生成画像 / NL2SQL 报表）并持久化记录。

    :param db: 数据库会话
    :param emp_id: 触发的数字员工 ID
    :param user_id: 触发用户 ID
    :param task_type: 任务类型：pipeline_run / asset_profile / nl2sql_report
    :param params: 任务参数字典
    :return: 已持久化并刷新的 EmployeeTaskRun 实体
    :raises ValueError: 未知任务类型或业务校验失败时抛出
    """
    task_run = EmployeeTaskRun(
        employee_id=emp_id,
        user_id=user_id,
        task_type=task_type,
        params=params,
        status="queued",
        started_at=datetime.utcnow(),
    )
    db.add(task_run)
    db.flush()

    try:
        task_run.status = "running"
        db.commit()

        result: Any = None

        if task_type == "pipeline_run":
            pipeline_id = (params or {}).get("pipeline_id")
            from services.data_pipeline import execute_pipeline

            run = execute_pipeline(db, pipeline_id, triggered_by=f"employee_{emp_id}")
            result = {
                "run_id": getattr(run, "id", None),
                "rows_count": getattr(run, "rows_count", None),
                "status": getattr(run, "status", None),
            }

        elif task_type == "asset_profile":
            safe_params = params or {}
            if "asset_id" not in safe_params:
                raise ValueError("缺少必要参数: asset_id")
            asset_id = safe_params["asset_id"]
            from services.data_asset import generate_profile

            profile = generate_profile(db, asset_id, generated_by=user_id)
            result = {
                "profile_id": getattr(profile, "id", None),
                "report": getattr(profile, "report_text", None),
            }

        elif task_type == "nl2sql_report":
            safe_params = params or {}
            if "question" not in safe_params:
                raise ValueError("缺少必要参数: question")
            question = safe_params["question"]
            asset_ids = safe_params.get("asset_ids", [])
            from services.llm_service import generate_nl2sql_with_answer

            result = generate_nl2sql_with_answer(
                question=question,
                asset_ids=asset_ids,
                db=db,
            )

        else:
            raise ValueError(f"未知任务类型:{task_type}")

        task_run.status = "success"
        task_run.result = result
        task_run.finished_at = datetime.utcnow()

    except Exception as e:
        task_run.status = "failed"
        task_run.error_msg = str(e)
        task_run.finished_at = datetime.utcnow()

    db.commit()
    db.refresh(task_run)
    return task_run
