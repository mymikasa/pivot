import json
import sys
import argparse

from mcp.server.fastmcp import FastMCP

from src.rag.retrieval import search_chunks

mcp = FastMCP("pivot-search")


@mcp.tool()
def search_knowledge_base(query: str, kb_id: int, top_k: int = 5) -> str:
    """在知识库中搜索与查询相关的内容片段。

    Args:
        query: 搜索关键词
        kb_id: 知识库 ID
        top_k: 返回结果数量，默认 5
    """
    results = search_chunks(query=query, kb_id=kb_id, top_k=top_k)

    output = []
    for r in results:
        output.append(
            {
                "content": r.content,
                "score": r.score,
                "filename": r.filename,
                "chunk_index": r.chunk_index,
                "document_id": r.document_id,
            }
        )

    return json.dumps(output, ensure_ascii=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Pivot Search MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="传输方式 (默认 stdio)",
    )
    parser.add_argument("--port", type=int, default=8080, help="SSE 模式端口")
    args = parser.parse_args()

    if args.transport == "stdio":
        mcp.run(transport="stdio")
    else:
        print(f"Pivot Search MCP Server (SSE) 启动于端口 {args.port}", file=sys.stderr)
        mcp.run(transport="sse", port=args.port)


if __name__ == "__main__":
    main()
