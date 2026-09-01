'use client';

import { useEffect, useState, useMemo } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger, DropdownMenuSeparator } from '@/components/ui/dropdown-menu';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import {
  Plus, MessageSquare, Brain, Notebook, Calendar, LogOut, Bot, ChevronDown, ChevronRight,
  Pin, Users, Sparkles, MoreVertical, FolderKanban, Settings, Smartphone,
  ImageIcon, ClipboardList, FileText, Inbox, Globe, Mail, Video, TrendingUp, Search, Edit3, X,
  PanelLeftClose, PanelLeftOpen, Wifi, WifiOff, AlertTriangle, ArrowLeft
} from 'lucide-react';
import apiClient from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';
import { useUserSettings } from '@/contexts/UserSettingsContext';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';
import { useDrag, useDrop } from 'react-dnd';
import { useWebSocketContext } from '@/contexts/WebSocketContext';
import { WebSocketMessage } from '@/hooks/useWebSocket';
import { ThemeToggle } from './ThemeToggle';
import { UniversalSearchDialog } from './UniversalSearchDialog';
import { useSearch } from '@/contexts/SearchContext';
import { Badge } from '@/components/ui/badge';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';

interface SidebarProps {
  isCollapsed: boolean;
  onLinkClick?: () => void;
  showToolText?: boolean;
  onToggleCollapse?: () => void;
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

interface GroupedThreads {
  label: string;
  threads: ChatThread[];
}

function getRelativeTimeString(dateString: string): string {
  if (!dateString) return '';
  const date = new Date(dateString);
  const now = new Date();
  const diffInMs = now.getTime() - date.getTime();
  if (isNaN(diffInMs) || diffInMs < 0) return '';

  const diffInMins = Math.floor(diffInMs / (1000 * 60));
  const diffInHours = Math.floor(diffInMs / (1000 * 60 * 60));
  const diffInDays = Math.floor(diffInMs / (1000 * 60 * 60 * 24));
  const diffInWeeks = Math.floor(diffInDays / 7);
  const diffInMonths = Math.floor(diffInDays / 30);

  if (diffInMins < 1) return 'hace 1 min';
  if (diffInMins < 60) return `hace ${diffInMins} min`;
  if (diffInHours < 24) return `hace ${diffInHours} h`;
  if (diffInDays < 7) return `hace ${diffInDays} d`;
  if (diffInWeeks < 5) return `hace ${diffInWeeks} sem`;
  return `hace ${diffInMonths || 1} m`;
}

function groupThreadsByDate(threadsList: ChatThread[]): GroupedThreads[] {
  const now = new Date();
  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const yesterdayStart = todayStart - 86400000;
  const sevenDaysAgoStart = todayStart - 6 * 86400000;
  const thirtyDaysAgoStart = todayStart - 29 * 86400000;

  const monthNames = [
    'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
  ];

  const groupMap: Map<string, ChatThread[]> = new Map();
  groupMap.set('Hoy', []);
  groupMap.set('Ayer', []);
  groupMap.set('7 días previos', []);
  groupMap.set('30 días previos', []);

  threadsList.forEach((thread) => {
    const threadDate = new Date(thread.created_at);
    const threadTime = threadDate.getTime();

    if (threadTime >= todayStart) {
      groupMap.get('Hoy')!.push(thread);
    } else if (threadTime >= yesterdayStart) {
      groupMap.get('Ayer')!.push(thread);
    } else if (threadTime >= sevenDaysAgoStart) {
      groupMap.get('7 días previos')!.push(thread);
    } else if (threadTime >= thirtyDaysAgoStart) {
      groupMap.get('30 días previos')!.push(thread);
    } else {
      const monthLabel = monthNames[threadDate.getMonth()] || 'Anteriores';
      if (!groupMap.has(monthLabel)) {
        groupMap.set(monthLabel, []);
      }
      groupMap.get(monthLabel)!.push(thread);
    }
  });

  const result: GroupedThreads[] = [];
  groupMap.forEach((threads, label) => {
    if (threads.length > 0) {
      result.push({ label, threads });
    }
  });

  return result;
}

export function Sidebar({ isCollapsed, onLinkClick, showToolText = !isCollapsed, onToggleCollapse }: SidebarProps) {
  const [threads, setThreads] = useState<ChatThread[]>([]);
  const [pinnedThreads, setPinnedThreads] = useState<ChatThread[]>([]);
  const [isToolsCollapsed, setIsToolsCollapsed] = useState(true);
  const [isPinnedCollapsed, setIsPinnedCollapsed] = useState(false);
  const [isUniversalSearchDialogOpen, setIsUniversalSearchDialogOpen] = useState(false);

  const { logout, user } = useAuth();
  const { settings } = useUserSettings();
  const { searchTerm, setSearchTerm } = useSearch();
  const { isConnected, connectionError, reconnect, registerMessageHandler } = useWebSocketContext();

  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();

  const [activeWorkspaceId, setActiveWorkspaceId] = useState<string | null>(null);
  const [activeWorkspace, setActiveWorkspace] = useState<{ id: string; name: string } | null>(null);
  const [platformFilter, setPlatformFilter] = useState<'all' | 'web' | 'telegram'>('all');

  // Shortcut de teclado para búsqueda universal (Cmd+K / Ctrl+K)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsUniversalSearchDialogOpen(prev => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

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
    if (activeWorkspaceId) {
      apiClient.get(`/api/workspaces/${activeWorkspaceId}`)
        .then(res => setActiveWorkspace(res.data))
        .catch(() => setActiveWorkspace(null));
    } else {
      setActiveWorkspace(null);
    }
  }, [activeWorkspaceId]);

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

  const applyFilters = (threadList: ChatThread[]) => {
    let filtered = threadList;

    if (searchTerm && !isUniversalSearchDialogOpen) {
      filtered = filtered.filter(thread => thread.title?.toLowerCase().includes(searchTerm.toLowerCase()));
    }

    if (platformFilter !== 'all') {
      filtered = filtered.filter(thread => thread.platform === platformFilter);
    }

    return filtered;
  };

  const filteredThreadsBySearch = applyFilters(threads);
  const filteredPinnedThreadsBySearch = applyFilters(pinnedThreads);

  const groupedRecentThreads = useMemo(() => {
    return groupThreadsByDate(filteredThreadsBySearch);
  }, [filteredThreadsBySearch]);

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

    const isSelected = pathname === `/chat/${thread.id}`;
    const timeString = getRelativeTimeString(thread.created_at);

    return (
      <div ref={drag as any} className={cn('opacity-100 group/item relative w-full flex justify-center', isDragging && 'opacity-50')}>
        <Link href={`/chat/${thread.id}`} passHref onClick={onLinkClick} title={thread.title || "Conversación"} className={cn("block", isCollapsed ? "w-auto" : "w-full")}>
          <Button
            variant="ghost"
            className={cn(
              "font-normal transition-all duration-150 rounded-xl overflow-hidden hover:bg-accent/60",
              isCollapsed ? "h-8 w-8 p-0 flex items-center justify-center mx-auto" : "w-full justify-between gap-1.5 text-left h-8 px-2 py-1",
              isSelected && "bg-secondary/80 text-foreground font-medium"
            )}
          >
            {isCollapsed ? (
              <MessageSquare className="h-4 w-4 text-muted-foreground shrink-0" />
            ) : (
              <>
                <div className="flex items-center gap-2 min-w-0 flex-1 overflow-hidden">
                  {thread.platform === 'telegram' ? (
                    <Smartphone className="h-3 w-3 text-blue-500 shrink-0" />
                  ) : isSelected ? (
                    <div className="h-1.5 w-1.5 rounded-full bg-primary shrink-0" />
                  ) : null}
                  <span className="truncate text-xs text-foreground/90 font-normal group-hover/item:text-foreground">
                    {thread.title || "Sin título"}
                  </span>
                </div>

                <div className="flex items-center gap-1 shrink-0">
                  {timeString && (
                    <span className="text-[11px] text-muted-foreground/60 font-normal group-hover/item:hidden select-none">
                      {timeString}
                    </span>
                  )}
                  <div className="relative shrink-0 hidden group-hover/item:block">
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <div
                          className="h-4 w-4 p-0 cursor-pointer flex items-center justify-center rounded hover:bg-accent transition-colors"
                          onClick={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                          }}
                        >
                          <MoreVertical className="h-3 w-3 text-muted-foreground" />
                        </div>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end" className="w-40 text-xs">
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
                            toast.info("Generando un nuevo título...");
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
                </div>
              </>
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
    <div className={cn("flex flex-col h-full w-full select-none bg-background/50 overflow-x-hidden", isCollapsed ? "items-center px-1.5 py-3" : "px-3 py-3")}>
      
      {/* Encabezado Superior del Sidebar: Logo + Nombre + Toggle Colapsar */}
      {!isCollapsed ? (
        <div className="flex items-center justify-between px-1.5 py-1 mb-2">
          <Link href="/chat" onClick={onLinkClick} className="flex items-center gap-2.5 hover:opacity-85 transition-opacity">
            <div className="relative flex items-center justify-center p-1 rounded-xl bg-card/80 border border-border/40 shadow-xs">
              <Image src="/logo-simple.png" alt="Kognito Logo" width={22} height={22} className="rounded-lg object-contain" />
            </div>
            <span className="font-bold text-sm tracking-tight text-foreground">Kognito AI</span>
          </Link>
          {onToggleCollapse && (
            <Button
              variant="ghost"
              size="icon"
              onClick={onToggleCollapse}
              className="h-7 w-7 rounded-lg text-muted-foreground hover:text-foreground hover:bg-accent/60 transition-all"
              title="Contraer barra lateral"
            >
              <PanelLeftClose className="h-4 w-4" />
            </Button>
          )}
        </div>
      ) : (
        <div className="flex flex-col items-center mb-3">
          {onToggleCollapse ? (
            <Button
              variant="ghost"
              size="icon"
              onClick={onToggleCollapse}
              className="h-9 w-9 rounded-xl hover:bg-accent/60 transition-all p-0 flex items-center justify-center"
              title="Expandir barra lateral"
            >
              <Image src="/logo-simple.png" alt="Kognito" width={24} height={24} className="rounded-lg object-contain" />
            </Button>
          ) : (
            <div className="p-1">
              <Image src="/logo-simple.png" alt="Kognito" width={24} height={24} className="rounded-lg object-contain" />
            </div>
          )}
        </div>
      )}

      {/* Banner de Contexto de Workspace si está activo */}
      {!isCollapsed && activeWorkspace && (
        <div className="mb-2 px-0.5">
          <div className="flex items-center justify-between bg-primary/10 border border-primary/20 rounded-xl px-2.5 py-1.5 text-xs text-primary font-medium">
            <div className="flex items-center gap-1.5 truncate">
              <Bot className="h-3.5 w-3.5 shrink-0 animate-pulse" />
              <span className="truncate font-semibold">{activeWorkspace.name}</span>
            </div>
            <Button
              variant="ghost"
              size="icon"
              className="h-5 w-5 p-0 rounded hover:bg-primary/20 text-primary"
              onClick={() => router.push(`/workspaces/${activeWorkspace.id}`)}
              title="Ir al Workspace"
            >
              <ArrowLeft className="h-3 w-3" />
            </Button>
          </div>
        </div>
      )}

      {/* Botones principales superiores */}
      <div className={cn("w-full mb-2", isCollapsed ? "flex flex-col items-center gap-1.5" : "space-y-0.5")}>
        {/* Nuevo Chat */}
        <Button
          onClick={handleNewChat}
          variant="ghost"
          className={cn(
            "transition-colors duration-150 hover:bg-accent/60 rounded-xl font-normal text-foreground",
            isCollapsed ? "h-9 w-9 p-0 flex items-center justify-center mx-auto" : "w-full justify-start h-9 px-2"
          )}
          title="Nuevo Chat"
        >
          <Edit3 className={cn("h-4 w-4 text-foreground/80 shrink-0", !isCollapsed && "mr-2.5")} />
          {!isCollapsed && <span className="text-xs font-medium">Nuevo Chat</span>}
        </Button>

        {/* Buscar (Abre Diálogo Universal) */}
        <Button
          onClick={() => setIsUniversalSearchDialogOpen(true)}
          variant="ghost"
          className={cn(
            "transition-colors duration-150 hover:bg-accent/60 rounded-xl font-normal text-foreground",
            isCollapsed ? "h-9 w-9 p-0 flex items-center justify-center mx-auto" : "w-full justify-between h-9 px-2"
          )}
          title="Buscar en todo (⌘K)"
        >
          <div className="flex items-center gap-2 min-w-0">
            <Search className={cn("h-4 w-4 text-foreground/80 shrink-0", !isCollapsed && "mr-2.5")} />
            {!isCollapsed && <span className="text-xs font-medium">Buscar</span>}
          </div>
          {!isCollapsed && (
            <kbd className="hidden sm:inline-flex items-center px-1.5 py-0.5 text-[10px] font-mono text-muted-foreground/70 bg-accent/40 rounded border border-border/40">
              ⌘K
            </kbd>
          )}
        </Button>

        {/* Documentos */}
        <Link href="/documents" passHref onClick={onLinkClick} title="Documentos" className={cn("block", isCollapsed ? "w-auto" : "w-full")}>
          <Button
            variant={pathname?.startsWith('/documents') ? "secondary" : "ghost"}
            className={cn(
              "transition-colors duration-150 hover:bg-accent/60 rounded-xl font-normal text-foreground",
              isCollapsed ? "h-9 w-9 p-0 flex items-center justify-center mx-auto" : "w-full justify-start h-9 px-2",
              pathname?.startsWith('/documents') && "bg-secondary text-foreground font-medium"
            )}
          >
            <FileText className={cn("h-4 w-4 text-foreground/80 shrink-0", !isCollapsed && "mr-2.5")} />
            {!isCollapsed && <span className="text-xs font-medium">Documentos</span>}
          </Button>
        </Link>

        {/* Espacio de Trabajo */}
        <Link href="/workspaces" passHref onClick={onLinkClick} title="Espacio de Trabajo" className={cn("block", isCollapsed ? "w-auto" : "w-full")}>
          <Button
            variant={pathname?.startsWith('/workspaces') ? "secondary" : "ghost"}
            className={cn(
              "transition-colors duration-150 hover:bg-accent/60 rounded-xl font-normal text-foreground",
              isCollapsed ? "h-9 w-9 p-0 flex items-center justify-center mx-auto" : "w-full justify-start h-9 px-2",
              pathname?.startsWith('/workspaces') && "bg-secondary text-foreground font-medium"
            )}
          >
            <FolderKanban className={cn("h-4 w-4 text-foreground/80 shrink-0", !isCollapsed && "mr-2.5")} />
            {!isCollapsed && <span className="text-xs font-medium">Espacio de Trabajo</span>}
          </Button>
        </Link>
      </div>

      {/* Sección desplegable opcional de Herramientas adicionales */}
      {!isCollapsed && (
        <div className="w-full border-t border-border/20 pt-2 mb-2">
          <div
            className="flex items-center justify-between px-2 py-1 cursor-pointer group hover:bg-accent/40 rounded-lg transition-colors"
            onClick={() => setIsToolsCollapsed(!isToolsCollapsed)}
          >
            <span className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">Herramientas</span>
            <div className="h-4 w-4 flex items-center justify-center text-muted-foreground group-hover:text-foreground">
              {isToolsCollapsed ? <ChevronRight className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
            </div>
          </div>
          {!isToolsCollapsed && (
            <nav className="space-y-0.5 w-full mt-1">
              <Link href="/dashboard" passHref onClick={onLinkClick} title="Escritorio" className="w-full block">
                <Button variant={pathname === '/dashboard' ? 'secondary' : 'ghost'} className="w-full justify-start h-8 px-2 rounded-xl text-xs">
                  <FolderKanban className="h-3.5 w-3.5 mr-2 text-muted-foreground" />
                  <span>Escritorio</span>
                </Button>
              </Link>
              <Link href="/inbox" passHref onClick={onLinkClick} title="Bandeja" className="w-full block">
                <Button variant={pathname?.startsWith('/inbox') ? 'secondary' : 'ghost'} className="w-full justify-start h-8 px-2 rounded-xl text-xs">
                  <Inbox className="h-3.5 w-3.5 mr-2 text-muted-foreground" />
                  <span>Bandeja</span>
                </Button>
              </Link>
              <Link href="/rag" passHref onClick={onLinkClick} title="Conocimientos" className="w-full block">
                <Button variant={pathname?.startsWith('/rag') ? 'secondary' : 'ghost'} className="w-full justify-start h-8 px-2 rounded-xl text-xs">
                  <Brain className="h-3.5 w-3.5 mr-2 text-muted-foreground" />
                  <span>Conocimientos</span>
                </Button>
              </Link>
              <Link href="/agenda" passHref onClick={onLinkClick} title="Agenda" className="w-full block">
                <Button variant={pathname?.startsWith('/agenda') ? 'secondary' : 'ghost'} className="w-full justify-start h-8 px-2 rounded-xl text-xs">
                  <Calendar className="h-3.5 w-3.5 mr-2 text-muted-foreground" />
                  <span>Agenda</span>
                </Button>
              </Link>
              {settings?.galleries_enabled && (
                <Link href="/galleries" passHref onClick={onLinkClick} title="Galerías" className="w-full block">
                  <Button variant={pathname?.startsWith('/galleries') ? 'secondary' : 'ghost'} className="w-full justify-start h-8 px-2 rounded-xl text-xs">
                    <ImageIcon className="h-3.5 w-3.5 mr-2 text-muted-foreground" />
                    <span>Galerías</span>
                  </Button>
                </Link>
              )}
              {settings?.forms_enabled && (
                <Link href="/forms" passHref onClick={onLinkClick} title="Formularios" className="w-full block">
                  <Button variant={pathname?.startsWith('/forms') ? 'secondary' : 'ghost'} className="w-full justify-start h-8 px-2 rounded-xl text-xs">
                    <ClipboardList className="h-3.5 w-3.5 mr-2 text-muted-foreground" />
                    <span>Formularios</span>
                  </Button>
                </Link>
              )}
              {settings?.installed_extensions?.includes('fediverso') && (
                <Link href="/fediverso" passHref onClick={onLinkClick} title="Fediverso" className="w-full block">
                  <Button variant={pathname?.startsWith('/fediverso') ? 'secondary' : 'ghost'} className="w-full justify-start h-8 px-2 rounded-xl text-xs">
                    <Globe className="h-3.5 w-3.5 mr-2 text-muted-foreground" />
                    <span>Fediverso</span>
                  </Button>
                </Link>
              )}
              {settings?.installed_extensions?.includes('email_management') && (
                <Link href="/email" passHref onClick={onLinkClick} title="Correo" className="w-full block">
                  <Button variant={pathname?.startsWith('/email') ? 'secondary' : 'ghost'} className="w-full justify-start h-8 px-2 rounded-xl text-xs">
                    <Mail className="h-3.5 w-3.5 mr-2 text-muted-foreground" />
                    <span>Correo</span>
                  </Button>
                </Link>
              )}
              {settings?.installed_extensions?.includes('jitsi_meet') && (
                <Link href="/meet" passHref onClick={onLinkClick} title="Meet" className="w-full block">
                  <Button variant={pathname?.startsWith('/meet') ? 'secondary' : 'ghost'} className="w-full justify-start h-8 px-2 rounded-xl text-xs">
                    <Video className="h-3.5 w-3.5 mr-2 text-muted-foreground" />
                    <span>Meet</span>
                  </Button>
                </Link>
              )}
              {(settings?.installed_extensions?.includes('kognito_chat') || settings?.installed_extensions?.includes('kognichat')) && (
                <Link href="/kognito-chat" passHref onClick={onLinkClick} title="KognitoChat" className="w-full block">
                  <Button variant={pathname?.startsWith('/kognito-chat') ? 'secondary' : 'ghost'} className="w-full justify-start h-8 px-2 rounded-xl text-xs">
                    <MessageSquare className="h-3.5 w-3.5 mr-2 text-muted-foreground" />
                    <span>KognitoChat</span>
                  </Button>
                </Link>
              )}
              {settings?.installed_extensions?.includes('growth') && (
                <Link href="/growth" passHref onClick={onLinkClick} title="KogniGrowth" className="w-full block">
                  <Button variant={pathname?.startsWith('/growth') ? 'secondary' : 'ghost'} className="w-full justify-start h-8 px-2 rounded-xl text-xs">
                    <TrendingUp className="h-3.5 w-3.5 mr-2 text-muted-foreground" />
                    <span>KogniGrowth</span>
                  </Button>
                </Link>
              )}
            </nav>
          )}
        </div>
      )}

      {/* Area de scroll para conversaciones */}
      <ScrollArea className="flex-grow w-full border-t border-border/20 pt-2">
        {/* Conversaciones Fijadas */}
        {!isCollapsed && filteredPinnedThreadsBySearch.length > 0 && (
          <div className="mb-3">
            <div className="flex items-center justify-between px-2 py-1 mb-1">
              <span className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">Fijados</span>
              <Button
                variant="ghost"
                size="icon"
                className="p-0 h-4 w-4 rounded hover:bg-accent transition-colors"
                onClick={() => setIsPinnedCollapsed(!isPinnedCollapsed)}
              >
                {isPinnedCollapsed ? <ChevronRight className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
              </Button>
            </div>
            {!isPinnedCollapsed && (
              <DropArea onDrop={(thread, isPinned) => !isPinned && handlePinThread(thread)}>
                <div className="space-y-0.5">
                  {filteredPinnedThreadsBySearch.map((thread) => (
                    <ThreadItem key={thread.id} thread={thread} isPinned={true} />
                  ))}
                </div>
              </DropArea>
            )}
          </div>
        )}

        {/* Conversaciones Recientes Agrupadas por Fecha */}
        {!isCollapsed ? (
          <DropArea onDrop={(thread, isPinned) => isPinned && handleUnpinThread(thread)}>
            {groupedRecentThreads.length > 0 ? (
              groupedRecentThreads.map((group) => (
                <div key={group.label} className="mb-3">
                  <p className="text-[11px] font-semibold text-muted-foreground/70 px-2 py-1 mb-0.5">
                    {group.label}
                  </p>
                  <div className="space-y-0.5">
                    {group.threads.map((thread) => (
                      <ThreadItem key={thread.id} thread={thread} isPinned={false} />
                    ))}
                  </div>
                </div>
              ))
            ) : (
              <p className="text-xs text-muted-foreground/70 px-2 py-2">
                {searchTerm || platformFilter !== 'all'
                  ? "No hay conversaciones que coincidan."
                  : "Sin conversaciones recientes."}
              </p>
            )}
          </DropArea>
        ) : (
          <div className="flex flex-col items-center gap-1 w-full">
            {filteredThreadsBySearch.map((thread) => (
              <ThreadItem key={thread.id} thread={thread} isPinned={false} />
            ))}
          </div>
        )}
      </ScrollArea>

      {/* Footer del Sidebar: WebSocket Status, Selector de Tema y Perfil de Usuario */}
      <div className={cn("mt-auto w-full pt-3 border-t border-border/20 flex flex-col gap-2", isCollapsed && "items-center")}>
        
        {/* Fila de Utilidades: WebSocket + Theme Toggle */}
        {!isCollapsed ? (
          <div className="flex items-center justify-between px-1">
            {/* Estado WebSocket */}
            <div className="flex items-center">
              {connectionError ? (
                <Badge
                  variant="destructive"
                  className="flex items-center justify-center h-7 px-2 gap-1.5 rounded-lg cursor-pointer hover:bg-destructive/80 transition-all text-[10px] shadow-sm"
                  onClick={reconnect}
                  title="Error de conexión. Clic para reconectar"
                >
                  <AlertTriangle className="h-3 w-3" />
                  <span className="font-semibold uppercase tracking-wider">Error WS</span>
                </Badge>
              ) : isConnected ? (
                <Badge
                  variant="secondary"
                  className="flex items-center justify-center h-7 px-2 gap-1.5 rounded-lg bg-green-500/10 text-green-600 dark:text-green-400 border border-green-500/20 text-[10px]"
                >
                  <div className="h-1.5 w-1.5 rounded-full bg-green-500 animate-pulse" />
                  <span className="font-semibold uppercase tracking-wider">Online</span>
                </Badge>
              ) : (
                <Badge
                  variant="outline"
                  className="flex items-center justify-center h-7 px-2 gap-1.5 rounded-lg border-primary/20 text-primary animate-pulse cursor-pointer text-[10px]"
                  onClick={reconnect}
                  title="Conectando. Clic para reintentar"
                >
                  <WifiOff className="h-3 w-3" />
                  <span className="font-semibold uppercase tracking-wider">Conectando</span>
                </Badge>
              )}
            </div>

            {/* Theme Toggle */}
            <div className="flex items-center">
              <ThemeToggle />
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-2 mb-1">
            <ThemeToggle />
            <TooltipProvider delayDuration={200}>
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    onClick={reconnect}
                    className={cn(
                      "h-6 w-6 rounded-full flex items-center justify-center transition-all",
                      connectionError ? "bg-destructive/20 text-destructive" : isConnected ? "bg-green-500/10 text-green-500" : "bg-primary/10 text-primary animate-pulse"
                    )}
                  >
                    {connectionError ? (
                      <AlertTriangle className="h-3 w-3" />
                    ) : isConnected ? (
                      <div className="h-2 w-2 rounded-full bg-green-500" />
                    ) : (
                      <WifiOff className="h-3 w-3" />
                    )}
                  </button>
                </TooltipTrigger>
                <TooltipContent side="right">
                  <p className="text-xs">
                    {connectionError ? "Error WS (clic para reconectar)" : isConnected ? "WebSocket Online" : "Conectando..."}
                  </p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
        )}

        {/* Menú de Usuario */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              className={cn(
                "transition-colors duration-150 hover:bg-accent/60 rounded-xl group",
                isCollapsed ? "h-9 w-9 p-0 flex items-center justify-center mx-auto" : "w-full justify-start gap-2 h-auto py-1.5 px-2"
              )}
            >
              <div className="relative shrink-0">
                <Avatar className="h-7 w-7 border border-primary/20">
                  <AvatarImage src="https://github.com/shadcn.png" alt="@user" />
                  <AvatarFallback className="bg-primary text-primary-foreground font-semibold text-xs">
                    {user?.username?.slice(0, 2).toUpperCase() || "KA"}
                  </AvatarFallback>
                </Avatar>
                <div className="absolute -bottom-0.5 -right-0.5 w-2 h-2 bg-green-500 rounded-full border border-background"></div>
              </div>
              {!isCollapsed && (
                <div className="flex flex-col items-start overflow-hidden flex-1 leading-tight">
                  <span className="font-medium text-xs truncate w-full text-left text-foreground group-hover:text-primary transition-colors">
                    {user?.username || "Usuario"}
                  </span>
                  <span className="text-[11px] text-muted-foreground/70 truncate w-full text-left">
                    {user?.email || "Sin Email"}
                  </span>
                </div>
              )}
              {!isCollapsed && <Settings className="h-3.5 w-3.5 text-muted-foreground/70 group-hover:text-primary transition-colors shrink-0" />}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-52 text-xs">
            <div className="flex items-center justify-start gap-2 p-2">
              <div className="flex flex-col space-y-0.5 leading-none">
                {user?.username && <p className="font-medium text-xs">{user.username}</p>}
                {user?.email && <p className="w-[180px] truncate text-xs text-muted-foreground">{user.email}</p>}
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
              <LogOut className="mr-1.5 h-3.5 w-3.5 text-red-500" />
              <span className="text-red-500">Cerrar Sesión</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* Diálogo de Búsqueda Universal */}
      <UniversalSearchDialog
        isOpen={isUniversalSearchDialogOpen}
        onOpenChange={setIsUniversalSearchDialogOpen}
        searchTerm={searchTerm}
        setSearchTerm={setSearchTerm}
      />
    </div>
  );
}
