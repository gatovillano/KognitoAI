'use client';

import { useState, useEffect, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { BookMarked, Loader2, ChevronRight, Folder, File as FileIcon } from 'lucide-react';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Checkbox } from '@/components/ui/checkbox';
import { toast } from 'sonner';
import apiClient from '@/lib/api';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';

interface SelectedContextItem {
  id: string;
  type: 'document' | 'collection';
  name: string;
  title?: string;
  topic?: string;
}

interface ContextSelectorButtonProps {
  onContextSelected: (selectedItems: SelectedContextItem[]) => void;
  currentContext: SelectedContextItem[];
  workspaceId?: string;
}

export function ContextSelectorButton({ onContextSelected, currentContext, workspaceId }: ContextSelectorButtonProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [documents, setDocuments] = useState<SelectedContextItem[]>([]);
  const [selectedDocuments, setSelectedDocuments] = useState<SelectedContextItem[]>(currentContext || []);
  const [isLoading, setIsLoading] = useState(false);
  const [collections, setCollections] = useState<{ topic: string; items: SelectedContextItem[] }[]>([]);
  const [expandedTopics, setExpandedTopics] = useState<Record<string, boolean>>({});

  const fetchDocuments = useCallback(async () => {
    setIsLoading(true);
    try {
      const apiParams = { workspace_id: workspaceId || null };
      console.log('DEBUG ContextSelectorButton: workspaceId before API call:', workspaceId);
      
      const [collectionsRes, documentsRes] = await Promise.all([
        apiClient.get('/api/collections', { params: { ...apiParams } }),
        apiClient.get('/api/documents/list-documents', { params: { ...apiParams } }),
      ]);


      const fetchedCollections = collectionsRes.data.map((col: any) => ({
        id: col.id,
        type: 'collection',
        name: col.name,
        title: col.name,
        topic: col.name, // Usar el nombre de la colección como topic para agrupar
      }));

      const fetchedDocuments = documentsRes.data.map((doc: any) => ({
        id: doc.document_id,
        type: 'document',
        name: doc.title || doc.file_name,
        title: doc.title || doc.file_name,
        topic: doc.topic, // Usar el topic del documento para agrupar
      }));

      // Agrupar documentos por topic y colecciones por su nombre
      const groupedItems: { [key: string]: { topic: string; items: SelectedContextItem[] } } = {};

      fetchedCollections.forEach((col: SelectedContextItem) => {
        if (!groupedItems[col.topic!]) {
          groupedItems[col.topic!] = { topic: col.topic!, items: [] };
        }
        groupedItems[col.topic!].items.push(col);
      });

      fetchedDocuments.forEach((doc: SelectedContextItem) => {
        if (!groupedItems[doc.topic!]) {
          groupedItems[doc.topic!] = { topic: doc.topic!, items: [] };
        }
        groupedItems[doc.topic!].items.push(doc);
      });
      
      setCollections(Object.values(groupedItems));
      setDocuments(fetchedDocuments); // Mantener los documentos planos también si es necesario
    } catch (error) {
      toast.error('Error al cargar los documentos y colecciones');
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  }, [workspaceId]);

  useEffect(() => {
    if (isOpen && documents.length === 0) {
      fetchDocuments();
    }
  }, [isOpen, documents.length, workspaceId, fetchDocuments]); // Añadir workspaceId a las dependencias

  const toggleTopicExpansion = (topic: string) => {
    setExpandedTopics(prev => ({ ...prev, [topic]: !prev[topic] }));
  };

  const handleSelectItem = (item: SelectedContextItem) => {
    setSelectedDocuments(prev => {
      const isSelected = prev.some(d => d.id === item.id && d.type === item.type);
      if (isSelected) {
        return prev.filter(d => !(d.id === item.id && d.type === item.type));
      } else {
        return [...prev, item];
      }
    });
  };

  const handleSelectGroup = (group: { topic: string; items: SelectedContextItem[] }) => {
    setSelectedDocuments(prev => {
      const allItemsInGroupSelected = group.items.every(item => isItemSelected(item));
      if (allItemsInGroupSelected) {
        // Deseleccionar todos los items del grupo
        return prev.filter(selected => !group.items.some(item => item.id === selected.id && item.type === selected.type));
      } else {
        // Seleccionar todos los items del grupo que no estén ya seleccionados
        const newSelected = [...prev];
        group.items.forEach(item => {
          if (!isItemSelected(item)) {
            newSelected.push(item);
          }
        });
        return newSelected;
      }
    });
  };

  const handleApplyContext = () => {
    onContextSelected(selectedDocuments);
    setIsOpen(false);
    toast.success(`Contexto actualizado con ${selectedDocuments.length} ítem(s)`);
  };

  const isItemSelected = (item: SelectedContextItem) => {
    return selectedDocuments.some(d => d.id === item.id && d.type === item.type);
  };

  const isGroupSelected = (group: { topic: string; items: SelectedContextItem[] }) => {
    return group.items.every(item => isItemSelected(item));
  };

  return (
    <Popover open={isOpen} onOpenChange={setIsOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className={`rounded-full w-8 h-8 p-0 group flex items-center justify-center ${selectedDocuments.length > 0 ? 'bg-primary/10 text-primary' : 'hover:bg-muted'}`}
        >
          <BookMarked className="h-4 w-4 flex-shrink-0" />

        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-80 p-0" align="start">
        <div className="p-4 border-b">
          <h3 className="font-medium">Seleccionar Conocimiento para Contexto</h3>
          <p className="text-sm text-muted-foreground">
            {selectedDocuments.length} ítem(s) seleccionado(s)
          </p>
        </div>
        <ScrollArea className="h-60">
          {isLoading ? (
            <div className="flex items-center justify-center p-4">
              <Loader2 className="h-4 w-4 animate-spin" />
            </div>
          ) : collections.length === 0 ? (
            <div className="p-4 text-center text-sm text-muted-foreground">
              No hay conocimiento disponible
            </div>
          ) : (
            <div className="p-2">
              {collections.map((group) => (
                <Collapsible key={group.topic} open={expandedTopics[group.topic]} onOpenChange={() => toggleTopicExpansion(group.topic)}>
                  <CollapsibleTrigger asChild>
                    <div className="flex items-center space-x-2 p-2 hover:bg-muted rounded-md cursor-pointer">
                      <ChevronRight className={`h-4 w-4 transition-transform ${expandedTopics[group.topic] ? 'rotate-90' : ''}`} />
                      <Checkbox
                        id={`group-${group.topic}`}
                        checked={isGroupSelected(group)}
                        onCheckedChange={() => handleSelectGroup(group)}
                      />
                      <label
                        htmlFor={`group-${group.topic}`}
                        className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 flex-1 cursor-pointer"
                      >
                        <Folder className="inline-block h-4 w-4 mr-2 text-primary" />
                        {group.topic} ({group.items.length})
                      </label>
                    </div>
                  </CollapsibleTrigger>
                  <CollapsibleContent>
                    <div className="ml-6 border-l border-border">
                      {group.items.map((item) => (
                        <div
                          key={`${item.type}-${item.id}`}
                          className="flex items-center space-x-2 p-2 hover:bg-muted rounded-md cursor-pointer"
                          onClick={() => handleSelectItem(item)}
                        >
                          <Checkbox
                            id={`${item.type}-${item.id}`}
                            checked={isItemSelected(item)}
                            onCheckedChange={() => handleSelectItem(item)}
                          />
                          <label
                            htmlFor={`${item.type}-${item.id}`}
                            className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 flex-1 cursor-pointer"
                          >
                            <div className="flex items-center">
                              {item.type === 'document' ? <FileIcon className="h-4 w-4 mr-2 text-secondary flex-shrink-0" /> : <Folder className="h-4 w-4 mr-2 text-primary flex-shrink-0" />}
                              <div className="flex-grow">
                                <div className="font-medium truncate">{item.name || item.title}</div>
                                <div className="text-xs text-muted-foreground capitalize">{item.type}</div>
                              </div>
                            </div>
                          </label>
                        </div>
                      ))}
                    </div>
                  </CollapsibleContent>
                </Collapsible>
              ))}
            </div>
          )}
        </ScrollArea>
        <div className="p-4 border-t flex justify-between">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setSelectedDocuments([])}
            disabled={selectedDocuments.length === 0}
          >
            Limpiar
          </Button>
          <Button
            size="sm"
            onClick={handleApplyContext}
            disabled={isLoading}
          >
            Aplicar Contexto
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  );
}
