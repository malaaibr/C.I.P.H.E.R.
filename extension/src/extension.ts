import * as vscode from 'vscode';
import { CipherViewProvider } from './cipherViewProvider';
import { PythonHost } from './pythonHost';

let host: PythonHost | undefined;
let provider: CipherViewProvider | undefined;

export function activate(context: vscode.ExtensionContext): void {
  host = new PythonHost(context);
  provider = new CipherViewProvider(context, host);

  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider('cipher.mainView', provider, {
      webviewOptions: { retainContextWhenHidden: true },
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand('cipher.open', async () => {
      await vscode.commands.executeCommand('workbench.view.extension.cipher');
      await host!.ensureStarted();
    }),
    vscode.commands.registerCommand('cipher.restartHost', async () => {
      await host!.restart();
      provider!.notifyStatus('starting', 'Restarting Python host…');
    }),
    vscode.commands.registerCommand('cipher.runFull', async () => {
      try {
        const res = await fetch(`${host!.baseUrl()}/cipher/runs/full`, { method: 'POST' });
        const json = await res.json();
        vscode.window.showInformationMessage(`CIPHER: full V-cycle started — run ${json.runId}`);
      } catch (e) {
        vscode.window.showErrorMessage(`CIPHER: failed to start full run: ${e}`);
      }
    }),
    vscode.commands.registerCommand('cipher.resetWorkflow', async () => {
      try {
        await fetch(`${host!.baseUrl()}/cipher/workflow/reset`, { method: 'POST' });
        vscode.window.showInformationMessage('CIPHER: workflow reset.');
      } catch (e) {
        vscode.window.showErrorMessage(`CIPHER: reset failed: ${e}`);
      }
    }),
  );

  // Status bar
  const status = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
  status.text = '$(pulse) CIPHER';
  status.tooltip = 'CIPHER — click to open panel';
  status.command = 'cipher.open';
  status.show();
  context.subscriptions.push(status);
}

export function deactivate(): void {
  host?.stop();
}
