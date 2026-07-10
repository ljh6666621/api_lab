from typing import Generator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from openai import OpenAI

from app.core.config import settings
from app.prompts.roles import get_role_system_prompt, list_roles
from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["chat"])


def get_client() -> OpenAI:
    return OpenAI(
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_BASE_URL,
    )


@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest):
    if request.stream:
        raise HTTPException(status_code=400, detail="流式响应请使用 /chat/stream 接口")

    system_prompt = get_role_system_prompt(request.role)
    messages = [{"role": "system", "content": system_prompt}]
    for msg in request.messages:
        messages.append({"role": msg.role, "content": msg.content})

    client = get_client()
    response = client.chat.completions.create(
        model=settings.LLM_MODEL_ID,
        messages=messages,
        max_tokens=settings.LLM_MAX_TOKENS,
        temperature=request.temperature or settings.LLM_TEMPERATURE,
    )

    return ChatResponse(content=response.choices[0].message.content or "")


@router.post("/stream")
def chat_stream(request: ChatRequest) -> StreamingResponse:
    system_prompt = get_role_system_prompt(request.role)
    messages = [{"role": "system", "content": system_prompt}]
    for msg in request.messages:
        messages.append({"role": msg.role, "content": msg.content})

    client = get_client()
    stream = client.chat.completions.create(
        model=settings.LLM_MODEL_ID,
        messages=messages,
        max_tokens=settings.LLM_MAX_TOKENS,
        temperature=request.temperature or settings.LLM_TEMPERATURE,
        stream=True,
    )

    def generate() -> Generator[str, None, None]:
        for chunk in stream:
            if chunk.choices:
                content = chunk.choices[0].delta.content
                if content:
                    yield content

    return StreamingResponse(generate(), media_type="text/plain")


@router.get("/roles")
def get_roles():
    return {"roles": list_roles()}