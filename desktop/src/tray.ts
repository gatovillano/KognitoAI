import { Tray, Menu, app, BrowserWindow, nativeImage } from 'electron';
import * as path from 'path';

let tray: Tray | null = null;

export function createSystemTray(mainWindow: BrowserWindow): Tray {
  const iconPath = path.join(__dirname, '../assets/icon.png');
  const trayIcon = nativeImage.createFromPath(iconPath).resize({ width: 22, height: 22 });

  tray = new Tray(trayIcon);
  tray.setToolTip('KognitoAI');

  const contextMenu = Menu.buildFromTemplate([
    {
      label: 'Abrir KognitoAI',
      click: () => {
        mainWindow.show();
        mainWindow.focus();
      },
    },
    {
      label: 'Nuevo Chat',
      click: () => {
        mainWindow.show();
        mainWindow.focus();
        mainWindow.webContents.send('desktop:navigate', '/chat');
      },
    },
    {
      label: 'Configuración',
      click: () => {
        mainWindow.show();
        mainWindow.focus();
        mainWindow.webContents.send('desktop:navigate', '/settings');
      },
    },
    { type: 'separator' },
    {
      label: 'Minimizar a la bandeja',
      click: () => {
        mainWindow.hide();
      },
    },
    { type: 'separator' },
    {
      label: 'Salir de KognitoAI',
      click: () => {
        (app as any).isQuitting = true;
        app.quit();
      },
    },
  ]);

  tray.setContextMenu(contextMenu);

  tray.on('click', () => {
    if (mainWindow.isVisible()) {
      mainWindow.hide();
    } else {
      mainWindow.show();
      mainWindow.focus();
    }
  });

  return tray;
}

export function destroyTray(): void {
  if (tray) {
    tray.destroy();
    tray = null;
  }
}
