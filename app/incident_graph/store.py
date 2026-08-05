"""NetworkX-backed graph store behind project-owned contracts."""

from __future__ import annotations

from collections.abc import Iterable

import networkx as nx

from app.incident_graph.models import EdgeType, GraphEdge, GraphNode, NodeType


class NetworkXIncidentGraph:
    def __init__(self) -> None:
        self._graph = nx.MultiDiGraph()

    def upsert_node(self, node: GraphNode) -> None:
        self._graph.add_node(node.id, record=node.to_record())

    def get_node(self, node_id: str) -> GraphNode | None:
        if node_id not in self._graph:
            return None
        return GraphNode.model_validate(self._graph.nodes[node_id]["record"])

    def add_edge(self, edge: GraphEdge) -> None:
        missing = [
            node_id
            for node_id in (edge.source, edge.target)
            if node_id not in self._graph
        ]
        if missing:
            raise ValueError(f"missing graph node: {', '.join(missing)}")
        self._graph.add_edge(
            edge.source,
            edge.target,
            key=f"{edge.type.value}:{self._graph.number_of_edges()}",
            record=edge.to_record(),
        )

    def nodes(self, node_type: NodeType | str | None = None) -> list[GraphNode]:
        records = [
            GraphNode.model_validate(data["record"])
            for _node_id, data in self._graph.nodes(data=True)
        ]
        if node_type is None:
            return records
        resolved = NodeType(node_type)
        return [item for item in records if item.type is resolved]

    def edges(self, edge_type: EdgeType | str | None = None) -> list[GraphEdge]:
        records = [
            GraphEdge.model_validate(data["record"])
            for _source, _target, _key, data in self._graph.edges(
                keys=True,
                data=True,
            )
        ]
        if edge_type is None:
            return records
        resolved = EdgeType(edge_type)
        return [item for item in records if item.type is resolved]

    def outgoing(
        self,
        node_id: str,
        edge_type: EdgeType | str | None = None,
    ) -> list[tuple[GraphEdge, GraphNode]]:
        resolved = EdgeType(edge_type) if edge_type is not None else None
        output = []
        for _source, target, _key, data in self._graph.out_edges(
            node_id,
            keys=True,
            data=True,
        ):
            edge = GraphEdge.model_validate(data["record"])
            if resolved is not None and edge.type is not resolved:
                continue
            output.append((edge, self.get_node(target)))
        return [(edge, node) for edge, node in output if node is not None]

    def incoming(
        self,
        node_id: str,
        edge_type: EdgeType | str | None = None,
    ) -> list[tuple[GraphEdge, GraphNode]]:
        resolved = EdgeType(edge_type) if edge_type is not None else None
        output = []
        for source, _target, _key, data in self._graph.in_edges(
            node_id,
            keys=True,
            data=True,
        ):
            edge = GraphEdge.model_validate(data["record"])
            if resolved is not None and edge.type is not resolved:
                continue
            output.append((edge, self.get_node(source)))
        return [(edge, node) for edge, node in output if node is not None]

    def neighborhood(self, seed_ids: Iterable[str], max_hops: int) -> set[str]:
        undirected = self._graph.to_undirected()
        found = set(seed_ids)
        for seed_id in seed_ids:
            if seed_id not in undirected:
                continue
            lengths = nx.single_source_shortest_path_length(
                undirected,
                seed_id,
                cutoff=max_hops,
            )
            found.update(lengths)
        return found

    def to_record(self) -> dict[str, object]:
        return {
            "nodes": [item.to_record() for item in self.nodes()],
            "edges": [item.to_record() for item in self.edges()],
        }

    @classmethod
    def from_record(cls, record: dict[str, object]) -> NetworkXIncidentGraph:
        graph = cls()
        for item in record.get("nodes", []):
            graph.upsert_node(GraphNode.model_validate(item))
        for item in record.get("edges", []):
            graph.add_edge(GraphEdge.model_validate(item))
        return graph
