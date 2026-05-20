import json
import logging

from openai import OpenAI

from src.infrastructure.config import settings
from src.rag.retrieval import search_chunks
from src.rag.schemas import ChatResponse, ChatSource, SearchResult

logger = logging.getLogger(__name__)

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


def _execute_tool(
    function_name: str, arguments: dict, kb_id: int
) -> tuple[str, list[SearchResult]]:
    if function_name != "search_knowledge_base":
        return json.dumps(
            {"error": f"未知工具: {function_name}"}, ensure_ascii=False
        ), []

    results = search_chunks(
        query=arguments["query"],
        kb_id=kb_id,
        top_k=arguments.get("top_k", 5),
    )
    result_json = json.dumps(
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
    return result_json, results


def chat_with_tools(
    message: str,
    kb_id: int,
    history: list[dict] | None = None,
    top_k: int = 5,
) -> ChatResponse:
    client = OpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_api_base,
    )

    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT_TEMPLATE.format(kb_id=kb_id)}
    ]

    for msg in history or []:
        messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": message})

    all_sources: list[SearchResult] = []

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
            return ChatResponse(
                answer=assistant_message.content or "",
                sources=[
                    ChatSource(
                        content=r.content,
                        score=r.score,
                        filename=r.filename,
                        chunk_index=r.chunk_index,
                    )
                    for r in all_sources
                ],
            )

        for tool_call in assistant_message.tool_calls:
            fn_name = tool_call.function.name
            fn_args = json.loads(tool_call.function.arguments)
            logger.info(
                "工具调用: %s(%s)", fn_name, json.dumps(fn_args, ensure_ascii=False)
            )

            result_json, results = _execute_tool(fn_name, fn_args, kb_id)
            all_sources.extend(results)

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result_json,
                }
            )
