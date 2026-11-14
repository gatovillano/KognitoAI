import { contextBridge, ipcRenderer } from 'electron';

export interface DesktopAPI {
  isDesktop: boolean;
  platform: string;
  version: string;
  sendNotification: (title: string, body: string) => Promise<boolean>;
  captureScreen: () => Promise<string | null>;
  minimizeWindow: () => void;
  maximizeWindow: () => void;
  closeWindow: () => void;
  openExternal: (url: string) => void;
  onNavigate: (callback: (route: string) => void) => () => void;
}

export interface TabsAPI {
  createTab: (urlPath?: string) => void;
  switchTab: (tabId: string) => void;
  closeTab: (tabId: string) => void;
  goBack: () => void;
  goForward: () => void;
  reload: () => void;
  onTabsUpdated: (callback: (data: { tabs: any[]; activeId: string | null }) => void) => void;
}

const desktopAPI: DesktopAPI = {
  isDesktop: true,
  platform: process.platform,
  version: '1.0.0',
  sendNotification: (title: string, body: string) =>
    ipcRenderer.invoke('desktop:notify', { title, body }),
  captureScreen: () => ipcRenderer.invoke('desktop:capture-screen'),
  minimizeWindow: () => ipcRenderer.send('desktop:minimize'),
  maximizeWindow: () => ipcRenderer.send('desktop:maximize'),
  closeWindow: () => ipcRenderer.send('desktop:close'),
  openExternal: (url: string) => ipcRenderer.send('desktop:open-external', url),
  onNavigate: (callback: (route: string) => void) => {
    const listener = (_event: Electron.IpcRendererEvent, route: string) => callback(route);
    ipcRenderer.on('desktop:navigate', listener);
    return () => {
      ipcRenderer.removeListener('desktop:navigate', listener);
    };
  },
};

const tabsAPI: TabsAPI = {
  createTab: (urlPath?: string) => ipcRenderer.send('tabs:create', urlPath),
  switchTab: (tabId: string) => ipcRenderer.send('tabs:switch', tabId),
  closeTab: (tabId: string) => ipcRenderer.send('tabs:close', tabId),
  goBack: () => ipcRenderer.send('tabs:go-back'),
  goForward: () => ipcRenderer.send('tabs:go-forward'),
  reload: () => ipcRenderer.send('tabs:reload'),
  onTabsUpdated: (callback) => {
    ipcRenderer.on('desktop:tabs-updated', (_event, data) => callback(data));
  },
};

contextBridge.exposeInMainWorld('kognitoDesktop', desktopAPI);
contextBridge.exposeInMainWorld('kognitoTabs', tabsAPI);
