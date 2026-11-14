'use client';

import { useEffect, useState } from 'react';

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

declare global {
  interface Window {
    kognitoDesktop?: DesktopAPI;
  }
}

export function useDesktop() {
  const [isDesktop, setIsDesktop] = useState(false);
  const [desktopAPI, setDesktopAPI] = useState<DesktopAPI | null>(null);

  useEffect(() => {
    if (typeof window !== 'undefined' && window.kognitoDesktop) {
      setIsDesktop(true);
      setDesktopAPI(window.kognitoDesktop);
    }
  }, []);

  return {
    isDesktop,
    desktop: desktopAPI,
  };
}
