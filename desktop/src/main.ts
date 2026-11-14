import { app, BrowserWindow, globalShortcut } from 'electron';
import * as path from 'path';
import { createSystemTray, destroyTray } from './tray';
import { registerGlobalShortcuts, unregisterGlobalShortcuts } from './shortcuts';
import { setupIpcHandlers } from './ipc';
import { TabManager } from './tab-manager';

let mainWindow: BrowserWindow | null = null;
let tabManager: TabManager | null = null;
(app as any).isQuitting = false;

// Bloqueo de instancia única: enfocar la ventana existente si ya está abierta
const gotTheLock = app.requestSingleInstanceLock();
if (!gotTheLock) {
  app.quit();
} else {
  app.on('second-instance', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.show();
      mainWindow.focus();
    }
  });
}

function getBaseUrl(): string {
  return process.env.KOGNITO_SERVER_URL || 'https://kognitoai.cloud';
}

function createMainWindow(): void {
  const iconPath = path.join(__dirname, '../assets/icon.png');
  const tabsHtmlPath = path.join(__dirname, '../assets/tabs.html');

  mainWindow = new BrowserWindow({
    width: 1360,
    height: 900,
    minWidth: 980,
    minHeight: 650,
    frame: false, // Barra de pestañas personalizada moderna
    icon: iconPath,
    backgroundColor: '#070b14',
    title: 'KognitoAI',
    autoHideMenuBar: true,
    show: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: false,
    },
  });

  const baseUrl = getBaseUrl();
  tabManager = new TabManager(mainWindow, baseUrl);

  setupIpcHandlers(mainWindow, tabManager);
  createSystemTray(mainWindow);

  // Cargar barra de pestañas nativa
  mainWindow.loadFile(tabsHtmlPath);

  mainWindow.once('ready-to-show', () => {
    if (mainWindow) {
      mainWindow.show();
      mainWindow.focus();
    }
  });

  // Cuando la barra de pestañas esté lista, crear la primera pestaña
  mainWindow.webContents.once('did-finish-load', () => {
    if (tabManager) {
      tabManager.createTab('/login');
    }
  });

  // Configurar atajos de teclado locales para pestañas (Ctrl+T, Ctrl+W, Ctrl+R)
  mainWindow.webContents.on('before-input-event', (event, input) => {
    if (!tabManager) return;
    const isCtrl = input.control || input.meta;

    if (isCtrl && input.key.toLowerCase() === 't') {
      event.preventDefault();
      tabManager.createTab('/chat');
    } else if (isCtrl && input.key.toLowerCase() === 'w') {
      event.preventDefault();
      const activeId = tabManager.getActiveTabId();
      if (activeId) tabManager.closeTab(activeId);
    } else if (isCtrl && input.key.toLowerCase() === 'r') {
      event.preventDefault();
      tabManager.reload();
    }
  });

  // Cuando el usuario cierra la ventana, cerrar la aplicación completamente
  mainWindow.on('close', () => {
    (app as any).isQuitting = true;
    app.quit();
  });
}

app.whenReady().then(() => {
  createMainWindow();
  if (mainWindow) {
    registerGlobalShortcuts(mainWindow);
  }

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createMainWindow();
    } else if (mainWindow) {
      mainWindow.show();
      mainWindow.focus();
    }
  });
});

app.on('before-quit', () => {
  (app as any).isQuitting = true;
});

app.on('will-quit', () => {
  unregisterGlobalShortcuts();
  destroyTray();
});
