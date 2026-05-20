from contextlib import ExitStack
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from src.main import app
from src.rag.errors import RerankerUnavailableError
from tests.test_parse_task_api import auth_headers


def _mock_node_with_score(text, score, metadata):
    node = MagicMock()
    node.text = text
    node.metadata = metadata
    nws = MagicMock()
    nws.node = node
    nws.score = score
    return nws


def test_search_returns_ranked_results():
    mock_results = [
        _mock_node_with_score(
            "Pivot 是一个知识库管理平台",
            0.95,
            {
                "kb_id": 1,
                "pivot_document_id": 10,
                "chunk_index": 0,
                "section_title": "简介",
                "section_path": "/简介/",
                "filename": "intro.md",
                "content_type": "text/markdown",
                "token_count": 5,
            },
        ),
        _mock_node_with_score(
            "向量检索使用 Milvus 数据库",
            0.72,
            {
                "kb_id": 1,
                "pivot_document_id": 10,
                "chunk_index": 1,
                "section_title": "架构",
                "section_path": "/架构/",
                "filename": "intro.md",
                "content_type": "text/markdown",
                "token_count": 5,
            },
        ),
    ]

    with (
        patch("src.rag.retrieval.build_embedding") as mock_embed,
        patch("src.rag.retrieval.build_vector_store") as mock_vs,
        patch("src.rag.retrieval.VectorStoreIndex") as mock_index_cls,
    ):
        mock_embed.return_value = MagicMock()
        mock_vs.return_value = MagicMock()
        mock_index = MagicMock()
        mock_index_cls.from_vector_store.return_value = mock_index
        mock_retriever = MagicMock()
        mock_index.as_retriever.return_value = mock_retriever
        mock_retriever.retrieve.return_value = mock_results

        client = TestClient(app)
        response = client.post(
            "/api/v1/search",
            json={"query": "知识库管理", "kb_id": 1, "top_k": 5},
            headers=auth_headers(),
        )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert data["hits"][0]["score"] == 0.95
    assert data["hits"][0]["content"] == "Pivot 是一个知识库管理平台"
    assert data["hits"][0]["filename"] == "intro.md"
    assert data["hits"][0]["section_title"] == "简介"
    assert data["hits"][1]["score"] == 0.72


def test_search_returns_empty_when_no_hits():
    with (
        patch("src.rag.retrieval.build_embedding") as mock_embed,
        patch("src.rag.retrieval.build_vector_store") as mock_vs,
        patch("src.rag.retrieval.VectorStoreIndex") as mock_index_cls,
    ):
        mock_embed.return_value = MagicMock()
        mock_vs.return_value = MagicMock()
        mock_index = MagicMock()
        mock_index_cls.from_vector_store.return_value = mock_index
        mock_retriever = MagicMock()
        mock_index.as_retriever.return_value = mock_retriever
        mock_retriever.retrieve.return_value = []

        client = TestClient(app)
        response = client.post(
            "/api/v1/search",
            json={"query": "不存在的内容", "kb_id": 99},
            headers=auth_headers(),
        )

    assert response.status_code == 200
    assert response.json()["total"] == 0
    assert response.json()["hits"] == []


def test_search_requires_auth():
    client = TestClient(app)
    response = client.post(
        "/api/v1/search",
        json={"query": "test", "kb_id": 1},
    )
    assert response.status_code == 401


# ── reranker tests ──────────────────────────────────────────────


def _setup_search_mocks(stack, *, with_reranker=False):
    """在 ExitStack 上注册 search 所需的 patch，返回 (mock_embed, mock_vs, mock_index_cls[, mock_build_reranker])。"""
    mock_embed = stack.enter_context(patch("src.rag.retrieval.build_embedding"))
    mock_vs = stack.enter_context(patch("src.rag.retrieval.build_vector_store"))
    mock_index_cls = stack.enter_context(patch("src.rag.retrieval.VectorStoreIndex"))
    mock_embed.return_value = MagicMock()
    mock_vs.return_value = MagicMock()
    mock_index = MagicMock()
    mock_index_cls.from_vector_store.return_value = mock_index
    mock_retriever = MagicMock()
    mock_index.as_retriever.return_value = mock_retriever

    result = [mock_embed, mock_vs, mock_index_cls, mock_index, mock_retriever]
    if with_reranker:
        mock_build_reranker = stack.enter_context(
            patch("src.rag.retrieval.build_reranker")
        )
        result.append(mock_build_reranker)
    return result


