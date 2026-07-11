from fastapi import APIRouter

# 系统路由
router = APIRouter(tags=["系统"])


@router.get("/health")
def health():
    """健康检查接口，用于确认服务是否正常运行。"""
    return {"status": "ok", "service": "api_lab"}


@router.get("/hello")
def hello(name: str | None = None):
    """问候接口，可选传入 name 参数进行个性化问候。"""
    msg = "Hello, 企业智能协同平台!"
    if name:
        msg = f"Hello, {name}!"
    return {"message": msg}
