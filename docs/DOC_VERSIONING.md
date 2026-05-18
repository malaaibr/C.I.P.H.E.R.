---
doc_version: 1.0.0
last_updated: 2026-05-18
owner: CIPHER team
status: current
---

# CIPHER Doc Versioning Standard

Every Markdown doc in this repo carries a small **YAML frontmatter block** at the top and a **Revision History** table at the bottom. Git history is the canonical record; the in-doc fields exist so readers can answer "is this current?" without leaving the file.

---

## 1. Frontmatter (top of every doc)

```yaml
---
doc_version: 1.0.0
last_updated: YYYY-MM-DD
owner: CIPHER team | <name>
status: current | superseded | draft | deprecated
supersedes: path/to/old.md          # optional
superseded_by: path/to/new.md       # optional
---
```

| Field | Purpose | Rule |
|---|---|---|
| `doc_version` | semver-ish — bump on every meaningful edit | `MAJOR.MINOR.PATCH`. PATCH = typo/clarification, MINOR = section added/changed, MAJOR = rewrite or breaking restructure. |
| `last_updated` | the date the **frontmatter was bumped** | ISO date. Auto-updates when you bump `doc_version`. |
| `owner` | who to ping with questions | Team name or person. |
| `status` | one-word health check | `current` is the default. Use `superseded` for retired docs (point at the replacement with `superseded_by`). `draft` for in-flight, `deprecated` for kept-for-archeology. |
| `supersedes` / `superseded_by` | cross-link retired docs | Always reciprocal — if A supersedes B, B's `superseded_by` points back. |

## 2. Revision History (bottom of every doc)

```markdown
## Revision History

| Version | Date | Author | Change |
|---------|------|--------|--------|
| 1.1.0 | 2026-05-18 | CIPHER team | Added §3 covering DVF opt-in path. |
| 1.0.0 | 2026-05-17 | CIPHER team | Initial version. |
```

- Newest entry at the top.
- One-line summary per row — long explanations belong in the commit message, not here.
- Always bump `doc_version` in the frontmatter to match the top row.

## 3. When you edit a doc

1. Update the body.
2. Bump `doc_version` and `last_updated` in the frontmatter.
3. Add a row to the Revision History table.
4. Commit with `docs:` or `docs(scope):` prefix matching the doc area.

## 4. Authoritative reference docs

For the large architecture docs (`CIPHER_archi.md`, `CIPHER_HLD.md`, `CIPHER_LLD.md`) the rule is the same — but `MAJOR` bumps deserve a fresh "Revision History" row that names the architectural decision driving the change (e.g. "Pivot to VSIX webview surface — see ADR-0006").

## 5. Superseded docs

When a doc is replaced (e.g. `SESSION_HANDOFF.md` → `SPRINT_PLAN.md`), do **not** delete the old file. Instead:

- Set `status: superseded` in its frontmatter
- Set `superseded_by: <new path>`
- Add a one-line note at the very top of the body: `> **Superseded by [SPRINT_PLAN.md](SPRINT_PLAN.md) as of 2026-05-18.** Kept for archeology.`
- Keep the file in place so existing inbound links don't 404.

## Revision History

| Version | Date | Author | Change |
|---------|------|--------|--------|
| 1.0.0 | 2026-05-18 | CIPHER team | Initial versioning standard. |
