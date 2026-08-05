"""Deterministic local/global GraphRAG context extraction."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict

from app.incident_graph.models import GraphEdge, GraphNode
from app.incident_graph.store import NetworkXIncidentGraph
from app.retrieval.hybrid import DocumentChunk, HybridRetriever


def _tokens(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]+", value.lower()))


class GraphRAGContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    seed_node_ids: tuple[str, ...]
    nodes: tuple[GraphNode, ...]
    edges: tuple[GraphEdge, ...]
    global_summary: dict[str, object]
    documents: tuple[DocumentChunk, ...]
    citations: tuple[str, ...]

    def to_record(self) -> dict[str, object]:
        return self.model_dump(mode="json")


class GraphRAGRetriever:
    def __init__(
        self,
        graph: NetworkXIncidentGraph,
        *,
        documents: Sequence[DocumentChunk] = (),
        hybrid_retriever: HybridRetriever | None = None,
    ) -> None:
        self.graph = graph
        self.documents = list(documents)
        self.hybrid_retriever = hybrid_retriever

    def retrieve(
        self,
        query: str,
        *,
        max_hops: int = 2,
        top_k_documents: int = 5,
    ) -> GraphRAGContext:
        query_tokens = _tokens(query)
        seeds = []
        for node in self.graph.nodes():
            searchable = f"{node.name} {node.properties}"
            if query_tokens & _tokens(searchable):
                seeds.append(node.id)

        neighborhood_ids = self.graph.neighborhood(seeds, max_hops)
        nodes = tuple(
            node for node in self.graph.nodes() if node.id in neighborhood_ids
        )
        edges = tuple(
            edge
            for edge in self.graph.edges()
            if edge.source in neighborhood_ids and edge.target in neighborhood_ids
        )
        if self.hybrid_retriever is not None:
            documents = tuple(
                item.chunk
                for item in self.hybrid_retriever.search(
                    query,
                    top_k=top_k_documents,
                )
            )
        else:
            ranked_documents = sorted(
                self.documents,
                key=lambda item: (
                    -len(query_tokens & _tokens(item.content)),
                    item.chunk_id,
                ),
            )
            documents = tuple(
                item
                for item in ranked_documents
                if query_tokens & _tokens(item.content)
            )[:top_k_documents]
        node_types = Counter(node.type.value for node in self.graph.nodes())
        edge_types = Counter(edge.type.value for edge in self.graph.edges())
        citations = tuple(
            [f"[graph:{node.id}]" for node in nodes]
            + [f"[doc:{document.chunk_id}]" for document in documents]
        )
        return GraphRAGContext(
            seed_node_ids=tuple(seeds),
            nodes=nodes,
            edges=edges,
            global_summary={
                "node_count": len(self.graph.nodes()),
                "edge_count": len(self.graph.edges()),
                "node_types": dict(node_types),
                "edge_types": dict(edge_types),
            },
            documents=documents,
            citations=citations,
        )
