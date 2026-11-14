import { ipcMain, BrowserWindow, Notification, desktopCapturer, shell, app } from 'electron';
import { TabManager } from './tab-manager';

export function setupIpcHandlers(mainWindow: BrowserWindow, tabManager?: TabManager): void {
  // Notificaciones nativas
  ipcMain.handle('desktop:notify', async (_event, { title, body }) => {
    if (Notification.isSupported()) {
      new Notification({
        title: title || 'KognitoAI',
        body: body || '',
      }).show();
      return true;
    }
    return false;
  });

  // Captura de pantalla nativa
  ipcMain.handle('desktop:capture-screen', async () => {
    try {
      const sources = await desktopCapturer.getSources({
        types: ['screen'],
        thumbnailSize: { width: 1920, height: 1080 },
      });

      if (sources.length > 0) {
        return sources[0].thumbnail.toDataURL();
      }
      return null;
    } catch (err) {
      console.error('[KognitoDesktop] Error capturando pantalla:', err);
      return null;
    }
  });

  // Control de ventanas
  ipcMain.on('desktop:minimize', () => {
    mainWindow.minimize();
  });

  ipcMain.on('desktop:maximize', () => {
    if (mainWindow.isMaximized()) {
      mainWindow.unmaximize();
    } else {
      mainWindow.maximize();
    }
  });

  ipcMain.on('desktop:close', () => {
    (app as any).isQuitting = true;
    app.quit();
  });

  // Enlaces externos en navegador predeterminado
  ipcMain.on('desktop:open-external', (_event, url: string) => {
    if (url && (url.startsWith('http://') || url.startsWith('https://'))) {
      shell.openExternal(url);
    }
  });

  // Control de pestañas múltiples
  if (tabManager) {
    ipcMain.on('tabs:create', (_event, urlPath?: string) => {
      tabManager.createTab(urlPath);
    });
    ipcMain.on('tabs:switch', (_event, tabId: string) => {
      tabManager.switchTab(tabId);
    });
    ipcMain.on('tabs:close', (_event, tabId: string) => {
      tabManager.closeTab(tabId);
    });
    ipcMain.on('tabs:go-back', () => {
      tabManager.goBack();
    });
    ipcMain.on('tabs:go-forward', () => {
      tabManager.goForward();
    });
    ipcMain.on('tabs:reload', () => {
      tabManager.reload();
    });
  }
}
