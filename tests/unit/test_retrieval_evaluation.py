from app.evals.retrieval import evaluate_retrieval


def test_retrieval_metrics_separate_relevance_recall_and_citations() -> None:
    metrics = evaluate_retrieval(
        retrieved_ids=["doc-a", "doc-b", "doc-noise"],
        relevant_ids={"doc-a", "doc-b", "doc-c"},
        report="Root cause [doc:doc-a] and mitigation [doc:doc-b].",
        supported_claims=2,
        total_claims=2,
    )

    assert metrics.context_precision == 2 / 3
    assert metrics.context_recall == 2 / 3
    assert metrics.citation_coverage == 1.0
    assert metrics.faithfulness == 1.0


def test_retrieval_metrics_handle_empty_denominators() -> None:
    metrics = evaluate_retrieval(
        retrieved_ids=[],
        relevant_ids=set(),
        report="",
        supported_claims=0,
        total_claims=0,
    )

    assert metrics.context_precision == 0.0
    assert metrics.context_recall == 0.0
    assert metrics.citation_coverage == 0.0
    assert metrics.faithfulness == 0.0
