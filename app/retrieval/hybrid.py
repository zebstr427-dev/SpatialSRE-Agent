"""Vendor-neutral query rewrite, BM25, rank fusion, rerank, and filters."""

from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Callable, Sequence
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]+", text.lower())


class DocumentChunk(BaseModel):
    model_config = ConfigDict(frozen=True)

    chunk_id: str
    content: str
    source: str
    service: str | None = None
    fault_type: str | None = None
    version: str | None = None
    timestamp: datetime | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class MetadataFilter(BaseModel):
    model_config = ConfigDict(frozen=True)

    service: str | None = None
    fault_type: str | None = None
    version: str | None = None
    source_prefix: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None

    def matches(self, chunk: DocumentChunk) -> bool:
        return (
            (self.service is None or chunk.service == self.service)
            and (self.fault_type is None or chunk.fault_type == self.fault_type)
            and (self.version is None or chunk.version == self.version)
            and (
                self.source_prefix is None
                or chunk.source.startswith(self.source_prefix)
            )
            and (
                self.start_time is None
                or (chunk.timestamp is not None and chunk.timestamp >= self.start_time)
            )
            and (
                self.end_time is None
                or (chunk.timestamp is not None and chunk.timestamp <= self.end_time)
            )
        )


class QueryRewriter:
    def rewrite(
        self,
        query: str,
        *,
        service: str | None = None,
        fault_type: str | None = None,
    ) -> str:
        terms = _tokens(query)
        terms.extend(_tokens(service or ""))
        terms.extend(_tokens(fault_type or ""))
        terms.extend(("incident", "diagnosis"))
        return " ".join(dict.fromkeys(terms))


class BM25Index:
    def __init__(self, chunks: Sequence[DocumentChunk]) -> None:
        self.chunks = list(chunks)
        self.term_frequencies = [Counter(_tokens(item.content)) for item in chunks]
        self.lengths = [sum(counter.values()) for counter in self.term_frequencies]
        self.average_length = (
            sum(self.lengths) / len(self.lengths) if self.lengths else 0.0
        )
        self.document_frequency = Counter()
        for counter in self.term_frequencies:
            self.document_frequency.update(counter.keys())

    def scores(self, query: str) -> dict[str, float]:
        query_terms = set(_tokens(query))
        total = len(self.chunks)
        scores = {}
        for chunk, frequencies, length in zip(
            self.chunks,
            self.term_frequencies,
            self.lengths,
            strict=True,
        ):
            score = 0.0
            for term in query_terms:
                frequency = frequencies.get(term, 0)
                if not frequency:
                    continue
                document_frequency = self.document_frequency[term]
                inverse_frequency = math.log(
                    1 + (total - document_frequency + 0.5) / (document_frequency + 0.5)
                )
                normalization = frequency + 1.5 * (
                    0.25
                    + 0.75
                    * (length / self.average_length if self.average_length else 0)
                )
                score += inverse_frequency * (frequency * 2.5) / normalization
            scores[chunk.chunk_id] = score
        return scores


class RetrievalResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    chunk: DocumentChunk
    hybrid_score: float
    rerank_score: float
    lexical_rank: int | None
    vector_rank: int | None
    citation: str


class DeterministicReranker:
    def score(self, query: str, chunk: DocumentChunk, hybrid_score: float) -> float:
        query_terms = set(_tokens(query))
        content_terms = set(_tokens(chunk.content))
        overlap = len(query_terms & content_terms) / max(len(query_terms), 1)
        return hybrid_score + overlap


VectorSearch = Callable[[str, int], Sequence[tuple[str, float]]]


class HybridRetriever:
    def __init__(
        self,
        corpus: Sequence[DocumentChunk],
        *,
        vector_search: VectorSearch | None = None,
        query_rewriter: QueryRewriter | None = None,
        reranker: DeterministicReranker | None = None,
    ) -> None:
        self._corpus = list(corpus)
        self._by_id = {item.chunk_id: item for item in corpus}
        self._vector_search = vector_search
        self._query_rewriter = query_rewriter or QueryRewriter()
        self._reranker = reranker or DeterministicReranker()

    def search(
        self,
        query: str,
        *,
        top_k: int = 5,
        metadata_filter: MetadataFilter | None = None,
        service: str | None = None,
        fault_type: str | None = None,
    ) -> list[RetrievalResult]:
        rewritten = self._query_rewriter.rewrite(
            query,
            service=service,
            fault_type=fault_type,
        )
        filtered = [
            item
            for item in self._corpus
            if metadata_filter is None or metadata_filter.matches(item)
        ]
        allowed_ids = {item.chunk_id for item in filtered}
        lexical_scores = BM25Index(filtered).scores(rewritten)
        lexical_order = [
            chunk_id
            for chunk_id, score in sorted(
                lexical_scores.items(),
                key=lambda item: (-item[1], item[0]),
            )
            if score > 0
        ]
        lexical_ranks = {
            chunk_id: rank for rank, chunk_id in enumerate(lexical_order, 1)
        }

        vector_order: list[str] = []
        if self._vector_search is not None:
            try:
                vector_order = [
                    chunk_id
                    for chunk_id, _score in sorted(
                        self._vector_search(rewritten, max(top_k * 3, 10)),
                        key=lambda item: -item[1],
                    )
                    if chunk_id in allowed_ids
                ]
            except Exception:
                vector_order = []
        vector_ranks = {
            chunk_id: rank for rank, chunk_id in enumerate(vector_order, 1)
        }

        candidate_ids = set(lexical_ranks) | set(vector_ranks)
        results = []
        for chunk_id in candidate_ids:
            lexical_rank = lexical_ranks.get(chunk_id)
            vector_rank = vector_ranks.get(chunk_id)
            hybrid_score = (
                (1 / (60 + lexical_rank) if lexical_rank else 0)
                + (1 / (60 + vector_rank) if vector_rank else 0)
            )
            chunk = self._by_id[chunk_id]
            rerank_score = self._reranker.score(rewritten, chunk, hybrid_score)
            results.append(
                RetrievalResult(
                    chunk=chunk,
                    hybrid_score=hybrid_score,
                    rerank_score=rerank_score,
                    lexical_rank=lexical_rank,
                    vector_rank=vector_rank,
                    citation=f"[doc:{chunk.chunk_id}] {chunk.source}",
                )
            )
        return sorted(
            results,
            key=lambda item: (-item.rerank_score, item.chunk.chunk_id),
        )[:top_k]
