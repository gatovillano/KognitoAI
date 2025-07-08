// En: src/components/Sidebar.tsx (Versión completa y actualizada)

'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger, DropdownMenuSeparator } from '@/components/ui/dropdown-menu';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Plus, MessageSquare, BookMarked, Notebook, Calendar, LogOut, Bot, ChevronDown, ChevronRight, Pin, Users, Sparkles, MoreVertical, FolderKanban, Settings, BarChart3, Smartphone } from 'lucide-react';
import Image from 'next/image';
import apiClient from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';
import { cn } from '@/lib/utils';
import { InlineMarkdownRenderer } from './InlineMarkdownRenderer';
import { DndProvider, useDrag, useDrop } from 'react-dnd';
import { HTML5Backend } from 'react-dnd-html5-backend';

interface SidebarProps {
  isCollapsed: boolean;
  onLinkClick?: () => void;
}

interface ChatThread {
  id: string;
  title: string;
  isPinned?: boolean;
  platform?: string;
  workspace_id?: string | null;
}

export function Sidebar({ isCollapsed, onLinkClick }: SidebarProps) {
  const [threads, setThreads] = useState<ChatThread[]>([]);
  const [pinnedThreads, setPinnedThreads] = useState<ChatThread[]>([]);
  const [isPinnedCollapsed, setIsPinnedCollapsed] = useState(false);
  const [isRecentCollapsed, setIsRecentCollapsed] = useState(false);
  const { logout, user } = useAuth();
  const pathname = usePathname();
  const router = useRouter();

  const [activeWorkspaceId, setActiveWorkspaceId] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState<string>("");
  const [platformFilter, setPlatformFilter] = useState<'all' | 'web' | 'telegram'>('all');

  useEffect(() => {
    const updateActiveWorkspace = async () => {
      const threadIdMatch = pathname.match(/\/chat\/([a-f0-9-]+)/);
      if (threadIdMatch) {
        try {
          const response = await apiClient.get<ChatThread>(`/api/threads/${threadIdMatch[1]}`);
          setActiveWorkspaceId(response.data.workspace_id || null);
        } catch (error) {
          console.error('Error fetching thread details for workspace context:', error);
          setActiveWorkspaceId(null);
        }
      } else {
        const workspaceIdMatch = pathname.match(/\/workspaces\/([a-f0-9-]+)(?:\/chat\/[a-f0-9-]+)?/);
        if (workspaceIdMatch) {
          setActiveWorkspaceId(workspaceIdMatch[1]);
        } else {
          setActiveWorkspaceId(null);
        }
      }
    };

    updateActiveWorkspace();
  }, [pathname]);

  useEffect(() => {
    const fetchThreads = async () => {
      if (user) {
        try {
          // Se obtienen todos los hilos y se filtran en el cliente para mayor consistencia.
          const response = await apiClient.get<ChatThread[]>('/api/threads');
          const allThreads = response.data;
          
          const filteredThreads = activeWorkspaceId
            ? allThreads.filter(thread => thread.workspace_id === activeWorkspaceId)
            : allThreads.filter(thread => !thread.workspace_id);
            
          setThreads(filteredThreads.filter(thread => !thread.isPinned));
          setPinnedThreads(filteredThreads.filter(thread => thread.isPinned));
        } catch (error) {
          console.error('Error fetching threads:', error);
        }
      }
    };
    fetchThreads();
  }, [user, activeWorkspaceId]);

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(e.target.value);
  };

  const applyFilters = (threadList: ChatThread[]) => {
    let filtered = threadList;

    // Filtro por búsqueda
    if (searchTerm) {
      filtered = filtered.filter(thread => thread.title.toLowerCase().includes(searchTerm.toLowerCase()));
    }

    // Filtro por plataforma
    if (platformFilter !== 'all') {
      filtered = filtered.filter(thread => thread.platform === platformFilter);
    }

    return filtered;
  };

  const filteredThreadsBySearch = applyFilters(threads);
  const filteredPinnedThreadsBySearch = applyFilters(pinnedThreads);

  const handleNewChat = async () => {
    try {
      const payload = { workspace_id: activeWorkspaceId };
      const response = await apiClient.post<ChatThread>('/api/threads', payload);
      const newThread = response.data;
      setThreads((prevThreads) => [newThread, ...prevThreads]);
      router.push(`/chat/${newThread.id}`);
      if (onLinkClick) {
        onLinkClick();
      }
    } catch (error) {
      console.error('Error creating new chat:', error);
    }
  };

  const handlePinThread = async (thread: ChatThread) => {
    try {
      await apiClient.put(`/api/threads/${thread.id}/pin`, { isPinned: true });
      setThreads((prevThreads) => prevThreads.filter(t => t.id !== thread.id));
      setPinnedThreads((prevPinned) => [...prevPinned, { ...thread, isPinned: true }]);
    } catch (error) {
      console.error('Error pinning thread:', error);
    }
  };

  const handleUnpinThread = async (thread: ChatThread) => {
    try {
      await apiClient.put(`/api/threads/${thread.id}/pin`, { isPinned: false });
      setPinnedThreads((prevPinned) => prevPinned.filter(t => t.id !== thread.id));
      setThreads((prevThreads) => [...prevThreads, { ...thread, isPinned: false }]);
    } catch (error) {
      console.error('Error unpinning thread:', error);
    }
  };

  const handleDeleteThread = async (thread: ChatThread) => {
    try {
      await apiClient.delete(`/api/threads/${thread.id}`);
      setPinnedThreads((prevPinned) => prevPinned.filter(t => t.id !== thread.id));
      setThreads((prevThreads) => prevThreads.filter(t => t.id !== thread.id));
      if (pathname === `/chat/${thread.id}`) {
        router.push('/chat');
      }
    } catch (error) {
      console.error('Error deleting thread:', error);
    }
  };

    const ThreadItem = ({ thread, isPinned }: { thread: ChatThread; isPinned: boolean }) => {
    const [{ isDragging }, drag] = useDrag({
      type: 'THREAD',
      item: { thread, isPinned },
      collect: (monitor) => ({
        isDragging: monitor.isDragging(),
      }),
    });
    const [isMenuOpen, setIsMenuOpen] = useState(false);

    return (
      <div ref={drag as any} className={cn('opacity-100', isDragging && 'opacity-50')}>
        <Link href={`/chat/${thread.id}`} passHref onClick={onLinkClick} title={isCollapsed ? thread.title : undefined}>
          <Button
            variant={pathname === `/chat/${thread.id}` ? "secondary" : "ghost"}
            className={cn(
              "w-full font-normal items-start text-left transition-all duration-200 hover:bg-muted rounded-xl",
              isCollapsed ? "justify-center h-10 w-10 p-0" : "justify-start h-auto py-2 px-3"
            )}
          >
            <div className="flex items-center">
              <MessageSquare className={cn("h-4 w-4 mt-1 flex-shrink-0", !isCollapsed && "mr-2")} />
              {!isCollapsed && thread.platform === 'telegram' && (
                <div title="Telegram">
                  <Smartphone className="h-3 w-3 text-blue-500 mr-1 mt-1 flex-shrink-0" />
                </div>
              )}
            </div>
            {!isCollapsed && (
              <div className="whitespace-normal break-words flex-grow">
                <InlineMarkdownRenderer content={thread.title} />
              </div>
            )}
            {!isCollapsed && (
              <div className="ml-auto relative">
                <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <div
                        className="h-6 w-6 p-0 cursor-pointer flex items-center justify-center"
                        onClick={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                        }}
                      >
                        <MoreVertical className="h-4 w-4 text-muted-foreground" />
                      </div>
                    </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-48">
                    <DropdownMenuItem
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        isPinned ? handleUnpinThread(thread) : handlePinThread(thread);
                      }}
                    >
                      <Pin className={cn("h-4 w-4 mr-2", isPinned && "text-primary")} />
                      {isPinned ? "Desfijar" : "Fijar"}
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={async (e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        try {
                          const response = await apiClient.post(`/api/threads/${thread.id}/generate-title`);
                          const newTitle = response.data.title;
                          if (newTitle) {
                            const updatedThread = { ...thread, title: newTitle };
                            if (isPinned) {
                              setPinnedThreads((prev) => 
                                prev.map(t => t.id === thread.id ? updatedThread : t)
                              );
                            } else {
                              setThreads((prev) => 
                                prev.map(t => t.id === thread.id ? updatedThread : t)
                              );
                            }
                          }
                        } catch (error) {
                          console.error('Error generating title for thread:', error);
                        }
                      }}
                    >
                      <Sparkles className="h-4 w-4 mr-2 text-yellow-500" />
                      <span>Nombrar</span>
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        handleDeleteThread(thread);
                      }}
                    >
                      <span className="text-red-500">Eliminar</span>
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            )}
          </Button>
        </Link>
      </div>
    );
  };

  const DropArea = ({ onDrop, children }: { onDrop: (thread: ChatThread, isPinned: boolean) => void; children: React.ReactNode }) => {
    const [, drop] = useDrop({
      accept: 'THREAD',
      drop: (item: { thread: ChatThread; isPinned: boolean }) => {
        onDrop(item.thread, item.isPinned);
      },
    });

    return <div ref={drop as any} className="w-full">{children}</div>;
  };

  return (
    <div className={cn("flex flex-col h-full", isCollapsed ? "items-center p-2" : "p-6")}>
      {/* Header del sidebar */}
      <div className={cn("flex items-center w-full pb-6 mb-6 border-b border-border/50", isCollapsed ? "justify-center" : "justify-between")}>
        <div className="flex items-center gap-3">
          <div className="relative">
            <Image src="/logo-simple.png" alt="Kognito Logo" width={48} height={48} className="rounded-lg" />
            <div className="absolute -bottom-1 -right-1 w-4 h-4 bg-primary rounded-full border-2 border-background"></div>
          </div>
          {!isCollapsed && (
            <div className="flex flex-col">
              <span className="font-bold text-xl text-foreground">Kognito</span>
              <span className="text-xs text-muted-foreground">AI Labs</span>
            </div>
          )}
        </div>
        {!isCollapsed && (
          <Button
            onClick={handleNewChat}
            variant="ghost"
            size="icon"
            className="hover:bg-primary/10 hover:text-primary rounded-xl transition-all duration-200"
          >
            <Plus className="h-4 w-4" />
          </Button>
        )}
      </div>

      {/* Sección de herramientas */}
      <div className={cn("w-full", isCollapsed && "flex flex-col items-center")}>
        {!isCollapsed && (
          <div className="flex items-center gap-2 mb-4 px-2">
            <div className="w-1 h-1 rounded-full bg-primary"></div>
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Herramientas</p>
          </div>
        )}
        <nav className="space-y-2 w-full">
          <Link href="/dashboard" passHref onClick={onLinkClick} title="Escritorio">
            <Button
              variant={pathname.startsWith('/dashboard') ? 'secondary' : 'ghost'}
              className={cn(
                "w-full transition-all duration-300 hover:bg-primary/10 hover:text-primary rounded-xl group",
                isCollapsed ? "justify-center h-12 w-12 p-0" : "justify-start h-12 px-4",
                pathname.startsWith('/dashboard') && "bg-primary/10 text-primary border border-primary/20"
              )}
            >
              <Bot className={cn("h-5 w-5 transition-transform group-hover:scale-110", !isCollapsed && "mr-3")}/>
              {!isCollapsed && <span className="text-sm font-medium">Escritorio</span>}
            </Button>
          </Link>
          <Link href="/rag" passHref onClick={onLinkClick} title="Gestión de Conocimientos">
            <Button
              variant={pathname.startsWith('/rag') ? 'secondary' : 'ghost'}
              className={cn(
                "w-full transition-all duration-300 hover:bg-primary/10 hover:text-primary rounded-xl group",
                isCollapsed ? "justify-center h-12 w-12 p-0" : "justify-start h-12 px-4",
                pathname.startsWith('/rag') && "bg-primary/10 text-primary border border-primary/20"
              )}
            >
              <BookMarked className={cn("h-5 w-5 transition-transform group-hover:scale-110", !isCollapsed && "mr-3")}/>
              {!isCollapsed && <span className="text-sm font-medium">Conocimientos</span>}
            </Button>
          </Link>
          <Link href="/agenda" passHref onClick={onLinkClick} title="Agenda">
            <Button
              variant={pathname.startsWith('/agenda') ? 'secondary' : 'ghost'}
              className={cn(
                "w-full transition-all duration-300 hover:bg-primary/10 hover:text-primary rounded-xl group",
                isCollapsed ? "justify-center h-12 w-12 p-0" : "justify-start h-12 px-4",
                pathname.startsWith('/agenda') && "bg-primary/10 text-primary border border-primary/20"
              )}
            >
              <Calendar className={cn("h-5 w-5 transition-transform group-hover:scale-110", !isCollapsed && "mr-3")}/>
              {!isCollapsed && <span className="text-sm font-medium">Agenda</span>}
            </Button>
          </Link>
          <Link href="/notes" passHref onClick={onLinkClick} title="Notas">
            <Button
              variant={pathname.startsWith('/notes') ? 'secondary' : 'ghost'}
              className={cn(
                "w-full transition-all duration-300 hover:bg-primary/10 hover:text-primary rounded-xl group",
                isCollapsed ? "justify-center h-12 w-12 p-0" : "justify-start h-12 px-4",
                pathname.startsWith('/notes') && "bg-primary/10 text-primary border border-primary/20"
              )}
            >
              <Notebook className={cn("h-5 w-5 transition-transform group-hover:scale-110", !isCollapsed && "mr-3")}/>
              {!isCollapsed && <span className="text-sm font-medium">Notas</span>}
            </Button>
          </Link>
          <Link href="/analysis" passHref onClick={onLinkClick} title="Análisis">
            <Button
              variant={pathname.startsWith('/analysis') ? 'secondary' : 'ghost'}
              className={cn(
                "w-full transition-all duration-300 hover:bg-primary/10 hover:text-primary rounded-xl group",
                isCollapsed ? "justify-center h-12 w-12 p-0" : "justify-start h-12 px-4",
                pathname.startsWith('/analysis') && "bg-primary/10 text-primary border border-primary/20"
              )}
            >
              <BarChart3 className={cn("h-5 w-5 transition-transform group-hover:scale-110", !isCollapsed && "mr-3")}/>
              {!isCollapsed && <span className="text-sm font-medium">Análisis</span>}
            </Button>
          </Link>
          <Link href="/teams" passHref onClick={onLinkClick} title="Equipos">
            <Button
              variant={pathname.startsWith('/teams') ? 'secondary' : 'ghost'}
              className={cn(
                "w-full transition-all duration-300 hover:bg-primary/10 hover:text-primary rounded-xl group",
                isCollapsed ? "justify-center h-12 w-12 p-0" : "justify-start h-12 px-4",
                pathname.startsWith('/teams') && "bg-primary/10 text-primary border border-primary/20"
              )}
            >
              <Users className={cn("h-5 w-5 transition-transform group-hover:scale-110", !isCollapsed && "mr-3")}/>
              {!isCollapsed && <span className="text-sm font-medium">Equipos</span>}
            </Button>
          </Link>
          <Link href="/workspaces" passHref onClick={onLinkClick} title="Workspaces">
            <Button
              variant={pathname.startsWith('/workspaces') ? 'secondary' : 'ghost'}
              className={cn(
                "w-full transition-all duration-300 hover:bg-primary/10 hover:text-primary rounded-xl group",
                isCollapsed ? "justify-center h-12 w-12 p-0" : "justify-start h-12 px-4",
                pathname.startsWith('/workspaces') && "bg-primary/10 text-primary border border-primary/20"
              )}
            >
              <Bot className={cn("h-5 w-5 transition-transform group-hover:scale-110", !isCollapsed && "mr-3")}/>
              {!isCollapsed && <span className="text-sm font-medium">Workspaces</span>}
            </Button>
          </Link>
          <Link href="/chat" passHref onClick={onLinkClick} title="Chat">
            <Button
              variant={pathname.startsWith('/chat') ? 'secondary' : 'ghost'}
              className={cn(
                "w-full transition-all duration-300 hover:bg-primary/10 hover:text-primary rounded-xl group",
                isCollapsed ? "justify-center h-12 w-12 p-0" : "justify-start h-12 px-4",
                pathname.startsWith('/chat') && "bg-primary/10 text-primary border border-primary/20"
              )}
            >
              <MessageSquare className={cn("h-5 w-5 transition-transform group-hover:scale-110", !isCollapsed && "mr-3")}/>
              {!isCollapsed && <span className="text-sm font-medium">Chat</span>}
            </Button>
          </Link>
        </nav>
        {!isCollapsed && (
          <div className="mt-8 mb-6">
            <div className="flex items-center gap-2 mb-4 px-2">
              <div className="w-1 h-1 rounded-full bg-primary"></div>
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Conversaciones</p>
            </div>
            <div className="px-2 space-y-3">
              <input
                type="text"
                placeholder="Buscar conversaciones..."
                value={searchTerm}
                onChange={handleSearchChange}
                className="w-full p-3 rounded-xl bg-muted/50 border border-border/50 focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary/50 text-sm text-foreground placeholder:text-muted-foreground transition-all duration-200"
              />
              <div className="flex gap-1">
                <Button
                  variant={platformFilter === 'all' ? 'secondary' : 'ghost'}
                  size="sm"
                  onClick={() => setPlatformFilter('all')}
                  className="flex-1 text-xs h-8"
                >
                  Todos
                </Button>
                <Button
                  variant={platformFilter === 'web' ? 'secondary' : 'ghost'}
                  size="sm"
                  onClick={() => setPlatformFilter('web')}
                  className="flex-1 text-xs h-8"
                >
                  Web
                </Button>
                <Button
                  variant={platformFilter === 'telegram' ? 'secondary' : 'ghost'}
                  size="sm"
                  onClick={() => setPlatformFilter('telegram')}
                  className="flex-1 text-xs h-8 flex items-center gap-1"
                >
                  <Smartphone className="h-3 w-3" />
                  Telegram
                </Button>
              </div>
            </div>
          </div>
        )}
        {isCollapsed && (
          <Button onClick={handleNewChat} variant="ghost" size="icon" className="mb-4 rounded-full hover:bg-muted" title="Nuevo Chat">
            <Plus className="h-4 w-4" />
          </Button>
        )}
      </div>

      <ScrollArea className="flex-grow w-full">
        <DndProvider backend={HTML5Backend}>
          {!isCollapsed && (
            <div className="flex items-center justify-between mb-3 px-2">
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Fijados</p>
              <Button 
                variant="ghost" 
                size="icon" 
                className="p-0 h-6 w-6 rounded-full hover:bg-muted" 
                onClick={() => setIsPinnedCollapsed(!isPinnedCollapsed)}
              >
                {isPinnedCollapsed ? <ChevronRight className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
              </Button>
            </div>
          )}
          {!isCollapsed && !isPinnedCollapsed && (
            <DropArea onDrop={(thread, isPinned) => !isPinned && handlePinThread(thread)}>
              {filteredPinnedThreadsBySearch.length > 0 ? (
                <div className="space-y-1">
                  {filteredPinnedThreadsBySearch.map((thread) => (
                    <ThreadItem key={thread.id} thread={thread} isPinned={true} />
                  ))}
                </div>
              ) : (
                <p className="text-xs text-muted-foreground px-2 mb-2">
                  {searchTerm || platformFilter !== 'all'
                    ? "No se encontraron conversaciones fijadas que coincidan con los filtros."
                    : "No hay conversaciones fijadas."}
                </p>
              )}
            </DropArea>
          )}
          {!isCollapsed && (
            <div className="flex items-center justify-between mb-3 px-2 mt-4">
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Recientes</p>
              <Button 
                variant="ghost" 
                size="icon" 
                className="p-0 h-6 w-6 rounded-full hover:bg-muted" 
                onClick={() => setIsRecentCollapsed(!isRecentCollapsed)}
              >
                {isRecentCollapsed ? <ChevronRight className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
              </Button>
            </div>
          )}
          {!isRecentCollapsed && (
            <DropArea onDrop={(thread, isPinned) => isPinned && handleUnpinThread(thread)}>
              <div className="space-y-1">
                {filteredThreadsBySearch.map((thread) => (
                  <ThreadItem key={thread.id} thread={thread} isPinned={false} />
                ))}
              </div>
            </DropArea>
          )}
        </DndProvider>
      </ScrollArea>

      {/* Usuario */}
      <div className={cn("mt-auto w-full pt-6 border-t border-border/50", isCollapsed && "flex flex-col items-center")}>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              className={cn(
                "w-full h-auto py-4 transition-all duration-300 hover:bg-primary/10 hover:text-primary rounded-xl group",
                isCollapsed ? "h-12 w-12 p-0" : "justify-start gap-3"
              )}
            >
              <div className="relative">
                <Avatar className="h-10 w-10 border-2 border-primary/20">
                  <AvatarImage src="https://github.com/shadcn.png" alt="@shadcn" />
                  <AvatarFallback className="bg-primary text-primary-foreground font-semibold text-sm">
                    {user?.username?.slice(0, 2).toUpperCase() || "KA"}
                  </AvatarFallback>
                </Avatar>
                <div className="absolute -bottom-0.5 -right-0.5 w-3 h-3 bg-green-500 rounded-full border-2 border-background"></div>
              </div>
              {!isCollapsed && (
                <div className="flex flex-col items-start overflow-hidden flex-1">
                  <span className="font-semibold text-sm truncate w-full text-left text-foreground group-hover:text-primary transition-colors">
                    {user?.username || "Usuario"}
                  </span>
                  <span className="text-xs text-muted-foreground truncate w-full text-left">
                    {user?.email || "Sin Email"}
                  </span>
                </div>
              )}
              {!isCollapsed && <Settings className="h-4 w-4 text-muted-foreground group-hover:text-primary transition-colors" />}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <div className="flex items-center justify-start gap-2 p-2">
              <div className="flex flex-col space-y-1 leading-none">
                {user?.username && <p className="font-medium">{user.username}</p>}
                {user?.email && <p className="w-[200px] truncate text-sm text-muted-foreground">{user.email}</p>}
              </div>
            </div>
            <DropdownMenuSeparator />
            {user?.is_admin && (
              <DropdownMenuItem asChild>
                <Link href="/admin" onClick={onLinkClick}>
                  <Users className="mr-2 h-4 w-4" />
                  <span>Administración</span>
                </Link>
              </DropdownMenuItem>
            )}
            <DropdownMenuItem onClick={logout}>
              <LogOut className="mr-2 h-4 w-4" />
              <span>Cerrar Sesión</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  );
}
