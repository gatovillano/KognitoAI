import apiClient from '@/lib/api';
import React, { useState, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Download, MessageSquare, ExternalLink, Loader2, Save } from 'lucide-react';
import { toast } from 'sonner';
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
  const router = useRouter();
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
    const toastId = toast.loading("Generando documento PDF y guardando en Documentos...");
    try {
      const response = await apiClient.post('/api/deep_research/export_pdf', {
        title: analysis.title || "Informe de Investigación",
        final_report: deepResearchResult.final_report || deepResearchResult.summary || "Sin contenido",
        sources: deepResearchResult.sources,
        recommendations: deepResearchResult.recommendations,
        kai_synthesis: (deepResearchResult as any).kai_synthesis || null,
        visual_schema: (deepResearchResult as any).visual_schema || null,
        workspace_id: (analysis as any).workspace_id || (analysis as any).result_payload?.workspace_id || null
      });

      const data = response.data;
      if (data.status === "success" || data.document_id || data.url) {
        toast.success("PDF guardado en Documentos exitosamente", {
          id: toastId,
          description: data.filename 
            ? `Se guardó "${data.filename}" en tu nube de Documentos.` 
            : "El informe está disponible en tu sección de Documentos.",
          action: {
            label: "Ver en Documentos",
            onClick: () => {
              if (data.document_id) {
                router.push(`/documents?open=${data.document_id}`);
              } else {
                router.push('/documents');
              }
            }
          }
        });
      } else {
        toast.error("No se pudo guardar el PDF en Documentos", {
          id: toastId,
          description: data.detail || "Ocurrió un error inesperado al generar el PDF."
        });
      }
    } catch (error: any) {
      console.error("Error exporting PDF:", error);
      if (error.response?.status === 401) {
        toast.error("Sesión expirada. Por favor, inicia sesión de nuevo.", { id: toastId });
        window.location.href = '/login';
      } else {
        toast.error("Error al exportar PDF. Por favor, intenta de nuevo.", {
          id: toastId,
          description: error.response?.data?.detail || "Error en el servidor al generar el documento."
        });
      }
    } finally {
      setIsExportingPDF(false);
    }
  };

  if (!deepResearchResult || !(deepResearchResult.final_report || deepResearchResult.summary)) {
    return (
      <Dialog open={isOpen} onOpenChange={onOpenChange}>
        <DialogContent className="w-[95vw] sm:w-[90vw] md:max-w-3xl max-h-[90vh] overflow-y-auto rounded-2xl sm:rounded-3xl backdrop-blur-2xl bg-card/95 border-border/50 shadow-2xl">
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
        className="w-[95vw] sm:w-[90vw] md:max-w-4xl max-h-[92vh] flex flex-col overflow-hidden rounded-2xl sm:rounded-[2.5rem] backdrop-blur-2xl bg-card/95 border-border/50 shadow-2xl p-0 gap-0"
        onFocusOutside={(e) => {
          stop();
        }}
      >
        <div className="flex-1 overflow-y-auto overflow-x-hidden p-4 sm:p-8 space-y-6 min-w-0 w-full">
          <DialogHeader className="p-0 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 pr-8 sm:pr-10">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-2">
                  <Badge variant="secondary" className="rounded-full px-3 text-[10px] font-bold tracking-widest uppercase bg-primary/10 text-primary border-none">
                    Investigación Profunda
                  </Badge>
                </div>
                <DialogTitle className="text-2xl sm:text-3xl md:text-4xl font-black tracking-tight leading-tight break-words">
                  {analysis.title || "Informe de Investigación Profunda"}
                </DialogTitle>
              </div>
              <div className="flex-shrink-0 flex items-center gap-2 self-start sm:self-auto">
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={handleExportPDF}
                  disabled={isExportingPDF}
                  className="h-10 w-10 rounded-xl text-muted-foreground hover:text-primary hover:bg-primary/10 transition-all"
                  title="Guardar PDF en Documentos"
                >
                  {isExportingPDF ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
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

        <DialogFooter className="p-4 sm:p-6 border-t border-border/10 bg-muted/20 flex-shrink-0">
          <div className="flex flex-col-reverse sm:flex-row w-full justify-between items-stretch sm:items-center gap-3">
            <Button
              onClick={handleExportPDF}
              disabled={isExportingPDF}
              variant="outline"
              className="rounded-xl gap-2 font-bold border-border/40 hover:bg-background w-full sm:w-auto"
            >
              {isExportingPDF ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
              Guardar PDF en Documentos
            </Button>
            <Button
              onClick={() => onOpenChange(false)}
              variant="default"
              className="rounded-xl px-8 font-bold shadow-lg shadow-primary/20 w-full sm:w-auto"
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