from langchain_core.documents import Document

from app.tools.knowledge_tool import format_docs


def test_format_docs_emits_stable_chunk_citations() -> None:
    docs = [
        Document(
            page_content="Restart only after checking active connections.",
            metadata={
                "chunk_id": "runbook-checkout-3",
                "_file_name": "checkout.md",
                "h1": "Checkout Runbook",
            },
        )
    ]

    formatted = format_docs(docs)

    assert "[doc:runbook-checkout-3]" in formatted
    assert "来源: checkout.md" in formatted
    assert "Checkout Runbook" in formatted


def test_format_docs_hashes_content_when_chunk_id_is_missing() -> None:
    doc = Document(page_content="same content", metadata={"_file_name": "ops.md"})

    first = format_docs([doc])
    second = format_docs([doc])

    assert first == second
    assert "[doc:" in first
