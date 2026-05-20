import argparse
import json
import sys

from openai import OpenAI

from src.infrastructure.config import settings
from src.pipeline.search import search_chunks

SYSTEM_PROMPT_TEMPLATE = """你是一个知识库问答助手（当前知识库 ID: {kb_id}）。当用户提出问题时，你应该使用 search_knowledge_base 工具在知识库中搜索相关内容，然后基于搜索结果回答用户的问题。

回答要求：
- 基于搜索结果给出准确回答
- 如果搜索结果不足以回答问题，如实告知用户
- 引用相关内容时标注来源文档"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": "在知识库中搜索与查询相关的内容片段",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "返回结果数量，默认 5",
                    },
                },
                "required": ["query"],
            },
        },
    }
]


def execute_tool(function_name: str, arguments: dict, kb_id: int) -> str:
    if function_name != "search_knowledge_base":
        return json.dumps({"error": f"未知工具: {function_name}"}, ensure_ascii=False)

    results = search_chunks(
        query=arguments["query"],
        kb_id=kb_id,
        top_k=arguments.get("top_k", 5),
    )
    return json.dumps(
        [
            {
                "content": r.content,
                "score": r.score,
                "filename": r.filename,
                "chunk_index": r.chunk_index,
            }
            for r in results
        ],
        ensure_ascii=False,
    )


def run_chat(kb_id: int) -> None:
    client = OpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_api_base,
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT_TEMPLATE.format(kb_id=kb_id)}
    ]

    print(f"知识库问答助手 (kb_id={kb_id})")
    print("输入问题开始对话，输入 quit 退出\n")

    while True:
        try:
            user_input = input("你: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break

        if not user_input:
            continue
        if user_input.lower() == "quit":
            print("再见！")
            break

        messages.append({"role": "user", "content": user_input})

        while True:
            response = client.chat.completions.create(
                model=settings.llm_model,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
            )

            assistant_message = response.choices[0].message
            messages.append(assistant_message.model_dump())

            if assistant_message.tool_calls is None:
                print(f"\n助手: {assistant_message.content}\n")
                break

            for tool_call in assistant_message.tool_calls:
                fn_name = tool_call.function.name
                fn_args = json.loads(tool_call.function.arguments)
                print(
                    f"  [工具调用] {fn_name}({json.dumps(fn_args, ensure_ascii=False)})"
                )

                result = execute_tool(fn_name, fn_args, kb_id)
                print(f"  [工具结果] 返回 {len(json.loads(result))} 条搜索结果")

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result,
                    }
                )


def main() -> None:
    parser = argparse.ArgumentParser(description="Function Calling Demo")
    parser.add_argument("--kb-id", type=int, required=True, help="知识库 ID")
    args = parser.parse_args()

    if not settings.llm_api_key:
        print("错误: 请在 config.yaml 的 llm.api_key 中配置 API Key", file=sys.stderr)
        sys.exit(1)

    run_chat(args.kb_id)


if __name__ == "__main__":
    main()
