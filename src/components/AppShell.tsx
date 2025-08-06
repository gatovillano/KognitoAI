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
import { ChatSearchDialog } from './ChatSearchDialog';
import { PanelRightOpen, PanelRightClose } from 'lucide-react';

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
  
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [isRightPanelOpen, setIsRightPanelOpen] = useState(false); // New state for right panel
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  
  // Detectar si estamos en un chat de workspace
  const workspaceMatch = pathname?.match(/\/workspaces\/([a-f0-9-]+)\/chat\/([a-f0-9-]+)/);
  const isWorkspaceChat = !!workspaceMatch;
  const workspaceId = workspaceMatch?.[1];

  const toggleSidebar = () => {
    setIsSidebarCollapsed(!isSidebarCollapsed);
  };

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
        <div className="flex h-screen bg-background">
            {/* Sidebar para desktop (visible en md y superior) */}
            <div
              className={`hidden md:block bg-card/80 backdrop-blur-xl transition-all duration-500 ease-in-out ${isSidebarCollapsed ? 'w-16' : 'w-72'} h-full overflow-y-auto shadow-medium border-border/20`}
            >
              <Sidebar isCollapsed={isSidebarCollapsed} />
            </div>

            {/* Contenido principal */}
            <div className={`flex flex-col flex-1 transition-all duration-500 ease-in-out`}>
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
                    <Sidebar isCollapsed={false} onLinkClick={() => setIsMobileMenuOpen(false)} />
                  </SheetContent>
                </Sheet>

                {/* Botón para colapsar/expandir sidebar en desktop */}
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={toggleSidebar}
                  className="hidden md:flex rounded-xl hover:bg-primary/10 hover:text-primary transition-all duration-200"
                >
                  {isSidebarCollapsed ? <PanelLeftOpen className="h-5 w-5" /> : <PanelLeftClose className="h-5 w-5" />}
                </Button>
                
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
                    <div className="hidden md:flex items-center gap-3">
                      <div className="relative">
                        <Image src="/logo-simple.png" alt="Kognito Logo" width={40} height={40} className="rounded-lg" />
                        <div className="absolute -bottom-1 -right-1 w-3 h-3 bg-primary rounded-full border-2 border-background"></div>
                      </div>
                      <div className="flex flex-col">
                        <span className="font-bold text-lg text-foreground">Kognito</span>
                        <span className="text-xs text-muted-foreground">AI Labs</span>
                      </div>
                    </div>
                  )}
                </div>
                
                {/* Controles del header a la derecha */}
                <div className="ml-auto flex gap-3 items-center">
                  {isChatContext && (
                    <div className="relative">
                      <SearchInput />
                    </div>
                  )}
                  <ThemeToggle />
                  {/* New button for right panel */}
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={toggleRightPanel}
                    className="rounded-xl hover:bg-primary/10 hover:text-primary transition-all duration-200"
                  >
                    {isRightPanelOpen ? <PanelRightClose className="h-5 w-5" /> : <PanelRightOpen className="h-5 w-5" />}
                  </Button>
                </div>
              </header>
              <main className="flex-1 bg-background overflow-y-auto p-4 md:p-6">
                {children}
              </main>
            </div>
        </div>
      </SearchProvider>
    </LoadingProvider>
  );
}

function SearchInput() {
  const { searchTerm, setSearchTerm } = useSearch();
  const [isChatSearchDialogOpen, setIsChatSearchDialogOpen] = useState(false);

  useEffect(() => {
    if (searchTerm) {
      setIsChatSearchDialogOpen(true);
    } else {
      setIsChatSearchDialogOpen(false);
    }
  }, [searchTerm]);

  return (
    <div className="relative">
      <input
        type="text"
        placeholder="Buscar en chats y mensajes..."
        value={searchTerm}
        onChange={(e) => setSearchTerm(e.target.value)}
        className="pl-8 pr-4 py-2 border border-border rounded-full text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 w-64 bg-background text-foreground placeholder:text-muted-foreground transition-all"
      />
      <Search className="h-4 w-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground" />

      <ChatSearchDialog
        isOpen={isChatSearchDialogOpen}
        onOpenChange={setIsChatSearchDialogOpen}
        searchTerm={searchTerm}
        setSearchTerm={setSearchTerm}
      />
    </div>
  );
}
