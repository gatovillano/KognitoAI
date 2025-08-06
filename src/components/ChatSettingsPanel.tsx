import React, { useState, useEffect, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { X, BookMarked, FileText } from 'lucide-react';

interface PersistentContextItem {
  type: 'document' | 'collection';
  id: string; // This could be document ID or collection name/ID
  name?: string; // Optional: display name for the item
}

interface ChatSettingsPanelProps {
  threadId: string;
  isVisible: boolean;
  onClose: () => void;
  onRemoveContextItem: (threadId: string, item: PersistentContextItem) => Promise<void>;
  onAddContextItem: (threadId: string, item: PersistentContextItem) => Promise<void>; // New prop for adding
}

export const ChatSettingsPanel: React.FC<ChatSettingsPanelProps> = ({
  threadId,
  isVisible,
  onClose,
  onRemoveContextItem,
  onAddContextItem, // Include new prop
}) => {
  const [persistentContext, setPersistentContext] = useState<PersistentContextItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchPersistentContext = useCallback(async () => {
    if (!threadId) return;
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`/api/threads/${threadId}/context`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setPersistentContext(data.persistent_rag_context || []);
    } catch (e: any) {
      console.error("Error fetching persistent context:", e);
      setError(`Failed to load context: ${e.message}`);
    } finally {
      setLoading(false);
    }
  }, [threadId]);

  useEffect(() => {
    if (isVisible && threadId) {
      fetchPersistentContext();
    }
  }, [isVisible, threadId, fetchPersistentContext]);

  const handleRemoveItem = async (itemToRemove: PersistentContextItem) => {
    await onRemoveContextItem(threadId, itemToRemove);
    // Re-fetch to ensure UI is in sync with backend
    fetchPersistentContext();
  };

  // This function will be called from ChatInputBar when a new item is selected
  const handleAddItem = async (itemToAdd: PersistentContextItem) => {
    await onAddContextItem(threadId, itemToAdd);
    fetchPersistentContext(); // Refresh the list
  };

  if (!isVisible) {
    return null;
  }

  return (
    <div className="h-full flex flex-col bg-white border-l border-gray-200 shadow-lg">
      <div className="p-4 border-b border-gray-200 flex justify-between items-center">
        <h2 className="text-lg font-semibold">Configuración del Chat</h2>
        <Button variant="ghost" size="icon" onClick={onClose}>
          <X className="h-5 w-5" />
        </Button>
      </div>
      <div className="flex-1 overflow-auto p-4">
        <h3 className="text-md font-medium mb-2">Contexto RAG Persistente</h3>
        {loading && <p>Cargando contexto...</p>}
        {error && <p className="text-red-500">{error}</p>}
        {!loading && persistentContext.length === 0 && (
          <p className="text-gray-500">No hay contexto persistente añadido a este chat.</p>
        )}
        {!loading && persistentContext.length > 0 && (
          <ul className="space-y-2">
            {persistentContext.map((item, index) => (
              <li key={index} className="flex items-center justify-between bg-gray-100 p-2 rounded-md">
                <div className="flex items-center gap-2">
                  {item.type === 'document' ? (
                    <FileText className="h-4 w-4 text-blue-500" />
                  ) : (
                    <BookMarked className="h-4 w-4 text-green-500" />
                  )}
                  <span className="text-sm font-medium">{item.name || item.id}</span>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => handleRemoveItem(item)}
                  className="text-red-500 hover:bg-red-100"
                >
                  <X className="h-4 w-4" />
                </Button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
};