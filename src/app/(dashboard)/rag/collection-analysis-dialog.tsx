// En: src/app/(dashboard)/rag/collection-analysis-dialog.tsx
'use client';

import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';

interface CollectionAnalysisProps {
  analysis: any;
  isOpen: boolean;
  onOpenChange: (isOpen: boolean) => void;
  topic: string;
}

export function CollectionAnalysisDialog({ analysis, isOpen, onOpenChange, topic }: CollectionAnalysisProps) {
  if (!analysis) return null;

  // Map backend field names to frontend expected field names
  const mappedAnalysis = {
    resumen_general_coleccion: analysis.collection_summary || 'No summary available',
    temas_transversales: analysis.cross_cutting_themes || [],
    conexiones_identificadas: analysis.identified_connections || [],
    brechas_conocimiento: analysis.emergent_knowledge_gaps || []
  };

  // Adjust the conexiones_identificadas to match expected structure if necessary
  mappedAnalysis.conexiones_identificadas = mappedAnalysis.conexiones_identificadas.map((conn: any) => ({
    documentos: conn.document_titles || [],
    insight: conn.insight || 'No insight provided'
  }));

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle>Análisis de la Colección "{topic}"</DialogTitle>
        </DialogHeader>
        <ScrollArea className="max-h-[70vh] pr-4">
            <div className="space-y-6">
                <div>
                    <h3 className="font-semibold mb-2">Resumen General de la Colección</h3>
                    <p className="text-sm text-muted-foreground p-3 bg-muted rounded-md whitespace-pre-wrap">{mappedAnalysis.resumen_general_coleccion}</p>
                </div>
                <div>
                    <h3 className="font-semibold mb-2">Temas Transversales</h3>
                    <div className="flex flex-wrap gap-2">
                        {mappedAnalysis.temas_transversales?.map((t: string) => <Badge key={t}>{t}</Badge>)}
                    </div>
                </div>
                <div>
                    <h3 className="font-semibold mb-2">Conexiones Identificadas</h3>
                    <div className="space-y-3">
                       {mappedAnalysis.conexiones_identificadas?.map((conn: any, i: number) => (
                        <div key={i} className="text-sm border-l-2 border-primary pl-3">
                            <p className="font-semibold">{conn.documentos.join(' ↔ ')}</p>
                            <p className="text-muted-foreground">{conn.insight}</p>
                        </div>
                       ))}
                    </div>
                </div>
                 <div>
                    <h3 className="font-semibold mb-2">Brechas de Conocimiento</h3>
                    <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
                       {mappedAnalysis.brechas_conocimiento?.map((gap: string, i: number) => <li key={i}>{gap}</li>)}
                    </ul>
                </div>
            </div>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
}
