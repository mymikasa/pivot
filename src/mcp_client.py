import asyncio
import json
import sys
from contextlib import AsyncExitStack
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import OpenAI

from src.infrastructure.config import settings

SYSTEM_PROMPT = "你是一个知识库问答助手。使用 search_knowledge_base 工具在知识库中搜索相关内容，然后基于搜索结果回答用户的问题。"


class MCPChatClient:
    def __init__(self) -> None:
        self.session: ClientSession | None = None
        self.exit_stack = AsyncExitStack()
        self.client = OpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_api_base,
        )
        self.tools: list[dict[str, Any]] = []

    async def connect_to_server(self, server_script: str) -> None:
        server_params = StdioServerParameters(
            command=sys.executable,
            args=[server_script],
            env=None,
        )

        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(self.stdio, self.write)
        )

        await self.session.initialize()

        response = await self.session.list_tools()
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": tool.inputSchema,
                },
            }
            for tool in response.tools
        ]
        tool_names = [tool.name for tool in response.tools]
        print(f"已连接 MCP Server，可用工具: {tool_names}", file=sys.stderr)

    async def process_query(self, query: str) -> str:
        assert self.session is not None

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ]

        response = self.client.chat.completions.create(
            model=settings.llm_model,
            messages=messages,
            tools=self.tools,
            tool_choice="auto",
        )

        assistant_message = response.choices[0].message
        messages.append(assistant_message.model_dump())

        if assistant_message.tool_calls is None:
            return assistant_message.content or ""

        for tool_call in assistant_message.tool_calls:
            fn_name = tool_call.function.name
            fn_args = json.loads(tool_call.function.arguments)
            print(
                f"  [MCP 工具调用] {fn_name}({json.dumps(fn_args, ensure_ascii=False)})",
                file=sys.stderr,
            )

            result = await self.session.call_tool(fn_name, fn_args)
            result_text = "\n".join(
                item.text for item in result.content if hasattr(item, "text")
            )
            print(
                f"  [MCP 工具结果] 返回 {len(result.content)} 条内容",
                file=sys.stderr,
            )

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result_text,
                }
            )

        final_response = self.client.chat.completions.create(
            model=settings.llm_model,
            messages=messages,
        )

        return final_response.choices[0].message.content or ""

    async def chat_loop(self) -> None:
        print("\nMCP Chat Client 已启动！输入问题或 'quit' 退出。")
        while True:
            try:
                query = input("\n你: ").strip()
            except (EOFError, KeyboardInterrupt):
                break

            if not query:
                continue
            if query.lower() == "quit":
                break

            try:
                answer = await self.process_query(query)
                print(f"\n助手: {answer}")
            except Exception as e:
                print(f"\n错误: {e}", file=sys.stderr)

    async def cleanup(self) -> None:
        await self.exit_stack.aclose()


async def main() -> None:
    if len(sys.argv) < 2:
        print(
            "用法: uv run python -m src.mcp_client <mcp_server_script>", file=sys.stderr
        )
        sys.exit(1)

    if not settings.llm_api_key:
        print("错误: 请在 config.yaml 的 llm.api_key 中配置 API Key", file=sys.stderr)
        sys.exit(1)

    client = MCPChatClient()
    try:
        await client.connect_to_server(sys.argv[1])
        await client.chat_loop()
    finally:
        await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
