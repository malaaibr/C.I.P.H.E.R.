---
doc_version: 1.0.0
last_updated: 2026-05-18
owner: CIPHER team
status: current
---

# Trace Graph Panel — DevNex Assistant

Visualises the full ISO 26262 / ASPICE traceability chain across five columns:

```
HLD  →  LLD  →  CODE  →  TESTS  →  UTD
```

---

## Architecture

```
TracePanel (QWidget)
├── TraceFilterBar          chip bar: [ ALL ] [ HLD ] [ LLD ] [ CODE ] [ TEST ] [ UTD ]
├── TraceGraphCanvas        QGraphicsView bezier diagram
│   ├── Column headers      one per NodeKind, accent-coloured
│   ├── TraceNodeCard items 180×56 px custom-painted QGraphicsObject
│   └── _EdgeItem items     cubic Bezier QGraphicsPathItem
└── Detail drawer (QFrame)  slides in on node click — ID, ASIL, neighbours, Open button
```

---

## trace_graph.json schema

Written by `TraceReportSkill` (and `emit_trace_json()`) into `generated_artifacts/`.  
`TracePanel` watches this file via `QFileSystemWatcher` and reloads automatically.

```jsonc
{
  "nodes": [
    {
      "id":          "HLD-TSYN-001",   // unique node identifier
      "kind":        "HLD",            // HLD | LLD | CODE | TEST | UTD
      "label":       "HLD-TSYN-001",   // main card text
      "sublabel":    "HLD REQ",        // small muted line above label
      "title":       "Init torque syncing",  // shown in detail drawer
      "source_file": "src/tsyn.c",     // opened on double-click / Open button
      "line_no":     42,               // line in source_file (0 = top of file)
      "asil":        "B",              // "A"|"B"|"C"|"D"|"" — shown as amber pill
      "metadata":    {}                // arbitrary key-value pairs (reserved)
    }
  ],
  "edges": [
    {
      "source_id":  "HLD-TSYN-001",
      "target_id":  "TSYN_LLD_001",
      "kind":       "covers",          // "link" | "covers" | "verifies"
      "confidence": 1.0                // 0..1 — weak links are dimmed
    }
  ]
}
```

---

## CSV artifact contracts

### `HLD_LLD_Trace_Matrix.csv`  (written by S3)

| Column | Description |
|---|---|
| `HLD_ID` | HLD requirement identifier |
| `HLD_TITLE` | Human-readable title |
| `LLD_ID` | LLD design item identifier |
| `LLD_TITLE` | Human-readable title |
| `LINK_TYPE` | `covers` / `link` |
| `CONFIDENCE` | 0.0 – 1.0 |

### `LLD_Code_Trace_Matrix.csv`  (written by S4)

Same shape — `LLD_ID`, `LLD_TITLE`, `CODE_ID`, `CODE_TITLE`, `LINK_TYPE`, `CONFIDENCE`.

### `Full_Downstream_Trace.csv`  (written by S5)

Same shape — `CODE_ID`, `CODE_TITLE`, `TEST_ID`, `TEST_TITLE`, `LINK_TYPE`, `CONFIDENCE`.

### `UTD_LLD_Links.json`  (written by S8)

```json
{
  "links": [
    { "utd_id": "UTD-001", "lld_id": "LLD-001", "test_id": "TC-001" }
  ]
}
```

All fields are optional per entry; missing `lld_id` / `test_id` skips that edge.

---

## Visual tokens

| NodeKind | Accent colour |
|---|---|
| HLD  | `#00c8ff` cyan-blue |
| LLD  | `#00ff9d` success-green |
| CODE | `#ffb700` warning-amber |
| TEST | `#8b5cf6` violet |
| UTD  | `#ff3a8a` magenta / pink-red |

Background: `#010a15` · Panel cards: `#041624` · Muted text: `#2d5f7a`

---

## Keyboard shortcuts

| Key | Action |
|---|---|
| `Ctrl + wheel` | Zoom in / out (0.4× – 2.5×) |
| `Space + drag` | Pan the canvas |
| `Middle-mouse + drag` | Pan the canvas |
| `Ctrl + 0` | Reset zoom and fit view |

---

## Extension hooks

### Custom `on_open_source` callback

Pass a callable `(path: str, line_no: int) -> None` to `TracePanel`:

```python
def my_opener(path: str, line_no: int) -> None:
    my_editor.open(path, line_no)

panel = TracePanel(
    artifacts_dir=Path("generated_artifacts"),
    on_open_source=my_opener,
)
```

### Programmatic graph injection

```python
from core.trace_model import TraceGraph, TraceNode, TraceEdge, NodeKind

graph = TraceGraph(
    nodes=[TraceNode(id="X1", kind=NodeKind.HLD, label="X1")],
    edges=[],
)
panel._canvas.set_graph(graph)
```

### Auto-reload trigger

`TracePanel.update_from_state(state: dict)` is the hook called by `MainWindow`
after every stage completion. Internally it just calls `reload()`, which reads
`trace_graph.json` (preferred) or falls back to individual CSV files.

---

## Running the tests

```bash
cd devnex_assistant
pytest tests/test_trace_model.py -v
```

Tests cover:

- CSV → TraceGraph happy path (single + multiple CSVs)
- Missing files → empty graph, no exception
- Malformed rows skipped + warning logged
- Extra CSV columns silently ignored
- `trace_graph.json` preferred over CSVs when both present
- `UTD_LLD_Links.json` merged correctly
- `to_json` / `from_json` round-trip identity (all fields preserved)
- `emit_trace_json` writes valid, loadable JSON
