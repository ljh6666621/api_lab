from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from routers import health, products, users, department, chat, data_pipelines, data_assets, modelskills, digital_employees, im
from routers.im import setup_im_websocket
from init_db import init_all
from core.scheduler import SCHEDULER
from core.config import IM_ENABLE, SCHEDULER_ENABLE

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI 应用生命周期管理：
    - 启动前执行：建表并填充种子数据 + 启动 APScheduler 调度器
    - 关闭时执行：关闭 APScheduler 调度器
    """
    init_all(verbose=False)
    if SCHEDULER_ENABLE:
        SCHEDULER.start()
    yield
    if SCHEDULER_ENABLE:
        SCHEDULER.shutdown()


app = FastAPI(
    title="企业智能协同平台 API Lab",
    description="",
    version="0.4.0",
    lifespan=lifespan,
)


@app.exception_handler(HTTPException)
async def fastapi_exception_handler(request: Request, exc: HTTPException):
    """
    统一捕获 FastAPI HTTPException，返回标准 JSON 结构 {code, message}。
    避免默认响应格式与业务错误格式不一致。
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.status_code, "message": exc.detail},
    )


@app.exception_handler(StarletteHTTPException)
async def starlette_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    统一捕获 Starlette 层异常（如 404 路由不存在），返回标准化 JSON 错误。
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.status_code,
            "message": exc.detail if exc.detail else "资源不存在",
        },
    )


app.include_router(health.router)
app.include_router(products.router)
app.include_router(users.router)
app.include_router(department.router)
app.include_router(chat.router)
app.include_router(data_pipelines.router)
app.include_router(data_assets.router)
app.include_router(modelskills.router)
app.include_router(digital_employees.router)
if IM_ENABLE:
    app.include_router(im.router)
    setup_im_websocket(app)


if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def root():
    """访问根路径时返回门户首页 portal.html，不存在则回退智能问数前端。"""
    portal_file = STATIC_DIR / "portal.html"
    index_file = STATIC_DIR / "index.html"
    if portal_file.exists():
        return FileResponse(str(portal_file))
    if index_file.exists():
        return FileResponse(str(index_file))
    return {
        "message": "API Lab 运行中",
        "docs": "/docs",
        "project": "企业智能协同平台",
        "day": 4,
        "version": "0.4.0",
        "features": [
            "分层架构(routers/services/models/schemas/core)",
            "商品数据库持久化",
            "用户注册/登录(JWT)",
            "密码bcrypt加密",
            "部门CRUD",
            "LLM聊天服务(/chat)",
            "NL2SQL自然语言转SQL(/chat/nl2sql)",
            "人格角色切换(9种角色)",
            "数据采集流水线(/pipelines)",
            "数据资产分析(/assets)",
            "NL2SQL多轮对话(/chat/sessions)",
            "即时通讯(WebSocket /im/ws + /static/im.html)",
            "数字员工(/employees)",
            "模型与技能管理(/modelskills)",
        ],
    }


@app.get("/api/status")
def api_status():
    """API 状态端点，返回服务运行信息（JSON 格式，不返回前端页面）。"""
    return {
        "message": "API Lab 运行中",
        "docs": "/docs",
        "project": "企业智能协同平台",
        "day": 4,
        "version": "0.4.0",
        "features": [
            "分层架构(routers/services/models/schemas/core)",
            "商品数据库持久化",
            "用户注册/登录(JWT)",
            "密码bcrypt加密",
            "部门CRUD",
            "LLM聊天服务(/chat)",
            "NL2SQL自然语言转SQL(/chat/nl2sql)",
            "人格角色切换(9种角色)",
            "数据采集流水线(/pipelines)",
            "数据资产分析(/assets)",
            "NL2SQL多轮对话(/chat/sessions)",
            "即时通讯(WebSocket /im/ws + /static/im.html)",
            "数字员工(/employees)",
            "模型与技能管理(/modelskills)",
        ],
    }
