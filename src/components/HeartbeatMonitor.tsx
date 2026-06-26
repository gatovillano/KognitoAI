'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Activity, Clock, Play, ChevronRight, RefreshCw, AlertCircle, CheckCircle2 } from 'lucide-react';
import { toast } from 'sonner';
import apiClient from '@/lib/api';
import { motion, AnimatePresence } from 'framer-motion';
import { MarkdownRenderer } from '@/components/MarkdownRenderer';

interface HeartbeatThread {
  id: string;
  title: string;
  platform: string;
  created_at: string;
}

interface ChatMessage {
  id?: string;
  text: string;
  sender: 'user' | 'ai';
  created_at?: string;
}

export function HeartbeatMonitor() {
  const [runs, setRuns] = useState<HeartbeatThread[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isTriggering, setIsTriggering] = useState(false);
  const [selectedRun, setSelectedRun] = useState<HeartbeatThread | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);

  const fetchRuns = async () => {
    try {
      const response = await apiClient.get('/api/threads/system?limit=10');
      if (response.data && response.data.threads) {
        setRuns(response.data.threads);
      }
    } catch (error) {
      console.error('Error fetching system threads:', error);
      toast.error('No se pudieron cargar las ejecuciones del heartbeat.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchRuns();
  }, []);

  const fetchMessagesForRun = async (threadId: string) => {
    setIsLoadingMessages(true);
    try {
      const response = await apiClient.get(`/api/threads/${threadId}/messages?limit=50`);
      if (response.data && response.data.messages) {
        // Map Langchain messages to our simplified ChatMessage format
        const mapped = response.data.messages.map((m: any) => ({
          id: m.id,
          text: m.text,
          sender: m.sender === 'human' ? 'user' : 'ai',
          created_at: m.created_at,
        }));
        // Sort by created_at ascending to show flow
        mapped.reverse();
        setMessages(mapped);
      } else {
        setMessages([]);
      }
    } catch (error) {
      console.error('Error fetching messages for system thread:', error);
      toast.error('No se pudieron obtener los detalles de la ejecución.');
    } finally {
      setIsLoadingMessages(false);
    }
  };

  const handleRunClick = (run: HeartbeatThread) => {
    setSelectedRun(run);
    fetchMessagesForRun(run.id);
  };

  const handleTriggerHeartbeat = async () => {
    setIsTriggering(true);
    toast.info('Iniciando el heartbeat autónomo en segundo plano...');
    try {
      const response = await apiClient.post('/api/scheduled-tools/autonomous-heartbeat/trigger');
      toast.success('¡Heartbeat autónomo completado con éxito!');
      await fetchRuns();
      // If a run was created, try to open the latest one
      if (response.data && response.data.status === 'success') {
        const latestResponse = await apiClient.get('/api/threads/system?limit=1');
        if (latestResponse.data && latestResponse.data.threads && latestResponse.data.threads.length > 0) {
          handleRunClick(latestResponse.data.threads[0]);
        }
      }
    } catch (error: any) {
      console.error('Error triggering heartbeat:', error);
      toast.error(error.response?.data?.detail || 'Ocurrió un error al iniciar el heartbeat autónomo.');
    } finally {
      setIsTriggering(false);
    }
  };

  const formatRelativeTime = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return 'Hace unos instantes';
    if (diffMins < 60) return `Hace ${diffMins} min`;
    if (diffHours < 24) return `Hace ${diffHours} h`;
    return `Hace ${diffDays} d`;
  };

  return (
    <Card className="border-none shadow-lg bg-gradient-to-br from-card to-card/50 backdrop-blur-sm h-full flex flex-col">
      <CardHeader className="pb-3 flex flex-row items-center justify-between space-y-0">
        <div>
          <CardTitle className="flex items-center gap-2 text-lg">
            <Activity className="h-5 w-5 text-primary animate-pulse" />
            Monitoreo de Heartbeats
          </CardTitle>
          <CardDescription>
            Visualiza la ejecución del sistema autónomo y el hilo de chat del heartbeat.
          </CardDescription>
        </div>
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="outline"
            className="h-8 bg-background/50 border-muted/40 hover:bg-muted/30"
            onClick={fetchRuns}
            disabled={isLoading}
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          </Button>
          <Button
            size="sm"
            className="h-8 gap-1.5 font-medium shadow-md hover:shadow-lg transition-all"
            onClick={handleTriggerHeartbeat}
            disabled={isTriggering}
          >
            {isTriggering ? (
              <>
                <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                Ejecutando...
              </>
            ) : (
              <>
                <Play className="h-3 w-3 fill-current" />
                Ejecutar Heartbeat
              </>
            )}
          </Button>
        </div>
      </CardHeader>
      
      <CardContent className="flex-1 overflow-auto max-h-[420px] scrollbar-thin">
        {isLoading ? (
          <div className="flex h-40 items-center justify-center">
            <div className="flex flex-col items-center gap-2">
              <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
              <p className="text-xs text-muted-foreground">Cargando ejecuciones...</p>
            </div>
          </div>
        ) : runs.length > 0 ? (
          <div className="space-y-2.5">
            {runs.map((run) => (
              <div
                key={run.id}
                onClick={() => handleRunClick(run)}
                className="flex items-center justify-between p-3.5 rounded-2xl bg-background/40 border border-muted/20 hover:border-primary/20 hover:bg-primary/5 transition-all cursor-pointer group"
              >
                <div className="flex items-center gap-3.5 min-w-0">
                  <div className="h-9 w-9 rounded-xl bg-primary/10 flex items-center justify-center text-primary group-hover:bg-primary/20 transition-all shadow-inner">
                    <Activity className="h-4.5 w-4.5" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-semibold truncate text-foreground group-hover:text-primary transition-colors">
                      {run.title.split(' - ')[0] || 'Heartbeat autónomo'}
                    </p>
                    <div className="flex items-center gap-2.5 mt-0.5 text-xs text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {new Date(run.created_at).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}
                      </span>
                      <span>•</span>
                      <span>{formatRelativeTime(run.created_at)}</span>
                    </div>
                  </div>
                </div>
                
                <div className="flex items-center gap-2">
                  <Badge variant="secondary" className="bg-primary/10 text-primary border-none text-[10px] px-2 py-0.5 rounded-full font-medium">
                    {run.platform.toUpperCase()}
                  </Badge>
                  <ChevronRight className="h-4.5 w-4.5 text-muted-foreground opacity-40 group-hover:opacity-100 group-hover:translate-x-0.5 transition-all" />
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="h-40 flex flex-col items-center justify-center text-muted-foreground">
            <Activity className="h-10 w-10 mb-2.5 opacity-20" />
            <p className="text-sm">No se han registrado ejecuciones de heartbeat.</p>
          </div>
        )}
      </CardContent>

      <Dialog open={!!selectedRun} onOpenChange={(open) => !open && setSelectedRun(null)}>
        <DialogContent className="max-w-3xl h-[80vh] flex flex-col rounded-3xl backdrop-blur-xl bg-card/95 border-0 shadow-2xl overflow-hidden p-6">
          <DialogHeader className="pb-3 border-b border-muted/20">
            <DialogTitle className="flex items-center gap-2 text-xl">
              <Activity className="h-5 w-5 text-primary" />
              <span>Hilo de Chat del Heartbeat</span>
            </DialogTitle>
            <DialogDescription className="flex items-center gap-2 mt-1">
              <span>Ejecución: {selectedRun?.id.substring(0, 8)}...</span>
              <span>•</span>
              <span>
                {selectedRun && new Date(selectedRun.created_at).toLocaleString('es-ES')}
              </span>
            </DialogDescription>
          </DialogHeader>

          <div className="flex-1 overflow-y-auto py-4 space-y-4 pr-1 scrollbar-thin">
            {isLoadingMessages ? (
              <div className="h-full flex items-center justify-center">
                <div className="flex flex-col items-center gap-2">
                  <RefreshCw className="h-8 w-8 animate-spin text-primary" />
                  <p className="text-sm text-muted-foreground">Recuperando traza de ejecución...</p>
                </div>
              </div>
            ) : messages.length > 0 ? (
              messages.map((msg, index) => (
                <div
                  key={index}
                  className={`flex flex-col max-w-[90%] p-4 rounded-2xl ${
                    msg.sender === 'user'
                      ? 'ml-auto bg-primary text-primary-foreground rounded-tr-none'
                      : 'bg-muted/40 text-foreground rounded-tl-none border border-muted/20'
                  } shadow-sm animate-in fade-in slide-in-from-bottom-2 duration-300`}
                >
                  <div className="flex items-center gap-2 mb-1.5 text-[10px] opacity-75 font-semibold uppercase tracking-wider">
                    {msg.sender === 'user' ? 'Solicitud / Disparador' : 'Resultado / Proceso'}
                    {msg.created_at && (
                      <span className="normal-case opacity-80 font-normal">
                        - {new Date(msg.created_at).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                      </span>
                    )}
                  </div>
                  <div className={`text-sm leading-relaxed prose dark:prose-invert max-w-none ${msg.sender === 'user' ? 'text-primary-foreground' : ''}`}>
                    <MarkdownRenderer content={msg.text} />
                  </div>
                </div>
              ))
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-muted-foreground">
                <AlertCircle className="h-10 w-10 mb-2 opacity-20" />
                <p className="text-sm">Esta ejecución no contiene mensajes guardados.</p>
              </div>
            )}
          </div>

          <div className="pt-3 border-t border-muted/20 flex justify-end">
            <Button
              variant="outline"
              className="rounded-xl"
              onClick={() => setSelectedRun(null)}
            >
              Cerrar Detalle
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </Card>
  );
}
