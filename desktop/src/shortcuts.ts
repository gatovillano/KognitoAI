import { globalShortcut, BrowserWindow } from 'electron';

export function registerGlobalShortcuts(mainWindow: BrowserWindow, spotlightWindow?: BrowserWindow): void {
  // Atajo 1: Mostrar/Ocultar ventana principal
  const mainShortcut = 'CommandOrControl+Shift+K';
  try {
    globalShortcut.register(mainShortcut, () => {
      if (mainWindow.isVisible()) {
        if (mainWindow.isFocused()) {
          mainWindow.hide();
        } else {
          mainWindow.show();
          mainWindow.focus();
        }
      } else {
        mainWindow.show();
        mainWindow.focus();
      }
    });
  } catch (_e) {}

  // Atajo 2: Spotlight Flotante
  if (spotlightWindow) {
    const spotlightShortcut = 'CommandOrControl+Alt+K';
    try {
      globalShortcut.register(spotlightShortcut, () => {
        if (spotlightWindow.isVisible()) {
          spotlightWindow.hide();
        } else {
          spotlightWindow.show();
          spotlightWindow.focus();
        }
      });
    } catch (_e) {}
  }
}

export function unregisterGlobalShortcuts(): void {
  globalShortcut.unregisterAll();
}
