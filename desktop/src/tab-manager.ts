import { BrowserWindow, BrowserView, shell } from 'electron';
import * as path from 'path';

export interface TabInfo {
  id: string;
  title: string;
  url: string;
  isLoading: boolean;
}

export class TabManager {
  private mainWindow: BrowserWindow;
  private tabs: Map<string, { info: TabInfo; view: BrowserView }> = new Map();
  private activeTabId: string | null = null;
  private baseUrl: string;

  constructor(mainWindow: BrowserWindow, baseUrl: string) {
    this.mainWindow = mainWindow;
    this.baseUrl = baseUrl.replace(/\/+$/, '');

    // Ajustar límites de la pestaña activa cuando se redimensiona la ventana
    this.mainWindow.on('resize', () => {
      this.updateActiveTabBounds();
    });
  }

  private updateActiveTabBounds(): void {
    if (!this.activeTabId) return;
    const tab = this.tabs.get(this.activeTabId);
    if (!tab) return;

    const bounds = this.mainWindow.getContentBounds();
    const TAB_BAR_HEIGHT = 44;
    tab.view.setBounds({
      x: 0,
      y: TAB_BAR_HEIGHT,
      width: bounds.width,
      height: Math.max(bounds.height - TAB_BAR_HEIGHT, 100),
    });
  }

  public createTab(urlPath?: string): string {
    const tabId = 'tab_' + Math.random().toString(36).substring(2, 9);
    const targetUrl = urlPath
      ? `${this.baseUrl}${urlPath.startsWith('/') ? '' : '/'}${urlPath}`
      : `${this.baseUrl}/login`;

    const view = new BrowserView({
      webPreferences: {
        preload: path.join(__dirname, 'preload.js'),
        nodeIntegration: false,
        contextIsolation: true,
        sandbox: false,
      },
    });

    view.setAutoResize({ width: true, height: true });

    const info: TabInfo = {
      id: tabId,
      title: 'KognitoAI',
      url: targetUrl,
      isLoading: true,
    };

    // Actualizar título de la pestaña según la página
    view.webContents.on('page-title-updated', (_event, title) => {
      let cleanTitle = title || 'KognitoAI';
      if (cleanTitle.includes('Kognito') && cleanTitle.length > 25) {
        cleanTitle = cleanTitle.replace(/ - Kognito AI.*$/, '');
      }
      info.title = cleanTitle;
      this.notifyTabsUpdated();
    });

    view.webContents.on('did-start-loading', () => {
      info.isLoading = true;
      this.notifyTabsUpdated();
    });

    view.webContents.on('did-stop-loading', () => {
      info.isLoading = false;
      this.notifyTabsUpdated();
    });

    // Manejar popup de Telegram OAuth en cada pestaña
    view.webContents.setWindowOpenHandler(({ url }) => {
      if (url.includes('telegram.org') || url.includes('oauth.telegram.org')) {
        return {
          action: 'allow',
          overrideBrowserWindowOptions: {
            width: 550,
            height: 650,
            autoHideMenuBar: true,
            title: 'Telegram Login',
          },
        };
      }
      if (url.startsWith('http:') || url.startsWith('https:') || url.startsWith('tg:')) {
        shell.openExternal(url);
      }
      return { action: 'deny' };
    });

    view.webContents.loadURL(targetUrl);

    this.tabs.set(tabId, { info, view });

    // Activar de inmediato la nueva pestaña
    this.switchTab(tabId);

    return tabId;
  }

  public switchTab(tabId: string): void {
    const tab = this.tabs.get(tabId);
    if (!tab) return;

    this.activeTabId = tabId;
    this.mainWindow.setBrowserView(tab.view);
    this.updateActiveTabBounds();
    this.notifyTabsUpdated();
  }

  public closeTab(tabId: string): void {
    const tab = this.tabs.get(tabId);
    if (!tab) return;

    // Destruir la vista
    (tab.view.webContents as any).destroy?.();
    this.tabs.delete(tabId);

    // Si cerramos la pestaña activa, cambiar a otra
    if (this.activeTabId === tabId) {
      const remainingIds = Array.from(this.tabs.keys());
      if (remainingIds.length > 0) {
        this.switchTab(remainingIds[remainingIds.length - 1]);
      } else {
        // Si no quedan pestañas, abrir una nueva por defecto
        this.createTab('/login');
      }
    } else {
      this.notifyTabsUpdated();
    }
  }

  public goBack(): void {
    if (!this.activeTabId) return;
    const tab = this.tabs.get(this.activeTabId);
    if (tab && tab.view.webContents.canGoBack()) {
      tab.view.webContents.goBack();
    }
  }

  public goForward(): void {
    if (!this.activeTabId) return;
    const tab = this.tabs.get(this.activeTabId);
    if (tab && tab.view.webContents.canGoForward()) {
      tab.view.webContents.goForward();
    }
  }

  public reload(): void {
    if (!this.activeTabId) return;
    const tab = this.tabs.get(this.activeTabId);
    if (tab) {
      tab.view.webContents.reload();
    }
  }

  public getActiveView(): BrowserView | null {
    if (!this.activeTabId) return null;
    return this.tabs.get(this.activeTabId)?.view || null;
  }

  public getTabs(): TabInfo[] {
    return Array.from(this.tabs.values()).map((t) => t.info);
  }

  public getActiveTabId(): string | null {
    return this.activeTabId;
  }

  private notifyTabsUpdated(): void {
    const payload = {
      tabs: this.getTabs(),
      activeId: this.activeTabId,
    };
    this.mainWindow.webContents.send('desktop:tabs-updated', payload);
  }
}