def test_search_default_no_rerank_uses_top_k():
    """默认不带 rerank 时，retriever 使用 top_k 召回。"""
    mock_results = [
        _mock_node_with_score(
            "chunk A",
            0.9,
            {
                "kb_id": 1,
                "pivot_document_id": 10,
                "chunk_index": 0,
                "filename": "a.md",
                "content_type": "text/markdown",
                "token_count": 5,
            },
        ),
    ]

    with ExitStack() as stack:
        _, _, _, mock_index, mock_retriever = _setup_search_mocks(stack)
        mock_retriever.retrieve.return_value = mock_results

        client = TestClient(app)
        response = client.post(
            "/api/v1/search",
            json={"query": "测试", "kb_id": 1, "top_k": 3},
            headers=auth_headers(),
        )

    assert response.status_code == 200
    mock_index.as_retriever.assert_called_once()
    call_kwargs = mock_index.as_retriever.call_args[1]
    assert call_kwargs["similarity_top_k"] == 3


def test_search_rerank_without_top_k_uses_default_candidate():
    """rerank=true 且未传 rerank_top_k 时，候选数为 min(top_k*5, 50)。"""
    from src.rag.schemas import SearchResult

    mock_nodes = [
        _mock_node_with_score(
            "chunk A",
            0.9,
            {
                "kb_id": 1,
                "pivot_document_id": 10,
                "chunk_index": 0,
                "filename": "a.md",
                "content_type": "text/markdown",
                "token_count": 5,
            },
        ),
    ]
    reranked_results = [
        SearchResult(
            chunk_index=0,
            document_id=10,
            kb_id=1,
            score=0.99,
            content="chunk A",
            token_count=5,
            source_page=None,
            section_title=None,
            section_path=None,
            filename="a.md",
            content_type="text/markdown",
        ),
    ]

    with ExitStack() as stack:
        _, _, _, mock_index, mock_retriever, mock_build_reranker = _setup_search_mocks(
            stack, with_reranker=True
        )
        mock_retriever.retrieve.return_value = mock_nodes
        fake_reranker = MagicMock()
        fake_reranker.rerank.return_value = reranked_results
        mock_build_reranker.return_value = fake_reranker

        client = TestClient(app)
        response = client.post(
            "/api/v1/search",
            json={"query": "测试", "kb_id": 1, "top_k": 5, "rerank": True},
            headers=auth_headers(),
        )

    assert response.status_code == 200
    call_kwargs = mock_index.as_retriever.call_args[1]
    assert call_kwargs["similarity_top_k"] == 25


def test_search_rerank_with_explicit_top_k():
    """rerank=true + rerank_top_k 时，retriever 使用 rerank_top_k，最终返回 top_k 条。"""
    from src.rag.schemas import SearchResult

    candidates = [
        SearchResult(
            chunk_index=i,
            document_id=10,
            kb_id=1,
            score=0.9 - i * 0.1,
            content=f"chunk {i}",
            token_count=5,
            source_page=None,
            section_title=None,
            section_path=None,
            filename="a.md",
            content_type="text/markdown",
        )
        for i in range(8)
    ]
    reranked = candidates[:3]

    with ExitStack() as stack:
        _, _, _, mock_index, mock_retriever, mock_build_reranker = _setup_search_mocks(
            stack, with_reranker=True
        )
        mock_nodes = [
            _mock_node_with_score(
                c.content,
                c.score,
                {
                    "kb_id": c.kb_id,
                    "pivot_document_id": c.document_id,
                    "chunk_index": c.chunk_index,
                    "filename": c.filename,
                    "content_type": c.content_type,
                    "token_count": c.token_count,
                },
            )
            for c in candidates
        ]
        mock_retriever.retrieve.return_value = mock_nodes
        fake_reranker = MagicMock()
        fake_reranker.rerank.return_value = reranked
        mock_build_reranker.return_value = fake_reranker

        client = TestClient(app)
        response = client.post(
            "/api/v1/search",
            json={
                "query": "测试",
                "kb_id": 1,
                "top_k": 3,
                "rerank": True,
                "rerank_top_k": 8,
            },
            headers=auth_headers(),
        )

    assert response.status_code == 200
    call_kwargs = mock_index.as_retriever.call_args[1]
    assert call_kwargs["similarity_top_k"] == 8
    data = response.json()
    assert data["total"] == 3
    assert len(data["hits"]) == 3


