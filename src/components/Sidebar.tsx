// En: src/components/Sidebar.tsx (Versión completa y actualizada)

'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger, DropdownMenuSeparator } from '@/components/ui/dropdown-menu';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Plus, MessageSquare, Brain, Notebook, Calendar, LogOut, Bot, ChevronDown, ChevronRight, Pin, Users, Sparkles, MoreVertical, FolderKanban, Settings, BarChart3, Smartphone, User, Image as ImageIcon, ClipboardList, FileText, Inbox, Globe, Mail, Video } from 'lucide-react';
import Image from 'next/image';
import apiClient from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';
import { useUserSettings } from '@/contexts/UserSettingsContext'; // Importar el nuevo hook
import { cn } from '@/lib/utils';
import { InlineMarkdownRenderer } from './InlineMarkdownRenderer';
import { toast } from 'sonner';
import { useDrag, useDrop } from 'react-dnd';
import { useWebSocketContext } from '@/contexts/WebSocketContext';
import { WebSocketMessage } from '@/hooks/useWebSocket';

interface SidebarProps {
  isCollapsed: boolean;
  onLinkClick?: () => void;
  showToolText?: boolean; // New prop to control tool text visibility
}

interface ChatThread {
  id: string;
  title: string;
  isPinned?: boolean;
  platform?: string;
  workspace_id?: string | null;
  hidden_from_sidebar?: boolean;
  created_at: string;
}

