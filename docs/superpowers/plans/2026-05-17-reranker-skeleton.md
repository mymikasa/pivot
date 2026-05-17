# Reranker 接口骨架开发计划

## Summary

为现有向量检索增加可插拔 reranker 管线骨架，不引入真实模型依赖。`/api/v1/search` 支持请求级控制：默认保持现有向量检索行为；当请求启用 rerank 时，服务端先扩大候选召回，再调用已配置的 reranker 实现；如果未配置可用 reranker，则明确返回服务不可用错误。

## Key Changes

- 在 `src/pipeline/search.py` 中拆分检索流程：
  - `top_k` 表示最终返回条数。
  - 新增 `rerank: bool = False` 和 `rerank_top_k: int | None = None`。
  - 未启用 rerank 时，保持当前行为，向量召回 `top_k`。
  - 启用 rerank 时，候选数为 `rerank_top_k`，未传则用 `min(top_k * 5, 50)`。
- 新增 reranker 抽象：
  - 定义 `Reranker` 协议/基类，输入 `query` 与候选 `SearchResult` 列表，输出重排后的列表。
  - 新增 `build_reranker()` 工厂函数。
  - 第一版不注册真实模型 provider；未配置实现时抛出 `RerankerUnavailableError`。
- 扩展配置：
  - `Settings` 增加 `reranker_provider: str = ""`、`reranker_model: str = ""`。
  - `src/config.yaml` 增加 `reranker:` 分组，默认空 provider/model。
- 扩展 API schema：
  - `SearchRequest` 增加 `rerank: bool = False`。
  - `SearchRequest` 增加 `rerank_top_k: int | None = Field(default=None, ge=1, le=200)`。
  - 校验：传入 `rerank_top_k` 时必须 `>= top_k`。
  - `SearchResponse` 和 `SearchHit` 暂不增加字段，避免前端响应契约膨胀。
- API 错误处理：
  - `src/api/search.py` 捕获 `RerankerUnavailableError`。
  - 返回 `503 Service Unavailable`，detail 使用中文，例如：`"reranker 未配置或不可用"`。

## Test Plan

- 更新 `tests/test_search_api.py`：
  - 默认请求不带 `rerank` 时，仍只召回 `top_k`，响应与现有测试一致。
  - 请求 `rerank=true` 且未传 `rerank_top_k` 时，retriever 使用 `min(top_k * 5, 50)` 作为候选数。
  - 请求 `rerank=true` 且传入 `rerank_top_k` 时，retriever 使用该候选数，最终响应仍只返回 `top_k` 条。
  - 使用 fake reranker monkeypatch `build_reranker()`，验证结果顺序按 reranker 输出改变。
  - 未配置 reranker 且请求 `rerank=true` 时，API 返回 503。
  - `rerank_top_k < top_k` 时，API 返回 422。
- 更新 `tests/test_config.py`：
  - YAML 中可读取 `reranker.provider` 和 `reranker.model`。
  - 缺省配置时两个字段为空字符串。
- 运行验证：
  - `uv run pytest tests/test_search_api.py tests/test_config.py`
  - 如时间允许，再运行 `uv run pytest`

## Assumptions

- 第一版不新增 `sentence-transformers`、`FlagEmbedding`、LlamaIndex reranker postprocessor 等依赖。
- 第一版不提供真实模型 provider；启用 rerank 但未配置实现时必须显式失败。
- `top_k` 保持公开语义不变：它始终是最终返回数量。
- 候选召回默认值固定为 `min(top_k * 5, 50)`，请求可用 `rerank_top_k` 覆盖，上限为 200。
