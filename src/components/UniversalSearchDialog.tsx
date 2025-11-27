'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation'; // Importar useRouter
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Search, MessageSquare, StickyNote, BookOpen, CalendarDays } from 'lucide-react';
import { useSearch } from '@/contexts/SearchContext';
import apiClient from '@/lib/api';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useAuth } from '@/contexts/AuthContext';

import { useWorkspace } from '@/contexts/WorkspaceContext';

interface UniversalSearchDialogProps {
  isOpen: boolean;
  onOpenChange: (isOpen: boolean) => void;
  searchTerm: string;
  setSearchTerm: (term: string) => void;
}

export function UniversalSearchDialog({ isOpen, onOpenChange, searchTerm, setSearchTerm }: UniversalSearchDialogProps) {
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const { user } = useAuth();
  const { currentWorkspace: activeWorkspace } = useWorkspace();
  const router = useRouter(); // Inicializar useRouter

  useEffect(() => {
    const fetchResults = async () => {
      if (!searchTerm || searchTerm.length < 2 || !user?.id) {
        setResults([]);
        setLoading(false);
        return;
      }

      setLoading(true);
      try {
        const params = {
          query: searchTerm,
          user_id: user.id,
          workspace_id: activeWorkspace?.id,
        };
        const response = await apiClient.get(`/api/universal_search`, {
          params: { ...params }, // Clonar el objeto params
        });
        setResults(response.data);
      } catch (error) {
        console.error('Error fetching universal search results:', error);
        setResults([]);
      } finally {
        setLoading(false);
      }
    };

    if (isOpen) {
      fetchResults();
    } else {
      setResults([]);
    }
  }, [searchTerm, isOpen, user?.id, activeWorkspace?.id]);

  const handleResultClick = (result: any) => {
    let url = '';
    switch (result.type) {
      case 'chat_thread':
      case 'chat_message':
        url = `/chat/${result.id}`;
        break;
      case 'note':
        url = `/notes?noteId=${result.id}`;
        break;
      case 'knowledge':
        // Asumiendo que los conocimientos se pueden ver en una página de RAG o similar
        // Necesitaríamos más información sobre cómo se visualizan los "conocimientos"
        // Por ahora, redirigiremos a una página genérica o al dashboard de RAG
        url = `/rag`; // O una URL más específica si existe
        break;
      case 'agenda':
        // Asumiendo que los eventos de agenda se pueden ver en una página de agenda
        url = `/agenda`; // O una URL más específica si existe, quizás con un modal
        break;
      default:
        console.warn('Tipo de resultado desconocido, no se puede navegar:', result.type);
        return;
    }
    onOpenChange(false); // Cerrar el diálogo de búsqueda
    router.push(url); // Redirigir al usuario
  };

  const getIcon = (type: string) => {
    switch (type) {
      case 'chat_thread':
      case 'chat_message':
        return <MessageSquare className="h-4 w-4 text-blue-500" />;
      case 'note':
        return <StickyNote className="h-4 w-4 text-green-500" />;
      case 'knowledge':
        return <BookOpen className="h-4 w-4 text-purple-500" />;
      case 'agenda':
        return <CalendarDays className="h-4 w-4 text-red-500" />;
      default:
        return <Search className="h-4 w-4 text-gray-500" />;
    }
  };

  const renderResult = (result: any) => {
    switch (result.type) {
      case 'chat_thread':
        return (
          <div className="flex items-center space-x-2 p-2 hover:bg-muted rounded-md cursor-pointer" onClick={() => handleResultClick(result)}>
            {getIcon(result.type)}
            <div>
              <p className="font-medium">Hilo de Chat: {result.title || 'Hilo sin título'}</p>
              <p className="text-xs text-muted-foreground">{result.created_at ? new Date(result.created_at).toLocaleDateString() : ''}</p>
            </div>
          </div>
        );
      case 'chat_message':
        return (
          <div className="flex items-start space-x-2 p-2 hover:bg-muted rounded-md cursor-pointer" onClick={() => handleResultClick(result)}>
            {getIcon(result.type)}
            <div>
              <p className="font-medium">Mensaje en "{result.thread_title}"</p>
              <p className="text-sm text-foreground line-clamp-2">{result.content}</p>
              <p className="text-xs text-muted-foreground">{result.created_at ? new Date(result.created_at).toLocaleDateString() : ''} - {result.sender}</p>
            </div>
          </div>
        );
      case 'note':
        return (
          <div className="flex items-start space-x-2 p-2 hover:bg-muted rounded-md cursor-pointer" onClick={() => handleResultClick(result)}>
            {getIcon(result.type)}
            <div>
              <p className="font-medium">Nota: {result.title}</p>
              <p className="text-sm text-foreground line-clamp-2">{result.content}</p>
              <p className="text-xs text-muted-foreground">{result.created_at ? new Date(result.created_at).toLocaleDateString() : ''}</p>
            </div>
          </div>
        );
      case 'knowledge':
        return (
          <div className="flex items-start space-x-2 p-2 hover:bg-muted rounded-md cursor-pointer" onClick={() => handleResultClick(result)}>
            {getIcon(result.type)}
            <div>
              <p className="font-medium">Conocimiento: {result.title}</p>
              <p className="text-sm text-foreground line-clamp-2">{result.content}</p>
              <p className="text-xs text-muted-foreground">Tema: {result.topic}</p>
            </div>
          </div>
        );
      case 'agenda':
        return (
          <div className="flex items-start space-x-2 p-2 hover:bg-muted rounded-md cursor-pointer" onClick={() => handleResultClick(result)}>
            {getIcon(result.type)}
            <div>
              <p className="font-medium">Evento: {result.title}</p>
              <p className="text-sm text-foreground line-clamp-2">{result.description}</p>
              <p className="text-xs text-muted-foreground">{result.start_time ? new Date(result.start_time).toLocaleString() : ''}</p>
            </div>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px] max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>Búsqueda Universal</DialogTitle>
          <DialogDescription>
            Busca en tus Chats, Notas, Conocimientos y Agenda.
          </DialogDescription>
        </DialogHeader>
        <div className="relative mb-4">
          <Input
            type="text"
            placeholder="Escribe para buscar..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-8"
          />
          <Search className="h-4 w-4 absolute left-2.5 top-1/2 transform -translate-y-1/2 text-muted-foreground" />
        </div>
        <div className="flex-1 overflow-y-auto -mr-4 pr-4">
          <ScrollArea className="h-full">
            {loading && searchTerm && <p className="text-center text-muted-foreground">Buscando...</p>}
            {!loading && searchTerm && results.length === 0 && (
              <p className="text-center text-muted-foreground">{`No se encontraron resultados para &quot;${searchTerm}&quot;`}</p>
            )}
            {!loading && !searchTerm && (
              <p className="text-center text-muted-foreground">Empieza a escribir para buscar en todos tus datos.</p>
            )}
            {!loading && results.length > 0 && (
              <div className="space-y-2">
                {results.map((result, index) => (
                  <React.Fragment key={index}>
                    {renderResult(result)}
                  </React.Fragment>
                ))}
              </div>
            )}
          </ScrollArea>
        </div>
      </DialogContent>
    </Dialog>
  );
}