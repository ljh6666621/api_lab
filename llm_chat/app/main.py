from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import chat

app = FastAPI(
    title="LLM Chat API",
    description="基于 FastAPI 的 LLM 聊天服务，支持 CLI、流式响应和人格切换",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)


@app.get("/")
def root():
    return {
        "message": "LLM Chat API 运行中",
        "docs": "/docs",
        "features": [
            "CLI 聊天工具",
            "/chat 非流式接口",
            "/chat/stream 流式接口",
            "/chat/roles 人格角色列表",
            "支持 temperature 参数",
        ],
    }