'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import { Button } from '@/components/ui/button';
import { BookMarked, Loader2, ChevronRight, Folder, File as FileIcon, FileText } from 'lucide-react';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Checkbox } from '@/components/ui/checkbox';
import { toast } from 'sonner';
import apiClient from '@/lib/api';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { SelectedContextItem } from '@/types/context';

interface ContextSelectorButtonProps {
  onContextSelected: (selectedItems: SelectedContextItem[]) => void;
  currentContext: SelectedContextItem[];
  workspaceId?: string;
}

interface OnlyOfficeDocItem {
  id: string;
  filename: string;
  extension: string;
  workspace_name?: string;
}

export function ContextSelectorButton({ onContextSelected, currentContext, workspaceId }: ContextSelectorButtonProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<'rag' | 'onlyoffice'>('rag');
  const [selectedDocuments, setSelectedDocuments] = useState<SelectedContextItem[]>(currentContext || []);
  const [isLoading, setIsLoading] = useState(false);

  // RAG State
  const [collections, setCollections] = useState<{ topic: string; items: SelectedContextItem[] }[]>([]);
  const [expandedTopics, setExpandedTopics] = useState<Record<string, boolean>>({});

  // OnlyOffice State
  const [onlyOfficeDocs, setOnlyOfficeDocs] = useState<SelectedContextItem[]>([]);

  const fetchContextData = useCallback(async () => {
    setIsLoading(true);
    try {
      const apiParams: { workspace_id?: string | null } = {};
      if (workspaceId) {
        apiParams.workspace_id = workspaceId;
      }
      
      const [collectionsRes, documentsRes, onlyofficeRes] = await Promise.all([
        apiClient.get('/api/collections', { params: { ...apiParams } }).catch(() => ({ data: [] })),
        apiClient.get('/api/documents/list-documents', { params: { ...apiParams } }).catch(() => ({ data: [] })),
        apiClient.get('/api/onlyoffice/list', { params: { ...apiParams } }).catch(() => ({ data: [] })),
      ]);

      // 1. Procesar Documentos y Colecciones RAG
      const fetchedCollections: SelectedContextItem[] = (collectionsRes.data || []).map((col: any) => ({
        id: col.id,
        type: 'collection',
        name: col.name,
        title: col.name,
        topic: col.name,
        doc_source: 'rag',
      }));

      const fetchedDocuments: SelectedContextItem[] = (documentsRes.data || []).map((doc: any) => ({
        id: doc.document_id,
        type: 'document',
        name: doc.title || doc.file_name,
        title: doc.title || doc.file_name,
        topic: doc.topic,
        file_name: doc.file_name,
        doc_source: 'rag',
      }));

      // Agrupar RAG por topic
      const groupedItems: { [key: string]: { id: string; topic: string; items: SelectedContextItem[] } } = {};
      let groupIdCounter = 0;

      fetchedCollections.forEach((col: SelectedContextItem) => {
        const topicKey = col.topic || 'Sin categoría';
        if (!groupedItems[topicKey]) {
          groupedItems[topicKey] = { id: `group-${groupIdCounter++}`, topic: topicKey, items: [] };
        }
        groupedItems[topicKey].items.push(col);
      });

      fetchedDocuments.forEach((doc: SelectedContextItem) => {
        const topicKey = doc.topic || 'Sin categoría';
        if (!groupedItems[topicKey]) {
          groupedItems[topicKey] = { id: `group-${groupIdCounter++}`, topic: topicKey, items: [] };
        }
        groupedItems[topicKey].items.push(doc);
      });
      
      setCollections(Object.values(groupedItems));

      // 2. Procesar Documentos OnlyOffice
      const fetchedOnlyOffice: SelectedContextItem[] = (onlyofficeRes.data || []).map((doc: OnlyOfficeDocItem) => ({
        id: doc.id,
        type: 'onlyoffice',
        name: doc.filename,
        title: doc.filename,
        topic: 'OnlyOffice',
        file_name: doc.filename,
        doc_source: 'onlyoffice',
      }));
      setOnlyOfficeDocs(fetchedOnlyOffice);

    } catch (error) {
      toast.error('Error al cargar documentos');
      console.error('Error fetching context items:', error);
    } finally {
      setIsLoading(false);
    }
  }, [workspaceId]);

  useEffect(() => {
    if (isOpen) {
      fetchContextData();
      setSelectedDocuments(currentContext || []);
    }
  }, [isOpen, workspaceId, fetchContextData, currentContext]);

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
        return prev.filter(selected => !group.items.some(item => item.id === selected.id && item.type === selected.type));
      } else {
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

  // Contadores por tipo
  const ragCount = useMemo(() => {
    return selectedDocuments.filter(d => d.type === 'document' || d.type === 'collection' || d.doc_source === 'rag').length;
  }, [selectedDocuments]);

  const onlyofficeCount = useMemo(() => {
    return selectedDocuments.filter(d => d.type === 'onlyoffice' || d.doc_source === 'onlyoffice').length;
  }, [selectedDocuments]);

  return (
    <Popover open={isOpen} onOpenChange={setIsOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className={`rounded-full w-8 h-8 p-0 group flex items-center justify-center ${selectedDocuments.length > 0 ? 'bg-primary/10 text-primary' : 'hover:bg-muted'}`}
          title="Seleccionar contexto para el agente"
        >
          <BookMarked className="h-4 w-4 flex-shrink-0" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-88 sm:w-96 p-0 shadow-lg" align="start">
        <div className="p-3 border-b bg-muted/30">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-sm">Contexto para el Agente</h3>
            <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded-full font-medium">
              {selectedDocuments.length} ítem(s)
            </span>
          </div>
          <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
            <span className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 inline-block" />
              {ragCount} RAG
            </span>
            <span>•</span>
            <span className="flex items-center gap-1 text-blue-600 dark:text-blue-400">
              <span className="w-1.5 h-1.5 rounded-full bg-blue-500 inline-block" />
              {onlyofficeCount} OnlyOffice
            </span>
          </div>
        </div>

        <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as 'rag' | 'onlyoffice')} className="w-full">
          <div className="px-3 pt-2">
            <TabsList className="grid grid-cols-2 w-full h-8">
              <TabsTrigger value="rag" className="text-xs flex items-center gap-1.5 data-[state=active]:text-emerald-700 dark:data-[state=active]:text-emerald-300">
                <BookMarked className="h-3.5 w-3.5 text-emerald-500" />
                <span>Base RAG</span>
              </TabsTrigger>
              <TabsTrigger value="onlyoffice" className="text-xs flex items-center gap-1.5 data-[state=active]:text-blue-700 dark:data-[state=active]:text-blue-300">
                <FileText className="h-3.5 w-3.5 text-blue-500" />
                <span>OnlyOffice</span>
              </TabsTrigger>
            </TabsList>
          </div>

          <ScrollArea className="h-64 px-2 py-1">
            {isLoading ? (
              <div className="flex flex-col items-center justify-center p-8 text-muted-foreground">
                <Loader2 className="h-5 w-5 animate-spin mb-2" />
                <span className="text-xs">Cargando documentos...</span>
              </div>
            ) : (
              <>
                {/* PESTAÑA: BASE DE CONOCIMIENTO RAG */}
                <TabsContent value="rag" className="m-0 space-y-1">
                  <div className="px-2 py-1 text-[11px] text-muted-foreground bg-emerald-50/50 dark:bg-emerald-950/20 rounded border border-emerald-200/50 dark:border-emerald-800/30 mb-2">
                    💡 Documentos indexados para <strong>búsqueda semántica</strong> y consulta conceptual.
                  </div>
                  {collections.length === 0 ? (
                    <div className="p-4 text-center text-xs text-muted-foreground">
                      No hay documentos RAG disponibles.
                    </div>
                  ) : (
                    collections.map((group) => (
                      <Collapsible key={group.topic} open={expandedTopics[group.topic]} onOpenChange={() => toggleTopicExpansion(group.topic)}>
                        <CollapsibleTrigger asChild>
                          <div className="flex items-center space-x-2 p-1.5 hover:bg-muted rounded-md cursor-pointer text-xs">
                            <ChevronRight className={`h-3.5 w-3.5 transition-transform ${expandedTopics[group.topic] ? 'rotate-90' : ''}`} />
                            <Checkbox
                              id={`group-${group.topic}`}
                              checked={isGroupSelected(group)}
                              onCheckedChange={() => handleSelectGroup(group)}
                            />
                            <label
                              htmlFor={`group-${group.topic}`}
                              className="font-medium flex-1 cursor-pointer flex items-center justify-between"
                            >
                              <span className="flex items-center">
                                <Folder className="h-3.5 w-3.5 mr-1.5 text-amber-500" />
                                {group.topic} ({group.items.length})
                              </span>
                              <span className="text-[10px] uppercase font-semibold text-emerald-600 bg-emerald-50 dark:bg-emerald-950/40 px-1 rounded">RAG</span>
                            </label>
                          </div>
                        </CollapsibleTrigger>
                        <CollapsibleContent>
                          <div className="ml-5 pl-2 border-l border-border/60 space-y-0.5">
                            {group.items.map((item) => (
                              <div
                                key={`${item.type}-${item.id}`}
                                className="flex items-center space-x-2 p-1.5 hover:bg-muted/80 rounded-md cursor-pointer text-xs"
                                onClick={() => handleSelectItem(item)}
                              >
                                <Checkbox
                                  id={`${item.type}-${item.id}`}
                                  checked={isItemSelected(item)}
                                  onCheckedChange={() => handleSelectItem(item)}
                                />
                                <label
                                  htmlFor={`${item.type}-${item.id}`}
                                  className="flex-1 cursor-pointer flex items-center justify-between min-w-0"
                                >
                                  <div className="flex items-center min-w-0 mr-1">
                                    {item.type === 'document' ? (
                                      <FileIcon className="h-3.5 w-3.5 mr-1.5 text-emerald-500 flex-shrink-0" />
                                    ) : (
                                      <Folder className="h-3.5 w-3.5 mr-1.5 text-amber-500 flex-shrink-0" />
                                    )}
                                    <span className="truncate">{item.name || item.title}</span>
                                  </div>
                                  <span className="text-[10px] text-muted-foreground flex-shrink-0">
                                    {item.type === 'document' ? 'doc' : 'col'}
                                  </span>
                                </label>
                              </div>
                            ))}
                          </div>
                        </CollapsibleContent>
                      </Collapsible>
                    ))
                  )}
                </TabsContent>

                {/* PESTAÑA: DOCUMENTOS ONLYOFFICE */}
                <TabsContent value="onlyoffice" className="m-0 space-y-1">
                  <div className="px-2 py-1 text-[11px] text-muted-foreground bg-blue-50/50 dark:bg-blue-950/20 rounded border border-blue-200/50 dark:border-blue-800/30 mb-2">
                    📝 Archivos editables en la nube (<strong>Word, Excel, PowerPoint</strong>).
                  </div>
                  {onlyOfficeDocs.length === 0 ? (
                    <div className="p-4 text-center text-xs text-muted-foreground">
                      No se encontraron documentos en OnlyOffice.
                    </div>
                  ) : (
                    onlyOfficeDocs.map((doc) => (
                      <div
                        key={`oo-${doc.id}`}
                        className="flex items-center space-x-2 p-1.5 hover:bg-muted/80 rounded-md cursor-pointer text-xs"
                        onClick={() => handleSelectItem(doc)}
                      >
                        <Checkbox
                          id={`oo-${doc.id}`}
                          checked={isItemSelected(doc)}
                          onCheckedChange={() => handleSelectItem(doc)}
                        />
                        <label
                          htmlFor={`oo-${doc.id}`}
                          className="flex-1 cursor-pointer flex items-center justify-between min-w-0"
                        >
                          <div className="flex items-center min-w-0 mr-1">
                            <FileText className="h-3.5 w-3.5 mr-1.5 text-blue-500 flex-shrink-0" />
                            <span className="truncate">{doc.name}</span>
                          </div>
                          <span className="text-[10px] font-semibold text-blue-600 bg-blue-50 dark:bg-blue-950/40 px-1 rounded flex-shrink-0">
                            Office
                          </span>
                        </label>
                      </div>
                    ))
                  )}
                </TabsContent>
              </>
            )}
          </ScrollArea>
        </Tabs>

        <div className="p-3 border-t bg-muted/10 flex items-center justify-between">
          <Button
            variant="ghost"
            size="sm"
            className="h-7 text-xs"
            onClick={() => setSelectedDocuments([])}
            disabled={selectedDocuments.length === 0}
          >
            Limpiar
          </Button>
          <Button
            size="sm"
            className="h-7 text-xs px-3"
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
