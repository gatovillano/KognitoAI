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
import { useArtifactPanel } from '@/contexts/ArtifactPanelContext';
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
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  
  // Detectar si estamos en un chat de workspace
  const workspaceMatch = pathname?.match(/\/workspaces\/([a-f0-9-]+)\/chat\/([a-f0-9-]+)/);
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
        <div className="fixed inset-0 bg-background">
          <div
            className={`bg-card/80 backdrop-blur-xl transition-all duration-500 ease-in-out ${isSidebarCollapsed ? 'w-16' : 'w-64'} h-full overflow-y-auto fixed left-0 top-0 z-10 shadow-medium border-r border-border/20`}
          >
            <Sidebar isCollapsed={isSidebarCollapsed} />
          </div>

          <div className={`fixed top-0 bottom-0 right-0 flex flex-col transition-all duration-500 ease-in-out ${isSidebarCollapsed ? 'left-16' : 'left-64'}`}>
            <header className="flex h-16 items-center gap-4 bg-card/80 backdrop-blur-xl px-6 shrink-0 shadow-soft border-b border-border/20">
              <Button
                variant="ghost"
                size="icon"
                onClick={toggleSidebar}
                className="rounded-xl hover:bg-primary/10 hover:text-primary transition-all duration-200"
              >
                {isSidebarCollapsed ? <PanelLeftOpen className="h-5 w-5" /> : <PanelLeftClose className="h-5 w-5" />}
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
                    className="rounded-xl hover:bg-primary/10 hover:text-primary hover:border-primary/20 transition-all duration-200"
                    title="Volver al Workspace"
                  >
                    <ArrowLeft className="h-4 w-4" />
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
            <main className="flex-1 bg-background overflow-y-auto pl-6">
              {children}
            </main>
          </div>
        </div>
      ) : (
        <div className="min-h-screen flex flex-col bg-background">
          <header className="flex h-16 items-center gap-4 bg-card/80 backdrop-blur-xl px-4 sticky top-0 z-10 border-b border-border/30 shadow-soft">
            <Sheet open={isMobileMenuOpen} onOpenChange={setIsMobileMenuOpen}>
              <SheetTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="rounded-xl hover:bg-primary/10 hover:text-primary transition-all duration-200"
                >
                  <PanelLeftOpen className="h-5 w-5" />
                </Button>
              </SheetTrigger>
              <SheetContent side="left" className="flex flex-col p-0 w-72 border-r-0 bg-card/95 backdrop-blur-xl">
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
                <div className="flex items-center gap-3">
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
  const [isSearchMenuOpen, setIsSearchMenuOpen] = useState(false);
  const [isChatSearchDialogOpen, setIsChatSearchDialogOpen] = useState(false);
  const [searchResults, setSearchResults] = useState<{chats: any[], quotes: any[]}>({chats: [], quotes: []});
  const [isSearching, setIsSearching] = useState(false);

  // Función para buscar chats y citas
  const performSearch = async (term: string) => {
    if (!term.trim()) {
      setSearchResults({chats: [], quotes: []});
      return;
    }

    setIsSearching(true);
    try {
      // Aquí harías la llamada real a la API
      // Por ahora simulo algunos resultados
      const mockChats = [
        { id: '1', title: 'Conversación sobre React', lastMessage: 'Hablamos sobre hooks...', date: '2024-01-15' },
        { id: '2', title: 'Análisis de datos', lastMessage: 'Revisamos las métricas...', date: '2024-01-14' }
      ];

      const mockQuotes = [
        { id: '1', text: 'Los hooks de React permiten usar estado...', context: 'En la conversación sobre React', chatId: '1', date: '2024-01-15' },
        { id: '2', text: 'Las métricas muestran un crecimiento...', context: 'En el análisis de datos', chatId: '2', date: '2024-01-14' }
      ];

      setSearchResults({
        chats: mockChats.filter(chat =>
          chat.title.toLowerCase().includes(term.toLowerCase()) ||
          chat.lastMessage.toLowerCase().includes(term.toLowerCase())
        ),
        quotes: mockQuotes.filter(quote =>
          quote.text.toLowerCase().includes(term.toLowerCase())
        )
      });
    } catch (error) {
      console.error('Error searching:', error);
    } finally {
      setIsSearching(false);
    }
  };

  // Efecto para buscar cuando cambia el término
  useEffect(() => {
    const debounceTimer = setTimeout(() => {
      if (searchTerm) {
        performSearch(searchTerm);
        setIsSearchMenuOpen(true);
      } else {
        setIsSearchMenuOpen(false);
        setSearchResults({chats: [], quotes: []});
      }
    }, 300);

    return () => clearTimeout(debounceTimer);
  }, [searchTerm]);

  return (
    <div className="relative">
      <input
        type="text"
        placeholder="Buscar chats y citas..."
        value={searchTerm}
        onChange={(e) => setSearchTerm(e.target.value)}
        onFocus={() => searchTerm && setIsSearchMenuOpen(true)}
        className="pl-8 pr-4 py-2 border border-border rounded-full text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 w-64 bg-background text-foreground placeholder:text-muted-foreground transition-all"
      />
      <Search className="h-4 w-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground" />

      {/* Menú desplegable de búsqueda */}
      {isSearchMenuOpen && (
        <div className="absolute top-full left-0 right-0 mt-2 bg-card border border-border rounded-lg shadow-lg z-50 max-h-96 overflow-hidden">
          {/* Header con botón para abrir búsqueda avanzada */}
          <div className="p-3 border-b border-border">
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setIsChatSearchDialogOpen(true);
                setIsSearchMenuOpen(false);
              }}
              className="w-full justify-start"
            >
              <ExternalLink className="h-4 w-4 mr-2" />
              Abrir búsqueda avanzada
            </Button>
          </div>

          {isSearching ? (
            <div className="p-4 text-center text-sm text-muted-foreground">
              Buscando...
            </div>
          ) : (
            <div className="max-h-80 overflow-y-auto">
              {/* Sección de Chats */}
              {searchResults.chats.length > 0 && (
                <div className="p-3">
                  <div className="flex items-center gap-2 mb-2 text-xs font-medium text-muted-foreground uppercase tracking-wide">
                    <MessageSquare className="h-3 w-3" />
                    Chats ({searchResults.chats.length})
                  </div>
                  <div className="space-y-1">
                    {searchResults.chats.slice(0, 3).map((chat) => (
                      <div
                        key={chat.id}
                        className="p-2 rounded-md hover:bg-muted cursor-pointer transition-colors"
                        onClick={() => {
                          // Navegar al chat
                          setIsSearchMenuOpen(false);
                          setSearchTerm('');
                        }}
                      >
                        <div className="font-medium text-sm">{chat.title}</div>
                        <div className="text-xs text-muted-foreground truncate">{chat.lastMessage}</div>
                        <div className="text-xs text-muted-foreground">{chat.date}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Sección de Citas */}
              {searchResults.quotes.length > 0 && (
                <div className="p-3 border-t border-border">
                  <div className="flex items-center gap-2 mb-2 text-xs font-medium text-muted-foreground uppercase tracking-wide">
                    <Quote className="h-3 w-3" />
                    Citas ({searchResults.quotes.length})
                  </div>
                  <div className="space-y-1">
                    {searchResults.quotes.slice(0, 3).map((quote) => (
                      <div
                        key={quote.id}
                        className="p-2 rounded-md hover:bg-muted cursor-pointer transition-colors"
                        onClick={() => {
                          // Copiar cita o navegar
                          setIsSearchMenuOpen(false);
                          setSearchTerm('');
                        }}
                      >
                        <div className="text-sm line-clamp-2">"{quote.text}"</div>
                        <div className="text-xs text-muted-foreground">{quote.context} • {quote.date}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Estado vacío */}
              {!isSearching && searchResults.chats.length === 0 && searchResults.quotes.length === 0 && searchTerm && (
                <div className="p-4 text-center text-sm text-muted-foreground">
                  No se encontraron resultados para "{searchTerm}"
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Overlay para cerrar el menú */}
      {isSearchMenuOpen && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => setIsSearchMenuOpen(false)}
        />
      )}

      {/* Diálogo de búsqueda avanzada */}
      <ChatSearchDialog
        isOpen={isChatSearchDialogOpen}
        onOpenChange={setIsChatSearchDialogOpen}
        messages={[]} // Aquí pasarías los mensajes reales
      />
    </div>
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
