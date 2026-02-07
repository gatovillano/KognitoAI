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
import { Separator } from '@/components/ui/separator';

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
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [isRightPanelOpen, setIsRightPanelOpen] = useState(false); // New state for right panel
  const [workspace, setWorkspace] = useState<Workspace | null>(null);

  const toggleSidebar = () => {
    setIsSidebarCollapsed(!isSidebarCollapsed);
  };

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
        <div className="h-screen bg-background overflow-hidden flex font-sans selection:bg-primary/20 selection:text-primary relative">
          {/* Gradiente de fondo sutil para profundidad - ahora cubre toda la pantalla */}
          <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-secondary/5 pointer-events-none z-0" />

          {/* Sidebar para desktop (fijo en md y superior) */}
          <aside className={`hidden md:block h-full p-4 pr-0 flex-shrink-0 transition-all duration-500 ease-in-out z-10 ${isSidebarCollapsed ? 'w-24' : 'w-72'}`}>
            <div className="h-full w-full bg-card/40 backdrop-blur-2xl shadow-xl border border-border/40 rounded-3xl overflow-hidden transition-all duration-300 hover:border-primary/20">
              <Sidebar isCollapsed={isSidebarCollapsed} showToolText={!isSidebarCollapsed} />
            </div>
          </aside>

          {/* Contenido principal */}
          <div className="flex-1 flex flex-col min-w-0 h-full relative z-10">

            <header className="flex h-16 sm:h-20 items-center gap-2 sm:gap-4 bg-transparent px-4 sm:px-6 md:px-8 shrink-0 z-10">
              {/* Botón de toggle para desktop */}
              <Button
                variant="ghost"
                size="icon"
                onClick={toggleSidebar}
                className="hidden md:flex rounded-2xl hover:bg-primary/10 hover:text-primary transition-all duration-300"
                title={isSidebarCollapsed ? "Expandir Sidebar" : "Contraer Sidebar"}
              >
                {isSidebarCollapsed ? <PanelLeftOpen className="h-5 w-5" /> : <PanelLeftClose className="h-5 w-5" />}
              </Button>

              {/* Botón de menú para móvil (visible hasta md) */}
              <Sheet open={isMobileMenuOpen} onOpenChange={setIsMobileMenuOpen}>
                <SheetTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="md:hidden rounded-2xl hover:bg-primary/10 hover:text-primary transition-all duration-300"
                  >
                    <PanelLeftOpen className="h-5 w-5" />
                  </Button>
                </SheetTrigger>
                <SheetContent side="left" className="flex flex-col p-4 w-72 border-none bg-background/95 backdrop-blur-2xl">
                  <div className="h-full w-full bg-card/40 backdrop-blur-xl border border-border/40 rounded-3xl overflow-hidden">
                    <Sidebar isCollapsed={false} showToolText={true} onLinkClick={() => setIsMobileMenuOpen(false)} />
                  </div>
                </SheetContent>
              </Sheet>


              {/* Título del Workspace o Logo */}
              <div className="flex items-center gap-1.5 sm:gap-3 min-w-0 flex-1 sm:flex-none">
                {isWorkspaceChat && workspace ? (
                  <div className="flex items-center gap-3 bg-card/40 backdrop-blur-md px-4 py-2 rounded-2xl border border-border/40 shadow-sm">
                    <Bot className="h-5 w-5 text-primary flex-shrink-0 animate-pulse" />
                    <h1 className="text-sm sm:text-base font-bold text-foreground truncate max-w-[100px] sm:max-w-[200px] tracking-tight">{workspace.name}</h1>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={handleBackToWorkspace}
                      className="h-8 w-8 p-0 rounded-xl hover:bg-primary/10 hover:text-primary transition-all duration-200"
                      title="Volver al Workspace"
                    >
                      <ArrowLeft className="h-4 w-4" />
                    </Button>
                  </div>
                ) : (
                  null
                )}
              </div>

              {/* Controles del header a la derecha */}
              <div className="ml-auto flex gap-2 sm:gap-4 items-center flex-shrink-0">
                <div className="relative hidden sm:block">
                  <UniversalSearchInput />
                </div>

                {/* Indicador de estado de conexión WebSocket */}
                <div className="flex items-center">
                  {connectionError ? (
                    <Badge
                      variant="destructive"
                      className="flex items-center justify-center h-9 px-3 gap-2 rounded-2xl cursor-pointer hover:bg-destructive/80 transition-all duration-300 shadow-lg shadow-destructive/20"
                      onClick={reconnect}
                    >
                      <AlertTriangle className="h-4 w-4" />
                      <span className="hidden lg:inline font-bold text-xs uppercase tracking-wider">Error WS</span>
                    </Badge>
                  ) : isConnected ? (
                    <Badge
                      variant="secondary"
                      className="flex items-center justify-center h-9 px-3 gap-2 rounded-2xl bg-green-500/10 text-green-600 dark:text-green-400 border border-green-500/20 shadow-lg shadow-green-500/5"
                    >
                      <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
                      <span className="hidden lg:inline font-bold text-xs uppercase tracking-wider">Online</span>
                    </Badge>
                  ) : (
                    <Badge
                      variant="outline"
                      className="flex items-center justify-center h-9 px-3 gap-2 rounded-2xl border-primary/20 text-primary animate-pulse"
                      onClick={reconnect}
                    >
                      <WifiOff className="h-4 w-4" />
                      <span className="hidden lg:inline font-bold text-xs uppercase tracking-wider">Conectando</span>
                    </Badge>
                  )}
                </div>

                <div className="flex items-center gap-2 bg-card/40 backdrop-blur-md p-1 rounded-2xl border border-border/40">
                  <ThemeToggle />
                  <Separator orientation="vertical" className="h-6 mx-1 opacity-20" />
                  <div className="relative group">
                    <div className="absolute -inset-0.5 bg-gradient-to-r from-primary to-secondary rounded-xl blur opacity-30 group-hover:opacity-60 transition duration-300" />
                    <Image src="/logo-simple.png" alt="Kognito Logo" width={36} height={36} className="relative rounded-xl border border-white/10" />
                  </div>
                </div>
              </div>
            </header>

            <main className={`flex-1 relative z-0 ${isChatContext ? 'overflow-hidden p-0' : 'p-1 md:p-8 lg:p-10 overflow-y-auto custom-scrollbar'}`}>
              <div className={isChatContext ? 'h-full w-full' : 'max-w-7xl mx-auto'}>
                {children}
              </div>
            </main>
          </div>
        </div>
      </SearchProvider>
    </LoadingProvider>
  );
}

