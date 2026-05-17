---
doc-id: AGENT-RES-001
agent-name: research
agent-id: AGT-005
status: STUB
trust-tier: T1 (Advisory)
layer: AAL (Application / Agent Layer)
role: External knowledge / standards research agent (planned)
implementation-path: CIPHER_Repo/cipher/agents/research/
planned-port: 7005
last-updated: 2026-05-17
---

# Research Agent — AGENT-RES-001

> **Status: STUB.** Only a README placeholder exists. This document describes the *planned* role per `CIPHER_HLD.md` §6.6 and `CIPHER_archi.md` §4.1; no executable code is shipped yet.

## §1 Role & Capabilities (Planned)

The Research Agent is intended to be the **RAG specialist** of CIPHER — the agent other agents call when they need external or internal context that is not already in their working memory.

Planned capabilities, drawn from HLD §6.6 and the architecture taxonomy (archi.md §4.1):

- **External standards retrieval.** Fetch and summarize relevant passages from AUTOSAR specification PDFs, ISO 26262 clauses, MISRA C rule descriptions, and supplier datasheets.
- **Internal corpus retrieval.** Index and search team wikis, prior project artifacts (HLDs, LLDs, test reports), and CAR documents already in the Knowledge Graph.
- **Hybrid retrieval pipeline.** Vector search (Qdrant) + graph expansion (Memgraph PageRank) + cross-encoder rerank (bge-reranker-large), assembled into a token-budgeted **context pack** returned as a `ContextHandle`.
- **Internet research (policy-gated).** When OPA policy permits, fetch from approved external sources; all fetched content passes through the guardrail strip step (HLD §10 input-injection guidance).

This is the same workflow pattern observed manually in the **Dio demo trial**, where a human-driven "Scout" step (see `CAR-004` through `CAR-008`) gathered external standards references before downstream CAR drafting. The Research Agent is the automation target for that pattern.

## §2 Current State

**STUB.** The implementation directory contains only a README placeholder:

```
cipher/agents/research/
└── README.md   (3 lines: "Phase 2 advisory retrieval stub for datasheets, prior artifacts, and external technical context.")
```

No `__init__.py`, no agent skeleton, no A2A skill registration, no port :7005 listener. The agent is enumerated in the AAL roll-up and the architecture diagrams (HLD lines 192, 633, 693, 1448) but is not yet wired into the A2A Gateway, ToolBroker, or LangGraph fan-out from the Orchestrator.

## §3 Planned UC Mapping

The Research Agent supports use cases that need evidence-gathering before generation:

| Use case | Research Agent role |
|---|---|
| CAR document generation (à la Dio demo CAR-004..008) | Pull AUTOSAR / ISO 26262 reference passages cited in each CAR. |
| LLD / HLD drafting by DevNex | Provide datasheet excerpts and prior-project precedent before code generation. |
| Compliance Agent (AGT-004) evidence assembly | Retrieve normative clauses that compliance rules trace to. |
| ASIL Reviewer (AGT-003) rubric grounding | Surface ISO 26262 Part 6 / 8 clauses relevant to the artifact under review. |

## §4 Inputs / Outputs (Planned)

**A2A skill:** `research_query`

- **Input:** `{ query: str, context_handle: ContextHandle, token_budget: int, source_filter: ["autosar","iso26262","misra","wiki","internet"] }`
- **Output:** `ContextHandle` pointing to an assembled, reranked context pack stored in MKF (caller materializes on demand to avoid blowing the token budget).

## §5 Dependencies (Planned)

- **TRF (LLM Gateway).** For query expansion and reranking calls; routed via `TaskClassRouter`.
- **MKF (Memory & Knowledge Fabric).** Primary downstream — calls `memory.retrieve()` for the four-stage hybrid retrieval pipeline. Caches fetched external documents so the same standard clause is not refetched per request.
- **GCL (Governance & Control Layer).** OPA policy decides which external sources are permitted per project; every external fetch writes an entry to the SQLite audit journal so the provenance of external evidence is auditable.
- **ToolBroker (AGT-008).** When implemented, all internet fetches go through ToolBroker MCP `tasks/call`, never directly from the agent process.

## §6 Open Items

- **Not yet implemented.** No code, no port listener, no A2A registration.
- **Corpus indexing pipeline undefined.** HLD §6.6 mentions "indexed at project setup time" but no setup hook exists.
- **Scout-pattern automation gap.** The Dio demo trial showed the value of the Scout role (CAR-004..008) end-to-end, but those CARs were assembled by a human operator; this agent is the planned automation target. Until it lands, CAR generation remains a manual evidence-gathering step.
- **Internet policy.** OPA bundles for `research.internet.allow` are not yet authored.
- **Reranker hosting.** `bge-reranker-large` is referenced in HLD but not present in the local `ollama pull` bootstrap; deployment story TBD.
