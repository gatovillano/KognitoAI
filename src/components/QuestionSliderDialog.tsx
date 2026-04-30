'use client';

import { useState, useEffect, useRef } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogTrigger } from '@/components/ui/dialog';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { ChevronLeft, ChevronRight, Zap, Loader2, Sparkles, FileText, Target, Lightbulb, ExternalLink, Send, MessageSquareQuote, File as FileIcon, Notebook, Network, Folder } from 'lucide-react';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { useToast } from '@/hooks/use-toast';
import { useWebSocketContext } from '@/contexts/WebSocketContext';
import apiClient from '@/lib/api'; // Corregimos la importación de apiClient
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { MarkdownRenderer } from '@/components/MarkdownRenderer';
import DeepResearchVisualizer from '@/components/DeepResearchVisualizer';

export interface Source {
  id: number | string;
  title: string;
  url: string;
  snippet: string;
  type: 'web' | 'document' | 'memory' | 'code' | 'database' | 'note' | 'graph';
  metadata?: Record<string, any>;
  name?: string;
}

export interface ContentPart {
  type: 'text' | 'citation';
  content?: string;
  source?: Source;
  citationNumber?: number;
}

export interface QuestionSliderDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  questions: any[];
  title: string;
  analysisId?: string;
  onDevelopClick?: (question: string) => void;
}

interface GapDevelopmentStatus {
  status: 'pending' | 'processing' | 'completed' | 'failed';
  analysisId?: string;
  message?: string;
  report?: any;
  error?: string;
  question?: string;
}

/**
 * Normaliza los hallazgos a un array de strings.
 * El backend devuelve 'findings' como string, pero el frontend espera un array.
 */
const normalizeFindings = (findings: any): string[] => {
  if (!findings) return [];
  if (Array.isArray(findings)) return findings;
  if (typeof findings === 'string') {
    // Dividir por párrafos (doble salto de línea) y filtrar vacíos
    return findings
      .split(/\n\s*\n/)
      .map(f => f.trim())
      .filter(f => f.length > 0);
  }
  return [];
};

