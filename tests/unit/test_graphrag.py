import json

from app.incident_graph import GraphEdge, GraphNode, NetworkXIncidentGraph
from app.incident_graph.graphrag import GraphRAGRetriever
from app.retrieval.hybrid import DocumentChunk, HybridRetriever


def test_graphrag_combines_entity_neighborhood_global_summary_and_documents() -> None:
    graph = NetworkXIncidentGraph()
    graph.upsert_node(
        GraphNode(
            id="payment",
            type="service",
            name="Payment Service",
            properties={"owner": "payments-sre"},
        )
    )
    graph.upsert_node(
        GraphNode(id="inventory", type="service", name="Inventory Service")
    )
    graph.upsert_node(
        GraphNode(
            id="change-v2",
            type="change",
            name="Payment v2 rollout",
        )
    )
    graph.add_edge(
        GraphEdge(source="payment", target="inventory", type="depends_on")
    )
    graph.add_edge(
        GraphEdge(source="payment", target="change-v2", type="changed_by")
    )
    document = DocumentChunk(
        chunk_id="payment-runbook",
        content="Payment CPU diagnosis and rollback evidence",
        source="runbooks/payment.md",
        service="payment",
    )

    context = GraphRAGRetriever(graph, documents=[document]).retrieve(
        "payment CPU after rollout",
        max_hops=1,
        top_k_documents=2,
    )

    assert context.seed_node_ids == ("payment", "change-v2")
    assert {node.id for node in context.nodes} == {
        "payment",
        "inventory",
        "change-v2",
    }
    assert context.global_summary["node_types"]["service"] == 2
    assert context.documents[0].chunk_id == "payment-runbook"
    assert "[graph:payment]" in context.citations
    assert "[doc:payment-runbook]" in context.citations
    json.dumps(context.to_record())


def test_graphrag_uses_hybrid_retriever_for_vector_only_documents() -> None:
    graph = NetworkXIncidentGraph()
    graph.upsert_node(GraphNode(id="payment", type="service", name="Payment"))
    document = DocumentChunk(
        chunk_id="historical-case",
        content="opaque archived incident",
        source="incidents/payment-2025.md",
        service="payment",
    )
    hybrid = HybridRetriever(
        [document],
        vector_search=lambda _query, _top_k: [("historical-case", 0.99)],
    )

    context = GraphRAGRetriever(
        graph,
        documents=[document],
        hybrid_retriever=hybrid,
    ).retrieve("payment CPU saturation")

    assert [item.chunk_id for item in context.documents] == ["historical-case"]
    assert "[doc:historical-case]" in context.citations
