'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { toast } from 'sonner';
import apiClient from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { InlineMarkdownRenderer } from '@/components/InlineMarkdownRenderer';
import { Bot, Inbox, Lightbulb, Loader2, Trash2, Info, CheckCircle, XCircle, CheckSquare, Search, ArrowUpDown, Filter } from 'lucide-react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '@/components/ui/sheet';
import { AnalysisDetailDialog } from '@/app/(dashboard)/analysis/analysis-detail-dialog';
import { ViewNoteDialog } from '@/app/(dashboard)/notes/view-note-dialog';
import { Analysis, Note } from '@/lib/models';

type AgentMessage = {
  id: number;
  title?: string | null;
  content: string;
  category?: string | null;
  created_at: string;
  workspace_name?: string | null;
  workspace_color?: string | null;
};

type InsightItem = {
  id: string;
  title?: string;
  summary: string;
  created_at: string;
  action_suggestion?: string;
  workspace_name?: string | null;
  workspace_color?: string | null;
  workspace_id?: string | null;
  status?: string;
};

type InboxItem =
  | { kind: 'agent_message'; id: string; created_at: string; title: string; preview: string; payload: AgentMessage }
  | { kind: 'insight'; id: string; created_at: string; title: string; preview: string; payload: InsightItem };

export default function InboxPage({ isEmbedded = false }: { params?: any; searchParams?: any; isEmbedded?: boolean }) {
  const [isLoading, setIsLoading] = useState(true);
  const [items, setItems] = useState<InboxItem[]>([]);
  const [isInfoSheetOpen, setIsInfoSheetOpen] = useState(false);

  const [searchQuery, setSearchQuery] = useState('');
  const [sortOrder, setSortOrder] = useState<'desc' | 'asc'>('desc');
  const [filterType, setFilterType] = useState<'all' | 'insight' | 'agent_message'>('all');

  // Estados para los dialogs
  const [selectedNote, setSelectedNote] = useState<Note | null>(null);
  const [isNoteDialogOpen, setIsNoteDialogOpen] = useState(false);
  const [selectedAnalysis, setSelectedAnalysis] = useState<Analysis | null>(null);
  const [isAnalysisDialogOpen, setIsAnalysisDialogOpen] = useState(false);

  const fetchInbox = useCallback(async () => {
    setIsLoading(true);
    try {
      const [messagesRes, insightsRes] = await Promise.all([
        apiClient.post('/api/notes/list-notes', {
          only_agent_messages: true,
          limit: 100,
          skip: 0,
        }),
        apiClient.post('/api/get-all-analysis', {
          analysis_type: 'insight',
          limit: 100,
          offset: 0,
        }),
      ]);

      const messages: AgentMessage[] = (messagesRes.data?.notes || []).map((n: any) => ({
        id: n.id,
        title: n.title,
        content: n.content,
        category: n.category,
        created_at: n.created_at,
        workspace_name: n.workspace_name,
        workspace_color: n.workspace_color,
      }));

      const insights: InsightItem[] = (insightsRes.data?.analysis || []).map((i: any) => ({
        id: i.id,
        title: i.title,
        summary: i.summary,
        created_at: i.created_at,
        action_suggestion: i.action_suggestion,
        workspace_name: i.workspace_name,
        workspace_color: i.workspace_color,
        workspace_id: i.workspace_id,
        status: i.status || 'pending',
      }));

      const merged: InboxItem[] = [
        ...messages.map((msg) => ({
          kind: 'agent_message' as const,
          id: `msg-${msg.id}`,
          created_at: msg.created_at,
          title: msg.title || 'Mensaje del agente',
          preview: msg.content,
          payload: msg,
        })),
        ...insights.map((insight) => ({
          kind: 'insight' as const,
          id: `insight-${insight.id}`,
          created_at: insight.created_at,
          title: insight.title || 'Insight',
          preview: insight.summary,
          payload: insight,
        })),
      ].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

      setItems(merged);
    } catch (error) {
      toast.error('No se pudo cargar la bandeja de entrada.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchInbox();
  }, [fetchInbox]);

  const filteredAndSortedItems = useMemo(() => {
    let result = [...items];

    if (filterType !== 'all') {
      result = result.filter(item => item.kind === filterType);
    }

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(item => 
        (item.title && item.title.toLowerCase().includes(q)) || 
        (item.preview && item.preview.toLowerCase().includes(q))
      );
    }

    result.sort((a, b) => {
      const timeA = new Date(a.created_at).getTime();
      const timeB = new Date(b.created_at).getTime();
      return sortOrder === 'desc' ? timeB - timeA : timeA - timeB;
    });

    return result;
  }, [items, filterType, searchQuery, sortOrder]);

  const emptyState = useMemo(
    () => (
      <div className="text-center py-20 border-2 border-dashed border-border/40 rounded-3xl bg-card/20">
        <Inbox className="h-10 w-10 mx-auto text-muted-foreground/50 mb-3" />
        <h3 className="font-semibold">Tu bandeja está vacía</h3>
        <p className="text-sm text-muted-foreground">Aquí verás mensajes del agente e insights.</p>
      </div>
    ),
    []
  );

  const handleAcceptInsight = async (item: InboxItem) => {
    if (item.kind !== 'insight') return;
    try {
      const description = item.payload.action_suggestion 
          ? `[Insight Aceptado] ${item.payload.title || 'Acción sugerida'}\n\n${item.payload.action_suggestion}`
          : `[Insight Aceptado] ${item.payload.summary}`;
      
      await apiClient.post('/api/tasks', {
        description: description,
        workspace_id: item.payload.workspace_id || undefined,
      });

      await apiClient.post('/api/accept-proactive-insight', {
        insight_id: Number(item.payload.id),
      });
      
      setItems((prev) => 
        prev.map((entry) => {
          if (entry.id === item.id && entry.kind === 'insight') {
            return { ...entry, payload: { ...entry.payload, status: 'accepted' } };
          }
          return entry;
        })
      );
      if (selectedAnalysis?.id === item.payload.id) {
        setSelectedAnalysis(null);
        setIsAnalysisDialogOpen(false);
      }
      toast.success('Insight aceptado. Tarea creada en la Agenda.');
    } catch (error) {
      toast.error('Hubo un error al aceptar el insight.');
    }
  };

  const handleDelete = async (item: InboxItem) => {
    try {
      if (item.kind === 'agent_message') {
        await apiClient.post('/api/delete-note', { note_id: item.payload.id });
      } else {
        await apiClient.delete('/api/delete-proactive-insight', {
          data: { insight_id: Number(item.payload.id) },
        });
      }
      setItems((prev) => prev.filter((entry) => entry.id !== item.id));
      if (item.kind === 'agent_message' && selectedNote?.id === item.payload.id) {
        setSelectedNote(null);
        setIsNoteDialogOpen(false);
      }
      if (item.kind === 'insight' && selectedAnalysis?.id === item.payload.id) {
        setSelectedAnalysis(null);
        setIsAnalysisDialogOpen(false);
      }
      toast.success('Elemento eliminado de la bandeja.');
    } catch (error) {
      toast.error('No se pudo eliminar el elemento.');
    }
  };

  const handleCardClick = (item: InboxItem) => {
    if (item.kind === 'agent_message') {
      // Construir objeto Note para el ViewNoteDialog
      const note: Note = {
        id: item.payload.id,
        title: item.payload.title || 'Mensaje del agente',
        content: item.payload.content,
        category: item.payload.category || 'General',
        created_at: item.payload.created_at,
        workspace_name: item.payload.workspace_name || undefined,
        workspace_color: item.payload.workspace_color || undefined,
      };
      setSelectedNote(note);
      setIsNoteDialogOpen(true);
    } else {
      // Construir objeto Analysis para el AnalysisDetailDialog
      const analysis: Analysis = {
        id: item.payload.id,
        type: 'insight',
        title: item.payload.title || 'Insight',
        summary: item.payload.summary,
        created_at: item.payload.created_at,
        action_suggestion: item.payload.action_suggestion,
        workspace_name: item.payload.workspace_name || null,
        workspace_color: item.payload.workspace_color || null,
        result: {
          insight_message: item.payload.summary,
          action_suggestion: item.payload.action_suggestion || '',
          confidence_score: 0,
          related_items: [],
        } as any,
      };
      setSelectedAnalysis(analysis);
      setIsAnalysisDialogOpen(true);
    }
  };

  const getItemBadgeColor = (item: InboxItem) => {
    if (item.kind === 'insight') {
      return 'bg-yellow-100 text-yellow-800 border-yellow-200';
    }
    return 'bg-blue-100 text-blue-800 border-blue-200';
  };

  const getItemBadgeLabel = (item: InboxItem) => {
    if (item.kind === 'insight') return 'Insight';
    return 'Mensaje del agente';
  };

  return (
    <div className={isEmbedded ? "space-y-6" : "p-4 sm:p-8 max-w-7xl mx-auto overflow-x-hidden space-y-6"}>
      {!isEmbedded ? (
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold flex items-center">
              <Inbox className="mr-3 h-8 w-8 text-primary" />
              Bandeja de entrada
              <Button
                variant="ghost"
                size="icon"
                className="ml-2 h-6 w-6 text-muted-foreground"
                onClick={() => setIsInfoSheetOpen(true)}
              >
                <Info className="h-4 w-4" />
              </Button>
            </h1>
          </div>
          <Button variant="outline" onClick={fetchInbox}>Actualizar</Button>
        </div>
      ) : (
        <div className="flex items-center justify-between gap-4 mb-4">
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-black uppercase tracking-widest text-muted-foreground/70">Bandeja de entrada</h2>
            <Button
              variant="ghost"
              size="icon"
              className="ml-2 h-6 w-6 text-muted-foreground"
              onClick={() => setIsInfoSheetOpen(true)}
            >
              <Info className="h-4 w-4" />
            </Button>
          </div>
          <Button variant="outline" onClick={fetchInbox}>Actualizar</Button>
        </div>
      )}

      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      ) : (
        <div className="space-y-6">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Buscar en la bandeja..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9 bg-card/50"
              />
            </div>
            <div className="flex gap-2">
              <Select value={filterType} onValueChange={(val: any) => setFilterType(val)}>
                <SelectTrigger className="w-[180px] bg-card/50">
                  <Filter className="w-4 h-4 mr-2" />
                  <SelectValue placeholder="Tipo" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos</SelectItem>
                  <SelectItem value="insight">Insights</SelectItem>
                  <SelectItem value="agent_message">Mensajes</SelectItem>
                </SelectContent>
              </Select>
              <Button
                variant="outline"
                className="bg-card/50 px-3"
                onClick={() => setSortOrder(prev => prev === 'desc' ? 'asc' : 'desc')}
                title={`Ordenar por fecha (${sortOrder === 'desc' ? 'Más recientes' : 'Más antiguos'})`}
              >
                <ArrowUpDown className="h-4 w-4 mr-2" />
                {sortOrder === 'desc' ? 'Nuevos' : 'Antiguos'}
              </Button>
            </div>
          </div>

          <Tabs defaultValue="pending" className="w-full">
            <TabsList className="mb-6 bg-card/50 border border-border/50">
              <TabsTrigger value="pending" className="data-[state=active]:bg-primary/10 data-[state=active]:text-primary rounded-md px-6">
                Pendientes
              </TabsTrigger>
              <TabsTrigger value="accepted" className="data-[state=active]:bg-green-500/10 data-[state=active]:text-green-600 rounded-md px-6">
                Aceptados
              </TabsTrigger>
            </TabsList>
            
            <TabsContent value="pending" className="mt-0 outline-none">
              {filteredAndSortedItems.filter(i => i.kind !== 'insight' || i.payload.status !== 'accepted').length === 0 ? (
                emptyState
              ) : (
                <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
                  {filteredAndSortedItems.filter(i => i.kind !== 'insight' || i.payload.status !== 'accepted').map((item) => (
                  <Card
                    key={item.id}
                    className="group relative cursor-pointer overflow-hidden border-border/40 bg-card/40 backdrop-blur-xl transition-all duration-500 hover:shadow-2xl hover:shadow-primary/5 hover:-translate-y-1"
                    onClick={() => handleCardClick(item)}
                  >
                    <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none" style={{ background: 'linear-gradient(135deg, hsl(var(--primary)/0.08) 0%, transparent 60%)' }} />
      
                    <CardHeader className="space-y-3 relative z-10">
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <div className="p-2 rounded-xl bg-background/50 border border-border/40 shadow-inner group-hover:scale-110 transition-transform duration-500">
                            {item.kind === 'agent_message' ? (
                              <Bot className="h-4 w-4 text-primary" />
                            ) : (
                              <Lightbulb className="h-4 w-4 text-yellow-500" />
                            )}
                          </div>
                          <Badge variant="outline" className={`text-[10px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-full border-none ${getItemBadgeColor(item)}`}>
                            {getItemBadgeLabel(item)}
                          </Badge>
                        </div>
                        {item.kind === 'insight' ? (
                          <div className="flex items-center gap-1">
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8 text-green-500 hover:text-green-600 hover:bg-green-50"
                              onClick={(event) => {
                                event.stopPropagation();
                                handleAcceptInsight(item);
                              }}
                              title="Aceptar y generar tarea"
                            >
                              <CheckCircle className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8 text-red-500 hover:text-red-600 hover:bg-red-50"
                              onClick={(event) => {
                                event.stopPropagation();
                                handleDelete(item);
                              }}
                              title="Rechazar insight"
                            >
                              <XCircle className="h-4 w-4" />
                            </Button>
                          </div>
                        ) : (
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8"
                            onClick={(event) => {
                              event.stopPropagation();
                              handleDelete(item);
                            }}
                            title="Eliminar mensaje"
                          >
                            <Trash2 className="h-4 w-4 text-destructive" />
                          </Button>
                        )}
                      </div>
                      <CardTitle className="text-base line-clamp-2 group-hover:text-primary transition-colors leading-tight tracking-tight">
                        {item.title}
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3 relative z-10">
                      <div className="text-sm text-muted-foreground/80 line-clamp-4 leading-relaxed font-medium">
                        <InlineMarkdownRenderer content={item.preview} />
                      </div>
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-xs text-muted-foreground/60">
                          {new Date(item.created_at).toLocaleString('es-ES')}
                        </span>
                        {item.payload.workspace_name && (
                          <Badge
                            variant="outline"
                            className="text-[10px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-full"
                            style={{
                              color: item.payload.workspace_color || 'inherit',
                              borderColor: item.payload.workspace_color ? `${item.payload.workspace_color}40` : undefined,
                              backgroundColor: item.payload.workspace_color ? `${item.payload.workspace_color}15` : undefined,
                            }}
                          >
                            {item.payload.workspace_name}
                          </Badge>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>

            <TabsContent value="accepted" className="mt-0 outline-none">
              {filteredAndSortedItems.filter(i => i.kind === 'insight' && i.payload.status === 'accepted').length === 0 ? (
                <div className="text-center py-20 border-2 border-dashed border-border/40 rounded-3xl bg-card/20">
                  <CheckSquare className="h-10 w-10 mx-auto text-green-500/50 mb-3" />
                  <h3 className="font-semibold text-green-700 dark:text-green-500">Sin insights aceptados</h3>
                  <p className="text-sm text-muted-foreground">Los insights que aceptes aparecerán aquí.</p>
                </div>
              ) : (
                <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
                  {filteredAndSortedItems.filter(i => i.kind === 'insight' && i.payload.status === 'accepted').map((item) => (
                  <Card
                    key={item.id}
                    className="group relative cursor-pointer overflow-hidden border-border/40 bg-green-50/30 dark:bg-green-950/10 backdrop-blur-xl transition-all duration-500 hover:shadow-2xl hover:shadow-green-500/5 hover:-translate-y-1"
                    onClick={() => handleCardClick(item)}
                  >
                    <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none" style={{ background: 'linear-gradient(135deg, hsl(var(--primary)/0.08) 0%, transparent 60%)' }} />
      
                    <CardHeader className="space-y-3 relative z-10">
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <div className="p-2 rounded-xl bg-background/50 border border-border/40 shadow-inner group-hover:scale-110 transition-transform duration-500">
                            <Lightbulb className="h-4 w-4 text-green-500" />
                          </div>
                          <Badge variant="outline" className={`text-[10px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-full border-none bg-green-100 text-green-800 border-green-200`}>
                            Aceptado
                          </Badge>
                        </div>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 text-red-500 hover:text-red-600 hover:bg-red-50"
                          onClick={(event) => {
                            event.stopPropagation();
                            handleDelete(item);
                          }}
                          title="Eliminar insight"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                      <CardTitle className="text-base line-clamp-2 group-hover:text-primary transition-colors leading-tight tracking-tight">
                        {item.title}
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3 relative z-10">
                      <div className="text-sm text-muted-foreground/80 line-clamp-4 leading-relaxed font-medium">
                        <InlineMarkdownRenderer content={item.preview} />
                      </div>
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-xs text-muted-foreground/60">
                          {new Date(item.created_at).toLocaleString('es-ES')}
                        </span>
                        {item.payload.workspace_name && (
                          <Badge
                            variant="outline"
                            className="text-[10px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-full"
                            style={{
                              color: item.payload.workspace_color || 'inherit',
                              borderColor: item.payload.workspace_color ? `${item.payload.workspace_color}40` : undefined,
                              backgroundColor: item.payload.workspace_color ? `${item.payload.workspace_color}15` : undefined,
                            }}
                          >
                            {item.payload.workspace_name}
                          </Badge>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>
        </Tabs>
      </div>
    )}

      {/* Dialog para mensajes del agente (mismo que ViewNoteDialog) */}
      <ViewNoteDialog
        isOpen={isNoteDialogOpen}
        onOpenChange={setIsNoteDialogOpen}
        note={selectedNote}
        onNoteUpdated={fetchInbox}
      />

      {/* Dialog para insights (mismo que AnalysisDetailDialog) */}
      <AnalysisDetailDialog
        analysis={selectedAnalysis}
        isOpen={isAnalysisDialogOpen}
        onOpenChange={setIsAnalysisDialogOpen}
        onAnalysisDeleted={(analysisId) => {
          setItems((prev) => prev.filter((entry) => entry.id !== `insight-${analysisId}`));
        }}
      />

      {/* Panel lateral de información desplegable */}
      <Sheet open={isInfoSheetOpen} onOpenChange={setIsInfoSheetOpen}>
        <SheetContent side="right" className="w-[400px] sm:w-[540px] overflow-y-auto">
          <SheetHeader className="pb-6 border-b">
            <SheetTitle className="text-2xl font-bold flex items-center gap-2">
              <Inbox className="h-6 w-6 text-primary" />
              Guía de Bandeja de Entrada
            </SheetTitle>
            <SheetDescription>
              Centro de notificaciones, recomendaciones e insights generados por tu Inteligencia Artificial.
            </SheetDescription>
          </SheetHeader>
          
          <div className="py-6 space-y-8">
            <section className="space-y-3">
              <h3 className="text-sm font-bold uppercase tracking-wider text-primary">¿Qué es la Bandeja de Entrada?</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Este panel centraliza la comunicación asíncrona de la IA contigo. Aquí recibirás análisis proactivos, alertas del estado del sistema y mensajes directos del agente basados en tu actividad y base de conocimientos.
              </p>
            </section>

            <section className="space-y-3">
              <h3 className="text-sm font-bold uppercase tracking-wider text-primary">Tipos de Elementos</h3>
              <div className="grid grid-cols-1 gap-3 text-xs">
                <div className="flex gap-3 p-3 rounded-xl bg-blue-500/5 text-blue-700 dark:text-blue-400 border border-blue-500/10">
                  <Bot className="h-5 w-5 shrink-0 text-blue-500" />
                  <div>
                    <span className="font-bold block mb-1">Mensaje del Agente</span>
                    Comunicaciones directas del agente, como respuestas a tareas completadas, alertas operativas o solicitudes de información.
                  </div>
                </div>
                <div className="flex gap-3 p-3 rounded-xl bg-yellow-500/5 text-yellow-700 dark:text-yellow-400 border border-yellow-500/10">
                  <Lightbulb className="h-5 w-5 shrink-0 text-yellow-500" />
                  <div>
                    <span className="font-bold block mb-1">Insight Proactivo</span>
                    Descubrimientos automáticos, propuestas de acción y síntesis de conocimientos derivados de tus notas, documentos e interacciones.
                  </div>
                </div>
              </div>
            </section>

            <section className="space-y-3">
              <h3 className="text-sm font-bold uppercase tracking-wider text-primary">Acciones Disponibles</h3>
              <ul className="text-xs space-y-2 text-muted-foreground list-disc pl-4 leading-relaxed">
                <li><strong>Detalle del elemento:</strong> Haz clic en cualquier tarjeta para abrir su vista detallada en un modal y ver sugerencias de acción o el contenido completo.</li>
                <li><strong>Eliminar de la bandeja:</strong> Usa el icono de papelera en la esquina de cada tarjeta para limpiar elementos que ya no necesites.</li>
                <li><strong>Actualizar:</strong> Mantén tu bandeja al día solicitando nuevas alertas de forma manual con el botón "Actualizar".</li>
              </ul>
            </section>
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
}
