'use client';

import React, { useState, useEffect } from 'react';
import { useMediaQuery } from '@uidotdev/usehooks';
import { usePathname, useRouter } from 'next/navigation';
import { Sidebar } from './Sidebar';
import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet';
import { PanelLeftClose, PanelLeftOpen, ArrowLeft, Bot } from 'lucide-react';
import Image from 'next/image';
import apiClient from '@/lib/api';
import { ThemeToggle } from './ThemeToggle'; // Importamos el botón de tema
import { LoadingProvider } from '@/contexts/LoadingContext';
import { SearchProvider, useSearch } from '@/contexts/SearchContext';
import { useArtifactPanel } from '@/contexts/ArtifactPanelContext';
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
  const isChatContext = pathname.includes('/chat/');
  
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  
  // Detectar si estamos en un chat de workspace
  const workspaceMatch = pathname.match(/\/workspaces\/([a-f0-9-]+)\/chat\/([a-f0-9-]+)/);
  const isWorkspaceChat = !!workspaceMatch;
  const workspaceId = workspaceMatch?.[1];

  const toggleSidebar = () => {
    setIsSidebarCollapsed(!isSidebarCollapsed);
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
      {isDesktop ? (
        <div className="h-screen max-h-screen overflow-hidden flex bg-background">
          <div
            className={`bg-card transition-all duration-300 ease-in-out rounded-tr-lg ${isSidebarCollapsed ? 'w-20' : 'w-80'}`}
          >
            <Sidebar isCollapsed={isSidebarCollapsed} />
          </div>

          <div className="flex-grow flex flex-col">
            <header className="flex h-14 items-center gap-4 bg-card px-6 shrink-0 border-b border-border/50">
              <Button variant="ghost" size="icon" onClick={toggleSidebar} className="rounded-full hover:bg-muted">
                {isSidebarCollapsed ? <PanelLeftOpen className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
              </Button>
              
              {/* Información del workspace si estamos en un chat de workspace */}
              {isWorkspaceChat && workspace && (
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-2">
                    <Bot className="h-5 w-5 text-primary" />
                    <h1 className="text-lg font-semibold text-foreground">{workspace.name}</h1>
                  </div>
                  <Button 
                    variant="outline" 
                    size="sm" 
                    onClick={handleBackToWorkspace}
                    className="rounded-full"
                    title="Volver al Workspace"
                  >
                    <ArrowLeft className="h-3 w-3" />
                  </Button>
                </div>
              )}
              
              <div className="ml-auto flex gap-3 items-center">
                {isChatContext && (
                  <div className="relative">
                    <SearchInput />
                  </div>
                )}
                <ThemeToggle />
                <ArtifactPanelToggleButton />
              </div>
            </header>
            <main className="flex-grow overflow-y-auto bg-background">
              {children}
            </main>
          </div>
        </div>
      ) : (
        <div className="min-h-screen flex flex-col bg-background">
          <header className="flex h-14 items-center gap-4 bg-card px-4 sticky top-0 z-10 border-b border-border/50">
            <Sheet open={isMobileMenuOpen} onOpenChange={setIsMobileMenuOpen}>
              <SheetTrigger asChild>
                <Button variant="ghost" size="icon" className="rounded-full hover:bg-muted">
                  <PanelLeftOpen className="h-4 w-4" />
                </Button>
              </SheetTrigger>
              <SheetContent side="left" className="flex flex-col p-0 w-72 border-r-0">
                <Sidebar isCollapsed={false} onLinkClick={() => setIsMobileMenuOpen(false)} />
              </SheetContent>
            </Sheet>
            <div className="w-full flex-1 flex items-center gap-3">
              {isWorkspaceChat && workspace ? (
                <div className="flex items-center gap-2">
                  <Bot className="h-5 w-5 text-primary" />
                  <h1 className="text-lg font-semibold text-foreground truncate">{workspace.name}</h1>
                </div>
              ) : (
                <>
                  <Image src="/logo-simple.png" alt="Kognito Logo" width={40} height={40} />
                  <span className="font-bold text-lg text-foreground">Kognito</span>
                </>
              )}
              {isChatContext && !isWorkspaceChat && (
                <div className="relative ml-auto">
                  <SearchInput />
                </div>
              )}
            </div>
            <div className="ml-auto flex gap-3 items-center">
              {isWorkspaceChat && workspace && (
                <Button 
                  variant="ghost" 
                  size="icon" 
                  onClick={handleBackToWorkspace}
                  className="rounded-full hover:bg-muted"
                  title="Volver al Workspace"
                >
                  <ArrowLeft className="h-4 w-4" />
                </Button>
              )}
              <ThemeToggle />
              <ArtifactPanelToggleButton />
            </div>
          </header>
          <main className="flex-grow">
            {children}
          </main>
        </div>
      )}
    </SearchProvider>
    </LoadingProvider>
  );
}

function SearchInput() {
  const { searchTerm, setSearchTerm } = useSearch();
  return (
    <>
      <input
        type="text"
        placeholder="Buscar en el chat..."
        value={searchTerm}
        onChange={(e) => setSearchTerm(e.target.value)}
        className="pl-8 pr-4 py-2 border border-border rounded-full text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 w-64 bg-background text-foreground placeholder:text-muted-foreground transition-all"
      />
      <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
      </svg>
    </>
  );
}

function ArtifactPanelToggleButton() {
  const { isVisible, toggleVisibility } = useArtifactPanel();
  return (
    <Button variant="ghost" size="icon" onClick={toggleVisibility} className="rounded-full hover:bg-muted">
      {isVisible ? <PanelRightClose className="h-4 w-4" /> : <PanelRightOpen className="h-4 w-4" />}
    </Button>
  );
}
