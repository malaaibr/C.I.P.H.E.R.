import * as fs from 'fs';
import * as path from 'path';
import * as vscode from 'vscode';
import { PythonHost } from './pythonHost';

export class CipherViewProvider implements vscode.WebviewViewProvider {
  private view: vscode.WebviewView | undefined;

  constructor(
    private readonly ctx: vscode.ExtensionContext,
    private readonly host: PythonHost,
  ) {}

  resolveWebviewView(view: vscode.WebviewView): void {
    this.view = view;
    view.webview.options = {
      enableScripts: true,
      localResourceRoots: [vscode.Uri.joinPath(this.ctx.extensionUri, 'webview')],
    };
    view.webview.html = this.renderHtml(view.webview);

    view.webview.onDidReceiveMessage(async (msg) => {
      switch (msg?.type) {
        case 'vscode.openFile':
          try {
            const doc = await vscode.workspace.openTextDocument(vscode.Uri.file(msg.path));
            const editor = await vscode.window.showTextDocument(doc);
            if (typeof msg.line === 'number') {
              const pos = new vscode.Position(Math.max(0, msg.line - 1), 0);
              editor.revealRange(new vscode.Range(pos, pos));
              editor.selection = new vscode.Selection(pos, pos);
            }
          } catch (e) {
            vscode.window.showErrorMessage(`CIPHER: openFile failed: ${e}`);
          }
          break;
        case 'vscode.notify':
          ({
            error: vscode.window.showErrorMessage,
            warn: vscode.window.showWarningMessage,
            info: vscode.window.showInformationMessage,
          }[msg.level as 'info' | 'warn' | 'error'] ?? vscode.window.showInformationMessage)(
            String(msg.message ?? ''),
          );
          break;
        case 'host.restart':
          await vscode.commands.executeCommand('cipher.restartHost');
          break;
        case 'webview.ready':
          this.notifyStatus('starting', 'Spawning Python host…');
          try {
            await this.host.ensureStarted();
            this.notifyStatus('ready', this.host.baseUrl());
          } catch (e) {
            this.notifyStatus('error', String(e));
          }
          break;
      }
    });
  }

  notifyStatus(state: 'starting' | 'ready' | 'error', detail?: string): void {
    this.view?.webview.postMessage({ type: 'host.status', state, detail });
  }

  private renderHtml(webview: vscode.Webview): string {
    const nonce = Array.from({ length: 32 }, () =>
      'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'[
        Math.floor(Math.random() * 62)
      ],
    ).join('');

    const htmlPath = path.join(this.ctx.extensionUri.fsPath, 'webview', 'index.html');
    let html = fs.readFileSync(htmlPath, 'utf8');

    const port = vscode.workspace.getConfiguration('cipher').get<number>('ports.a2a', 8100);
    const cspSource = webview.cspSource;
    const csp =
      `default-src 'none'; ` +
      `style-src ${cspSource} 'unsafe-inline'; ` +
      `img-src ${cspSource} data:; ` +
      `font-src ${cspSource}; ` +
      `script-src 'nonce-${nonce}'; ` +
      `connect-src http://127.0.0.1:${port} http://127.0.0.1:8200;`;

    html = html
      .replaceAll('{{CSP}}', csp)
      .replaceAll('{{NONCE}}', nonce)
      .replaceAll('{{A2A_BASE}}', `http://127.0.0.1:${port}`);

    return html;
  }
}
