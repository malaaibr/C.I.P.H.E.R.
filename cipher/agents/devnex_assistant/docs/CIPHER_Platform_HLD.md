# CIPHER Platform — High-Level Design

> **Document revision:** Sprint 0 complete (2026-05-16)
> Covers the full CIPHER 7-layer architecture, the 24-UC capability catalog,
> three LLM backends, ASDLC process gates, and Sprint 0/1 delivery status.

---

## 1. What is CIPHER?

**CIPHER** (Cognitive Intelligence Platform for High-integrity Embedded Real-time systems)
is an AI-assisted engineering platform for ISO 26262 / ASPICE automotive SWC development.

It automates the full V-cycle — from HLD/LLD generation through code linking,
traceability, test generation, and final sign-off — while enforcing ASIL safety gates at
every handoff.

**Core principles:**
- Safety-first: ASIL-D violations hard-block the pipeline (`SemanticConflictError`)
- Traceable: every artifact links back through HLD → LLD → Code → Test
- Wrap-first: default WRAP (adapter), then REFACTOR, REWRITE only with explicit ADR
- Non-negotiable backends: Ollama (TRIAGE), Gemini CLI (PLAN), GCA (CODE_GEN)
- Deployment: Docker Compose only — no Kubernetes

---

## 2. CIPHER 7-Layer Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Layer 7 — AAL  Agent Adaptation Layer                          │
│  Agent personas (Senior Dev, Tester, QA, Arch, Safety Eng)      │
├─────────────────────────────────────────────────────────────────┤
│  Layer 6 — ARE  Autonomous Reasoning Engine                      │
│  UC dispatcher, ASIL gate, ASDLC gate sequencer                 │
├─────────────────────────────────────────────────────────────────┤
│  Layer 5 — GCL  Grounded Context Layer                           │
│  Hybrid RAG (BM25 + Qdrant), traceability graph, prompt context │
├─────────────────────────────────────────────────────────────────┤
│  Layer 4 — TRF  Transformation Layer                             │
│  LLM backends: Ollama TRIAGE · Gemini PLAN · GCA CODE_GEN       │
├─────────────────────────────────────────────────────────────────┤
│  Layer 3 — MKF  Multi-Knowledge Fusion                           │
│  Standards corpus (ISO 26262, MISRA-C, AUTOSAR), code index     │
├─────────────────────────────────────────────────────────────────┤
│  Layer 2 — PKL  Persistent Knowledge Layer                       │
│  Config, workflow state, artifact store, trace graph             │
├─────────────────────────────────────────────────────────────────┤
│  Layer 1 — DRS  Data Reception & Sanitisation                    │
│  SWC source files, HLD/LLD CSVs, linker scripts, map files      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Agent Roles (AAL — Layer 7)

| Role | Sprint 0 Responsibility | Primary UCs |
|---|---|---|
| **Tech Lead / Architect** | UC catalog owner, sprint planning, ADR sign-off | UC catalog (18 UCs defined) |
| **Senior Developer** | Implements UC modules per LLD spec | UC 3.1, UC 4.1, UC 4.4, F-001…F-010 |
| **Tester** | Creates test environments, pytest suites | Sprint 0 test suite (169 tests) |
| **QA Engineer** | Defines ASDLC process, enforces gates | ASDLC G0–G5, CHANGELOG |
| **Safety Engineer** | Required sign-off for ASIL-D nodes | UC 4.4 HARD_BLOCK gate |

---

## 4. Three-Backend LLM Triangle (Layer 4 — TRF)

```
                    ┌─────────────┐
                    │  USER / CI  │
                    └──────┬──────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
   ┌──────────────┐ ┌─────────────┐ ┌─────────────────┐
   │ Ollama :11434 │ │ Gemini CLI  │ │ GCA WebSocket   │
   │ LOCAL / FAST  │ │ subprocess  │ │ ws://localhost  │
   │               │ │             │ │ :37778          │
   │ TRIAGE phase  │ │ PLAN phase  │ │ CODE_GEN phase  │
   │ Embedding gen │ │ Fix strategy│ │ Final artifacts │
   │ QA answers    │ │ Standards   │ │ Retries: 3      │
   └──────────────┘ └─────────────┘ └─────────────────┘
```

**Constraint:** All three backends are NON-NEGOTIABLE. No single-backend shortcut.

---

## 5. Use Case Catalog (24 UCs)

### Stage 1 — LLD Generation (S1)
| UC | Name | Sprint | Status |
|---|---|---|---|
| UC 1.1 | LLD Generation from SWC Source | Sprint 1 | Planned |
| UC 1.2 | Requirements Management Upload Gate | Sprint 0 | ✅ Complete (S1N2) |
| UC 1.3 | LLD ID Extraction Gate | Sprint 0 | ✅ Complete (S1N3) |
| UC 1.4 | Full Traceability Chain | Sprint 1 | Planned |

### Stage 2 — Code Linking (S2)
| UC | Name | Sprint | Status |
|---|---|---|---|
| UC 2.1 | LLD Requirement Embedding in Source | Sprint 0 | ✅ Complete (S2N1) |
| UC 2.2 | Annotated Source Review Gate | Sprint 0 | ✅ Complete (S2N2) |

### Stage 3 — ASIL Code Review
| UC | Name | Sprint | Status |
|---|---|---|---|
| UC 3.1 | ASIL-B/C/D Code Review Assistant | **Sprint 0** | ✅ **Implemented** |

### Stage 4 — Knowledge and Standards
| UC | Name | Sprint | Status |
|---|---|---|---|
| UC 4.1 | ISO 26262 / MISRA-C / AUTOSAR Standards Q&A | **Sprint 0** | ✅ **Implemented** |
| UC 4.2 | Codebase Pattern Q&A | Sprint 2 | Planned |
| UC 4.3 | HLD/LLD Review Assistant | Sprint 2 | Planned |
| UC 4.4 | RAM / Memory Overlap Detection | **Sprint 0** | ✅ **Implemented** |

