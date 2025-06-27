// En: src/app/(dashboard)/rag/collection-analysis-dialog.tsx
'use client';

import { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

interface CollectionAnalysisProps {
  analysis: any;
  isOpen: boolean;
  onOpenChange: (isOpen: boolean) => void;
  topic: string;
}

export function CollectionAnalysisDialog({ analysis, isOpen, onOpenChange, topic }: CollectionAnalysisProps) {
  const [selectedConnection, setSelectedConnection] = useState<any>(null);
  const [selectedTheme, setSelectedTheme] = useState<any>(null);
  const [isConnectionDialogOpen, setIsConnectionDialogOpen] = useState(false);
  const [isThemeDialogOpen, setIsThemeDialogOpen] = useState(false);

  if (!analysis) return null;

  // Map backend field names to frontend expected field names
  const mappedAnalysis = {
    resumen_general_coleccion: analysis.collection_summary || 'No summary available',
    temas_transversales: analysis.cross_cutting_themes || [],
    conceptos_centrales: analysis.central_concepts || [],
    relaciones_conceptos: analysis.concept_relationships || [],
    conexiones_identificadas: analysis.identified_connections || [],
    brechas_conocimiento: analysis.emergent_knowledge_gaps || []
  };

  // Adjust the conexiones_identificadas to match expected structure if necessary
  mappedAnalysis.conexiones_identificadas = mappedAnalysis.conexiones_identificadas.map((conn: any) => ({
    documentos: conn.document_titles || [],
    insight: conn.insight || 'No insight provided'
  }));

  const handleConnectionClick = (connection: any) => {
    setSelectedConnection(connection);
    setIsConnectionDialogOpen(true);
  };

  const handleThemeClick = (theme: any) => {
    setSelectedTheme(theme);
    setIsThemeDialogOpen(true);
  };

  return (
    <>
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
                          {mappedAnalysis.temas_transversales?.map((t: any) => (
                              <Badge 
                                key={typeof t === 'string' ? t : t.theme} 
                                className="cursor-pointer hover:bg-muted/80" 
                                onClick={() => handleThemeClick(t)}
                              >
                                {typeof t === 'string' ? t : t.theme}
                              </Badge>
                          ))}
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
                          {mappedAnalysis.relaciones_conceptos?.map((relation: string, i: number) => <li key={i}>{relation}</li>)}
                      </ul>
                  </div>
                  <div>
                      <h3 className="font-semibold mb-2">Conexiones Identificadas</h3>
                      <div className="space-y-3">
                         {mappedAnalysis.conexiones_identificadas?.map((conn: any, i: number) => (
                          <div key={i} className="text-sm border-l-2 border-primary pl-3 cursor-pointer hover:bg-muted/80" onClick={() => handleConnectionClick(conn)}>
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

      {/* Diálogo secundario para mostrar detalles de la conexión */}
      <Dialog open={isConnectionDialogOpen} onOpenChange={setIsConnectionDialogOpen}>
        <DialogContent className="max-w-xl">
          <DialogHeader>
            <DialogTitle>Detalles de la Conexión</DialogTitle>
          </DialogHeader>
          {selectedConnection && (
            <div className="space-y-4">
              <p className="text-base">{selectedConnection.insight}</p>
              <div>
                <h4 className="font-semibold">Documentos Relacionados:</h4>
                <ul className="list-disc list-inside text-sm text-muted-foreground">
                  {selectedConnection.documentos.map((title: string, i: number) => <li key={i}>{title}</li>)}
                </ul>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsConnectionDialogOpen(false)}>Cerrar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Diálogo secundario para mostrar citas relacionadas con el tema transversal */}
      <Dialog open={isThemeDialogOpen} onOpenChange={setIsThemeDialogOpen}>
        <DialogContent className="max-w-xl">
          <DialogHeader>
            <DialogTitle>Detalles del Tema Transversal</DialogTitle>
          </DialogHeader>
          {selectedTheme && (
            <div className="space-y-4">
              <p className="text-base font-semibold">{typeof selectedTheme === 'string' ? selectedTheme : selectedTheme.theme}</p>
              {typeof selectedTheme !== 'string' && selectedTheme.related_quotes && selectedTheme.related_quotes.length > 0 && (
                <div>
                  <h4 className="font-semibold">Citas Relacionadas:</h4>
                  <ul className="list-disc list-inside text-sm text-muted-foreground space-y-2">
                    {selectedTheme.related_quotes.map((quote: any, i: number) => (
                      <li key={i}>
                        <strong>{quote.document_title}</strong>: {quote.quote}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsThemeDialogOpen(false)}>Cerrar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