export function Sidebar({ isCollapsed, onLinkClick, showToolText = !isCollapsed }: SidebarProps) {
  const [threads, setThreads] = useState<ChatThread[]>([]);
  const [pinnedThreads, setPinnedThreads] = useState<ChatThread[]>([]);
  const [isToolsCollapsed, setIsToolsCollapsed] = useState(false);
  const [isPinnedCollapsed, setIsPinnedCollapsed] = useState(false);
  const [isRecentCollapsed, setIsRecentCollapsed] = useState(false);
  const { logout, user } = useAuth();
  const { settings, loading: settingsLoading } = useUserSettings(); // Obtener settings
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();

  const [activeWorkspaceId, setActiveWorkspaceId] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState<string>("");
  const [platformFilter, setPlatformFilter] = useState<'all' | 'web' | 'telegram'>('all');

  const { registerMessageHandler } = useWebSocketContext();

  useEffect(() => {
    const updateActiveWorkspace = async () => {
      const threadIdMatch = pathname?.match(/\/chat\/([a-f0-9-]+)/);
      if (threadIdMatch) {
        try {
          const response = await apiClient.get<ChatThread>(`/api/threads/${threadIdMatch[1]}`);
          setActiveWorkspaceId(response.data.workspace_id || null);
        } catch (error) {
          console.error('Error fetching thread details for workspace context:', error);
          setActiveWorkspaceId(null);
        }
      } else {
        const workspaceIdMatch = pathname?.match(/\/workspaces\/([a-f0-9-]+)(?:\/chat\/[a-f0-9-]+)?/);
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
          let apiUrl = '/api/threads?limit=100';
          if (activeWorkspaceId) {
            apiUrl += `&workspace_id=${activeWorkspaceId}`;
          }
          const response = await apiClient.get(apiUrl);
          let allThreads = response.data.threads.sort((a: ChatThread, b: ChatThread) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

          if (!activeWorkspaceId) {
            allThreads = allThreads.filter((thread: ChatThread) => !thread.workspace_id);
          }

          // Excluir hilos que estén marcados como ocultos desde el backend
          // Ocultar hilos marcados como ocultos o hilos generados por el sistema ('system')
          const visibleThreads = allThreads.filter((thread: ChatThread) => !thread.hidden_from_sidebar && thread.platform !== 'system');

          setThreads(visibleThreads.filter((thread: ChatThread) => !thread.isPinned));
          setPinnedThreads(visibleThreads.filter((thread: ChatThread) => thread.isPinned));
        } catch (error) {
          console.error('Error fetching threads:', error);
        }
      }
    };
    fetchThreads();
  }, [user, activeWorkspaceId]);

  useEffect(() => {
    const handleWebSocketMessage = (message: WebSocketMessage) => {
      if (!message) return;

      const { type, ...data } = message;

      if (type === 'thread_title_updated') {
        toast.info(`Conversación renombrada: "${data.new_title}"`);
        const { thread_id, new_title } = data;
        const updateThreadTitle = (thread: ChatThread) =>
          thread.id === thread_id ? { ...thread, title: new_title } : thread;

        setThreads(prev => prev.map(updateThreadTitle));
        setPinnedThreads(prev => prev.map(updateThreadTitle));
      } else if (type === 'thread_created') {
        const newThread: ChatThread = data.thread;
        // No mostrar hilos que el backend marque como ocultos o hilos del sistema
        if (newThread.hidden_from_sidebar || newThread.platform === 'system') return;

        const shouldAdd = (activeWorkspaceId && newThread.workspace_id === activeWorkspaceId) || (!activeWorkspaceId && !newThread.workspace_id);
        if (shouldAdd) {
          setThreads(prev => {
            const exists = prev.some(t => t.id === newThread.id);
            if (!exists) {
              return [newThread, ...prev].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
            }
            return prev;
          });
          toast.success(`Nueva conversación creada: "${newThread.title || 'Sin título'}"`);
        }
      }
    };

    const unregister = registerMessageHandler(handleWebSocketMessage);
    return unregister;
  }, [registerMessageHandler, activeWorkspaceId]);

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(e.target.value);
  };

  const applyFilters = (threadList: ChatThread[]) => {
    let filtered = threadList;

    if (searchTerm) {
      filtered = filtered.filter(thread => thread.title.toLowerCase().includes(searchTerm.toLowerCase()));
    }

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
      setThreads((prevThreads) => [newThread, ...prevThreads].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()));

      if (activeWorkspaceId) {
        router.push(`/workspaces/${activeWorkspaceId}/chat/${newThread.id}`);
      } else {
        router.push(`/chat/${newThread.id}`);
      }

      if (onLinkClick) {
        onLinkClick();
      }
    } catch (error) {
      console.error('Error creating new chat:', error);
    }
  };

  const handleRenameAllThreads = async () => {
    toast.info("Iniciando el proceso para nombrar todas las conversaciones. Esto puede tardar unos minutos...");
    try {
      const response = await apiClient.post('/api/threads/generate-all-titles');
      toast.success(response.data.message || "Proceso iniciado correctamente. Los títulos se actualizarán en breve.");
    } catch (error) {
      console.error('Error starting the process to rename all threads:', error);
      toast.error("Hubo un error al iniciar el proceso. Por favor, inténtalo de nuevo.");
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
        <Link href={`/chat/${thread.id}`} passHref onClick={onLinkClick} title={isCollapsed ? thread.title : undefined} className="w-full block">
          <Button
            variant={pathname === `/chat/${thread.id}` ? "secondary" : "ghost"}
            className={cn(
              "w-full font-normal items-start text-left transition-all duration-200 hover:bg-accent/50 rounded-xl overflow-hidden whitespace-normal h-auto",
              isCollapsed ? "justify-center h-9 w-9 p-0" : "justify-start h-auto py-1.5 px-2",
              pathname === `/chat/${thread.id}` && "bg-primary/10 text-primary font-medium"
            )}
          >
            <div className="flex w-full items-start gap-2 overflow-hidden">
              {!isCollapsed && thread.platform === 'telegram' && (
                <div title="Telegram" className="mt-1 shrink-0">
                  <Smartphone className="h-2.5 w-2.5 text-blue-500 flex-shrink-0" />
                </div>
              )}
              {!isCollapsed && (
                <div className="whitespace-pre-wrap break-words [overflow-wrap:anywhere] [word-break:break-word] flex-grow text-sm py-1 min-w-0 overflow-hidden">
                  <InlineMarkdownRenderer content={thread.title} />
                </div>
              )}
              {!isCollapsed && (
                <div className="ml-auto relative shrink-0">
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <div
                        className="h-5 w-5 p-0 cursor-pointer flex items-center justify-center rounded-lg hover:bg-accent/50 transition-colors"
                        onClick={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                        }}
                      >
                        <MoreVertical className="h-3 w-3 text-muted-foreground" />
                      </div>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end" className="w-40 text-sm">
                      <DropdownMenuItem
                        onClick={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          isPinned ? handleUnpinThread(thread) : handlePinThread(thread);
                        }}
                      >
                        <Pin className={cn("h-3.5 w-3.5 mr-1.5", isPinned && "text-primary")} />
                        {isPinned ? "Desfijar" : "Fijar"}
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        onClick={async (e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          toast.info("Generando un nuevo título para la conversación...");
                          try {
                            await apiClient.post(`/api/threads/${thread.id}/generate-title`);
                          } catch (error) {
                            console.error('Error generating title for thread:', error);
                            toast.error("No se pudo generar un nuevo título.");
                          }
                        }}
                      >
                        <Sparkles className="h-3.5 w-3.5 mr-1.5 text-yellow-500" />
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
            </div>
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
    <div className={cn("flex flex-col h-full overflow-x-hidden border-r border-border/20 backdrop-blur-md", isCollapsed ? "items-center p-2" : "p-6")}>
      {/* Header del sidebar */}
      <div className={cn("flex items-center w-full pb-4 mb-2 border-b border-border/20", isCollapsed ? "justify-center" : "justify-start")}>
        <Button
          onClick={handleNewChat}
          variant="default"
          className={cn(
            "w-full transition-all duration-200 shadow-sm hover:shadow-md",
            isCollapsed ? "h-9 w-9 p-0 rounded-full" : "h-9 px-4 rounded-full"
          )}
        >
          <Plus className={cn("h-4 w-4", !isCollapsed && "mr-2")} />
          {!isCollapsed && <span className="text-sm font-medium">Nuevo Chat</span>}
        </Button>
      </div>

      {/* Sección de herramientas */}
      <div className={cn("w-full mt-2", isCollapsed && "flex flex-col items-center")}>
        {!isCollapsed && (
          <div className="flex items-center justify-between mb-3 px-2">
            <p className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Herramientas</p>
            <Button
              variant="ghost"
              size="icon"
              className="p-0 h-6 w-6 rounded-full hover:bg-accent/50 transition-colors"
              onClick={() => setIsToolsCollapsed(!isToolsCollapsed)}
            >
              {isToolsCollapsed ? <ChevronRight className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
            </Button>
          </div>
        )}
        {!isToolsCollapsed && (
          <nav className="space-y-0.5 w-full">

            <Link href="/dashboard" passHref onClick={onLinkClick} title="Escritorio" className="w-full block">
              <Button
                variant={pathname === '/dashboard' ? 'secondary' : 'ghost'}
                className={cn(
                  "w-full transition-all duration-200 hover:bg-accent/50 rounded-xl group",
                  isCollapsed ? "justify-center h-9 w-9 p-0" : "justify-start h-9 px-2",
                  pathname === '/dashboard' && "bg-primary/10 text-primary font-medium"
                )}
              >
                <FolderKanban className={cn("h-4 w-4 transition-transform group-hover:scale-110", showToolText && "mr-2")} />
                {showToolText && <span className="text-sm font-medium">Escritorio</span>}
              </Button>
            </Link>

            <Link href="/inbox" passHref onClick={onLinkClick} title="Bandeja de entrada" className="w-full block">
              <Button
                variant={pathname?.startsWith('/inbox') ? 'secondary' : 'ghost'}
                className={cn(
                  "w-full transition-all duration-200 hover:bg-accent/50 rounded-xl group",
                  isCollapsed ? "justify-center h-9 w-9 p-0" : "justify-start h-9 px-2",
                  pathname?.startsWith('/inbox') && "bg-primary/10 text-primary font-medium"
                )}
              >
                <Inbox className={cn("h-4 w-4 transition-transform group-hover:scale-110", showToolText && "mr-2")} />
                {showToolText && <span className="text-sm font-medium">Bandeja</span>}
              </Button>
            </Link>
            <Link href="/rag" passHref onClick={onLinkClick} title="Gestión de Conocimientos" className="w-full block">
              <Button
                variant={pathname?.startsWith('/rag') ? 'secondary' : 'ghost'}
                className={cn(
                  "w-full transition-all duration-200 hover:bg-accent/50 rounded-xl group",
                  isCollapsed ? "justify-center h-9 w-9 p-0" : "justify-start h-9 px-2",
                  pathname?.startsWith('/rag') && "bg-primary/10 text-primary font-medium"
                )}
              >
                <Brain className={cn("h-4 w-4 transition-transform group-hover:scale-110", showToolText && "mr-2")} />
                {showToolText && <span className="text-sm font-medium">Conocimientos</span>}
              </Button>
            </Link>
            <Link href="/agenda" passHref onClick={onLinkClick} title="Agenda" className="w-full block">
              <Button
                variant={pathname?.startsWith('/agenda') ? 'secondary' : 'ghost'}
                className={cn(
                  "w-full transition-all duration-200 hover:bg-accent/50 rounded-xl group",
                  isCollapsed ? "justify-center h-9 w-9 p-0" : "justify-start h-9 px-2",
                  pathname?.startsWith('/agenda') && "bg-primary/10 text-primary font-medium"
                )}
              >
                <Calendar className={cn("h-4 w-4 transition-transform group-hover:scale-110", showToolText && "mr-2")} />
                {showToolText && <span className="text-sm font-medium">Agenda</span>}
              </Button>
            </Link>
            {settings?.galleries_enabled && (
              <Link href="/galleries" passHref onClick={onLinkClick} title="Álbumes" className="w-full block">
                <Button
                  variant={pathname?.startsWith('/galleries') ? 'secondary' : 'ghost'}
                  className={cn(
                    "w-full transition-all duration-200 hover:bg-accent/50 rounded-xl group",
                    isCollapsed ? "justify-center h-9 w-9 p-0" : "justify-start h-9 px-2",
                    pathname?.startsWith('/galleries') && "bg-primary/10 text-primary font-medium"
                  )}
                >
                  <ImageIcon className={cn("h-4 w-4 transition-transform group-hover:scale-110", showToolText && "mr-2")} />
                  {showToolText && <span className="text-sm font-medium">Galerías</span>}
                </Button>
              </Link>
            )}
            {settings?.forms_enabled && (
              <Link href="/forms" passHref onClick={onLinkClick} title="Formularios" className="w-full block">
                <Button
                  variant={pathname?.startsWith('/forms') ? 'secondary' : 'ghost'}
                  className={cn(
                    "w-full transition-all duration-200 hover:bg-accent/50 rounded-xl group",
                    isCollapsed ? "justify-center h-9 w-9 p-0" : "justify-start h-9 px-2",
                    pathname?.startsWith('/forms') && "bg-primary/10 text-primary font-medium"
                  )}
                >
                  <ClipboardList className={cn("h-4 w-4 transition-transform group-hover:scale-110", showToolText && "mr-2")} />
                  {showToolText && <span className="text-sm font-medium">Formularios</span>}
                </Button>
              </Link>
            )}

            <Link href="/documents" passHref onClick={onLinkClick} title="Documentos" className="w-full block">
              <Button
                variant={pathname?.startsWith('/documents') ? 'secondary' : 'ghost'}
                className={cn(
                  "w-full transition-all duration-200 hover:bg-accent/50 rounded-xl group",
                  isCollapsed ? "justify-center h-9 w-9 p-0" : "justify-start h-9 px-2",
                  pathname?.startsWith('/documents') && "bg-primary/10 text-primary font-medium"
                )}
              >
                <FileText className={cn("h-4 w-4 transition-transform group-hover:scale-110", showToolText && "mr-2")} />
                {showToolText && <span className="text-sm font-medium">Documentos</span>}
              </Button>
            </Link>

            <Link href="/workspaces" passHref onClick={onLinkClick} title="Workspaces" className="w-full block">
              <Button
                variant={pathname?.startsWith('/workspaces') ? 'secondary' : 'ghost'}
                className={cn(
                  "w-full transition-all duration-200 hover:bg-accent/50 rounded-xl group",
                  isCollapsed ? "justify-center h-9 w-9 p-0" : "justify-start h-9 px-2",
                  pathname?.startsWith('/workspaces') && "bg-primary/10 text-primary font-medium"
                )}
              >
                <Bot className={cn("h-4 w-4 transition-transform group-hover:scale-110", showToolText && "mr-2")} />
                {showToolText && <span className="text-sm font-medium">Workspaces</span>}
              </Button>
            </Link>

            {settings?.installed_extensions?.includes('fediverso') && (
              <Link href="/fediverso" passHref onClick={onLinkClick} title="Fediverso" className="w-full block">
                <Button
                  variant={pathname?.startsWith('/fediverso') ? 'secondary' : 'ghost'}
                  className={cn(
                    "w-full transition-all duration-200 hover:bg-accent/50 rounded-xl group",
                    isCollapsed ? "justify-center h-9 w-9 p-0" : "justify-start h-9 px-2",
                    pathname?.startsWith('/fediverso') && "bg-primary/10 text-primary font-medium"
                  )}
                >
                  <Globe className={cn("h-4 w-4 transition-transform group-hover:scale-110", showToolText && "mr-2")} />
                  {showToolText && <span className="text-sm font-medium">Fediverso</span>}
                </Button>
              </Link>
            )}

            {settings?.installed_extensions?.includes('email_management') && (
              <Link href="/email" passHref onClick={onLinkClick} title="Correo" className="w-full block">
                <Button
                  variant={pathname?.startsWith('/email') ? 'secondary' : 'ghost'}
                  className={cn(
                    "w-full transition-all duration-200 hover:bg-accent/50 rounded-xl group",
                    isCollapsed ? "justify-center h-9 w-9 p-0" : "justify-start h-9 px-2",
                    pathname?.startsWith('/email') && "bg-primary/10 text-primary font-medium"
                  )}
                >
                  <Mail className={cn("h-4 w-4 transition-transform group-hover:scale-110", showToolText && "mr-2")} />
                  {showToolText && <span className="text-sm font-medium">Correo</span>}
                </Button>
              </Link>
            )}

            {settings?.installed_extensions?.includes('jitsi_meet') && (
              <Link href="/meet" passHref onClick={onLinkClick} title="Meet" className="w-full block">
                <Button
                  variant={pathname?.startsWith('/meet') ? 'secondary' : 'ghost'}
                  className={cn(
                    "w-full transition-all duration-200 hover:bg-accent/50 rounded-xl group",
                    isCollapsed ? "justify-center h-9 w-9 p-0" : "justify-start h-9 px-2",
                    pathname?.startsWith('/meet') && "bg-primary/10 text-primary font-medium"
                  )}
                >
                  <Video className={cn("h-4 w-4 transition-transform group-hover:scale-110", showToolText && "mr-2")} />
                  {showToolText && <span className="text-sm font-medium">Meet</span>}
                </Button>
              </Link>
            )}
          </nav>
        )}

      </div>

      <ScrollArea className="flex-grow w-full">
        {!isCollapsed && (
          <div className="mt-4 mb-6">
            <div className="flex items-center justify-between gap-2 mb-4 px-2">
              <div className="flex items-center gap-2">
                <p className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Conversaciones</p>
              </div>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="icon" className="h-5 w-5 p-0 rounded-full hover:bg-accent/50 transition-colors">
                    <MoreVertical className="h-3.5 w-3.5 text-muted-foreground" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="text-sm">
                  <DropdownMenuItem onClick={handleRenameAllThreads}>
                    <Sparkles className="mr-1.5 h-3.5 w-3.5 text-yellow-500" />
                    <span>Nombrar todos</span>
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>

          </div>
        )}
        {!isCollapsed && (
          <div className="flex items-center justify-between mb-3 px-2">
            <p className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Fijados</p>
            <Button
              variant="ghost"
              size="icon"
              className="p-0 h-6 w-6 rounded-full hover:bg-accent/50 transition-colors"
              onClick={() => setIsPinnedCollapsed(!isPinnedCollapsed)}
            >
              {isPinnedCollapsed ? <ChevronRight className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
            </Button>
          </div>
        )}
        {!isCollapsed && !isPinnedCollapsed && (
          <DropArea onDrop={(thread, isPinned) => !isPinned && handlePinThread(thread)}>
            {filteredPinnedThreadsBySearch.length > 0 ? (
              <div className="space-y-2">
                {filteredPinnedThreadsBySearch.map((thread) => (
                  <ThreadItem key={thread.id} thread={thread} isPinned={true} />
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground px-2 mb-2">
                {searchTerm || platformFilter !== 'all'
                  ? "No se encontraron conversaciones fijadas que coincidan con los filtros."
                  : "No hay conversaciones fijadas."}
              </p>
            )}
          </DropArea>
        )}
        {!isCollapsed && (
          <div className="flex items-center justify-between mb-3 px-2 mt-4">
            <p className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Recientes</p>
            <Button
              variant="ghost"
              size="icon"
              className="p-0 h-6 w-6 rounded-full hover:bg-accent/50 transition-colors"
              onClick={() => setIsRecentCollapsed(!isRecentCollapsed)}
            >
              {isRecentCollapsed ? <ChevronRight className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
            </Button>
          </div>
        )}
        {!isRecentCollapsed && (
          <DropArea onDrop={(thread, isPinned) => isPinned && handleUnpinThread(thread)}>
            <div className="space-y-2">
              {filteredThreadsBySearch.map((thread) => (
                <ThreadItem key={thread.id} thread={thread} isPinned={false} />
              ))}
            </div>
          </DropArea>
        )}
      </ScrollArea>

      {/* Usuario */}
      <div className={cn("mt-auto w-full pt-4 border-t border-border/20", isCollapsed && "flex flex-col items-center")}>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              className={cn(
                "w-full h-auto py-2 transition-all duration-200 hover:bg-accent/50 rounded-xl group",
                isCollapsed ? "h-10 w-10 p-0" : "justify-start gap-2"
              )}
            >
              <div className="relative">
                <Avatar className="h-8 w-8 border border-primary/20">
                  <AvatarImage src="https://github.com/shadcn.png" alt="@shadcn" />
                  <AvatarFallback className="bg-primary text-primary-foreground font-semibold text-sm">
                    {user?.username?.slice(0, 2).toUpperCase() || "KA"}
                  </AvatarFallback>
                </Avatar>
                <div className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 bg-green-500 rounded-full border-2 border-background"></div>
              </div>
              {!isCollapsed && (
                <div className="flex flex-col items-start overflow-hidden flex-1">
                  <span className="font-semibold text-sm truncate w-full text-left text-foreground group-hover:text-primary transition-colors">
                    {user?.username || "Usuario"}
                  </span>
                  <span className="text-sm text-muted-foreground truncate w-full text-left">
                    {user?.email || "Sin Email"}
                  </span>
                </div>
              )}
              {!isCollapsed && <Settings className="h-3.5 w-3.5 text-muted-foreground group-hover:text-primary transition-colors" />}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-52 text-sm">
            <div className="flex items-center justify-start gap-2 p-2">
              <div className="flex flex-col space-y-0.5 leading-none">
                {user?.username && <p className="font-medium text-sm">{user.username}</p>}
                {user?.email && <p className="w-[180px] truncate text-sm text-muted-foreground">{user.email}</p>}
              </div>
            </div>
            <DropdownMenuSeparator />
            <DropdownMenuItem asChild>
              <Link href="/settings" onClick={onLinkClick}>
                <Settings className="mr-1.5 h-3.5 w-3.5" />
                <span>Configuración</span>
              </Link>
            </DropdownMenuItem>
            {user?.is_admin && (
              <DropdownMenuItem asChild>
                <Link href="/admin" onClick={onLinkClick}>
                  <Users className="mr-1.5 h-3.5 w-3.5" />
                  <span>Administración</span>
                </Link>
              </DropdownMenuItem>
            )}
            <DropdownMenuItem onClick={logout}>
              <LogOut className="mr-1.5 h-3.5 w-3.5" />
              <span>Cerrar Sesión</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  );
}
