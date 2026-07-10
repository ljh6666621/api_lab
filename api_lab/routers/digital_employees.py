from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from core.database import get_db
from core.security import get_current_user
from models.user import User
from schemas.digital_employee import (
    EmployeeChatRequest,
    EmployeeCreate,
    EmployeeResponse,
    EmployeeTaskRequest,
    EmployeeUpdate,
    TaskRunResponse,
)
from schemas.product import DeleteResponse
from services.digital_employee import (
    EmployeeRepository,
    chat_with_employee,
    run_employee_task,
)

router = APIRouter(prefix="/employees", tags=["数字员工"])


@router.post("", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
def create_employee(
    body: EmployeeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建数字员工接口（需登录）：接收员工信息并持久化，返回创建后的员工。"""
    data = body.model_dump(exclude_unset=True)
    data.setdefault("owner_id", current_user.id)
    emp = EmployeeRepository.create(db, data)
    return emp


@router.get("", response_model=list[EmployeeResponse])
def list_employees(
    skip: int = Query(0, ge=0, description="跳过条数，用于分页"),
    limit: int = Query(100, ge=1, le=500, description="返回最大条数"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """数字员工列表接口（需登录）：分页获取所有员工列表。"""
    return EmployeeRepository.list(db, skip=skip, limit=limit)


@router.get("/{eid}", response_model=EmployeeResponse)
def get_employee(
    eid: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """根据员工 ID 获取单个数字员工详情（需登录）；不存在时返回 HTTP 404。"""
    emp = EmployeeRepository.get(db, eid)
    if not emp:
        raise HTTPException(status_code=404, detail="数字员工不存在")
    return emp


@router.put("/{eid}", response_model=EmployeeResponse)
def update_employee(
    eid: int,
    body: EmployeeUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新数字员工接口（需登录）：按 ID 局部更新字段；无有效字段或员工不存在时报错。"""
    data = body.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="无更新字段")
    updated = EmployeeRepository.update(db, eid, data)
    if not updated:
        raise HTTPException(status_code=404, detail="数字员工不存在")
    return updated


@router.delete("/{eid}", response_model=DeleteResponse)
def delete_employee(
    eid: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除数字员工接口（需登录）：根据 ID 删除，删除失败（不存在）返回 404。"""
    if not EmployeeRepository.delete(db, eid):
        raise HTTPException(status_code=404, detail="数字员工不存在")
    return DeleteResponse(success=True, message="删除成功")


@router.post("/{eid}/chat")
def chat_employee(
    eid: int,
    body: EmployeeChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """与数字员工对话接口（需登录）：支持单轮文本或多轮消息列表输入，返回回答。"""
    if body.content is not None and body.content.strip():
        messages = [{"role": "user", "content": body.content}]
    elif body.messages is not None:
        messages = body.messages
    else:
        raise HTTPException(status_code=400, detail="必须提供 content 或 messages 之一")

    try:
        answer = chat_with_employee(db, eid, messages, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"answer": answer}


@router.post("/{eid}/tasks", response_model=TaskRunResponse)
def run_task(
    eid: int,
    body: EmployeeTaskRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """触发数字员工后台任务接口（需登录）：同步执行并返回任务记录详情。"""
    emp = EmployeeRepository.get(db, eid)
    if not emp:
        raise HTTPException(status_code=404, detail="数字员工不存在")
    try:
        task_run = run_employee_task(
            db,
            emp_id=eid,
            user_id=current_user.id,
            task_type=body.task_type,
            params=body.params,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return task_run


@router.get("/{eid}/tasks", response_model=list[TaskRunResponse])
def list_employee_tasks(
    eid: int,
    skip: int = Query(0, ge=0, description="跳过条数"),
    limit: int = Query(100, ge=1, le=500, description="最大条数"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """指定员工的历史任务记录接口（需登录）：按 started_at 倒序返回任务列表。"""
    emp = EmployeeRepository.get(db, eid)
    if not emp:
        raise HTTPException(status_code=404, detail="数字员工不存在")
    return EmployeeRepository.list_task_runs_by_employee(db, eid, skip=skip, limit=limit)


@router.get("/tasks/me", response_model=list[TaskRunResponse])
def list_my_tasks(
    skip: int = Query(0, ge=0, description="跳过条数"),
    limit: int = Query(100, ge=1, le=500, description="最大条数"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """我发起的任务接口（需登录）：按 started_at 倒序返回当前用户发起的所有任务。"""
    return EmployeeRepository.list_task_runs_by_user(db, current_user.id, skip=skip, limit=limit)
