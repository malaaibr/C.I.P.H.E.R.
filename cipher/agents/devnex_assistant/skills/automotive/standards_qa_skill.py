"""standards_qa_skill.py — UC 4.1: ISO 26262 / AUTOSAR / MISRA-C Standards Q&A.

Architecture:
  - Dense retrieval : Qdrant vector store (pluggable — falls back to in-memory)
  - Sparse retrieval: BM25 (rank-bm25 or fallback keyword search)
  - Score fusion   : hybrid_score = alpha * dense_score + (1 - alpha) * bm25_score
  - Answer gen     : Ollama TRIAGE (summarise) -> citation-formatted response

Index keys supported:
  "iso26262"   — ISO 26262 Parts 1-12
  "misra_c"    — MISRA-C:2012 / 2023
  "autosar"    — AUTOSAR R20-11 / R21-11 BSW specs
  "codebase"   — Project codebase (UC 4.2 reuse)
"""
from __future__ import annotations

import json
import math
import re
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

try:
    from core.console_logging import format_console_log, utc_timestamp
except (ImportError, AttributeError):
    def format_console_log(module, level, msg, ts="", caller=""):
        return f"[{level}] {module}: {msg}"

    def utc_timestamp():
        from datetime import datetime, timezone
        return datetime.now(tz=timezone.utc).isoformat()

MODULE_NAME = "StandardsQASkill"

# Alpha weight: 0.7 dense + 0.3 BM25 (configurable)
DEFAULT_ALPHA = 0.7
TOP_K         = 5


@dataclass
class SourceChunk:
    """One retrieved passage from the knowledge index."""
    doc_id:     str
    text:       str
    source:     str        # e.g. "ISO 26262-6:2018 §8.4.3"
    dense_score:  float = 0.0
    bm25_score:   float = 0.0
    hybrid_score: float = 0.0


@dataclass
class QAAnswer:
    """Result of a standards Q&A query."""
    question:   str
    answer:     str
    sources:    list = field(default_factory=list)
    index_used: str = ""
    top_k:      int = TOP_K


