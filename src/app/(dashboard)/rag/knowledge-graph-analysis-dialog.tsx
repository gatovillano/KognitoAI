import React from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';

interface KnowledgeGraphAnalysisDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  analysis: any; // Aquí se pasará el resultado del análisis del grafo
}

export function KnowledgeGraphAnalysisDialog({ isOpen, onOpenChange, analysis }: KnowledgeGraphAnalysisDialogProps) {
  if (!analysis) return null;

  const { graph_summary, nodes, relationships } = analysis.result_payload || {};

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[800px] h-[90vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>Análisis de Grafo de Conocimiento</DialogTitle>
          <DialogDescription>
            Resultados detallados del análisis del grafo de conocimiento para la colección.
          </DialogDescription>
        </DialogHeader>
        <ScrollArea className="flex-1 p-4 -mx-4">
          <div className="space-y-6">
            {graph_summary && (
              <div>
                <h3 className="text-lg font-semibold mb-2">Resumen General</h3>
                <p className="text-sm text-muted-foreground">{graph_summary}</p>
              </div>
            )}

            {nodes && nodes.length > 0 && (
              <div>
                <h3 className="text-lg font-semibold mb-2">Nodos Identificados ({nodes.length})</h3>
                <div className="flex flex-wrap gap-2">
                  {nodes.map((node: any, index: number) => (
                    <Badge key={index} variant="secondary" className="px-3 py-1">
                      {node.name} ({node.type})
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {relationships && relationships.length > 0 && (
              <div>
                <h3 className="text-lg font-semibold mb-2">Relaciones Identificadas ({relationships.length})</h3>
                <div className="space-y-2">
                  {relationships.map((rel: any, index: number) => (
                    <div key={index} className="text-sm text-muted-foreground bg-accent/20 p-2 rounded-md">
                      <span className="font-medium">{rel.source}</span> --({rel.type})--&gt; <span className="font-medium">{rel.target}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {!graph_summary && (!nodes || nodes.length === 0) && (!relationships || relationships.length === 0) && (
              <p className="text-center text-muted-foreground">No se encontraron resultados detallados para el análisis del grafo.</p>
            )}
          </div>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
}
