// En: src/components/Sidebar.tsx (Versión completa y actualizada)

'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Plus, MessageSquare, BookMarked, Notebook, Calendar, LogOut } from 'lucide-react';
import Image from 'next/image';
import apiClient from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';
import { cn } from '@/lib/utils';
import { InlineMarkdownRenderer } from './InlineMarkdownRenderer'; // <-- IMPORTAR EL NUEVO COMPONENTE

interface SidebarProps {
  isCollapsed: boolean;
  onLinkClick?: () => void;
}

interface ChatThread {
  id: string;
  title: string;
}

export function Sidebar({ isCollapsed, onLinkClick }: SidebarProps) {
  const [threads, setThreads] = useState<ChatThread[]>([]);
  const { logout, user } = useAuth();
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    const fetchThreads = async () => {
      if (user) {
        try {
          const response = await apiClient.get<ChatThread[]>('/api/threads');
          setThreads(response.data);
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
        {!isCollapsed && <p className="font-semibold text-muted-foreground mb-2 px-2 whitespace-nowrap">Conversaciones</p>}
        {isCollapsed && (
          <Button onClick={handleNewChat} variant="ghost" size="icon" className="mb-2" title="Nuevo Chat">
            <Plus className="h-5 w-5" />
          </Button>
        )}
      </div>

      <ScrollArea className="flex-grow w-full">
        <div className="space-y-1">
          {threads.map((thread) => (
            <Link key={thread.id} href={`/chat/${thread.id}`} passHref onClick={onLinkClick} title={isCollapsed ? thread.title : undefined}>
              <Button
                variant={pathname === `/chat/${thread.id}` ? "secondary" : "ghost"}
                className={cn(
                  "w-full font-normal items-start text-left",
                  isCollapsed ? "justify-center h-10 w-10 p-0" : "justify-start h-auto py-2 px-2"
                )}
              >
                <MessageSquare className={cn("h-4 w-4 mt-1 flex-shrink-0", !isCollapsed && "mr-2")} />
                {/* ---- CAMBIO: Usamos el nuevo renderizador para el título ---- */}
                {!isCollapsed && (
                  <div className="whitespace-normal break-words">
                    <InlineMarkdownRenderer content={thread.title} />
                  </div>
                )}
              </Button>
            </Link>
          ))}
        </div>
      </ScrollArea>

      <div className={cn("mt-auto w-full pt-2 border-t", isCollapsed && "flex flex-col items-center")}>
        <nav className="space-y-1 w-full">
          {!isCollapsed && <p className="font-semibold text-muted-foreground my-2 px-2 whitespace-nowrap">Herramientas</p>}
          <Link href="/notes" passHref onClick={onLinkClick} title="Notas">
             <Button variant={pathname.startsWith('/notes') ? 'secondary' : 'ghost'} className={cn("w-full", isCollapsed ? "justify-center h-10 w-10 p-0" : "justify-start")}>
                <Notebook className={cn("h-4 w-4", !isCollapsed && "mr-2")}/>
                {!isCollapsed && "Notas"}
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
        </nav>
        <Button onClick={logout} variant="outline" className={cn("w-full mt-4", isCollapsed ? "h-10 w-10 p-0" : "justify-start gap-2")}>
          <LogOut className="h-4 w-4" />
          {!isCollapsed && "Cerrar Sesión"}
        </Button>
      </div>
    </div>
  );
}
