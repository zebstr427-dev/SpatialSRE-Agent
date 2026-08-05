import json

import pytest

from app.incident_graph import (
    GraphEdge,
    GraphNode,
    IncidentGraphQueries,
    NetworkXIncidentGraph,
)


def _graph() -> NetworkXIncidentGraph:
    graph = NetworkXIncidentGraph()
    for node in (
        GraphNode(id="checkout", type="service", name="Checkout"),
        GraphNode(id="payment", type="service", name="Payment"),
        GraphNode(id="inventory", type="service", name="Inventory"),
        GraphNode(
            id="change-v2",
            type="change",
            name="Payment v2 deployment",
            properties={"timestamp": "2026-08-05T01:55:00+00:00"},
        ),
        GraphNode(
            id="incident-old",
            type="incident",
            name="Payment CPU incident",
            properties={"error_code": "THREAD_POOL_EXHAUSTED"},
        ),
        GraphNode(
            id="incident-current",
            type="incident",
            name="Current payment incident",
            properties={"error_code": "THREAD_POOL_EXHAUSTED"},
        ),
    ):
        graph.upsert_node(node)
    for edge in (
        GraphEdge(source="checkout", target="payment", type="depends_on"),
        GraphEdge(source="payment", target="inventory", type="depends_on"),
        GraphEdge(source="payment", target="change-v2", type="changed_by"),
        GraphEdge(
            source="incident-current",
            target="payment",
            type="affects",
        ),
        GraphEdge(source="incident-old", target="payment", type="affects"),
    ):
        graph.add_edge(edge)
    return graph


def test_graph_validates_endpoints_and_round_trips_json() -> None:
    graph = _graph()

    with pytest.raises(ValueError, match="missing graph node"):
        graph.add_edge(
            GraphEdge(source="checkout", target="missing", type="depends_on")
        )

    restored = NetworkXIncidentGraph.from_record(graph.to_record())

    assert restored.get_node("payment").name == "Payment"
    assert len(restored.edges()) == len(graph.edges())
    json.dumps(restored.to_record())


def test_graph_queries_cover_dependencies_impact_changes_and_similarity() -> None:
    queries = IncidentGraphQueries(_graph())

    assert [node.id for node in queries.dependencies("checkout", max_depth=2)] == [
        "payment",
        "inventory",
    ]
    assert [node.id for node in queries.impacted_services("payment")] == [
        "checkout"
    ]
    correlated = queries.correlated_changes(
        "payment",
        start="2026-08-05T01:30:00+00:00",
        end="2026-08-05T02:00:00+00:00",
    )
    assert [node.id for node in correlated] == ["change-v2"]
    assert [node.id for node in queries.similar_incidents("incident-current")] == [
        "incident-old"
    ]
