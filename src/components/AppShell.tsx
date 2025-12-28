'use client';

import React, { useState, useEffect } from 'react';
import { useMediaQuery } from '@uidotdev/usehooks';
import { usePathname, useRouter } from 'next/navigation';
import { Sidebar } from './Sidebar';
import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet';
import { PanelLeftClose, PanelLeftOpen, ArrowLeft, Bot, Search, MessageSquare, Quote, ExternalLink } from 'lucide-react';
import Image from 'next/image';
import apiClient from '@/lib/api';
import { ThemeToggle } from './ThemeToggle';
import { LoadingProvider } from '@/contexts/LoadingContext';
import { SearchProvider, useSearch } from '@/contexts/SearchContext';
import { PanelRightOpen, PanelRightClose } from 'lucide-react';
import { UniversalSearchInput } from './UniversalSearchInput';
import { useWebSocketContext } from '@/contexts/WebSocketContext';
import { Badge } from '@/components/ui/badge';
import { Wifi, WifiOff, AlertTriangle } from 'lucide-react';
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels';

interface AppShellProps {
  children: React.ReactNode;
}

interface Workspace {
  id: string;
  name: string;
}

export function AppShell({ children }: AppShellProps) {
  const isDesktop = useMediaQuery('(min-width: 768px)');
  const pathname = usePathname();
  const router = useRouter();
  const isChatContext = pathname?.includes('/chat/');

  // Estado de conexión WebSocket
  const { isConnected, connectionError, reconnect } = useWebSocketContext();

  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isRightPanelOpen, setIsRightPanelOpen] = useState(false); // New state for right panel
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [sidebarSize, setSidebarSize] = useState(22); // Track sidebar size in percentage
  
  // Detectar si estamos en un chat de workspace
  const workspaceMatch = pathname?.match(/\/workspaces\/([a-f0-9-]+)\/chat\/([a-f0-9-]+)/);
  const isWorkspaceChat = !!workspaceMatch;
  const workspaceId = workspaceMatch?.[1];

  const toggleRightPanel = () => { // New toggle function for right panel
    setIsRightPanelOpen(!isRightPanelOpen);
  };

  const handleBackToWorkspace = () => {
    if (workspaceId) {
      router.push(`/workspaces/${workspaceId}`);
    }
  };

  // Obtener información del workspace cuando estamos en un chat de workspace
  useEffect(() => {
    if (isWorkspaceChat && workspaceId) {
      const fetchWorkspace = async () => {
        try {
          const response = await apiClient.get(`/api/workspaces/${workspaceId}`);
          setWorkspace(response.data);
        } catch (error) {
          console.error('Error fetching workspace:', error);
          setWorkspace(null);
        }
      };
      fetchWorkspace();
    } else {
      setWorkspace(null);
    }
  }, [isWorkspaceChat, workspaceId]);

  return (
    <LoadingProvider>
      <SearchProvider>
        <div className="h-screen bg-background overflow-x-hidden">
          <PanelGroup direction="horizontal" className="h-full">
            {/* Sidebar para desktop (visible en md y superior) */}
            <Panel
              defaultSize={22} // 22% por defecto
              minSize={4}
              maxSize={35}
              onResize={setSidebarSize}
              className="hidden md:block"
            >
              <div className="h-full bg-card/80 backdrop-blur-xl shadow-medium border-border/20">
                <Sidebar isCollapsed={sidebarSize < 12} showToolText={sidebarSize > 8} />
              </div>
            </Panel>

            <PanelResizeHandle className="hidden md:flex w-1 bg-border hover:bg-primary/20 transition-colors cursor-col-resize" />

            {/* Contenido principal */}
            <Panel defaultSize={78} minSize={50}>
              <div className={`flex flex-col h-full`}>
              <header className="flex h-16 items-center gap-4 bg-card/80 backdrop-blur-xl px-4 md:px-6 shrink-0 shadow-soft border-border/20">
                {/* Botón de menú para móvil (visible hasta md) */}
                <Sheet open={isMobileMenuOpen} onOpenChange={setIsMobileMenuOpen}>
                  <SheetTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="md:hidden rounded-xl hover:bg-primary/10 hover:text-primary transition-all duration-200"
                    >
                      <PanelLeftOpen className="h-5 w-5" />
                    </Button>
                  </SheetTrigger>
                  <SheetContent side="left" className="flex flex-col p-0 w-72 border-r-0 bg-card/95 backdrop-blur-xl">
                    <Sidebar isCollapsed={false} showToolText={true} onLinkClick={() => setIsMobileMenuOpen(false)} />
                  </SheetContent>
                </Sheet>

                
                {/* Título del Workspace o Logo */}
                <div className="flex items-center gap-3">
                  {isWorkspaceChat && workspace ? (
                    <>
                      <Bot className="h-5 w-5 text-primary" />
                      <h1 className="text-lg font-semibold text-foreground truncate">{workspace.name}</h1>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={handleBackToWorkspace}
                        className="rounded-xl hover:bg-primary/10 hover:text-primary hover:border-primary/20 transition-all duration-200"
                        title="Volver al Workspace"
                      >
                        <ArrowLeft className="h-4 w-4" />
                      </Button>
                    </>
                  ) : (
                    null
                  )}
                </div>
                
                {/* Controles del header a la derecha */}
                <div className="ml-auto flex gap-3 items-center">
                  <div className="relative">
                    <UniversalSearchInput />
                  </div>

                  {/* Indicador de estado de conexión WebSocket */}
                  <div className="flex items-center gap-2">
                    {connectionError ? (
                      <Badge
                        variant="destructive"
                        className="flex items-center gap-1 cursor-pointer hover:bg-destructive/80 transition-colors"
                        onClick={reconnect}
                        title={`Error de conexión: ${connectionError}. Haz clic para reconectar.`}
                      >
                        <AlertTriangle className="h-3 w-3" />
                        <span className="hidden sm:inline">Error WS</span>
                      </Badge>
                    ) : isConnected ? (
                      <Badge
                        variant="secondary"
                        className="flex items-center gap-1 bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200"
                        title="Conexión WebSocket activa"
                      >
                        <Wifi className="h-3 w-3" />
                        <span className="hidden sm:inline">Conectado</span>
                      </Badge>
                    ) : (
                      <Badge
                        variant="outline"
                        className="flex items-center gap-1 cursor-pointer hover:bg-primary/10 transition-colors"
                        onClick={reconnect}
                        title="Conectando WebSocket... Haz clic para reconectar."
                      >
                        <WifiOff className="h-3 w-3" />
                        <span className="hidden sm:inline">Conectando</span>
                      </Badge>
                    )}
                  </div>

                  <ThemeToggle />
                  {/* New button for right panel */}
                  {/* Botón de despliegue del menú de la derecha eliminado */}
                  <Image src="/logo-simple.png" alt="Kognito Logo" width={40} height={40} className="rounded-lg" />
                </div>
              </header>
              <main className="flex-1 bg-background p-4 md:p-6 overflow-y-auto pb-24">
                {children}
              </main>
            </div>
            </Panel>
          </PanelGroup>
        </div>
      </SearchProvider>
    </LoadingProvider>
  );
}

