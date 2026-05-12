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
import apiClient from '@/lib/api';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { MarkdownRenderer } from '@/components/MarkdownRenderer';
import DeepResearchVisualizer from '@/components/DeepResearchVisualizer';

import { SourcesTab } from './SourcesTab';
import { Source, ContentPart } from './SourceButton';
import { processMessageWithCitations as processCitations, collectSourcesFromMessage } from '@/lib/chatUtils';

export interface QuestionSliderDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  questions: any[];
  title: string;
  analysisId?: string;
  onDevelopClick?: (question: string) => void;
  hideDevelopButtons?: boolean;
}

interface GapDevelopmentStatus {
  status: 'pending' | 'processing' | 'completed' | 'failed';
  analysisId?: string;
  message?: string;
  report?: any;
  error?: string;
  question?: string;
}

const normalizeFindings = (findings: any): string[] => {
  if (!findings) return [];
  if (Array.isArray(findings)) return findings;
  if (typeof findings === 'string') {
    return findings
      .split(/\n\s*\n/)
      .map(f => f.trim())
      .filter(f => f.length > 0);
  }
  return [];
};


export function QuestionSliderDialog({ isOpen, onOpenChange, questions, title, analysisId, onDevelopClick, hideDevelopButtons }: QuestionSliderDialogProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [developmentStatus, setDevelopmentStatus] = useState<GapDevelopmentStatus | null>(null);
  const [progressValue, setProgressValue] = useState(0);
  const [researchStatus, setResearchStatus] = useState('Iniciando investigación...');
  const [isDeveloping, setIsDeveloping] = useState(false);
  const [clarificationAnswer, setClarificationAnswer] = useState('');
  const [activeAnalysisId, setActiveAnalysisId] = useState<string | null>(null);
  const [processedSources, setProcessedSources] = useState<Source[]>([]);
  const [processedContentParts, setProcessedContentParts] = useState<ContentPart[]>([]);
  const activeAnalysisIdRef = useRef<string | null>(null);
  const { toast } = useToast();
  const { registerMessageHandler } = useWebSocketContext();

  useEffect(() => {
    activeAnalysisIdRef.current = activeAnalysisId;
  }, [activeAnalysisId]);

  useEffect(() => {
    if (!isOpen) {
      setDevelopmentStatus(null);
      setProgressValue(0);
      setIsDeveloping(false);
      setClarificationAnswer('');
      setActiveAnalysisId(null);
      setProcessedSources([]);
      setProcessedContentParts([]);
    }
  }, [isOpen]);

  useEffect(() => {
    const unregister = registerMessageHandler((message: any) => {
      if (message.type === 'gap_development_update') {
        if (message.analysis_id && message.analysis_id === activeAnalysisIdRef.current) {
          setDevelopmentStatus({
            status: message.status,
            analysisId: message.analysis_id,
            message: message.message,
            report: message.report,
            error: message.error,
            question: message.question
          });

          if (message.message) setResearchStatus(message.message);
          if (message.status === 'completed') setProgressValue(100);
          else if (message.status === 'processing' && message.progress !== undefined) setProgressValue(message.progress);
        }
      }
    });
    return () => unregister();
  }, [registerMessageHandler, toast]);

  useEffect(() => {
    if (developmentStatus?.status === 'completed' && developmentStatus.report) {
      const report = developmentStatus.report;
      const rawSources = report.sources || [];
      const { citationSources, additionalSources } = collectSourcesFromMessage(rawSources);

      const { contentParts: parts, resolvedSources } = processCitations(
        report.final_report || report.summary || "",
        citationSources
      );
      setProcessedSources(resolvedSources.length > 0 ? resolvedSources : additionalSources);
      setProcessedContentParts(parts);
    }
  }, [developmentStatus]);

  const handleAction = async (mode: 'research' | 'draft', customContext?: string) => {
    const question = customContext || questions[currentIndex];
    if (!question) return;

    setIsDeveloping(true);
    setDevelopmentStatus({ 
      status: 'pending', 
      message: mode === 'draft' ? 'Analizando brecha y redactando borrador...' : 'Iniciando investigación profunda...' 
    });
    setProgressValue(0);

    try {
      console.log("DEBUG FRONTEND: Enviando petición al API con modo:", mode);
      const response = await apiClient.post('/api/gap-development/', {
        gap_id: question,
        context: question,
        depth: 3,
        mode: mode,
        parent_analysis_id: analysisId // Pasar el ID del análisis padre
      });

      if (response.data && response.data.analysis_id) {
        setActiveAnalysisId(response.data.analysis_id);
        toast({
          title: mode === 'draft' ? "Desarrollo iniciado" : "Investigación iniciada",
          description: mode === 'draft' ? "El borrador está siendo redactado." : "Recibirás actualizaciones en tiempo real.",
        });
      } else {
        throw new Error("No se recibió un ID de análisis del servidor.");
      }
    } catch (error) {
      console.error("Error developing:", error);
      setDevelopmentStatus({ status: 'failed', error: 'No se pudo iniciar la operación' });
      toast({
        title: "Error",
        description: "No se pudo iniciar la operación solicitada.",
        variant: "destructive",
      });
    } finally {
      setIsDeveloping(false);
    }
  };

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

  const renderDevelopmentContent = () => {
    if (!developmentStatus) return null;

    switch (developmentStatus.status) {
      case 'pending':
      case 'processing':
        return (
          <div className="w-full max-w-2xl mx-auto py-10">
            <DeepResearchVisualizer progress={progressValue} statusText={researchStatus} />
          </div>
        );

      case 'completed':
        const report = developmentStatus.report || {};
        return (
          <motion.div initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} className="w-full space-y-6">
            {report.document_id && (
              <div className="flex items-center justify-between p-4 rounded-2xl bg-primary/10 border border-primary/20 mb-4 animate-pulse">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-primary/20 text-primary"><Notebook className="h-6 w-6" /></div>
                  <div>
                    <h4 className="font-bold text-primary">¡Borrador Creado con Éxito!</h4>
                  </div>
                </div>
                <Button onClick={() => window.open(`/notes?id=${report.document_id}`, '_blank')} className="bg-primary text-white rounded-xl gap-2 font-bold">
                  <ExternalLink className="h-4 w-4" /> Abrir Nota
                </Button>
              </div>
            )}
            <Tabs defaultValue="summary" className="w-full">
              <TabsList className="grid w-full grid-cols-2 h-12 p-1 bg-muted/50 rounded-xl">
                <TabsTrigger value="summary">Resumen</TabsTrigger>
                <TabsTrigger value="sources">Fuentes</TabsTrigger>
              </TabsList>
              
              <div className="mt-6">
                <TabsContent value="summary">
                  <Card className="border-0 shadow-none bg-transparent">
                    <CardContent className="p-0">
                      <div className="text-lg leading-relaxed">
                        <MarkdownRenderer
                          contentParts={processedContentParts}
                          content={report.final_report || report.summary}
                        />
                      </div>
                    </CardContent>
                  </Card>
                </TabsContent>

                <TabsContent value="sources">
                  <div className="space-y-4 pt-4">
                    <SourcesTab sources={processedSources} />
                  </div>
                </TabsContent>
              </div>
            </Tabs>
          </motion.div>
        );
        default: return null;
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-5xl rounded-3xl p-0 overflow-hidden">
        <div className="flex flex-col h-full max-h-[90vh]">
          <DialogHeader className="p-8 pb-0">
            <DialogTitle className="text-4xl font-black">{title}</DialogTitle>
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

                    {!hideDevelopButtons && (
                      <div className="flex gap-3 w-full justify-center">
                        <Button onClick={() => handleAction('draft', questions[currentIndex])} size="lg" className="h-16 px-8 rounded-2xl text-lg font-bold shadow-xl transition-all gap-3" disabled={isDeveloping}>
                          {isDeveloping ? <Loader2 className="animate-spin" /> : <FileText />} Desarrollar Documento Borrador
                        </Button>
                        <Button onClick={() => handleAction('research', questions[currentIndex])} size="lg" variant="outline" className="h-16 px-8 rounded-2xl text-lg font-bold transition-all gap-3" disabled={isDeveloping}>
                          {isDeveloping ? <Loader2 className="animate-spin" /> : <Zap />} Investigación Profunda
                        </Button>
                      </div>
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
  );
}