def test_search_rerank_changes_result_order():
    """fake reranker 反转顺序时，响应应反映 reranker 的输出顺序。"""
    from src.rag.schemas import SearchResult

    original_order = [
        SearchResult(
            chunk_index=0,
            document_id=10,
            kb_id=1,
            score=0.9,
            content="高分 chunk",
            token_count=5,
            source_page=None,
            section_title=None,
            section_path=None,
            filename="a.md",
            content_type="text/markdown",
        ),
        SearchResult(
            chunk_index=1,
            document_id=10,
            kb_id=1,
            score=0.7,
            content="低分 chunk",
            token_count=5,
            source_page=None,
            section_title=None,
            section_path=None,
            filename="a.md",
            content_type="text/markdown",
        ),
    ]
    reversed_order = list(reversed(original_order))

    with ExitStack() as stack:
        _, _, _, mock_index, mock_retriever, mock_build_reranker = _setup_search_mocks(
            stack, with_reranker=True
        )
        mock_nodes = [
            _mock_node_with_score(
                c.content,
                c.score,
                {
                    "kb_id": c.kb_id,
                    "pivot_document_id": c.document_id,
                    "chunk_index": c.chunk_index,
                    "filename": c.filename,
                    "content_type": c.content_type,
                    "token_count": c.token_count,
                },
            )
            for c in original_order
        ]
        mock_retriever.retrieve.return_value = mock_nodes
        fake_reranker = MagicMock()
        fake_reranker.rerank.return_value = reversed_order
        mock_build_reranker.return_value = fake_reranker

        client = TestClient(app)
        response = client.post(
            "/api/v1/search",
            json={"query": "测试", "kb_id": 1, "top_k": 2, "rerank": True},
            headers=auth_headers(),
        )

    assert response.status_code == 200
    data = response.json()
    assert data["hits"][0]["content"] == "低分 chunk"
    assert data["hits"][1]["content"] == "高分 chunk"


def test_search_rerank_unconfigured_returns_503():
    """未配置 reranker 但请求 rerank=true 时，返回 503。"""
    with ExitStack() as stack:
        _, _, _, _, mock_retriever = _setup_search_mocks(stack)
        mock_retriever.retrieve.return_value = [
            _mock_node_with_score(
                "chunk",
                0.5,
                {
                    "kb_id": 1,
                    "pivot_document_id": 10,
                    "chunk_index": 0,
                    "filename": "a.md",
                    "content_type": "text/markdown",
                    "token_count": 5,
                },
            ),
        ]
        # 模拟 build_reranker 抛出 RerankerUnavailableError
        stack.enter_context(
            patch(
                "src.rag.retrieval.build_reranker",
                side_effect=RerankerUnavailableError("reranker 未配置"),
            )
        )

        client = TestClient(app)
        response = client.post(
            "/api/v1/search",
            json={"query": "测试", "kb_id": 1, "top_k": 5, "rerank": True},
            headers=auth_headers(),
        )

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert "reranker 未配置" in detail or "不可用" in detail


def test_search_rerank_top_k_less_than_top_k_returns_422():
    """rerank_top_k < top_k 时，返回 422 校验错误。"""
    client = TestClient(app)
    response = client.post(
        "/api/v1/search",
        json={
            "query": "测试",
            "kb_id": 1,
            "top_k": 10,
            "rerank": True,
            "rerank_top_k": 5,
        },
        headers=auth_headers(),
    )
    assert response.status_code == 422


# ── HuggingFaceReranker unit tests ──────────────────────────────


def test_huggingface_reranker_sorts_by_score():
    """HuggingFaceReranker 按模型打分重排序并更新 score。"""
    from src.rag.schemas import SearchResult

    results = [
        SearchResult(
            chunk_index=0,
            document_id=10,
            kb_id=1,
            score=0.9,
            content="低相关",
            token_count=5,
            source_page=None,
            section_title=None,
            section_path=None,
            filename="a.md",
            content_type="text/markdown",
        ),
        SearchResult(
            chunk_index=1,
            document_id=10,
            kb_id=1,
            score=0.5,
            content="高相关",
            token_count=5,
            source_page=None,
            section_title=None,
            section_path=None,
            filename="a.md",
            content_type="text/markdown",
        ),
    ]

    with patch("src.rag.rerank._CrossEncoder") as MockCE:
        import numpy as np

        MockCE.return_value.predict.return_value = np.array([0.3, 0.9])

        from src.rag.rerank import HuggingFaceReranker

        reranker = HuggingFaceReranker("test-model")
        ranked = reranker.rerank("query", results)

    assert ranked[0].content == "高相关"
    assert ranked[0].score == 0.9
    assert ranked[1].content == "低相关"
    assert ranked[1].score == 0.3


def test_huggingface_reranker_empty_input():
    """空列表输入直接返回空列表。"""
    with patch("src.rag.rerank._CrossEncoder") as MockCE:
        from src.rag.rerank import HuggingFaceReranker

        reranker = HuggingFaceReranker("test-model")
        ranked = reranker.rerank("query", [])

    assert ranked == []
    MockCE.return_value.predict.assert_not_called()
