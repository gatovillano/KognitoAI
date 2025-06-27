// En: src/components/Sidebar.tsx (Versión completa y actualizada)

'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Plus, MessageSquare, BookMarked, Notebook, Calendar, LogOut, Bot, ChevronDown, ChevronRight, Pin, Users } from 'lucide-react';
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
}

export function Sidebar({ isCollapsed, onLinkClick }: SidebarProps) {
  const [threads, setThreads] = useState<ChatThread[]>([]);
  const [pinnedThreads, setPinnedThreads] = useState<ChatThread[]>([]);
  const [isPinnedCollapsed, setIsPinnedCollapsed] = useState(false);
  const [isRecentCollapsed, setIsRecentCollapsed] = useState(false);
  const { logout, user } = useAuth();
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    const fetchThreads = async () => {
      if (user) {
        try {
          const response = await apiClient.get<ChatThread[]>('/api/threads');
          const allThreads = response.data;
          setThreads(allThreads.filter(thread => !thread.isPinned));
          setPinnedThreads(allThreads.filter(thread => thread.isPinned));
        } catch (error) {
          console.error('Error fetching threads:', error);
        }
      }
    };
    fetchThreads();
  }, [user]);

  const handleNewChat = async () => {
    try {
      const response = await apiClient.post<ChatThread>('/api/threads');
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

  const ThreadItem = ({ thread, isPinned }: { thread: ChatThread; isPinned: boolean }) => {
    const [{ isDragging }, drag] = useDrag({
      type: 'THREAD',
      item: { thread, isPinned },
      collect: (monitor) => ({
        isDragging: monitor.isDragging(),
      }),
    });

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
              <div
                className="h-6 w-6 ml-auto cursor-pointer"
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  isPinned ? handleUnpinThread(thread) : handlePinThread(thread);
                }}
              >
                <Pin className={cn("h-4 w-4", isPinned && "text-primary")} />
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
    <div className={cn("flex flex-col h-full p-2", isCollapsed ? "items-center" : "p-4")}>
      <div className={cn("flex items-center w-full pb-2 mb-2 border-b", isCollapsed ? "justify-center" : "justify-between")}>
        <Image src="/logo-simple.png" alt="Kognito Logo" width={30} height={30} className={cn(!isCollapsed && "mr-2")} />
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
          <Link href="/rag" passHref onClick={onLinkClick} title="Gestión de Documentos">
            <Button variant={pathname.startsWith('/rag') ? 'secondary' : 'ghost'} className={cn("w-full", isCollapsed ? "justify-center h-10 w-10 p-0" : "justify-start")}>
              <BookMarked className={cn("h-4 w-4", !isCollapsed && "mr-2")}/>
              {!isCollapsed && "Gestión de Documentos"}
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
          <Link href="/chat" passHref onClick={onLinkClick} title="Chat">
            <Button variant={pathname.startsWith('/chat') ? 'secondary' : 'ghost'} className={cn("w-full", isCollapsed ? "justify-center h-10 w-10 p-0" : "justify-start")}>
              <MessageSquare className={cn("h-4 w-4", !isCollapsed && "mr-2")}/>
              {!isCollapsed && "Chat"}
            </Button>
          </Link>
        </nav>
        {!isCollapsed && (
          <div className="flex items-center justify-between mb-2 px-2 mt-4">
            <p className="font-semibold text-muted-foreground whitespace-nowrap">Conversaciones</p>
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
              {pinnedThreads.length > 0 ? (
                <div className="space-y-1">
                  {pinnedThreads.map((thread) => (
                    <ThreadItem key={thread.id} thread={thread} isPinned={true} />
                  ))}
                </div>
              ) : (
                <p className="text-xs text-muted-foreground px-2 mb-2">No hay conversaciones fijadas.</p>
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
                {threads.map((thread) => (
                  <ThreadItem key={thread.id} thread={thread} isPinned={false} />
                ))}
              </div>
            </DropArea>
          )}
        </DndProvider>
      </ScrollArea>

      <div className={cn("mt-auto w-full pt-2 border-t", isCollapsed && "flex flex-col items-center")}>
        <Button onClick={logout} variant="outline" className={cn("w-full mt-4", isCollapsed ? "h-10 w-10 p-0" : "justify-start gap-2")}>
          <LogOut className="h-4 w-4" />
          {!isCollapsed && "Cerrar Sesión"}
        </Button>
      </div>
    </div>
  );
}
