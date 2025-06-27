// En: src/app/(dashboard)/rag/analysis-result-dialog.tsx
'use client';

import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { InlineMarkdownRenderer } from '@/components/InlineMarkdownRenderer';
import apiClient from '@/lib/api';
import { toast } from 'sonner';
import { type Document } from './columns'; // Importamos el tipo

interface AnalysisResultDialogProps {
  document: Document | null; // <-- Ahora es obligatorio
  analysis: any;
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
}

export function AnalysisResultDialog({ document, analysis, isOpen, onOpenChange }: AnalysisResultDialogProps) {
  if (!analysis) return null;

  // Log the analysis object for debugging
  console.log("Analysis object:", analysis);

  // Map backend field names to frontend expected field names
  const mappedAnalysis = {
    resumen_ejecutivo: analysis.executive_summary || analysis.resumen_ejecutivo || 'No summary available',
    temas_clave_avanzados: analysis.key_themes || analysis.temas_clave_avanzados || [],
    conceptos_centrales: analysis.central_concepts || analysis.conceptos_centrales || [],
    relaciones_conceptos: analysis.concept_relationships || analysis.relaciones_conceptos || [],
    preguntas_para_explorar: analysis.knowledge_gaps || analysis.preguntas_para_explorar || []
  };

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Resultados del Análisis</DialogTitle>
          <DialogDescription className="truncate">
            Para el documento: {document?.file_name || 'Nombre no disponible'}
          </DialogDescription>
        </DialogHeader>
        <ScrollArea className="max-h-[60vh] pr-4">
            <div className="space-y-6">
                <div>
                    <h3 className="font-semibold mb-2">Resumen Ejecutivo por IA</h3>
                    <p className="text-sm text-muted-foreground p-3 bg-muted rounded-md whitespace-pre-wrap">{mappedAnalysis.resumen_ejecutivo}</p>
                </div>
                <div>
                    <h3 className="font-semibold mb-2">Temas Clave Avanzados</h3>
                    <div className="flex flex-wrap gap-2">
                        {mappedAnalysis.temas_clave_avanzados?.map((topic: string) => <Badge key={topic}>{topic}</Badge>)}
                    </div>
                </div>
                <div>
                    <h3 className="font-semibold mb-2">Conceptos Centrales</h3>
                    <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
                        {mappedAnalysis.conceptos_centrales?.map((concept: string, i: number) => <li key={i}>{concept}</li>)}
                    </ul>
                </div>
                <div>
                    <h3 className="font-semibold mb-2">Relaciones entre Conceptos</h3>
                    <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
                        {mappedAnalysis.relaciones_conceptos?.map((relation: string, i: number) => (
                            <li key={i}>
                                <InlineMarkdownRenderer content={relation} />
                            </li>
                        ))}
                    </ul>
                </div>
                <div>
                    <h3 className="font-semibold mb-2">Preguntas para Explorar</h3>
                    <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
                       {mappedAnalysis.preguntas_para_explorar?.map((question: string, i: number) => <li key={i}>{question}</li>)}
                    </ul>
                </div>
            </div>
        </ScrollArea>
        <div className="flex justify-between mt-4">
          <Button 
            variant="destructive" 
            onClick={async () => {
              try {
                await apiClient.post('/api/delete-analysis', { task_id: analysis.id });
                toast.success('Análisis eliminado correctamente.');
                onOpenChange(false);
              } catch (error) {
                toast.error('Error al eliminar el análisis.');
                console.error(error);
              }
            }}
          >
            Eliminar Análisis
          </Button>
          <Button 
            variant="outline" 
            onClick={() => onOpenChange(false)}
          >
            Cerrar
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