### Stage 5 — Traceability (S3–S5)
| UC | Name | Sprint | Status |
|---|---|---|---|
| UC 5.1 | PR / Merge Review with ASIL Gate | Sprint 1 | Planned |
| UC 5.2 | LLD-to-Code Trace Matrix | Sprint 0 | ✅ Complete (S3N1 canonical name fix) |
| UC 5.3 | HLD-to-LLD Link Matrix | Sprint 0 | ✅ Complete (S4N1 canonical name fix) |
| UC 5.4 | Full Downstream Trace Matrix | Sprint 0 | ✅ Complete (S5N1 canonical name fix) |

### Stage 6–9 — Testing and Final Sign-Off
| UC | Name | Sprint | Status |
|---|---|---|---|
| UC 6.1 | VectorCAST/Tessy Test Artifact Generation | Sprint 0 | ✅ Complete (S6N1) |
| UC 7.1 | Unit Test Documentation Generation | Sprint 0 | ✅ Complete (S7N1) |
| UC 8.1 | UTD-to-LLD Link Generation | Sprint 0 | ✅ Complete (S8N1) |
| UC 9.1 | Final Full Traceability Matrix | Sprint 0 | ✅ Complete (S9N1) |

---

## 6. ASDLC — AI Software Development Lifecycle

```
G0 ── INTAKE ──────────── Workspace valid, ruleset loaded, config checked
  │
G1 ── DESIGN ──────────── Sprint complete: 100% tests passing
  │
G2 ── IMPLEMENTATION ──── Artifact filenames match trace_loader contract
  │
G3 ── CODE REVIEW ──────── ASIL-A/B/QM: WARN allowed, HOLD on violations
  │
G4 ── INTEGRATION ──────── ASIL-C: HOLD — Safety Engineer review
  │
G5 ── RELEASE ──────────── ASIL-D: HARD_BLOCK or sign-off required
```

**Sprint 0 status: G1 gate CLOSED — 169/169 tests passing.**

---

## 7. CIPHER Platform Components

### 7.1 DevNex Assistant (this repo)
- **Path:** `cipher/agents/devnex_assistant/`
- **Role:** V-cycle automation engine — primary delivery agent for automotive SWC workflows
- **Status Sprint 0:** 13 V-cycle nodes, 3 UC modules (3.1, 4.1, 4.4), 10 gap fixes

### 7.2 Integrator Agent
- **Path:** `cipher/agents/integrator_agent/` (reference impl)
- **Role:** Vehicle Signal Specification (VSS) signal processing and integration
- **Status:** Reference design captured in LLDV1/V2/V3

### 7.3 Shared Persistence Layer (PKL)
- Config: `generated_artifacts/config.json`
- State: `~/.devnex/workflow_state.json`
- Artifacts: `~/.devnex/runs/{run_id}/`
- Trace graph: `trace_graph.json` (canonical) or CSV fallback

### 7.4 Standards Knowledge Base (MKF)
- ISO 26262 Parts 1–12 corpus
- MISRA-C:2012 mandatory rule set (R1.3, R11.3, R11.8, R14.4, R15.5, R17.7, R21.3)
- AUTOSAR Classic Platform guidelines
- Indexed via Qdrant (dense) + BM25Okapi (sparse)

---

## 8. Infrastructure (Docker Compose)

```yaml
# Target composition (Sprint 1 planning)
services:
  devnex:        # Python app — ports 37778 (bridge)
  ollama:        # Ollama — port 11434
  qdrant:        # Qdrant — port 6333
  # gemini: invoked as subprocess, no container needed
```

**Constraint:** Docker Compose ONLY. No Kubernetes.

---

## 9. Sprint Roadmap

| Sprint | Focus | Gate | Status |
|---|---|---|---|
| **Sprint 0** | Infrastructure fixes (F-001…F-010), UC 3.1, UC 4.1, UC 4.4, ASDLC doc | G1 (169 tests) | ✅ **COMPLETE** |
| Sprint 1 | UC 1.1 LLD improvements, UC 5.1 PR review, NATS event bus, LangGraph adapter | G2 (artifact contract) | 🔄 Planned |
| Sprint 2 | UC 4.2 codebase Q&A, UC 4.3 HLD/LLD review, StateStore file lock, Docker Compose | G3/G4 | 📋 Backlog |
| Sprint 3 | UC 1.4 full trace chain, GUI UC 4.4 button, CI/CD post-merge hook | G5 | 📋 Backlog |

---

## 10. Key Design Decisions (ADR Summary)

| ADR | Decision | Rationale |
|---|---|---|
| ADR-001 | Wrap-first discipline | Preserve existing code; targeted REFACTOR only with justification |
| ADR-002 | Three non-negotiable LLM backends | Ollama for local speed, Gemini for planning, GCA for final generation |
| ADR-003 | Docker Compose, no Kubernetes | Simplicity for embedded dev laptop environments |
| ADR-004 | Canonical artifact filenames (F-001) | `trace_loader._CSV_MAP` requires exact names; decouples nodes from loader |
| ADR-005 | `removeprefix` over `lstrip` for glob patterns | `lstrip` strips char sets, not substrings — caused `rglob(".c")` bug |
| ADR-006 | ASIL-D = `SemanticConflictError` (hard block) | ISO 26262 requires deterministic blocking for ASIL-D safety violations |
| ADR-007 | BM25 + Qdrant hybrid RAG for standards QA | BM25 handles keyword precision; Qdrant handles semantic similarity |
