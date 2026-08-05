from app.retrieval.hybrid import (
    DeterministicReranker,
    DocumentChunk,
    HybridRetriever,
    MetadataFilter,
    QueryRewriter,
)


def _corpus() -> list[DocumentChunk]:
    return [
        DocumentChunk(
            chunk_id="cpu-runbook",
            content="checkout high CPU thread pool saturation runbook",
            source="runbooks/cpu.md",
            service="checkout",
            fault_type="cpu",
            version="v2",
            timestamp="2026-08-01T00:00:00+00:00",
        ),
        DocumentChunk(
            chunk_id="payment-history",
            content="payment timeout after deployment historical incident",
            source="incidents/payment.md",
            service="payment",
            fault_type="latency",
            version="v1",
            timestamp="2026-07-01T00:00:00+00:00",
        ),
        DocumentChunk(
            chunk_id="checkout-deploy",
            content="checkout deployment rollback procedure",
            source="runbooks/rollback.md",
            service="checkout",
            fault_type="deployment",
            version="v2",
            timestamp="2026-08-02T00:00:00+00:00",
        ),
    ]


def test_query_rewrite_adds_operational_context_without_llm() -> None:
    rewritten = QueryRewriter().rewrite(
        "Why is CPU high?",
        service="checkout",
        fault_type="cpu",
    )

    assert rewritten == "why is cpu high checkout incident diagnosis"


def test_hybrid_search_fuses_vector_and_keyword_ranks_with_citations() -> None:
    def vector_search(_query: str, _top_k: int):
        return [("checkout-deploy", 0.95), ("cpu-runbook", 0.80)]

    retriever = HybridRetriever(
        _corpus(),
        vector_search=vector_search,
        reranker=DeterministicReranker(),
    )

    results = retriever.search(
        "checkout CPU saturation",
        top_k=2,
        metadata_filter=MetadataFilter(service="checkout", version="v2"),
    )

    assert results[0].chunk.chunk_id == "cpu-runbook"
    assert results[0].lexical_rank == 1
    assert results[0].citation == "[doc:cpu-runbook] runbooks/cpu.md"
    assert all(item.chunk.service == "checkout" for item in results)


def test_vector_failure_falls_back_to_bm25_and_applies_time_filter() -> None:
    def unavailable(_query: str, _top_k: int):
        raise RuntimeError("Milvus unavailable")

    retriever = HybridRetriever(_corpus(), vector_search=unavailable)

    results = retriever.search(
        "payment timeout deployment",
        top_k=3,
        metadata_filter=MetadataFilter(
            start_time="2026-06-01T00:00:00+00:00",
            end_time="2026-07-15T00:00:00+00:00",
        ),
    )

    assert [item.chunk.chunk_id for item in results] == ["payment-history"]
    assert results[0].vector_rank is None


def test_metadata_filter_supports_fault_type_and_source() -> None:
    retriever = HybridRetriever(_corpus())

    results = retriever.search(
        "rollback",
        top_k=5,
        metadata_filter=MetadataFilter(
            fault_type="deployment",
            source_prefix="runbooks/",
        ),
    )

    assert [item.chunk.chunk_id for item in results] == ["checkout-deploy"]
