// En: src/app/(dashboard)/rag/analysis-result-dialog.tsx
'use client';

import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { type Document } from './columns'; // Importamos el tipo

interface AnalysisResultDialogProps {
  document: Document | null; // <-- Ahora es obligatorio
  analysis: any;
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
}

export function AnalysisResultDialog({ document, analysis, isOpen, onOpenChange }: AnalysisResultDialogProps) {
  if (!analysis) return null;

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
                    <p className="text-sm text-muted-foreground p-3 bg-muted rounded-md whitespace-pre-wrap">{analysis.resumen_ejecutivo}</p>
                </div>
                <div>
                    <h3 className="font-semibold mb-2">Temas Clave Avanzados</h3>
                    <div className="flex flex-wrap gap-2">
                        {analysis.temas_clave_avanzados?.map((topic: string) => <Badge key={topic}>{topic}</Badge>)}
                    </div>
                </div>
                <div>
                    <h3 className="font-semibold mb-2">Preguntas para Explorar</h3>
                    <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
                       {analysis.preguntas_para_explorar?.map((question: string, i: number) => <li key={i}>{question}</li>)}
                    </ul>
                </div>
            </div>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
}
