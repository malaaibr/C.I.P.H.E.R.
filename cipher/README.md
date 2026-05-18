---
doc_version: 1.0.0
last_updated: 2026-05-18
owner: CIPHER team
status: current
---

# CIPHER Package Scaffold

This package contains the local MVP scaffold for the CIPHER platform described in [`docs/CIPHER_archi.md`](../docs/CIPHER_archi.md).

Current status:

- directory structure created for the Phase 1 local MVP
- module boundaries established for core platform layers
- implementation intentionally minimal; most components are placeholders pending Phase 1 development

Phase 1 focus:

- `core/`: shared contracts and schemas
- `orchestrator/`: task scheduling and lifecycle control
- `memory/`: storage adapters and memory-agent ownership boundary
- `tools/`: MCP gateway and local tool-server surfaces
- `agents/`: Agent-001 implementation and MVP agent stubs
- `governance/`: policy and approval boundaries
- `observability/`: tracing and audit instrumentation
- `deploy/local/`: local deployment assets for the MVP
