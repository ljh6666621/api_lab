import sys

from openai import OpenAI

from core.llm_config import llm_config
from prompts.roles import ROLE_NAMES, get_role_system_prompt, list_roles
from services.llm_service import build_messages, chat_completion, generate_nl2sql


def get_client() -> OpenAI:
    return OpenAI(
        api_key=llm_config.LLM_API_KEY,
        base_url=llm_config.LLM_BASE_URL,
    )


def print_roles():
    roles = list_roles()
    print("\n可用人格角色：")
    for i, role in enumerate(roles, 1):
        print(f"  {i}. [{role['name']}] {role['description']}")
    print()


def handle_sql_command(question: str):
    print(f"\n[SQL 专家] 正在分析问题: {question}")
    result = generate_nl2sql(question)

    print("\n=== SQL 生成结果 ===")
    if result.get("sql"):
        print(f"SQL:\n{result['sql']}")
    else:
        print("SQL: (无法生成)")
    print(f"\n解释:\n{result['explanation']}")

    if result.get("results"):
        print("\n查询结果:")
        if result["results"]:
            columns = list(result["results"][0].keys())
            print(f"  {' | '.join(columns)}")
            print(f"  {'-|-'.join(['-'*len(col) for col in columns])}")
            for row in result["results"]:
                print(f"  {' | '.join(str(row[col]) for col in columns)}")
        else:
            print("  (空结果)")
    print("===================")


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
    print("  - 输入 /sql <问题> 生成 SQL 查询")
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
            if role_name in ROLE_NAMES:
                current_role = role_name
                print(f"\n已切换人格: {current_role} ({ROLE_NAMES[current_role]})")
                messages = []
            else:
                print(f"\n未知角色: {role_name}")
                print_roles()
            continue

        if user_input.startswith("/sql "):
            question = user_input.split("/sql ", 1)[1].strip()
            handle_sql_command(question)
            continue

        if user_input == "/clear":
            messages = []
            print("\n对话历史已清空")
            continue

        system_prompt = get_role_system_prompt(current_role)
        messages.append({"role": "user", "content": user_input})
        full_messages = build_messages(system_prompt, messages)

        print(f"\nAI{'[' + current_role + ']' if current_role else ''}: ", end="")
        sys.stdout.flush()

        stream = chat_completion(
            full_messages,
            temperature=llm_config.LLM_TEMPERATURE,
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