export const SourceButton: React.FC<{ source: Source; citationNumber: number }> = ({ source, citationNumber }) => {
  const getIcon = () => {
    switch (source.type) {
      case 'web': return <ExternalLink className="h-3 w-3 mr-1" />;
      case 'document': return <FileIcon className="h-3 w-3 mr-1" />;
      case 'note': return <Notebook className="h-3 w-3 mr-1" />;
      case 'graph': return <Network className="h-3 w-3 mr-1" />;
      default: return <FileIcon className="h-3 w-3 mr-1" />;
    }
  };

  return (
    <Dialog>
      <DialogTrigger asChild>
        <button className="inline-flex items-center text-xl bg-primary/10 text-primary font-bold rounded-full px-2 mx-0.5 focus:outline-none focus:ring-2 focus:ring-primary/50 leading-normal flex-shrink-0 hover:bg-primary/20 transition-colors">
          {getIcon()}
          {citationNumber}
        </button>
      </DialogTrigger>
      <DialogContent className="w-80 text-sm">
        <div className="flex items-center gap-2 mb-2">
          {getIcon()}
          <div className="font-bold whitespace-normal break-words">{source.title}</div>
        </div>
        <div className="text-xs text-muted-foreground mb-2 capitalize">
          Tipo: {source.type}
        </div>
        <p className="text-muted-foreground">
          {source.snippet}
        </p>
        {source.url && (
          <div className="text-xs text-muted-foreground mt-2 break-all">
            Fuente: {source.url}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};

const processMessageWithCitations = (text: string, allSources: Source[] | undefined): { contentParts: ContentPart[]; citedSources: Source[]; uncitedSources: Source[] } => {
  if (!allSources || allSources.length === 0) {
    return { contentParts: [{ type: 'text', content: text }], citedSources: [], uncitedSources: [] };
  }

  const contentParts: ContentPart[] = [];
  let lastIndex = 0;
  const citedSourceIds = new Set<string | number>();
  const citationRegex = /\[(\d+)\]/g;
  let match: RegExpExecArray | null;

  while ((match = citationRegex.exec(text)) !== null) {
    const citationNumber = parseInt(match[1], 10);
    const fullMatch = match[0];
    const index = match.index!;
    const source = allSources.find(s => s.id == citationNumber);

    if (source) {
      if (index > lastIndex) {
        contentParts.push({ type: 'text', content: text.substring(lastIndex, index) });
      }
      contentParts.push({ type: 'citation', source: source, citationNumber: citationNumber });
      citedSourceIds.add(source.id);
      lastIndex = index + fullMatch.length;
    }
  }

  if (lastIndex < text.length) {
    contentParts.push({ type: 'text', content: text.substring(lastIndex) });
  }

  const citedSources = allSources.filter(s => citedSourceIds.has(s.id));
  const uncitedSources = allSources.filter(s => !citedSourceIds.has(s.id));
  return { contentParts, citedSources, uncitedSources };
};

export function QuestionSliderDialog({ isOpen, onOpenChange, questions, title, analysisId, onDevelopClick }: QuestionSliderDialogProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [developmentStatus, setDevelopmentStatus] = useState<GapDevelopmentStatus | null>(null);
  const [progressValue, setProgressValue] = useState(0);
  const [researchStatus, setResearchStatus] = useState('Iniciando investigación...');
  const [isDeveloping, setIsDeveloping] = useState(false);
  const [clarificationAnswer, setClarificationAnswer] = useState('');
  const [activeAnalysisId, setActiveAnalysisId] = useState<string | null>(null);
  const activeAnalysisIdRef = useRef<string | null>(null);
  const { toast } = useToast();
  const { registerMessageHandler } = useWebSocketContext();

  // Update ref when state changes
  useEffect(() => {
    activeAnalysisIdRef.current = activeAnalysisId;
  }, [activeAnalysisId]);

  // Reset internal state when dialog opens/closes or question changes
  useEffect(() => {
    if (!isOpen) {
      setDevelopmentStatus(null);
      setProgressValue(0);
      setIsDeveloping(false);
      setClarificationAnswer('');
      setActiveAnalysisId(null);
    }
  }, [isOpen]);

  // Handle WebSocket updates
  useEffect(() => {
    const unregister = registerMessageHandler((message: any) => {
      if (message.type === 'gap_development_update') {
        console.log('✅ Received gap_development_update message:', message);
        console.log('🔍 Comparing analysis_id:', message.analysis_id, '===', activeAnalysisIdRef.current, ':', message.analysis_id === activeAnalysisIdRef.current);

        if (message.analysis_id && message.analysis_id === activeAnalysisIdRef.current) {
          console.log('📊 Processing message with progress:', message.progress);
          setDevelopmentStatus({
            status: message.status,
            analysisId: message.analysis_id,
            message: message.message,
            report: message.report,
            error: message.error,
            question: message.question
          });

          if (message.message) {
            setResearchStatus(message.message);
          }

          if (message.status === 'completed') {
            setProgressValue(100);
            toast({
              title: "Análisis completado",
              description: "La investigación profunda ha finalizado con éxito",
            });
          } else if (message.status === 'failed') {
            setProgressValue(0);
            if (message.error !== "Clarification needed") {
              toast({
                title: "Análisis fallido",
                description: message.error || "Error desconocido",
                variant: "destructive"
              });
            }
          } else if (message.status === 'processing' && message.progress !== undefined) {
            console.log('📈 Setting progress to:', message.progress);
            setProgressValue(message.progress);
          }
        } else if (message.analysis_id) {
          console.log('❌ Analysis ID mismatch - ignoring message. Expected:', activeAnalysisIdRef.current, 'Got:', message.analysis_id);
        }
      } else if (message.type === 'progress' && message.progress !== undefined) {
        // También escuchamos mensajes de progreso genéricos si están asociados a este análisis
        // Verificamos por thread_id o analysis_id para evitar colisiones con otras tareas
        const isTargetAnalysis = activeAnalysisIdRef.current && (
          (message.thread_id === activeAnalysisIdRef.current) ||
          (message.analysis_id === activeAnalysisIdRef.current) ||
          (message.taskId === activeAnalysisIdRef.current)
        );

        if (isTargetAnalysis) {
          console.log('📈 Setting progress from generic progress message:', message.progress);
          setProgressValue(message.progress);
          if (message.message) {
            setResearchStatus(message.message);
          }
        }
      }
    });

    return () => unregister();
  }, [registerMessageHandler, toast]);

  const handleNext = () => {
    setCurrentIndex((prev) => (prev + 1) % questions.length);
    setDevelopmentStatus(null);
    setActiveAnalysisId(null);
  };

  const handlePrev = () => {
    setCurrentIndex((prev) => (prev - 1 + questions.length) % questions.length);
    setDevelopmentStatus(null);
    setActiveAnalysisId(null);
  };

  const handleDevelop = async (customContext?: string) => {
    const question = customContext || questions[currentIndex];
    if (!question) return;

    setIsDeveloping(true);
    setDevelopmentStatus({ status: 'pending', message: customContext ? 'Resumiendo investigación con tu respuesta...' : 'Iniciando investigación...' });
    setProgressValue(0);

    try {
      const response = await apiClient.post('/api/gap-development/', {
        gap_id: question, // The question/gap itself is used as the ID
        context: question,
        depth: 3
      });

      if (response.data && response.data.analysis_id) {
        console.log('🎯 Setting activeAnalysisId to:', response.data.analysis_id);
        setActiveAnalysisId(response.data.analysis_id);
        toast({
          title: "Investigación iniciada",
          description: "Recibirás actualizaciones en tiempo real.",
        });
      } else {
        throw new Error("No se recibió un ID de análisis del servidor.");
      }
    } catch (error) {
      console.error("Error developing question:", error);
      setDevelopmentStatus({ status: 'failed', error: 'No se pudo iniciar la investigación' });
      toast({
        title: "Error",
        description: "No se pudo iniciar la investigación profunda.",
        variant: "destructive",
      });
    } finally {
      setIsDeveloping(false);
    }
  };

  const renderDevelopmentContent = () => {
    if (!developmentStatus) return null;

    switch (developmentStatus.status) {
      case 'pending':
      case 'processing':
        return (
          <div className="w-full max-w-2xl mx-auto py-10">
            <DeepResearchVisualizer
              progress={progressValue}
              statusText={researchStatus}
            />
            <p className="text-xs text-center text-muted-foreground italic mt-6">
              Esto puede tomar un momento mientras conectamos puntos de información...
            </p>
          </div>
        );

      case 'completed':
        const report = developmentStatus.report || {};
        return (
          <motion.div
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            className="w-full space-y-6"
          >
            <Tabs defaultValue="summary" className="w-full">
              <TabsList className="grid w-full grid-cols-4 h-12 p-1 bg-muted/50 rounded-xl">
                <TabsTrigger value="summary" className="rounded-lg gap-2"><FileText className="h-4 w-4" />Resumen</TabsTrigger>
                <TabsTrigger value="findings" className="rounded-lg gap-2"><Target className="h-4 w-4" />Hallazgos</TabsTrigger>
                <TabsTrigger value="sources" className="rounded-lg gap-2"><ExternalLink className="h-4 w-4" />Fuentes</TabsTrigger>
                <TabsTrigger value="recommendations" className="rounded-lg gap-2"><Lightbulb className="h-4 w-4" />Acciones</TabsTrigger>
              </TabsList>

              <div className="mt-6 min-h-[300px]">
                <TabsContent value="summary" className="m-0">
                  <Card className="border-0 shadow-none bg-transparent">
                    <CardContent className="p-0">
                      <div className="prose prose-sm dark:prose-invert max-w-none text-lg leading-relaxed text-foreground/90">
                        {(() => {
                          const { contentParts, citedSources, uncitedSources } = processMessageWithCitations(report.summary || "", report.sources);
                          return <MarkdownRenderer contentParts={contentParts} fontSize="text-lg" />;
                        })()}
                      </div>
                    </CardContent>
                  </Card>
                </TabsContent>

                <TabsContent value="findings" className="m-0">
                  <div className="grid gap-4">
                    {normalizeFindings(report.findings).map((finding: string, i: number) => (
                      <motion.div
                        key={i}
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: i * 0.1 }}
                        className="p-4 rounded-xl bg-card border border-border/50 hover:border-primary/30 transition-colors"
                      >
                        <div className="flex gap-3">
                          <span className="flex-shrink-0 w-6 h-6 rounded-full bg-primary/10 text-primary flex items-center justify-center text-xs font-bold">
                            {i + 1}
                          </span>
                          <div className="text-sm leading-relaxed prose prose-sm dark:prose-invert max-w-none">
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>{finding}</ReactMarkdown>
                          </div>
                        </div>
                      </motion.div>
                    ))}
                    {normalizeFindings(report.findings).length === 0 && (
                      <p className="text-muted-foreground text-center py-8">No hay hallazgos detallados.</p>
                    )}
                  </div>
                </TabsContent>

                <TabsContent value="sources" className="m-0">
                  <div className="grid gap-3">
                    {Array.isArray(report.sources) && report.sources.length > 0 ? (
                      report.sources.map((source: any, i: number) => (
                        <a
                          key={i}
                          href={source.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center justify-between p-4 rounded-xl bg-card border border-border/50 hover:bg-accent/50 transition-all group"
                        >
                          <div className="flex items-center gap-3 overflow-hidden">
                            <div className="p-2 rounded-lg bg-blue-500/10 text-blue-500">
                              <ExternalLink className="h-4 w-4" />
                            </div>
                            <span className="text-sm font-medium truncate">{source.url}</span>
                          </div>
                          <Badge variant="secondary" className="ml-2">
                            Relevancia: {source.relevance}/10
                          </Badge>
                        </a>
                      ))
                    ) : (
                      <p className="text-muted-foreground text-center py-8">No se citaron fuentes externas.</p>
                    )}
                  </div>
                </TabsContent>

                <TabsContent value="recommendations" className="m-0">
                  <div className="grid gap-4">
                    {Array.isArray(report.recommendations) && report.recommendations.length > 0 ? (
                      report.recommendations.map((rec: string, i: number) => (
                        <motion.div
                          key={i}
                          initial={{ opacity: 0, scale: 0.95 }}
                          animate={{ opacity: 1, scale: 1 }}
                          transition={{ delay: i * 0.1 }}
                          className="p-5 rounded-xl bg-green-500/5 border border-green-500/20 flex gap-4"
                        >
                          <div className="p-2 h-fit rounded-lg bg-green-500/10 text-green-600">
                            <Sparkles className="h-5 w-5" />
                          </div>
                          <div className="flex-1">
                            <h5 className="font-semibold text-green-800 dark:text-green-400 mb-1">Recomendación</h5>
                            <div className="text-sm text-green-700/90 dark:text-green-300/90 leading-relaxed prose prose-sm dark:prose-invert max-w-none">
                              <ReactMarkdown remarkPlugins={[remarkGfm]}>{rec}</ReactMarkdown>
                            </div>
                          </div>
                        </motion.div>
                      ))
                    ) : (
                      <p className="text-muted-foreground text-center py-8">
                        {typeof report.recommendations === 'string' ? report.recommendations : "No hay recomendaciones específicas."}
                      </p>
                    )}
                  </div>
                </TabsContent>
              </div>
            </Tabs>
          </motion.div>
        );

      case 'failed':
        const isClarification = developmentStatus.error === "Clarification needed";

        if (isClarification) {
          return (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="w-full max-w-2xl mx-auto space-y-6"
            >
              <div className="p-6 rounded-2xl bg-amber-500/5 border border-amber-500/20 space-y-4">
                <div className="flex items-center gap-3 text-amber-600 dark:text-amber-400">
                  <div className="p-2 rounded-lg bg-amber-500/10">
                    <MessageSquareQuote className="h-6 w-6" />
                  </div>
                  <h4 className="font-bold text-lg">El Investigador necesita más detalles</h4>
                </div>

                <p className="text-foreground/90 font-medium bg-background/50 p-4 rounded-xl border border-amber-500/10 italic">
                  "{developmentStatus.question}"
                </p>

                <div className="space-y-3">
                  <p className="text-sm text-muted-foreground">Tu respuesta ayudará a profundizar en la dirección correcta:</p>
                  <Textarea
                    placeholder="Escribe aquí los detalles adicionales..."
                    className="min-h-[120px] rounded-xl border-amber-500/20 focus-visible:ring-amber-500/30"
                    value={clarificationAnswer}
                    onChange={(e) => setClarificationAnswer(e.target.value)}
                  />
                </div>

                <div className="flex gap-3 pt-2">
                  <Button
                    className="flex-1 h-12 rounded-xl bg-amber-600 hover:bg-amber-700 text-white gap-2 font-bold"
                    onClick={() => handleDevelop(`Respuesta a clarificación: ${clarificationAnswer}. Contexto original: ${questions[currentIndex]}`)}
                    disabled={isDeveloping || !clarificationAnswer.trim()}
                  >
                    {isDeveloping ? <Loader2 className="h-5 w-5 animate-spin" /> : <Send className="h-5 w-5" />}
                    Enviar y Continuar
                  </Button>
                  <Button
                    variant="ghost"
                    className="h-12 rounded-xl"
                    onClick={() => setDevelopmentStatus(null)}
                    disabled={isDeveloping}
                  >
                    Cancelar
                  </Button>
                </div>
              </div>
            </motion.div>
          );
        }

        return (
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="p-6 rounded-2xl bg-destructive/5 border border-destructive/20 text-center space-y-4"
          >
            <div className="w-12 h-12 rounded-full bg-destructive/10 text-destructive flex items-center justify-center mx-auto">
              <Zap className="h-6 w-6" />
            </div>
            <div>
              <h4 className="font-bold text-destructive">Error en la investigación</h4>
              <p className="text-sm text-muted-foreground">{developmentStatus.error || "Ocurrió un problema inesperado"}</p>
            </div>
            <Button variant="outline" size="sm" onClick={() => setDevelopmentStatus(null)}>
              Intentar de nuevo
            </Button>
          </motion.div>
        );

      default:
        return null;
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <Dialog open={isOpen} onOpenChange={onOpenChange}>
          <DialogContent className="max-w-5xl rounded-3xl backdrop-blur-2xl bg-card/95 border-border/50 shadow-2xl p-0 overflow-hidden">
            <div className="flex flex-col h-full max-h-[90vh]">
              <DialogHeader className="p-8 pb-0">
                <div className="flex items-center justify-between mb-2">
                  <Badge variant="secondary" className="px-3 py-1 rounded-full text-xs font-bold tracking-wider uppercase">
                    Brecha de Conocimiento
                  </Badge>
                  {questions.length > 1 && (
                    <span className="text-xs font-medium text-muted-foreground bg-muted px-2 py-1 rounded-md">
                      {currentIndex + 1} de {questions.length}
                    </span>
                  )}
                </div>
                <DialogTitle className="text-4xl font-black tracking-tight leading-tight">
                  {title}
                </DialogTitle>
                <DialogDescription className="text-lg mt-2 text-muted-foreground/80">
                  Explora y desarrolla este concepto para cerrar la brecha informativa.
                </DialogDescription>
              </DialogHeader>

              <div className="flex-1 overflow-y-auto p-8 custom-scrollbar">
                <AnimatePresence mode="wait">
                  {!developmentStatus ? (
                    <motion.div
                      key={`q-${currentIndex}`}
                      initial={{ opacity: 0, x: 20 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -20 }}
                      className="flex flex-col items-center justify-center min-h-[300px] text-center space-y-10"
                    >
                      <div className="prose prose-2xl dark:prose-invert max-w-4xl font-semibold leading-tight text-foreground">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {questions[currentIndex] ? `"${typeof questions[currentIndex] === 'string' ? questions[currentIndex] : (typeof questions[currentIndex] === 'object' ? JSON.stringify(questions[currentIndex]) : String(questions[currentIndex]))}"` : "Pregunta no disponible"}
                        </ReactMarkdown>
                      </div>

                      {onDevelopClick && (
                        <Button
                          onClick={() => handleDevelop(questions[currentIndex])}
                          size="lg"
                          className="h-16 px-10 rounded-2xl text-lg font-bold shadow-xl shadow-primary/20 hover:shadow-primary/30 transition-all gap-3 group"
                          disabled={isDeveloping}
                        >
                          {isDeveloping ? (
                            <Loader2 className="h-6 w-6 animate-spin" />
                          ) : (
                            <Zap className="h-6 w-6 group-hover:fill-current transition-colors" />
                          )}
                          {isDeveloping ? 'Analizando...' : 'Iniciar Investigación Profunda'}
                        </Button>
                      )}
                    </motion.div>
                  ) : (
                    <div className="min-h-[400px]">
                      {renderDevelopmentContent()}
                    </div>
                  )}
                </AnimatePresence>
              </div>

              {!developmentStatus && questions.length > 1 && (
                <div className="p-8 pt-0 border-t border-border/10 bg-muted/5">
                  <div className="flex justify-between items-center mt-6">
                    <Button
                      variant="ghost"
                      onClick={handlePrev}
                      className="rounded-xl h-12 px-6 hover:bg-accent"
                    >
                      <ChevronLeft className="h-5 w-5 mr-2" />
                      Anterior
                    </Button>

                    <div className="flex gap-2">
                      {questions.map((_, index) => (
                        <button
                          key={index}
                          onClick={() => setCurrentIndex(index)}
                          className={`w-2.5 h-2.5 rounded-full transition-all duration-300 ${index === currentIndex
                            ? 'bg-primary w-8'
                            : 'bg-muted-foreground/20 hover:bg-muted-foreground/40'
                            }`}
                        />
                      ))}
                    </div>

                    <Button
                      variant="ghost"
                      onClick={handleNext}
                      className="rounded-xl h-12 px-6 hover:bg-accent"
                    >
                      Siguiente
                      <ChevronRight className="h-5 w-5 ml-2" />
                    </Button>
                  </div>
                </div>
              )}
            </div>
          </DialogContent>
        </Dialog>
      )}
    </AnimatePresence>
  );
}