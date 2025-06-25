// En: src/components/Sidebar.tsx
'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation'; // Importa useRouter
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Plus, MessageSquare, Notebook, BrainCircuit, Calendar, LayoutDashboard, LogOut } from 'lucide-react';
import Image from 'next/image';
import apiClient from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';

// Definimos el tipo para un hilo de chat para mayor seguridad
interface ChatThread {
  id: string;
  title: string;
}

export function Sidebar() {
  const [threads, setThreads] = useState<ChatThread[]>([]);
  const { logout, user } = useAuth();
  const pathname = usePathname(); // Hook para saber en qué URL estamos
  const router = useRouter();   // Hook para redirigir

  useEffect(() => {
    const fetchThreads = async () => {
      // Solo buscamos hilos si el usuario está logueado
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
  }, [user]); // El array de dependencias hace que se ejecute cuando el estado 'user' cambia

  const handleNewChat = async () => {
    try {
      // Llamamos al endpoint para crear un nuevo hilo
      const response = await apiClient.post<ChatThread>('/api/threads');
      const newThread = response.data;
      // Añadimos el nuevo hilo al principio de la lista para que se vea al instante
      setThreads((prevThreads) => [newThread, ...prevThreads]);
      // Redirigimos al usuario a la página del nuevo chat
      router.push(`/chat/${newThread.id}`);
    } catch (error) {
      console.error('Error creating new chat:', error);
    }
  };

  return (
    <div className="flex flex-col h-full bg-zinc-900/50 p-4 border-r">
      {/* Botón de Nuevo Chat */}
      <div className="flex items-center justify-between mb-4">
        <Image src="/logo-simple.png" alt="Kognito Logo" width={30} height={30} />
        <Button onClick={handleNewChat} variant="ghost" size="sm" className="gap-2">
          <Plus className="h-4 w-4" />
          Nuevo Chat
        </Button>
      </div>

      <p className="text-sm font-semibold text-muted-foreground mb-2 px-2">Conversaciones</p>
      <ScrollArea className="flex-grow mb-4">
        <div className="space-y-1">
          {threads.map((thread) => (
            // Cada hilo es un link a su página de chat
            <Link key={thread.id} href={`/chat/${thread.id}`} passHref>
              <Button
                variant={pathname === `/chat/${thread.id}` ? 'secondary' : 'ghost'}
                className="w-full justify-start font-normal"
              >
                <MessageSquare className="mr-2 h-4 w-4 flex-shrink-0" />
                <span className="truncate">{thread.title}</span>
              </Button>
            </Link>
          ))}
        </div>
      </ScrollArea>

      {/* RAG Management Link */}
      <Link href="/rag" passHref>
        <Button variant={pathname.startsWith('/rag') ? 'secondary' : 'ghost'} className="w-full justify-start text-muted-foreground hover:text-foreground mb-2">
          <BrainCircuit className="mr-2 h-4 w-4" />
          Gestión RAG
        </Button>
      </Link>

      {/* Menú inferior */}
      <div className="mt-auto pt-4 border-t">
        {user && (
          <div className="flex items-center gap-2 mb-4">
              <Image src="/logo-simple.png" alt="User" width={24} height={24} className="rounded-full" />
              <span className="text-sm font-medium truncate">{user.name || user.email}</span>
          </div>
        )}
        <Button onClick={logout} variant="outline" className="w-full justify-start gap-2">
          <LogOut className="h-4 w-4" />
          Cerrar Sesión
        </Button>
      </div>
    </div>
  );
}
