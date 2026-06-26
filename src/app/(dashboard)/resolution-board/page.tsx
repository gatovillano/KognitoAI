'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import apiClient from '@/lib/api';
import { toast } from 'sonner';
import { 
  ClipboardList, 
  CheckCircle2, 
  AlertTriangle, 
  Clock, 
  ArrowRight, 
  ShieldAlert, 
  Sparkles, 
  RefreshCcw, 
  CalendarRange,
  XCircle,
  TrendingUp,
  RotateCcw
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Analysis } from '@/lib/models';
import { AnalysisDetailDialog } from '@/app/(dashboard)/analysis/analysis-detail-dialog';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogFooter,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';

interface ResolutionTask {
  id: string;
  description: string;
  is_completed: boolean;
  start_date: string | null;
  end_date: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

interface ResolutionInsight {
  id: string;
  type: string;
  title: string;
  insight_message: string;
  confidence_score: number;
  action_suggestion: string;
  created_at: string;
  related_items: any[];
}

export default function ResolutionBoardPage() {
  const [tasks, setTasks] = useState<ResolutionTask[]>([]);
  const [insights, setInsights] = useState<ResolutionInsight[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [actionInProgress, setActionInProgress] = useState<string | null>(null);
  const [selectedAnalysis, setSelectedAnalysis] = useState<Analysis | null>(null);
  
  // States for cancellation justification dialog
  const [isCancelDialogOpen, setIsCancelDialogOpen] = useState(false);
  const [taskToCancel, setTaskToCancel] = useState<string | null>(null);
  const [cancellationJustification, setCancellationJustification] = useState('');

  // State for real-time countdown countdown
  const [now, setNow] = useState(new Date());

  const handleViewInsightDetails = (insight: ResolutionInsight) => {
    const mapped: Analysis = {
      id: insight.id,
      type: 'proactive_insight',
      title: insight.title,
      summary: insight.insight_message,
      confidence_score: insight.confidence_score,
      action_suggestion: insight.action_suggestion,
      related_items: insight.related_items,
      created_at: insight.created_at,
      result: {
        type: insight.type,
        title: insight.title,
        insight_message: insight.insight_message,
        confidence_score: insight.confidence_score,
        action_suggestion: insight.action_suggestion,
        related_items: insight.related_items,
      }
    };
    setSelectedAnalysis(mapped);
  };

  const fetchBoardData = async () => {
    setIsLoading(true);
    try {
      const response = await apiClient.get('/api/resolution-board');
      setTasks(response.data.tasks || []);
      setInsights(response.data.insights || []);
    } catch (error) {
      console.error('Error fetching resolution board data:', error);
      toast.error('No se pudo cargar el Tablero de Resolución.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchBoardData();
    
    // Tick current time every 30 seconds for real-time countdown
    const timerId = setInterval(() => {
      setNow(new Date());
    }, 30000);
    return () => clearInterval(timerId);
  }, []);

  const handleCompleteTask = async (taskId: string) => {
    setActionInProgress(taskId);
    try {
      await apiClient.put(`/api/tasks/${taskId}`, {
        is_completed: true,
        status: 'Completada'
      });
      toast.success('¡Tarea completada con éxito!');
      await fetchBoardData();
    } catch (error) {
      console.error('Error completing task:', error);
      toast.error('No se pudo completar la tarea.');
    } finally {
      setActionInProgress(null);
    }
  };

  const handlePostponeTask = async (taskId: string) => {
    setActionInProgress(taskId);
    try {
      await apiClient.post(`/api/tasks/${taskId}/postpone`);
      toast.success('Plazo extendido por 48 horas.');
      await fetchBoardData();
    } catch (error) {
      console.error('Error postponing task:', error);
      toast.error('No se pudo postergar la tarea.');
    } finally {
      setActionInProgress(null);
    }
  };

  const handleCancelTaskClick = (taskId: string) => {
    setTaskToCancel(taskId);
    setCancellationJustification('');
    setIsCancelDialogOpen(true);
  };

  const handleConfirmCancelTask = async () => {
    if (!taskToCancel) return;
    if (!cancellationJustification.trim()) {
      toast.error('Por favor, ingresa una justificación para la cancelación.');
      return;
    }
    setActionInProgress(taskToCancel);
    setIsCancelDialogOpen(false);
    try {
      await apiClient.post(`/api/tasks/${taskToCancel}/cancel`, {
        justification: cancellationJustification
      });
      toast.success('Tarea cancelada explícitamente.');
      await fetchBoardData();
    } catch (error) {
      console.error('Error cancelling task:', error);
      toast.error('No se pudo cancelar la tarea.');
    } finally {
      setActionInProgress(null);
      setTaskToCancel(null);
    }
  };

  const getStatusBadge = (task: ResolutionTask) => {
    switch (task.status) {
      case 'Completada':
        return <Badge className="bg-green-500/10 text-green-600 dark:text-green-400 border border-green-500/20">Completada</Badge>;
      case 'Escalada':
        return <Badge className="bg-red-500/10 text-red-600 dark:text-red-400 border border-red-500/20 animate-pulse">Escalada (Expirada)</Badge>;
      case 'Cancelada':
        return <Badge className="bg-muted text-muted-foreground border">Cancelada</Badge>;
      case 'Postergada':
        return <Badge className="bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20">Postergada</Badge>;
      default:
        return <Badge className="bg-primary/10 text-primary border border-primary/20">Pendiente</Badge>;
    }
  };

  const getTimeRemaining = (endDateStr: string | null) => {
    if (!endDateStr) return null;
    const end = new Date(endDateStr);
    const diffMs = end.getTime() - now.getTime();
    
    if (diffMs < 0) {
      const hoursAgo = Math.abs(Math.floor(diffMs / (1000 * 60 * 60)));
      return { expired: true, text: `Expiró hace ${hoursAgo}h` };
    }
    
    const hoursLeft = Math.floor(diffMs / (1000 * 60 * 60));
    if (hoursLeft === 0) {
      const minsLeft = Math.floor(diffMs / (1000 * 60));
      return { expired: false, text: `Termina en ${minsLeft}m` };
    }
    return { expired: false, text: `Faltan ${hoursLeft}h` };
  };

  if (isLoading) {
    return (
      <div className="flex h-[80vh] items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <RefreshCcw className="h-10 w-10 animate-spin text-primary" />
          <p className="text-muted-foreground animate-pulse">Cargando Tablero de Resolución...</p>
        </div>
      </div>
    );
  }

  const activeTasks = tasks.filter(t => !t.is_completed && t.status !== 'Escalada');
  const escalatedTasks = tasks.filter(t => t.status === 'Escalada');
  const completedTasks = tasks.filter(t => t.is_completed || t.status === 'Cancelada');

  return (
    <div className="p-4 sm:p-8 max-w-7xl mx-auto space-y-8 animate-in fade-in duration-700">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="h-12 w-12 rounded-2xl bg-primary/10 flex items-center justify-center shadow-inner">
            <ClipboardList className="h-6 w-6 text-primary" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Tablero de Resolución</h1>
            <p className="text-muted-foreground text-sm">
              Convirtiendo insights recurrentes en acciones concretas con plazos estrictos de 48 horas.
            </p>
          </div>
        </div>
        <Button onClick={fetchBoardData} variant="outline" size="sm" className="gap-2">
          <RefreshCcw className="h-4 w-4" /> Recargar
        </Button>
      </div>

      {/* Stats Summary */}
      <div className="grid gap-4 grid-cols-2 md:grid-cols-4">
        <Card className="border-none bg-card/40 backdrop-blur-md">
          <CardContent className="p-6">
            <div className="flex justify-between items-start">
              <span className="text-sm font-medium text-muted-foreground">Total Tareas</span>
              <ClipboardList className="h-4 w-4 text-primary" />
            </div>
            <div className="mt-2 text-3xl font-bold">{tasks.length}</div>
          </CardContent>
        </Card>

        <Card className="border-none bg-card/40 backdrop-blur-md">
          <CardContent className="p-6">
            <div className="flex justify-between items-start">
              <span className="text-sm font-medium text-muted-foreground">Pendientes</span>
              <Clock className="h-4 w-4 text-blue-500" />
            </div>
            <div className="mt-2 text-3xl font-bold text-blue-500">{activeTasks.length}</div>
          </CardContent>
        </Card>

        <Card className="border-none bg-card/40 backdrop-blur-md border border-red-500/10">
          <CardContent className="p-6">
            <div className="flex justify-between items-start">
              <span className="text-sm font-medium text-muted-foreground">Escaladas</span>
              <AlertTriangle className="h-4 w-4 text-red-500 animate-pulse" />
            </div>
            <div className="mt-2 text-3xl font-bold text-red-500">{escalatedTasks.length}</div>
          </CardContent>
        </Card>

        <Card className="border-none bg-card/40 backdrop-blur-md">
          <CardContent className="p-6">
            <div className="flex justify-between items-start">
              <span className="text-sm font-medium text-muted-foreground">Resueltas / Cerradas</span>
              <CheckCircle2 className="h-4 w-4 text-green-500" />
            </div>
            <div className="mt-2 text-3xl font-bold text-green-500">{completedTasks.length}</div>
          </CardContent>
        </Card>
      </div>

      {/* Main Grid */}
      <div className="grid gap-8 lg:grid-cols-3">
        
        {/* Column 1 & 2: Tareas de Resolución */}
        <div className="lg:col-span-2 space-y-6">
          
          {/* Escalated Tasks Section */}
          {escalatedTasks.length > 0 && (
            <Card className="border-2 border-red-500/20 bg-red-500/5 backdrop-blur-md shadow-lg overflow-hidden">
              <CardHeader className="bg-red-500/10 border-b border-red-500/10">
                <CardTitle className="text-red-500 flex items-center gap-2 text-lg">
                  <ShieldAlert className="h-5 w-5 animate-bounce" />
                  Decisión Requerida: Tareas Expiradas (Escaladas)
                </CardTitle>
                <CardDescription className="text-red-500/70">
                  Estas tareas superaron el plazo límite de 48 horas sin ser resueltas. Debes decidir si deseas postergar el vencimiento 48 horas adicionales o cancelar la tarea definitivamente.
                </CardDescription>
              </CardHeader>
              <CardContent className="divide-y divide-red-500/10 p-0">
                <AnimatePresence>
                  {escalatedTasks.map((task) => (
                    <motion.div
                      key={task.id}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      className="p-6 space-y-4"
                    >
                      <div className="flex justify-between items-start gap-4">
                        <div className="space-y-1">
                          <p className="text-sm font-semibold text-foreground">{task.description}</p>
                          <div className="flex items-center gap-2 text-xs text-red-400">
                            <Clock className="h-3.5 w-3.5" />
                            <span>Venció el: {task.end_date ? new Date(task.end_date).toLocaleString() : 'N/A'}</span>
                          </div>
                        </div>
                        {getStatusBadge(task)}
                      </div>
                      
                      <div className="flex flex-wrap gap-2">
                        <Button 
                          onClick={() => handlePostponeTask(task.id)}
                          disabled={actionInProgress === task.id}
                          variant="outline" 
                          size="sm" 
                          className="border-amber-500/30 text-amber-600 hover:bg-amber-500/10"
                        >
                          <RotateCcw className="mr-1.5 h-3.5 w-3.5" /> Postergar (48h)
                        </Button>
                        <Button 
                          onClick={() => handleCancelTaskClick(task.id)}
                          disabled={actionInProgress === task.id}
                          variant="outline" 
                          size="sm" 
                          className="border-red-500/30 text-red-600 hover:bg-red-500/10"
                        >
                          <XCircle className="mr-1.5 h-3.5 w-3.5" /> Cancelar Tarea
                        </Button>
                      </div>
                    </motion.div>
                  ))}
                </AnimatePresence>
              </CardContent>
            </Card>
          )}

          {/* Pending Resolution Tasks */}
          <Card className="border-none bg-card/40 backdrop-blur-md shadow-lg">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Clock className="h-5 w-5 text-primary" />
                Tareas Activas en Resolución (Plazo 48h)
              </CardTitle>
              <CardDescription>
                Tareas creadas automáticamente a partir de insights detectados más de dos veces.
              </CardDescription>
            </CardHeader>
            <CardContent className="p-0 divide-y divide-border/40">
              {activeTasks.length > 0 ? (
                <div className="divide-y divide-border/40">
                  {activeTasks.map((task) => {
                    const timer = getTimeRemaining(task.end_date);
                    return (
                      <div key={task.id} className="p-6 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 hover:bg-muted/10 transition-colors">
                        <div className="space-y-1 flex-1">
                          <p className="text-sm font-medium text-foreground">{task.description}</p>
                          <div className="flex flex-wrap items-center gap-4 text-xs text-muted-foreground">
                            {timer && (
                              <span className={`flex items-center gap-1 font-semibold ${timer.expired ? 'text-red-500' : 'text-primary'}`}>
                                <Clock className="h-3.5 w-3.5" />
                                {timer.text}
                              </span>
                            )}
                            <span>Iniciada: {task.start_date ? new Date(task.start_date).toLocaleDateString() : 'N/A'}</span>
                          </div>
                        </div>
                        
                        <div className="flex items-center gap-3 w-full sm:w-auto justify-between sm:justify-end">
                          {getStatusBadge(task)}
                          <Button 
                            onClick={() => handleCompleteTask(task.id)}
                            disabled={actionInProgress === task.id}
                            size="sm"
                            className="bg-green-600 hover:bg-green-700 text-white font-medium"
                          >
                            <CheckCircle2 className="mr-1.5 h-3.5 w-3.5" /> Completar
                          </Button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="p-12 text-center text-muted-foreground">
                  <CheckCircle2 className="h-12 w-12 mx-auto mb-3 text-green-500/40" />
                  <p className="font-semibold">¡Todo al día!</p>
                  <p className="text-sm">No tienes tareas de resolución pendientes en este momento.</p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Historial / Cerradas */}
          <Card className="border-none bg-card/40 backdrop-blur-md shadow-lg">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2 text-muted-foreground">
                <CheckCircle2 className="h-5 w-5 text-green-500" />
                Historial de Resoluciones y Cierres
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              {completedTasks.length > 0 ? (
                <div className="divide-y divide-border/30 max-h-[300px] overflow-y-auto custom-scrollbar">
                  {completedTasks.map((task) => (
                    <div key={task.id} className="p-4 flex justify-between items-center gap-4 hover:bg-muted/5 transition-colors">
                      <div className="space-y-0.5">
                        <p className="text-xs font-medium text-muted-foreground line-clamp-1">{task.description}</p>
                        <p className="text-[10px] text-muted-foreground">Actualizado: {new Date(task.updated_at).toLocaleString()}</p>
                      </div>
                      {getStatusBadge(task)}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="p-8 text-center text-xs text-muted-foreground">
                  No hay registros en el historial de cierres.
                </div>
              )}
            </CardContent>
          </Card>

        </div>

        {/* Column 3: Detección de Recurrencia */}
        <div className="space-y-6">
          <Card className="border-none bg-card/40 backdrop-blur-md shadow-lg overflow-hidden relative group">
            <div className="absolute inset-0 bg-gradient-to-br from-primary/10 to-transparent pointer-events-none opacity-50" />
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-primary animate-pulse" />
                Detección de Recurrencia
              </CardTitle>
              <CardDescription>
                Monitoreo autónomo del heartbeat de KognitoAI.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 relative">
              <div className="p-4 rounded-xl bg-background/60 border border-primary/10 space-y-2">
                <div className="flex items-center gap-2 text-xs font-semibold text-primary">
                  <TrendingUp className="h-4 w-4" />
                  REGLA DE CONVERSIÓN ACTIVA
                </div>
                <p className="text-xs text-muted-foreground">
                  Si un patrón o insight es identificado <strong>más de 2 veces</strong> por el agente autónomo, se genera automáticamente una tarea obligatoria en el sistema.
                </p>
              </div>

              <div className="p-4 rounded-xl bg-background/60 border border-amber-500/10 space-y-2">
                <div className="flex items-center gap-2 text-xs font-semibold text-amber-500">
                  <AlertTriangle className="h-4 w-4" />
                  MECANISMO DE ESCALACIÓN
                </div>
                <p className="text-xs text-muted-foreground">
                  Las tareas no completadas tras <strong>48 horas</strong> pasan al estado de Escalación. El sistema exige postergación explícita o cancelación para evitar bucles interminables.
                </p>
              </div>
            </CardContent>
          </Card>
        </div>

      </div>

      {/* Alertas de Escalación Proactivas (Panel de Tarjetas en 3 Columnas) */}
      <Card className="border-none bg-card/40 backdrop-blur-md shadow-lg rounded-[2rem]">
        <CardHeader className="pb-4">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-2xl bg-primary/10 flex items-center justify-center shadow-inner">
              <ShieldAlert className="h-5 w-5 text-primary" />
            </div>
            <div>
              <CardTitle className="text-xl font-bold tracking-tight">Alertas de Escalación Proactivas</CardTitle>
              <CardDescription>
                Alertas e incidentes registrados por el sistema.
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {insights.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              <AnimatePresence mode="popLayout">
                {insights.map((insight, index) => (
                  <motion.div
                    key={insight.id}
                    layout
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.95 }}
                    transition={{ duration: 0.3, delay: index * 0.05 }}
                  >
                    <Card 
                      className="group relative cursor-pointer overflow-hidden border-border/40 bg-card/40 backdrop-blur-xl hover:bg-card/60 transition-all duration-500 h-[280px] flex flex-col shadow-sm hover:shadow-2xl hover:shadow-primary/5 hover:-translate-y-1"
                      onClick={() => handleViewInsightDetails(insight)}
                    >
                      {/* Efecto de reflejo en el hover */}
                      <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none" style={{ background: 'linear-gradient(135deg, hsl(var(--primary)/0.08) 0%, transparent 60%)' }} />

                      <CardHeader className="pb-3 relative z-10">
                        <div className="flex items-center justify-between mb-3">
                          <div className="p-3 rounded-2xl bg-background/50 border border-border/40 shadow-inner group-hover:scale-110 transition-transform duration-500 flex-shrink-0">
                            <AlertTriangle className="h-5 w-5 text-red-500 dark:text-red-400" />
                          </div>
                          <Badge variant="outline" className="text-[10px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-full border-none bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400">
                            Alerta
                          </Badge>
                        </div>
                        <CardTitle className="text-base font-bold line-clamp-2 group-hover:text-primary transition-colors leading-tight tracking-tight">
                          {insight.title}
                        </CardTitle>
                      </CardHeader>

                      <CardContent className="pt-0 flex-grow overflow-hidden relative z-10">
                        <p className="text-xs text-muted-foreground/80 line-clamp-4 leading-relaxed font-medium">
                          {insight.insight_message}
                        </p>
                      </CardContent>

                      <CardFooter className="flex flex-col items-stretch gap-2 pt-3 mt-auto border-t border-border/20 relative z-10">
                        {insight.action_suggestion && (
                          <div className="text-[11px] text-primary font-semibold line-clamp-2">
                            Sugerencia: <span className="text-muted-foreground font-medium">{insight.action_suggestion}</span>
                          </div>
                        )}
                        <div className="flex justify-between items-center text-[10px] font-bold text-muted-foreground/60 uppercase tracking-widest pt-1 border-t border-border/10">
                          <div className="flex items-center gap-2">
                            <div className="w-1.5 h-1.5 rounded-full bg-primary/40" />
                            {new Date(insight.created_at).toLocaleDateString('es-ES', {
                              year: 'numeric', month: 'short', day: 'numeric'
                            })}
                          </div>
                        </div>
                      </CardFooter>
                    </Card>
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          ) : (
            <div className="py-12 text-center text-muted-foreground border-2 border-dashed border-border/40 rounded-2xl bg-card/20 backdrop-blur-sm">
              <ShieldAlert className="h-10 w-10 mx-auto mb-3 text-muted-foreground/40" />
              <p className="font-semibold">Sin alertas recientes</p>
              <p className="text-xs text-muted-foreground">No hay alertas proactivas emitidas recientemente.</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Diálogo de Detalles del Insight */}
      <AnalysisDetailDialog
        analysis={selectedAnalysis}
        isOpen={!!selectedAnalysis}
        onOpenChange={(open) => !open && setSelectedAnalysis(null)}
      />

    </div>
  );
}
