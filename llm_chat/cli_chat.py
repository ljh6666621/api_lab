import sys

from openai import OpenAI

from app.core.config import settings
from app.prompts.roles import get_role_system_prompt, list_roles


def get_client() -> OpenAI:
    return OpenAI(
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_BASE_URL,
    )


def print_roles():
    roles = list_roles()
    print("\n可用人格角色：")
    for i, role in enumerate(roles, 1):
        print(f"  {i}. [{role['name']}] {role['description']}")
    print()


def chat_cli():
    print("=" * 50)
    print("      LLM Chat CLI")
    print("=" * 50)
    print()

    current_role = None
    messages = []

    print("提示：")
    print("  - 直接输入消息进行聊天")
    print("  - 输入 /role 查看可用人格角色")
    print("  - 输入 /role <角色名> 切换人格")
    print("  - 输入 /clear 清空对话历史")
    print("  - 输入 /exit 或 /quit 退出")
    print()

    while True:
        try:
            user_input = input(f"\n{'[' + current_role + '] ' if current_role else ''}你: ")
        except EOFError:
            break

        user_input = user_input.strip()

        if not user_input:
            continue

        if user_input in ("/exit", "/quit", "exit", "quit"):
            print("\n再见！")
            break

        if user_input == "/role":
            print_roles()
            continue

        if user_input.startswith("/role "):
            role_name = user_input.split("/role ", 1)[1].strip()
            system_prompt = get_role_system_prompt(role_name)
            if role_name in [r["name"] for r in list_roles()]:
                current_role = role_name
                print(f"\n已切换人格: {current_role}")
                messages = []
            else:
                print(f"\n未知角色: {role_name}")
                print_roles()
            continue

        if user_input == "/clear":
            messages = []
            print("\n对话历史已清空")
            continue

        system_prompt = get_role_system_prompt(current_role)
        messages.append({"role": "user", "content": user_input})

        full_messages = [{"role": "system", "content": system_prompt}] + messages

        print(f"\nAI{'[' + current_role + ']' if current_role else ''}: ", end="")
        sys.stdout.flush()

        client = get_client()
        stream = client.chat.completions.create(
            model=settings.LLM_MODEL_ID,
            messages=full_messages,
            max_tokens=settings.LLM_MAX_TOKENS,
            temperature=settings.LLM_TEMPERATURE,
            stream=True,
        )

        response_content = ""
        for chunk in stream:
            if chunk.choices:
                content = chunk.choices[0].delta.content
                if content:
                    print(content, end="")
                    sys.stdout.flush()
                    response_content += content

        messages.append({"role": "assistant", "content": response_content})
        print()


if __name__ == "__main__":
    chat_cli()