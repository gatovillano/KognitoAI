
'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { X } from 'lucide-react';
import { toast } from 'sonner';

interface ContextItem {
  type: string;
  id: string;
  name?: string; // Assuming context items might have a display name
}

interface ChatConfigurationPanelProps {
  threadId: string;
  isOpen: boolean;
  onClose: () => void;
  onContextRemoved: (item: ContextItem) => void; // New prop
}

const ChatConfigurationPanel: React.FC<ChatConfigurationPanelProps> = ({ threadId, isOpen, onClose, onContextRemoved }) => {
  const [persistentContext, setPersistentContext] = useState<ContextItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const fetchPersistentContext = useCallback(async () => {
    if (!threadId) return;
    setIsLoading(true);
    try {
      const response = await fetch(`/api/threads/${threadId}/context`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setPersistentContext(data.persistent_rag_context || []);
    } catch (error) {
      console.error('Error fetching persistent context:', error);
      toast.error('Error al cargar el contexto persistente.');
    } finally {
      setIsLoading(false);
    }
  }, [threadId]);

  useEffect(() => {
    if (isOpen && threadId) {
      fetchPersistentContext();
    }
  }, [isOpen, threadId, fetchPersistentContext]);

  const handleRemoveContext = async (itemToRemove: ContextItem) => {
    setIsLoading(true);
    try {
      const response = await fetch(`/api/threads/${threadId}/context/remove`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ context_items: [itemToRemove] }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setPersistentContext(data.new_context || []);
      toast.success('Contexto eliminado correctamente.');
      onContextRemoved(itemToRemove); // Call the new prop here
    } catch (error) {
      console.error('Error removing persistent context:', error);
      toast.error('Error al eliminar el contexto persistente.');
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-40 flex justify-end">
      <div className="bg-card w-96 h-full shadow-lg p-6 overflow-y-auto relative">
        <Button
          variant="ghost"
          size="icon"
          className="absolute top-4 right-4"
          onClick={onClose}
        >
          <X className="h-6 w-6" />
        </Button>
        <h2 className="text-2xl font-bold mb-6">Configuración del Chat</h2>
        
        <div className="mb-6">
          <h3 className="text-lg font-semibold mb-3">Contexto Persistente</h3>
          {isLoading ? (
            <p>Cargando contexto...</p>
          ) : persistentContext.length === 0 ? (
            <p className="text-muted-foreground">No hay contexto persistente añadido a este chat.</p>
          ) : (
            <div className="space-y-2">
              {persistentContext.map((item, index) => (
                <div key={index} className="flex items-center justify-between bg-muted p-3 rounded-md">
                  <span className="text-sm font-medium">{item.name || item.id} ({item.type})</span>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => handleRemoveContext(item)}
                    className="text-muted-foreground hover:text-destructive"
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Aquí se pueden añadir más configuraciones en el futuro */}
      </div>
    </div>
  );
};

export default ChatConfigurationPanel;
