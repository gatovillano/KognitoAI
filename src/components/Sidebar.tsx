// En: src/components/Sidebar.tsx (Versión completa y actualizada)

'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger, DropdownMenuSeparator } from '@/components/ui/dropdown-menu';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Plus, MessageSquare, BookMarked, Notebook, Calendar, LogOut, Bot, ChevronDown, ChevronRight, Pin, Users, Sparkles, MoreVertical, FolderKanban, Settings } from 'lucide-react';
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

  const filteredThreadsBySearch = searchTerm 
    ? threads.filter(thread => thread.title.toLowerCase().includes(searchTerm.toLowerCase()))
    : threads;
  
  const filteredPinnedThreadsBySearch = searchTerm 
    ? pinnedThreads.filter(thread => thread.title.toLowerCase().includes(searchTerm.toLowerCase()))
    : pinnedThreads;

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
              "w-full font-normal items-start text-left",
              isCollapsed ? "justify-center h-10 w-10 p-0" : "justify-start h-auto py-2 px-2"
            )}
          >
            <MessageSquare className={cn("h-4 w-4 mt-1 flex-shrink-0", !isCollapsed && "mr-2")} />
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
    <div className={cn("flex flex-col h-full p-2 rounded-none", isCollapsed ? "items-center" : "p-4")}>
      <div className={cn("flex items-center w-full pb-2 mb-2 border-b", isCollapsed ? "justify-center" : "justify-between")}>
        <Image src="/logo-simple.png" alt="Kognito Logo" width={50} height={50} className={cn(!isCollapsed && "mr-2")} />
        {!isCollapsed && <span className="font-bold text-lg whitespace-nowrap">Kognito</span>}
        <Button onClick={handleNewChat} variant="ghost" size="icon" className={cn("hover:bg-primary/20", isCollapsed ? "hidden" : "ml-auto")}>
          <Plus className="h-5 w-5 text-primary" />
        </Button>
      </div>

      <div className={cn("w-full", isCollapsed && "flex flex-col items-center")}>
        {!isCollapsed && <p className="font-semibold text-muted-foreground mb-2 px-2 whitespace-nowrap">Herramientas</p>}
        <nav className="space-y-1 w-full">
          <Link href="/dashboard" passHref onClick={onLinkClick} title="Escritorio">
            <Button variant={pathname.startsWith('/dashboard') ? 'secondary' : 'ghost'} className={cn("w-full", isCollapsed ? "justify-center h-10 w-10 p-0" : "justify-start")}>
              <Bot className={cn("h-4 w-4", !isCollapsed && "mr-2")}/>
              {!isCollapsed && "Escritorio"}
            </Button>
          </Link>
          <Link href="/rag" passHref onClick={onLinkClick} title="Gestión de Conocimientos">
            <Button variant={pathname.startsWith('/rag') ? 'secondary' : 'ghost'} className={cn("w-full", isCollapsed ? "justify-center h-10 w-10 p-0" : "justify-start")}>
              <BookMarked className={cn("h-4 w-4", !isCollapsed && "mr-2")}/>
              {!isCollapsed && "Gestión de Conocimientos"}
            </Button>
          </Link>
          <Link href="/agenda" passHref onClick={onLinkClick} title="Agenda">
            <Button variant={pathname.startsWith('/agenda') ? 'secondary' : 'ghost'} className={cn("w-full", isCollapsed ? "justify-center h-10 w-10 p-0" : "justify-start")}>
              <Calendar className={cn("h-4 w-4", !isCollapsed && "mr-2")}/>
              {!isCollapsed && "Agenda"}
            </Button>
          </Link>
          <Link href="/notes" passHref onClick={onLinkClick} title="Notas">
            <Button variant={pathname.startsWith('/notes') ? 'secondary' : 'ghost'} className={cn("w-full", isCollapsed ? "justify-center h-10 w-10 p-0" : "justify-start")}>
              <Notebook className={cn("h-4 w-4", !isCollapsed && "mr-2")}/>
              {!isCollapsed && "Notas"}
            </Button>
          </Link>
          <Link href="/teams" passHref onClick={onLinkClick} title="Equipos">
            <Button variant={pathname.startsWith('/teams') ? 'secondary' : 'ghost'} className={cn("w-full", isCollapsed ? "justify-center h-10 w-10 p-0" : "justify-start")}>
              <Users className={cn("h-4 w-4", !isCollapsed && "mr-2")}/>
              {!isCollapsed && "Equipos"}
            </Button>
          </Link>
          <Link href="/workspaces" passHref onClick={onLinkClick} title="Workspaces">
            <Button variant={pathname.startsWith('/workspaces') ? 'secondary' : 'ghost'} className={cn("w-full", isCollapsed ? "justify-center h-10 w-10 p-0" : "justify-start")}>
              <Bot className={cn("h-4 w-4", !isCollapsed && "mr-2")}/>
              {!isCollapsed && "Workspaces"}
            </Button>
          </Link>
          <Link href="/chat" passHref onClick={onLinkClick} title="Chat">
            <Button variant={pathname.startsWith('/chat') ? 'secondary' : 'ghost'} className={cn("w-full", isCollapsed ? "justify-center h-10 w-10 p-0" : "justify-start")}>
              <MessageSquare className={cn("h-4 w-4", !isCollapsed && "mr-2")}/>
              {!isCollapsed && "Chat"}
            </Button>
          </Link>
        </nav>
        {!isCollapsed && (
          <div className="flex items-center justify-between mb-4 px-2 mt-4">
            <p className="font-semibold text-muted-foreground whitespace-nowrap">Conversaciones</p>
          </div>
        )}
        {!isCollapsed && (
          <div className="mb-4 px-2 mt-2">
            <input
              type="text"
              placeholder="Buscar conversaciones..."
              value={searchTerm}
              onChange={handleSearchChange}
              className="w-full p-2 rounded-full focus:outline-none focus:ring-2 focus:ring-primary text-sm text-gray-300"
              style={{ backgroundColor: '#1d1e20' }}
            />
          </div>
        )}
        {isCollapsed && (
          <Button onClick={handleNewChat} variant="ghost" size="icon" className="mb-2" title="Nuevo Chat">
            <Plus className="h-5 w-5" />
          </Button>
        )}
      </div>

      <ScrollArea className="flex-grow w-full">
        <DndProvider backend={HTML5Backend}>
          {!isCollapsed && (
            <div className="flex items-center justify-between mb-1 px-2">
              <p className="font-semibold text-muted-foreground text-sm whitespace-nowrap">Fijados</p>
              <Button 
                variant="ghost" 
                size="icon" 
                className="p-0 h-5 w-5" 
                onClick={() => setIsPinnedCollapsed(!isPinnedCollapsed)}
              >
                {isPinnedCollapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
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
                  {searchTerm ? "No se encontraron conversaciones fijadas que coincidan con la búsqueda." : "No hay conversaciones fijadas."}
                </p>
              )}
            </DropArea>
          )}
          {!isCollapsed && (
            <div className="flex items-center justify-between mb-1 px-2 mt-2">
              <p className="font-semibold text-muted-foreground text-sm whitespace-nowrap">Recientes</p>
              <Button 
                variant="ghost" 
                size="icon" 
                className="p-0 h-5 w-5" 
                onClick={() => setIsRecentCollapsed(!isRecentCollapsed)}
              >
                {isRecentCollapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
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

      <div className={cn("mt-auto w-full pt-2 border-t", isCollapsed && "flex flex-col items-center")}>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className={cn("w-full mt-4 h-auto py-2", isCollapsed ? "h-10 w-10 p-0" : "justify-start gap-2")}>
              <Avatar className={cn("h-8 w-8", !isCollapsed && "mr-2")}>
                <AvatarImage src="https://github.com/shadcn.png" alt="@shadcn" /> {/* Placeholder image */}
                <AvatarFallback>CN</AvatarFallback>
              </Avatar>
              {!isCollapsed && (
                <div className="flex flex-col items-start overflow-hidden">
                  <span className="font-semibold text-sm truncate w-full text-left">{user?.username || "Usuario"}</span>
                  <span className="text-xs text-muted-foreground truncate w-full text-left">{user?.email || "Sin Email"}</span>
                </div>
              )}
              {!isCollapsed && <Settings className="h-4 w-4 ml-auto" />}
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
