import * as cp from 'child_process';
import * as path from 'path';
import * as vscode from 'vscode';

export class PythonHost {
  private proc: cp.ChildProcess | undefined;
  private ready = false;
  private starting: Promise<void> | undefined;

  constructor(private readonly ctx: vscode.ExtensionContext) {}

  baseUrl(): string {
    const port = vscode.workspace.getConfiguration('cipher').get<number>('ports.a2a', 8100);
    return `http://127.0.0.1:${port}`;
  }

  async ensureStarted(): Promise<void> {
    if (this.ready) return;
    if (await this.probeHealth()) {
      this.ready = true;
      return;
    }
    if (this.starting) return this.starting;
    this.starting = this.spawn();
    try {
      await this.starting;
    } finally {
      this.starting = undefined;
    }
  }

  async restart(): Promise<void> {
    this.stop();
    this.ready = false;
    await this.ensureStarted();
  }

  stop(): void {
    if (this.proc && !this.proc.killed) {
      try { this.proc.kill(); } catch { /* ignore */ }
    }
    this.proc = undefined;
    this.ready = false;
  }

  private async probeHealth(): Promise<boolean> {
    try {
      const r = await fetch(`${this.baseUrl()}/cipher/healthz`, { method: 'GET' });
      return r.ok;
    } catch {
      return false;
    }
  }

  private async spawn(): Promise<void> {
    const cfg = vscode.workspace.getConfiguration('cipher');
    const python = cfg.get<string>('pythonPath', 'python');
    const repoCfg = cfg.get<string>('repoPath', '') || '';
    const workspaceRoot = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
    const repoPath = repoCfg || workspaceRoot;

    if (!repoPath) {
      vscode.window.showErrorMessage('CIPHER: set cipher.repoPath or open a workspace folder.');
      return;
    }

    const runPy = path.join(repoPath, 'run_poc.py');
    const out = vscode.window.createOutputChannel('CIPHER Host');
    out.show(true);
    out.appendLine(`[host] spawn: ${python} ${runPy} --headless  (cwd=${repoPath})`);

    this.proc = cp.spawn(python, [runPy, '--headless'], {
      cwd: repoPath,
      env: { ...process.env, PYTHONUNBUFFERED: '1' },
      detached: false,
    });

    this.proc.stdout?.on('data', (d: Buffer) => out.append(d.toString()));
    this.proc.stderr?.on('data', (d: Buffer) => out.append(d.toString()));
    this.proc.on('exit', (code) => {
      out.appendLine(`[host] exited code=${code}`);
      this.ready = false;
      this.proc = undefined;
    });

    // Poll /cipher/healthz up to ~30s.
    for (let i = 0; i < 60; i++) {
      await new Promise((r) => setTimeout(r, 500));
      if (await this.probeHealth()) {
        this.ready = true;
        out.appendLine('[host] ready ✓');
        return;
      }
    }
    out.appendLine('[host] timeout waiting for /cipher/healthz');
    throw new Error('CIPHER Python host failed to become healthy within 30s.');
  }
}
