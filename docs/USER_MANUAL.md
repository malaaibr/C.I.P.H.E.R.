# CIPHER — User Manual

Operating reference for the **CIPHER VSCode extension** and its Python host. For step-by-step first-time use, see `docs/USER_GUIDE.md`. For build/install, see `docs/BUILD.md`.

---

## 1. Components

| Component | Where | What it does |
|---|---|---|
| **VSIX extension** | VSCode | Activity-bar icon + Webview UI + spawns the Python host |
| **Python host** | `python run_poc.py --headless` | FastAPI A2A :8100 + LLM Gateway :8200 |
| **Webview UI** | inside VSCode | HUD + DevNex panels |
| **Orchestrator** | inside host | `CipherOrchestrator` → `DevNexOrchestrator` (13 V-cycle nodes) |
| **Infra (optional)** | `deploy/local/docker-compose.yml` | Redis, Memgraph, Qdrant, MinIO, NATS, OPA |
| **LLM (optional)** | Ollama or GCA | Drives node generation |

```
VSCode (Webview)  ──HTTP/SSE──►  run_poc.py --headless
                                       │
                                       ├── /cipher/*   REST
                                       ├── /events/sse SSE
                                       └── /v1/tasks   A2A
```

---

## 2. The webview UI

### Header
- **CIPHER** — brand mark.
- **HUD** / **DEVNEX** — mode badges (click to switch).
- **Status dot** — `starting` (yellow), `ready` (green), `error` (red).
- **{base URL}** — current Python host URL.

### Sidebar (left)
| Item | View | Purpose |
|---|---|---|
| Dashboard | HUD Mode 0 | Arc reactor + live infra status grid |
| Workflow | DevNex | V-cycle node grid; click to run a single node |
| Trace | DevNex | Artifact-edge SVG graph of run history |
| Review | DevNex | Pending human-review queue |
| Output Log | DevNex | Streamed events from `/events/sse` |
| Config | DevNex | SWC name, workspace path, ASIL, domain pack |
| Voice | DevNex | Mic capture (requires STT backend) |

### Workflow grid
Each node card:
- **Idle** — default border.
- **Running** — yellow border + glow.
- **Done** — green border.
- **Error** — red border.

Buttons:
- **Run Full V-Cycle** → `POST /cipher/runs/full`
- **Reset** → `POST /cipher/workflow/reset`
- **Click any node card** → `POST /cipher/nodes/{node_id}/run`

### Review modal
When a node emits a `review.needed` event, a modal appears with the prompt. **Approve** / **Reject** sends `POST /cipher/runs/{runId}/review`. The orchestrator's worker thread unblocks and continues.

---

## 3. REST API reference (`http://127.0.0.1:8100`)

| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/cipher/healthz` | — | `{ok, service, orchestrator_attached, active_runs}` |
| GET | `/cipher/config` | — | current config dict |
| PUT | `/cipher/config` | full config dict | `{ok, keys}` |
| POST | `/cipher/nodes/{node_id}/run` | — | `{runId}` |
| POST | `/cipher/runs/full` | — | `{runId}` |
| POST | `/cipher/runs/{run_id}/review` | `{approved: bool}` | `{ok, runId, approved}` |
| POST | `/cipher/workflow/reset` | — | `{ok}` |
| GET | `/cipher/infra/status` | — | `{services: {Redis: bool, ...}}` |
| POST | `/cipher/voice/transcribe` | multipart `audio` | 503 until STT backend wired |
| POST | `/cipher/voice/speak` | `{text}` | 503 until TTS backend wired |
| GET | `/events/sse` | — | text/event-stream |

### SSE event envelope

```json
{
  "ts": "2026-05-18T12:00:00Z",
  "kind": "log|node.started|node.complete|review.needed|progress|status|error",
  "runId": "uuid|null",
  "nodeId": "S1N1|null",
  "payload": { /* kind-specific */ }
}
```

---

## 4. Commands (VSCode command palette `Ctrl+Shift+P`)

| Command | Effect |
|---|---|
| `CIPHER: Open Panel` | Reveal the webview, spawn host if needed |
| `CIPHER: Restart Python Host` | Kill + respawn `run_poc.py --headless` |
| `CIPHER: Run Full V-Cycle` | POST `/cipher/runs/full` |
| `CIPHER: Reset Workflow` | POST `/cipher/workflow/reset` |

---

## 5. Settings

See `docs/BUILD.md` §6 for the full settings table.

---

## 6. Domain packs

Pick one in **Config → Domain pack**. Each pack constrains the validator (WF₁–WF₆).

| Pack id | Standard | ASIL | Max revisions | Notes |
|---|---|---|---|---|
| `iso26262_asil_b` | ISO 26262 | B | 3 | default |
| `iso26262_asil_c` | ISO 26262 | C | 2 | tighter error_handler / macro rules |
| `iso26262_asil_d` | ISO 26262 | D | 1 | strictest; needs REQUIREMENT *and* STANDARD_RULE |
| `aspice_l3` | ASPICE v4.0 | QM | 3 | process-focused |
| `misra_c_2012` | MISRA C:2012 | QM | 3 | coding-rule scope only |

To author a new pack: copy `cipher/gcl/domain_packs/iso26262_asil_b/` and edit `pack.yaml`, `schemas/permitted_types.json`, `schemas/phase_kinds.json`.

---

## 7. Troubleshooting runtime issues

| Symptom | Likely cause | Fix |
|---|---|---|
| Status dot stays yellow | Python host failed to start | View **Output → CIPHER Host** channel; check `cipher.pythonPath` |
| Status dot turns red | Health probe failed after 30s | Run `python run_poc.py --headless` in a terminal; read the error |
| Infra grid all DOWN | Docker stack not up | `cd deploy/local && docker compose up -d` |
| Node click logs but nothing runs | DevNex orchestrator init failed | Inspect log tail for "Orchestrator init failed: ..."; usually missing config |
| Review modal never appears but log says "review needed" | Webview lost SSE connection | Click **Restart Host** or reopen the panel |
| Voice button → 503 | STT backend not configured | Wire Whisper/Vosk in `cipher_routes.py:voice_transcribe` |
| Port conflict on second VSCode window | Two hosts trying to bind 8100 | Change `cipher.ports.a2a` in the second workspace, or close the first instance |

---

## 8. Logs & data locations

| Path | Content |
|---|---|
| VSCode → **Output → CIPHER Host** | stdout/stderr of `run_poc.py --headless` |
| Webview → **Output Log** view | live SSE event stream |
| `deploy/local/data/` (gitignored) | Docker volume mounts for Redis/Memgraph/etc. |
| `~/.cipher/` (planned) | per-user config + cache (not yet implemented) |

---

## 9. Security notes

- All HTTP traffic is loopback-only (`127.0.0.1`). The host does not bind external interfaces.
- Webview CSP whitelists exactly `connect-src http://127.0.0.1:8100 http://127.0.0.1:8200` — no other origin can be reached.
- Never commit `.env` files. `extension/node_modules/` and `extension/out/` are gitignored.
- The `.vsix` ships only TS/JS/HTML — no embedded Python or model weights.

---

## 10. Where to read more

- `docs/SPRINT_PLAN.md` — current backlog + sprint state
- `docs/VSIX_DESIGN.md` — extension architecture
- `docs/CIPHER_archi.md` — full platform architecture
- `docs/CIPHER_HLD.md` / `docs/CIPHER_LLD.md` — high/low-level design
- `docs/SESSION_HANDOFF.md` — historical session notes (superseded by SPRINT_PLAN.md)
