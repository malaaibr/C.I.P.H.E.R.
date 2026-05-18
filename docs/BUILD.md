# CIPHER — Build Guide

How to build, package, and install the **CIPHER VSCode extension (`.vsix`)** and the **Python host** it drives.

---

## 1. Prerequisites

| Tool | Version | Why |
|------|---------|-----|
| **Python** | 3.11 or 3.12 | Headless host (`run_poc.py --headless`) |
| **Node.js** | 20.x LTS | Build the TypeScript extension |
| **npm** | bundled with Node | Install extension deps |
| **VSCode** | 1.85+ | Run / sideload the extension |
| **Docker Desktop** | latest | (Optional) infra stack — Redis, Memgraph, Qdrant, MinIO, NATS, OPA |
| **Ollama** | latest | (Optional) local LLM model host |

Verify:

```powershell
python --version     # 3.11.x / 3.12.x
node --version       # v20.x
npm --version
code --version
```

---

## 2. Build the Python host

```powershell
cd C:\AI_Agents\CIPHER_Local_repo\CIPHER\CIPHER_Repo
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -e .
pip install pytest pydantic fastapi uvicorn httpx pyyaml PyQt6
```

Smoke check:

```powershell
python -m pytest tests/unit -q
# expected: 154 passed
```

Headless run (this is what the extension spawns):

```powershell
python run_poc.py --headless
# ... [CIPHER] VSIX bridge ready at http://127.0.0.1:8100/cipher/healthz
```

Manual health check from another shell:

```powershell
curl http://127.0.0.1:8100/cipher/healthz
# {"ok": true, "service": "cipher-vsix-bridge", "orchestrator_attached": true, ...}
```

---

## 3. Build the VSCode extension

```powershell
cd C:\AI_Agents\CIPHER_Local_repo\CIPHER\CIPHER_Repo\extension
npm install
npm run build
```

Output: compiled JS in `extension/out/`. The webview (`webview/index.html`) is shipped verbatim — no bundler in v0.1.0.

---

## 4. Package the `.vsix`

```powershell
cd extension
npx @vscode/vsce package -o cipher-vscode-0.1.0.vsix
```

This produces `extension/cipher-vscode-0.1.0.vsix`. Distribute by:

- **Sideload**: ship the file to colleagues; they install with `code --install-extension cipher-vscode-0.1.0.vsix`.
- **GitHub Releases**: attach the `.vsix` to a release tag.
- **Marketplace**: requires a publisher account; run `vsce publish` instead of `package`.

---

## 5. Install the `.vsix` locally

```powershell
code --install-extension cipher-vscode-0.1.0.vsix
```

Or in VSCode UI: **Extensions panel → ⋯ menu → Install from VSIX…**

---

## 6. Configure the extension

VSCode settings (Ctrl+,) → search "cipher":

| Setting | Default | Purpose |
|---|---|---|
| `cipher.pythonPath` | `python` | Interpreter that runs `run_poc.py --headless`. Use a venv path for reliability. |
| `cipher.repoPath` | `""` (= workspace folder) | Absolute path to the CIPHER repo. Required if the workspace is not the repo root. |
| `cipher.ports.a2a` | `8100` | A2A FastAPI port — must match Python host. |
| `cipher.ports.gateway` | `8200` | LLM Gateway port. |
| `cipher.showEditorButton` | `true` | Show the CIPHER button in the editor title bar. |

Recommended: point `cipher.pythonPath` at your venv directly:

```json
"cipher.pythonPath": "C:\\AI_Agents\\CIPHER_Local_repo\\CIPHER\\CIPHER_Repo\\.venv\\Scripts\\python.exe",
"cipher.repoPath":   "C:\\AI_Agents\\CIPHER_Local_repo\\CIPHER\\CIPHER_Repo"
```

---

## 7. Run from source (Extension Development Host)

For active development on the extension:

1. `cd extension && npm install && npm run watch` (leave running)
2. Open `extension/` in VSCode.
3. Press **F5** — an **Extension Development Host** window opens with the extension loaded.
4. Click the CIPHER icon in the activity bar of that window.

---

## 8. CI build

GitHub Actions / hosted CI is **intentionally out of scope** for this phase.
The recipe in §2–§4 is the canonical build path — run it locally before
distributing a `.vsix`.

---

## 9. Troubleshooting build issues

| Symptom | Fix |
|---|---|
| `pip install -e .` fails — no `pyproject.toml` extras | Install deps manually: `pip install pydantic fastapi uvicorn httpx pyyaml PyQt6` |
| `npm install` warns about peer deps | Safe to ignore on Node 20. |
| `vsce package` complains about missing publisher | Add `"publisher": "cipher"` (or your own) to `extension/package.json`. |
| Extension can't find Python | Set `cipher.pythonPath` to a full path (not `"python"`). |
| Port 8100/8200 already in use | Stop other CIPHER instances, or change `cipher.ports.*` and pass matching env to `run_poc.py`. |

See `docs/USER_MANUAL.md` for runtime troubleshooting.
