import apiClient from '@/lib/api';
import React, { useState, useMemo } from 'react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Download, MessageSquare, ExternalLink, Loader2 } from 'lucide-react';
import { Analysis, DeepResearchAnalysisResult } from '@/lib/models';
import { useTextToSpeech } from '@/hooks/useTextToSpeech';
import { ContextualChat } from '@/components/ContextualChat';
import { ShareAnalysisDialog } from '@/components/ShareAnalysisDialog';
import DeepResearchAnalysis from './DeepResearchAnalysis';

interface DeepResearchDetailDialogProps {
  analysis: Analysis;
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
}

export function DeepResearchDetailDialog({ analysis, isOpen, onOpenChange }: DeepResearchDetailDialogProps) {
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [isExportingPDF, setIsExportingPDF] = useState(false);
  const [isShareDialogOpen, setIsShareDialogOpen] = useState(false);

  // El backend a veces envuelve el resultado en un objeto 'report'
  const deepResearchResult = useMemo(() => {
    let rawResult = analysis.full_data || (analysis as any).result_payload || analysis.result;

    if (typeof rawResult === 'string') {
      try {
        rawResult = JSON.parse(rawResult);
      } catch (e) {
        console.error("Failed to parse rawResult JSON:", e);
      }
    }

    if (rawResult && typeof rawResult === 'object' && 'report' in rawResult) {
      return rawResult.report as DeepResearchAnalysisResult;
    }
    return rawResult as DeepResearchAnalysisResult;
  }, [analysis]);

  const { play, stop, isLoading, isPlaying, activeText } = useTextToSpeech();

  const handleExportPDF = async () => {
    if (!deepResearchResult) return;
    setIsExportingPDF(true);
    try {
      const response = await apiClient.post('/api/deep_research/export_pdf', {
        title: analysis.title || "Informe de Investigación",
        final_report: deepResearchResult.final_report || deepResearchResult.summary || "Sin contenido",
        sources: deepResearchResult.sources,
        recommendations: deepResearchResult.recommendations
      });

      const data = response.data;
      if (data.url) {
        window.open(data.url, '_blank');
      } else {
        // Mostrar error al usuario (puedes usar toast si está disponible)
        console.error("No se pudo generar el PDF: URL no recibida");
      }
    } catch (error: any) {
      console.error("Error exporting PDF:", error);
      // Manejar error 401 específicamente
      if (error.response?.status === 401) {
        // Redirigir al login o mostrar mensaje
        window.location.href = '/login';
      } else {
        // Mostrar error genérico
        alert("Error al exportar PDF. Por favor, intenta de nuevo.");
      }
    } finally {
      setIsExportingPDF(false);
    }
  };

  if (!deepResearchResult || !(deepResearchResult.final_report || deepResearchResult.summary)) {
    return (
      <Dialog open={isOpen} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto rounded-3xl backdrop-blur-2xl bg-card/95 border-border/50 shadow-2xl">
          <DialogHeader className="p-4">
            <DialogTitle className="text-3xl font-black tracking-tight leading-tight">
              Error al cargar la Investigación Profunda
            </DialogTitle>
            <DialogDescription className="text-base">
              No se encontraron datos válidos para la investigación profunda.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="p-4 border-t border-border/10">
            <Button onClick={() => onOpenChange(false)} variant="ghost" className="rounded-xl">
              Cerrar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    );
  }

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent
        className="max-w-4xl max-h-[95vh] overflow-y-auto rounded-[2.5rem] backdrop-blur-2xl bg-card/95 border-border/50 shadow-2xl p-0"
        onFocusOutside={(e) => {
          stop();
        }}
      >
        <div className="p-8 space-y-6">
          <DialogHeader className="p-0 space-y-4">
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  <Badge variant="secondary" className="rounded-full px-3 text-[10px] font-bold tracking-widest uppercase bg-primary/10 text-primary border-none">
                    Investigación Profunda
                  </Badge>
                </div>
                <DialogTitle className="text-3xl sm:text-4xl font-black tracking-tight leading-tight break-words">
                  {analysis.title || "Informe de Investigación Profunda"}
                </DialogTitle>
              </div>
              <div className="flex-shrink-0 flex gap-2">
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={handleExportPDF}
                  disabled={isExportingPDF}
                  className="h-10 w-10 rounded-xl text-muted-foreground hover:text-primary hover:bg-primary/10 transition-all"
                  title="Exportar a PDF"
                >
                  {isExportingPDF ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setIsChatOpen(true)}
                  className="h-10 w-10 rounded-xl text-muted-foreground hover:text-primary hover:bg-primary/10 transition-all"
                  title="Chatear con esta investigación"
                >
                  <MessageSquare className="h-4 w-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setIsShareDialogOpen(true)}
                  className="h-10 w-10 rounded-xl text-muted-foreground hover:text-primary hover:bg-primary/10 transition-all"
                  title="Compartir investigación"
                >
                  <ExternalLink className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </DialogHeader>

          <DeepResearchAnalysis
            analysis={deepResearchResult}
            play={play}
            isLoading={isLoading}
            isPlaying={isPlaying}
            activeText={activeText}
          />
        </div>

        <DialogFooter className="p-6 border-t border-border/10 bg-muted/20">
          <div className="flex w-full justify-between items-center">
            <Button
              onClick={handleExportPDF}
              disabled={isExportingPDF}
              variant="outline"
              className="rounded-xl gap-2 font-bold border-border/40 hover:bg-background"
            >
              {isExportingPDF ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
              Descargar Reporte PDF
            </Button>
            <Button
              onClick={() => onOpenChange(false)}
              variant="default"
              className="rounded-xl px-8 font-bold shadow-lg shadow-primary/20"
            >
              Finalizar Revisión
            </Button>
          </div>
        </DialogFooter>

        {/* Chat Contextual */}
        <ContextualChat
          isOpen={isChatOpen}
          onClose={() => setIsChatOpen(false)}
          context={{
            type: 'analysis',
            id: analysis.id,
            snapshot: analysis
          }}
          title={analysis.title || "Investigación Profunda"}
        />

        {/* Diálogo de compartir */}
        <ShareAnalysisDialog
          isOpen={isShareDialogOpen}
          onOpenChange={setIsShareDialogOpen}
          analysisId={analysis.id}
          analysisTitle={analysis.title}
        />
      </DialogContent>
    </Dialog>
  );
}