class HybridRetriever:
    """
    Hybrid BM25 + Dense retriever.

    When Qdrant is unavailable the retriever falls back to a pure BM25 /
    keyword search over an in-memory document store, so UC 4.1 remains
    functional without the vector database running.
    """

    def __init__(
        self,
        index_key: str = "iso26262",
        alpha: float   = DEFAULT_ALPHA,
        qdrant_url: str = "http://localhost:6333",
        ollama_url: str = "http://localhost:11434",
    ) -> None:
        self._index_key  = index_key
        self._alpha      = alpha
        self._qdrant_url = qdrant_url
        self._ollama_url = ollama_url
        self._mem_store: list[dict] = []   # in-memory fallback docs
        self._qdrant_ok: bool | None = None

    # ── Public ────────────────────────────────────────────────────────────

    def load_documents(self, docs: list[dict]) -> None:
        """
        Populate the in-memory BM25 fallback store.

        Each doc: {"id": str, "text": str, "source": str}
        """
        self._mem_store = docs

    def retrieve(self, query: str, top_k: int = TOP_K) -> list[SourceChunk]:
        """
        Retrieve top-k chunks for *query* using hybrid scoring.

        Falls back gracefully: Qdrant + BM25 -> BM25 only -> keyword only.
        """
        bm25_results  = self._bm25_search(query, top_k * 2)
        dense_results = self._dense_search(query, top_k * 2)

        # Merge by doc_id
        merged: dict[str, SourceChunk] = {}
        for chunk in bm25_results:
            merged[chunk.doc_id] = chunk
        for chunk in dense_results:
            if chunk.doc_id in merged:
                merged[chunk.doc_id].dense_score = chunk.dense_score
            else:
                merged[chunk.doc_id] = chunk

        # Compute hybrid score
        for chunk in merged.values():
            chunk.hybrid_score = (
                self._alpha * chunk.dense_score
                + (1 - self._alpha) * chunk.bm25_score
            )

        ranked = sorted(merged.values(), key=lambda c: c.hybrid_score, reverse=True)
        return ranked[:top_k]

    # ── BM25 (pure-Python TF-IDF fallback) ───────────────────────────────

    def _bm25_search(self, query: str, top_k: int) -> list[SourceChunk]:
        if not self._mem_store:
            return []
        try:
            from rank_bm25 import BM25Okapi
            tokenised_corpus = [doc["text"].lower().split() for doc in self._mem_store]
            bm25 = BM25Okapi(tokenised_corpus)
            scores = bm25.get_scores(query.lower().split())
        except ImportError:
            # Fallback: naive TF scoring
            scores = [self._naive_tf(query, doc["text"]) for doc in self._mem_store]

        indexed = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[:top_k]
        results = []
        max_s = max((s for _, s in indexed), default=1.0) or 1.0
        for idx, score in indexed:
            doc = self._mem_store[idx]
            results.append(SourceChunk(
                doc_id     = doc.get("id", str(idx)),
                text       = doc.get("text", ""),
                source     = doc.get("source", ""),
                bm25_score = score / max_s,
            ))
        return results

    @staticmethod
    def _naive_tf(query: str, text: str) -> float:
        terms = re.findall(r"\w+", query.lower())
        text_lower = text.lower()
        return sum(text_lower.count(t) for t in terms) / (len(text_lower) + 1)

    # ── Dense retrieval via Qdrant ────────────────────────────────────────

    def _dense_search(self, query: str, top_k: int) -> list[SourceChunk]:
        if self._qdrant_ok is False:
            return []
        embedding = self._embed_query(query)
        if embedding is None:
            self._qdrant_ok = False
            return []
        try:
            body = json.dumps({
                "vector": embedding,
                "limit": top_k,
                "with_payload": True,
            }).encode()
            req = urllib.request.Request(
                f"{self._qdrant_url}/collections/{self._index_key}/points/search",
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
            self._qdrant_ok = True
            results = []
            for hit in data.get("result", []):
                payload = hit.get("payload", {})
                results.append(SourceChunk(
                    doc_id      = str(hit.get("id", "")),
                    text        = payload.get("text", ""),
                    source      = payload.get("source", ""),
                    dense_score = float(hit.get("score", 0.0)),
                ))
            return results
        except Exception:
            self._qdrant_ok = False
            return []

    def _embed_query(self, query: str) -> list[float] | None:
        """Get embedding from Ollama /api/embeddings endpoint."""
        try:
            body = json.dumps({"model": "nomic-embed-text", "prompt": query}).encode()
            req = urllib.request.Request(
                f"{self._ollama_url}/api/embeddings",
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
            return data.get("embedding")
        except Exception:
            return None


class StandardsQASkill:
    """UC 4.1 — ISO 26262 / AUTOSAR / MISRA-C Standards Q&A via Hybrid RAG.

    Parameters
    ----------
    orchestrator :
        Optional DevNexOrchestrator — provides config and GCA invoker.
    index_key :
        Which knowledge index to query ('iso26262', 'misra_c', 'autosar', 'codebase').
    alpha :
        Dense/sparse fusion weight (0 = BM25-only, 1 = dense-only).
    ollama_url :
        Ollama REST endpoint for embedding + triage.
    qdrant_url :
        Qdrant vector database endpoint.
    on_log :
        Optional log callback.
    """

    def __init__(
        self,
        orchestrator=None,
        index_key:  str = "iso26262",
        alpha:      float = DEFAULT_ALPHA,
        ollama_url: str = "http://localhost:11434",
        qdrant_url: str = "http://localhost:6333",
        on_log: Callable | None = None,
    ) -> None:
        self._orch    = orchestrator
        self._on_log  = on_log or (lambda *_: None)
        self._ollama  = ollama_url
        self.retriever = HybridRetriever(
            index_key  = index_key,
            alpha      = alpha,
            qdrant_url = qdrant_url,
            ollama_url = ollama_url,
        )
        self._index_key = index_key

    # ── Public API ────────────────────────────────────────────────────────

    def answer(self, question: str, scope_filter: str = "") -> QAAnswer:
        """
        Answer a standards question using hybrid RAG.

        Parameters
        ----------
        question :
            Free-text question (e.g. 'What is ASIL-D requirements for software unit testing?')
        scope_filter :
            Optional chapter / rule filter (e.g. 'Part 6', 'R11.8').

        Returns QAAnswer with cited passages.
        """
        self._log(f"UC 4.1 Q&A | index={self._index_key} | question='{question[:80]}'")

        # Optionally narrow BM25 search with scope filter
        full_query = f"{scope_filter} {question}".strip() if scope_filter else question
        chunks = self.retriever.retrieve(full_query, top_k=TOP_K)

        if chunks:
            answer_text = self._generate_answer(question, chunks)
        else:
            answer_text = self._fallback_answer(question)

        sources = [
            {"source": c.source, "excerpt": c.text[:300], "score": round(c.hybrid_score, 3)}
            for c in chunks
        ]

        self._log(f"UC 4.1: Answer generated | {len(sources)} source(s) cited", level="SUCCESS")
        return QAAnswer(
            question   = question,
            answer     = answer_text,
            sources    = sources,
            index_used = self._index_key,
            top_k      = len(chunks),
        )

    def load_index(self, documents: list[dict]) -> None:
        """
        Seed the in-memory BM25 fallback index.

        Each document: {"id": str, "text": str, "source": str}
        Call this before answer() when Qdrant is not available.
        """
        self.retriever.load_documents(documents)
        self._log(f"UC 4.1: Loaded {len(documents)} document(s) into BM25 index.")

    # ── Private helpers ───────────────────────────────────────────────────

    def _generate_answer(self, question: str, chunks: list[SourceChunk]) -> str:
        """Build answer via Ollama TRIAGE over retrieved context."""
        context = "\n\n".join(
            f"[{c.source}]\n{c.text[:600]}"
            for c in chunks
        )
        prompt = (
            "You are an ISO 26262 / AUTOSAR / MISRA-C expert.\n"
            "Answer the question below using ONLY the provided context.\n"
            "For each claim, cite the source in parentheses: (Source: <citation>).\n"
            "If the context does not contain enough information, say so explicitly.\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {question}\n\n"
            "Answer:"
        )
        try:
            body = json.dumps({
                "model": "llama3",
                "prompt": prompt,
                "stream": False,
            }).encode()
            req = urllib.request.Request(
                f"{self._ollama}/api/generate",
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read())
            return data.get("response", "").strip()
        except Exception as exc:
            self._log(f"Ollama generate failed ({exc}) — using raw context.", level="WARN")
            return f"Context retrieved but LLM unavailable.\n\n{context[:1000]}"

    def _fallback_answer(self, question: str) -> str:
        return (
            f"[StandardsQASkill] No indexed documents found for index '{self._index_key}'.\n"
            f"Load documents via load_index() or connect Qdrant at {self.retriever._qdrant_url}.\n"
            f"Question received: {question}"
        )

    def _log(self, message: str, level: str = "INFO") -> None:
        line = format_console_log(MODULE_NAME, level, message, utc_timestamp(), "answer")
        print(line)
        self._on_log(message, level)
