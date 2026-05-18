---
doc_version: 1.0.0
last_updated: 2026-05-18
owner: CIPHER team
status: deprecated
---

> **Deprecated as of 2026-05-18 — historical reference only.**

# Wrap/Rewrite Decision Matrix — CAR-001: MainCipher Shell

- **Reference:** CAR-001 (MainCipher Shell — Platform GUI)
- **Codebase path:** reference/MainCipherdevnex-assistant/MainCipherdevnex-assistant/src/devnex_agent/gui/
- **Date:** 2026-05-16
- **ADRs referenced:** ADR-0005 (Shell-Panel Docking)

---

## Decision Matrix

| Module | Disposition | Integration Risk | Effort | Adapter Shape | Reasoning |
|--------|-------------|-----------------|--------|---------------|-----------|
| `gui/app.py` | REFACTOR | Low | S | Replace `_build_orchestrator()` with `CipherShellClient` factory | Entry point coupling to backend must be severed |
| `gui/main_window.py` | REFACTOR | Medium | M | Replace `Orchestrator` param → `CipherShellClient`; add panel registry loop | Core shell change; all panels flow through here |
| `gui/panels/cipher_boot_panel.py` | WRAP | Low | S | Copy to `gui/shell/boot_panel.py` unchanged | Pure animation, no backend coupling |
| `gui/panels/cipher_dashboard_panel.py` | REFACTOR | Medium | M | Replace static `inject_panel(index)` with `register_panel(descriptor)` loop | Central to ADR-0005 |
| `gui/panels/workflow_panel.py` | REFACTOR | Medium | M | Move to `gui/panels/devnex/workflow_panel.py`; replace `orchestrator.dispatch()` with `client.submit_task()` | Becomes DevNex panel internal widget |
| `gui/panels/trace_panel.py` | WRAP | Low | S | Move to `gui/panels/devnex/trace_panel.py` | Presentation only; data source changes later |
| `gui/panels/config_form.py` | WRAP | Low | S | Copy to `gui/shell/config_form.py` | Shell-level config stays in shell |
| `gui/panels/voice_panel.py` | WRAP | Low | S | Copy to `gui/shell/voice_panel.py` | Voice is shell feature |
| `gui/panels/output_log.py` | WRAP | Low | S | Copy to `gui/shell/output_log.py` | Generic shared widget |
| `gui/widgets/arc_reactor.py` | WRAP | Low | S | Copy to `gui/widgets/arc_reactor.py` | Pure visual |
| `gui/widgets/welcome_overlay.py` | WRAP | Low | S | Copy to `gui/widgets/welcome_overlay.py` | Pure visual |
| `gui/styles/hud_theme.py` | REFACTOR | Low | S | Upgrade PyQt5→PyQt6 QSS; export tokens | Mechanical import changes |
| `gui/workers/worker_thread.py` | REFACTOR | Medium | S | Replace direct orchestrator calls with async A2A via `CipherShellClient` | Bridge between Qt threads and async A2A |
| `gui/web_server.py` | WRAP | Low | S | Copy; likely unused in CIPHER (A2A replaces it) | Preserve for compatibility |
| `voice/voice_controller.py` | WRAP | Low | S | Copy to `gui/shell/voice/` | Shell-level voice |
| `voice/tts.py` | WRAP | Low | S | Copy to `gui/shell/voice/` | Hardware driver |
| `voice/stt.py` | WRAP | Low | S | Copy to `gui/shell/voice/` | Hardware driver |

---

## Summary

| Disposition | Count | Total Effort |
|-------------|-------|-------------|
| WRAP | 11 | 11 × S = ~11h |
| REFACTOR | 6 | 2M + 4S = ~2.5d |
| REWRITE | 0 | — |

**Primary risk:** The PyQt5→PyQt6 migration touches every module. Recommend doing it as a single batch task (T-GUI-001) before any other shell work.

**Decision: PyQt version unification.** The DevNex agent GUI (CAR-002) already uses PyQt6. The shell must upgrade to PyQt6. This is a mechanical change (import paths, `exec_()` → `exec()`, enum namespacing). Estimated: 4 hours.

## Revision History

| Version | Date | Author | Change |
|---------|------|--------|--------|
| 1.0.0 | 2026-05-18 | CIPHER team | Marked deprecated — predates CIPHER; kept for archeology. |
