// En: src/app/(dashboard)/rag/semantic-analysis-dialog.tsx
'use client';

import { useState, useMemo } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Expand, HelpCircle, Brain, Network, Lightbulb, Volume2, Loader2, Pause } from 'lucide-react';
import { QuestionSliderDialog } from '@/components/QuestionSliderDialog';
import { useTextToSpeech } from '@/hooks/useTextToSpeech';

interface SemanticAnalysisProps {
  analysis: any;
  isOpen: boolean;
  onOpenChange: (isOpen: boolean) => void;
  topic: string;
}

export function SemanticAnalysisDialog({ analysis, isOpen, onOpenChange, topic }: SemanticAnalysisProps) {
  const [selectedTheme, setSelectedTheme] = useState<any>(null);
  const [isThemeDialogOpen, setIsThemeDialogOpen] = useState(false);
  const [isKnowledgeGapsDialogOpen, setIsKnowledgeGapsDialogOpen] = useState(false);
  const [selectedConcept, setSelectedConcept] = useState<string | null>(null);
  const [isConceptDialogOpen, setIsConceptDialogOpen] = useState(false);
  const { play, stop, isLoading, isPlaying, activeText } = useTextToSpeech();

  if (!analysis) {
    console.log("❌ SemanticAnalysisDialog: No analysis data provided");
    return null;
  }

  console.log("🧠 SemanticAnalysisDialog - Analysis object:", analysis);
  console.log("🧠 SemanticAnalysisDialog - Topic:", topic);

  // El análisis semántico tiene una estructura específica
  const semanticData = {
    resumen_semantico: analysis.resumen_semantico || 'No hay resumen disponible',
    temas_transversales: analysis.temas_transversales || [],
    conceptos_centrales: analysis.conceptos_centrales || [],
    brechas_conocimiento: analysis.brechas_conocimiento || [],
    patrones_semanticos: analysis.patrones_semanticos || {}
  };



  const handleThemeClick = (theme: any) => {
    setSelectedTheme(theme);
    setIsThemeDialogOpen(true);
  };

  const handleConceptClick = (concept: string) => {
    setSelectedConcept(concept);
    setIsConceptDialogOpen(true);
  };

  const textToRead = useMemo(() => {
    return `Resumen Semántico: ${semanticData.resumen_semantico}`;
  }, [semanticData]);

  const handlePlayPause = () => play(textToRead);
  const isCurrentlyPlaying = isPlaying && activeText === textToRead;
  const isCurrentlyLoading = isLoading && activeText === textToRead;

  return (
    <>
      <Dialog open={isOpen} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-4xl">
          <DialogHeader >
            <DialogTitle className="flex items-center gap-2">
              <Brain className="h-5 w-5" />
              Resumen Semántico de "{topic}"
            </DialogTitle>
            <DialogDescription>
              Análisis semántico profundo de la colección con agrupación de conceptos y patrones
            </DialogDescription>
          </DialogHeader>
          <ScrollArea className="max-h-[70vh] pr-4">
            <div className="space-y-6">
              {/* Resumen Semántico Principal */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <Brain className="h-4 w-4" />
                      Resumen Semántico
                    </div>
                    <Button variant="ghost" size="icon" onClick={handlePlayPause} disabled={isCurrentlyLoading}>
                      {isCurrentlyLoading ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : isCurrentlyPlaying ? (
                        <Pause className="h-4 w-4" />
                      ) : (
                        <Volume2 className="h-4 w-4" />
                      )}
                    </Button>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground whitespace-pre-wrap leading-relaxed">
                    {semanticData.resumen_semantico}
                  </p>
                </CardContent>
              </Card>

              {/* Temas Transversales */}
              {semanticData.temas_transversales.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Network className="h-4 w-4" />
                      Temas Transversales
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="flex flex-wrap gap-2">
                      {semanticData.temas_transversales.map((tema: any, index: number) => (
                        <Badge
                          key={index}
                          className="cursor-pointer hover:bg-primary/80 transition-colors"
                          onClick={() => handleThemeClick(tema)}
                        >
                          {typeof tema === 'string' ? tema : tema.tema}
                        </Badge>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}
 
              {/* Conceptos Centrales */}
              {semanticData.conceptos_centrales.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Lightbulb className="h-4 w-4" />
                      Conceptos Centrales
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {semanticData.conceptos_centrales.map((concepto: string, index: number) => (
                        <div
                          key={index}
                          className="p-4 bg-muted/50 rounded-lg cursor-pointer hover:bg-muted transition-colors border border-transparent hover:border-muted-foreground/20"
                          onClick={() => handleConceptClick(concepto)}
                        >
                          <div className="text-sm font-medium">
                            {concepto}
                          </div>
                          <div className="text-xs text-muted-foreground mt-1">
                            Haz clic para ver más detalles
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}
 
              {/* Patrones Semánticos - Estadísticas */}
              {semanticData.patrones_semanticos && Object.keys(semanticData.patrones_semanticos).length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      Estadísticas del Análisis
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
                      {semanticData.patrones_semanticos.total_documentos && (
                        <div className="p-3 bg-muted rounded-md">
                          <div className="text-2xl font-bold text-primary">
                            {semanticData.patrones_semanticos.total_documentos}
                          </div>
                          <div className="text-xs text-muted-foreground">Documentos</div>
                        </div>
                      )}
                      {semanticData.patrones_semanticos.total_chunks_analizados && (
                        <div className="p-3 bg-muted rounded-md">
                          <div className="text-2xl font-bold text-primary">
                            {semanticData.patrones_semanticos.total_chunks_analizados}
                          </div>
                          <div className="text-xs text-muted-foreground">Fragmentos</div>
                        </div>
                      )}
                      {semanticData.patrones_semanticos.temas_identificados && (
                        <div className="p-3 bg-muted rounded-md">
                          <div className="text-2xl font-bold text-primary">
                            {semanticData.patrones_semanticos.temas_identificados}
                          </div>
                          <div className="text-xs text-muted-foreground">Temas</div>
                        </div>
                      )}
                      <div className="p-3 bg-muted rounded-md">
                        <div className="text-2xl font-bold text-primary">
                          {semanticData.conceptos_centrales.length}
                        </div>
                        <div className="text-xs text-muted-foreground">Conceptos</div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}
 
              {/* Brechas de Conocimiento */}
              {semanticData.brechas_conocimiento.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <HelpCircle className="h-4 w-4" />
                      Brechas de Conocimiento
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setIsKnowledgeGapsDialogOpen(true)}
                        className="ml-auto"
                      >
                        <Expand className="h-4 w-4" />
                      </Button>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {semanticData.brechas_conocimiento.slice(0, 3).map((brecha: string, index: number) => (
                        <div key={index} className="p-4 bg-muted/50 border-l-4 border-muted-foreground/30 rounded-r-lg">
                          <div className="text-sm text-foreground">
                            {brecha}
                          </div>
                        </div>
                      ))}
                      {semanticData.brechas_conocimiento.length > 3 && (
                        <div className="text-center">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setIsKnowledgeGapsDialogOpen(true)}
                          >
                            Ver todas las {semanticData.brechas_conocimiento.length} brechas
                          </Button>
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          </ScrollArea>
          <DialogFooter>
            <Button variant="outline" onClick={() => onOpenChange(false)}>Cerrar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Diálogo secundario para mostrar detalles del tema transversal */}
      <Dialog open={isThemeDialogOpen} onOpenChange={setIsThemeDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Detalles del Tema Transversal</DialogTitle>
          </DialogHeader>
          {selectedTheme && (
            <ScrollArea className="max-h-[60vh] pr-4">
              <div className="space-y-4">
                <div>
                  <h4 className="font-semibold text-lg mb-2">
                    {typeof selectedTheme === 'string' ? selectedTheme : selectedTheme.tema}
                  </h4>
                </div>
                {typeof selectedTheme !== 'string' && selectedTheme.citas && selectedTheme.citas.length > 0 && (
                  <div>
                    <h5 className="font-semibold mb-3">Citas Relacionadas:</h5>
                    <div className="space-y-3">
                      {selectedTheme.citas.map((cita: any, i: number) => (
                        <div key={i} className="p-3 bg-muted rounded-md">
                          <div className="font-medium text-sm mb-1">{cita.documento}</div>
                          <div className="text-sm text-muted-foreground italic">"{cita.cita}"</div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </ScrollArea>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsThemeDialogOpen(false)}>Cerrar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Diálogo para mostrar detalles del concepto */}
      <Dialog open={isConceptDialogOpen} onOpenChange={setIsConceptDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Detalles del Concepto</DialogTitle>
          </DialogHeader>
          {selectedConcept && (
            <ScrollArea className="max-h-[60vh] pr-4">
              <div className="space-y-4">
                <div>
                  <h4 className="font-semibold text-lg mb-3">
                    {selectedConcept.split(':')[0]}
                  </h4>
                  <div className="p-4 bg-muted/50 rounded-lg">
                    <p className="text-sm leading-relaxed">
                      {selectedConcept.split(':').slice(1).join(':').trim()}
                    </p>
                  </div>
                </div>

                <div className="mt-6">
                  <h5 className="font-semibold mb-3 text-sm">Definición y contexto:</h5>
                  <div className="p-4 bg-blue-50/50 border-l-4 border-blue-200 rounded-r-lg">
                    {(() => {
                      // Parsear el concepto en formato "CONCEPTO: DEFINICIÓN"
                      const conceptParts = selectedConcept?.split(':');
                      if (conceptParts && conceptParts.length >= 2) {
                        const conceptName = conceptParts[0].trim();
                        const conceptDefinition = conceptParts.slice(1).join(':').trim();
                        return (
                          <div className="space-y-3">
                            <div>
                              <h6 className="font-medium text-sm text-blue-800 mb-1">Concepto:</h6>
                              <p className="text-sm font-semibold">{conceptName}</p>
                            </div>
                            <div>
                              <h6 className="font-medium text-sm text-blue-800 mb-1">Definición:</h6>
                              <p className="text-sm text-muted-foreground leading-relaxed">{conceptDefinition}</p>
                            </div>
                            <div className="mt-4 pt-3 border-t border-blue-200">
                              <p className="text-xs text-blue-600">
                                💡 Este concepto fue identificado como central en el análisis semántico de la colección.
                                Para profundizar, puedes realizar una búsqueda dirigida en la colección.
                              </p>
                            </div>
                          </div>
                        );
                      } else {
                        return (
                          <div className="space-y-3">
                            <p className="text-sm text-muted-foreground leading-relaxed">{selectedConcept}</p>
                            <div className="mt-4 pt-3 border-t border-blue-200">
                              <p className="text-xs text-blue-600">
                                💡 Este concepto fue identificado como central en el análisis semántico de la colección.
                              </p>
                            </div>
                          </div>
                        );
                      }
                    })()}
                  </div>
                </div>
              </div>
            </ScrollArea>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsConceptDialogOpen(false)}>Cerrar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Diálogo para mostrar las brechas de conocimiento en grande */}
      <QuestionSliderDialog
        isOpen={isKnowledgeGapsDialogOpen}
        onOpenChange={setIsKnowledgeGapsDialogOpen}
        questions={semanticData.brechas_conocimiento || []}
        title="Brechas de Conocimiento Identificadas"
      />
    </>
  );
}
