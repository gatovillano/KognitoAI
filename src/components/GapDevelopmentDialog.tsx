// src/components/GapDevelopmentDialog.tsx

import React, { useState, useEffect } from 'react';
import { Button } from './ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from './ui/dialog';
import { Progress } from './ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from './ui/tooltip';
import { useToast } from '@/hooks/use-toast';
import { useWebSocketContext } from '@/contexts/WebSocketContext';
import { Zap, Loader2, Sparkles, FileText, Target, ExternalLink, Lightbulb } from 'lucide-react';

interface GapDevelopmentDialogProps {
  gapId: string;
  gapTitle: string;
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
}

interface GapDevelopmentStatus {
  status: 'pending' | 'processing' | 'completed' | 'failed';
  analysisId?: string;
  message?: string;
  report?: any;
  error?: string;
  question?: string;
}

export function GapDevelopmentDialog({ gapId, gapTitle, isOpen, onOpenChange }: GapDevelopmentDialogProps) {
  const [developmentStatus, setDevelopmentStatus] = useState<GapDevelopmentStatus | null>(null);
  const [progressValue, setProgressValue] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const { toast } = useToast();
  const { lastMessage } = useWebSocketContext();

  // Manejar mensajes de WebSocket
  useEffect(() => {
    if (lastMessage && lastMessage.type === 'gap_development_update') {
      const message = lastMessage as any;
      setDevelopmentStatus({
        status: message.status,
        analysisId: message.analysis_id,
        message: message.message,
        report: message.report,
        error: message.error,
        question: message.question
      });
      
      if (message.status === 'completed') {
        setProgressValue(100);
        toast({
          title: "Análisis completado",
          description: "La investigación profunda ha finalizado con éxito",
        });
      } else if (message.status === 'failed') {
        setProgressValue(0);
        toast({
          title: "Análisis fallido",
          description: message.error || "Error desconocido",
          variant: "destructive"
        });
      }
    }
  }, [lastMessage, toast]);

  // Manejar mensajes de WebSocket para progreso
  useEffect(() => {
    if (lastMessage && lastMessage.type === 'gap_development_update') {
      const message = lastMessage as any;
      if (message.status === 'processing' && message.progress !== undefined) {
        setProgressValue(message.progress);
      }
    }
  }, [lastMessage]);

  const handleStartDevelopment = async () => {
    setIsLoading(true);
    setProgressValue(10);
    
    try {
      const response = await fetch('/api/gap-development/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          gap_id: gapId,
          context: `Investigar brecha de conocimiento: ${gapTitle}`,
          depth: 3
        })
      });
      
      if (!response.ok) {
        throw new Error('Failed to start gap development');
      }
      
      const data = await response.json();
      setDevelopmentStatus({
        status: data.status,
        analysisId: data.analysis_id,
        message: data.message
      });
      
      toast({
        title: "Análisis iniciado",
        description: "La investigación profunda ha comenzado",
      });
      
    } catch (error) {
      console.error('Error starting gap development:', error);
      toast({
        title: "Error",
        description: "No se pudo iniciar el análisis",
        variant: "destructive"
      });
      setIsLoading(false);
    }
  };

  const getStatusBadge = () => {
    if (!developmentStatus) return null;
    
    const statusConfig = {
      pending: { text: "Pendiente", variant: "secondary" },
      processing: { text: "Procesando", variant: "default" },
      completed: { text: "Completado", variant: "success" },
      failed: { text: "Fallido", variant: "destructive" }
    };
    
    return (
      <Badge variant={statusConfig[developmentStatus.status].variant as any}>
        {statusConfig[developmentStatus.status].text}
      </Badge>
    );
  };

  const renderContent = () => {
    if (!developmentStatus) {
      return (
        <div className="text-center py-12 space-y-6">
          <div className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-4">
            <Zap className="h-8 w-8 text-primary animate-pulse" />
          </div>
          <p className="text-muted-foreground max-w-sm mx-auto">
            Preparado para iniciar una investigación profunda asistida por IA sobre esta brecha de conocimiento.
          </p>
          <Button 
            onClick={handleStartDevelopment}
            className="h-12 px-8 rounded-xl font-bold gap-2 shadow-lg shadow-primary/20"
            disabled={isLoading}
          >
            {isLoading ? <Loader2 className="h-5 w-5 animate-spin" /> : <Sparkles className="h-5 w-5" />}
            Iniciar Análisis Profundo
          </Button>
        </div>
      );
    }
    
    switch (developmentStatus.status) {
      case 'pending':
      case 'processing':
        return (
          <div className="space-y-6 p-4">
            <div className="flex justify-between items-center">
              <h3 className="text-lg font-semibold">Estado del Análisis</h3>
              {getStatusBadge()}
            </div>
            
            <div className="space-y-3">
              <p className="text-sm text-muted-foreground">
                {developmentStatus.message || "Procesando su solicitud..."}
              </p>
              <Progress value={progressValue} className="h-2" />
              <p className="text-xs text-right font-mono">
                {progressValue}%
              </p>
            </div>
            
            <div className="bg-primary/5 p-4 rounded-xl border border-primary/10">
              <h4 className="text-sm font-semibold mb-1">Información</h4>
              <p className="text-xs text-muted-foreground leading-relaxed">
                Este proceso puede tomar entre 30 y 120 segundos. Se le notificará automáticamente cuando el análisis esté completo.
              </p>
            </div>
          </div>
        );
      
      case 'completed':
        const report = developmentStatus.report || {};
        return (
          <div className="space-y-6">
            <Tabs defaultValue="summary" className="w-full">
              <TabsList className="grid w-full grid-cols-4 h-12 bg-muted/50 rounded-xl p-1">
                <TabsTrigger value="summary" className="gap-2"><FileText className="h-4 w-4" />Resumen</TabsTrigger>
                <TabsTrigger value="findings" className="gap-2"><Target className="h-4 w-4" />Hallazgos</TabsTrigger>
                <TabsTrigger value="sources" className="gap-2"><ExternalLink className="h-4 w-4" />Fuentes</TabsTrigger>
                <TabsTrigger value="recommendations" className="gap-2"><Lightbulb className="h-4 w-4" />Acciones</TabsTrigger>
              </TabsList>
              
              <div className="mt-6">
                <TabsContent value="summary">
                  <Card className="border-0 shadow-none bg-transparent">
                    <CardContent className="p-0">
                      <p className="text-lg leading-relaxed">
                        {report.summary || "No hay resumen disponible."}
                      </p>
                    </CardContent>
                  </Card>
                </TabsContent>
                
                <TabsContent value="findings">
                  <div className="space-y-4">
                    {report.findings?.map((finding: string, index: number) => (
                      <div key={index} className="p-4 rounded-xl bg-card border border-border/50 flex gap-4">
                        <span className="flex-shrink-0 w-6 h-6 rounded-full bg-primary/10 text-primary flex items-center justify-center text-xs font-bold">
                          {index + 1}
                        </span>
                        <p className="text-sm leading-relaxed">{finding}</p>
                      </div>
                    )) || <p className="text-muted-foreground text-center py-8">No hay hallazgos disponibles.</p>}
                  </div>
                </TabsContent>
                
                <TabsContent value="sources">
                  <div className="space-y-3">
                    {report.sources?.map((source: any, index: number) => (
                      <a 
                        key={index} 
                        href={source.url} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="flex items-center justify-between p-4 rounded-xl bg-card border border-border/50 hover:bg-accent/50 transition-all"
                      >
                        <span className="text-sm font-medium truncate max-w-[250px]">{source.url}</span>
                        <Badge variant="secondary">Relevancia: {source.relevance}/10</Badge>
                      </a>
                    )) || <p className="text-muted-foreground text-center py-8">No hay fuentes disponibles.</p>}
                  </div>
                </TabsContent>
                
                <TabsContent value="recommendations">
                  <div className="space-y-4">
                    {report.recommendations?.map((rec: string, index: number) => (
                      <div key={index} className="p-4 rounded-xl bg-green-500/5 border border-green-500/20 flex gap-4">
                        <Sparkles className="h-5 w-5 text-green-600 flex-shrink-0" />
                        <p className="text-sm text-green-800 dark:text-green-300 leading-relaxed">{rec}</p>
                      </div>
                    )) || <p className="text-muted-foreground text-center py-8">No hay recomendaciones disponibles.</p>}
                  </div>
                </TabsContent>
              </div>
            </Tabs>
          </div>
        );
      
      case 'failed':
        return (
          <div className="p-8 text-center space-y-4">
            <div className="w-16 h-16 bg-destructive/10 rounded-full flex items-center justify-center mx-auto">
              <Zap className="h-8 w-8 text-destructive" />
            </div>
            <div>
              <h4 className="font-bold text-lg">Error en el Análisis</h4>
              <p className="text-muted-foreground">
                {developmentStatus.error || "Ocurrió un error desconocido"}
              </p>
            </div>
            <Button 
              onClick={() => setDevelopmentStatus(null)}
              variant="outline"
              className="rounded-xl"
            >
              Intentar de nuevo
            </Button>
          </div>
        );
      
      default:
        return null;
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto rounded-3xl backdrop-blur-2xl bg-card/95 border-border/50 shadow-2xl">
        <DialogHeader className="p-4">
          <div className="flex items-center gap-2 mb-2">
            <Badge variant="secondary" className="rounded-full px-3 text-[10px] font-bold tracking-widest uppercase">Investigación</Badge>
          </div>
          <DialogTitle className="text-3xl font-black tracking-tight leading-tight">
            {gapTitle}
          </DialogTitle>
          <DialogDescription className="text-base">
            Desarrollo profundo de brecha de conocimiento asistido por IA.
          </DialogDescription>
        </DialogHeader>
        
        <div className="py-2">
          {renderContent()}
        </div>
        
        <DialogFooter className="p-4 border-t border-border/10">
          <Button 
            onClick={() => onOpenChange(false)}
            variant="ghost"
            className="rounded-xl"
            disabled={isLoading && developmentStatus?.status === 'processing'}
          >
            Cerrar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}