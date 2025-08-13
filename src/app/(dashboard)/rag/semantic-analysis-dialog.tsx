// En: src/app/(dashboard)/rag/semantic-analysis-dialog.tsx
'use client';

import { useState, useMemo } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Expand, HelpCircle, Brain, Network, Lightbulb, Volume2, Loader2, Pause, Calendar } from 'lucide-react';
import { QuestionSliderDialog } from '@/components/QuestionSliderDialog';
import { useTextToSpeech } from '@/hooks/useTextToSpeech';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

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

  // Mueve los hooks que dependen de `analysis` aquí, pero maneja el caso de que `analysis` sea null
  const semanticData = useMemo(() => {
    if (!analysis) {
      return {
        resumen_semantico: 'No hay resumen disponible',
        temas_transversales: [],
        conceptos_centrales: [],
        brechas_conocimiento: [],
        patrones_semanticos: {}
      };
    }
    return {
      resumen_semantico: analysis.resumen_semantico || 'No hay resumen disponible',
      temas_transversales: analysis.temas_transversales || [],
      conceptos_centrales: analysis.conceptos_centrales || [],
      brechas_conocimiento: analysis.brechas_conocimiento || [],
      patrones_semanticos: analysis.patrones_semanticos || {}
    };
  }, [analysis]);

  const textToRead = useMemo(() => {
    return `Resumen Semántico: ${semanticData.resumen_semantico}`;
  }, [semanticData]);

  if (!analysis) {
    console.log("❌ SemanticAnalysisDialog: No analysis data provided");
    return null;
  }

  console.log("🧠 SemanticAnalysisDialog - Analysis object:", analysis);
  console.log("🧠 SemanticAnalysisDialog - Topic:", topic);

  const handleThemeClick = (theme: any) => {
    setSelectedTheme(theme);
    setIsThemeDialogOpen(true);
  };

  const handleConceptClick = (concept: string) => {
    setSelectedConcept(concept);
    setIsConceptDialogOpen(true);
  };

  const handlePlayPause = () => play(textToRead);
  const isCurrentlyPlaying = isPlaying && activeText === textToRead;
  const isCurrentlyLoading = isLoading && activeText === textToRead;

  return (
    <>
      <Dialog open={isOpen} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-full sm:max-w-4xl max-h-[90vh] rounded-3xl backdrop-blur-xl bg-card/95 border-0 shadow-2xl">
          <DialogHeader >
            <DialogTitle className="flex items-center gap-2">
              <Brain className="h-5 w-5" />
              Resumen Semántico de &quot;{topic}&quot;
            </DialogTitle>
            <DialogDescription>
              Análisis semántico profundo de la colección con agrupación de conceptos y patrones
            </DialogDescription>
          </DialogHeader>
          <ScrollArea className="h-[75vh] sm:h-[70vh] pr-4">
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
                          className="text-xs cursor-pointer bg-purple-800 text-white hover:bg-purple-700 transition-colors"
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
                          <div className="text-sm font-medium line-clamp-2">
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>{concepto}</ReactMarkdown>
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
                    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4 text-center">
                      {semanticData.patrones_semanticos.total_documentos && (
                        <div className="p-3 bg-muted rounded-md">
                          <div className="text-2xl font-bold text-purple-600">
                            {semanticData.patrones_semanticos.total_documentos}
                          </div>
                          <div className="text-xs text-purple-400">Documentos</div>
                        </div>
                      )}
                      {semanticData.patrones_semanticos.total_chunks_analizados && (
                        <div className="p-3 bg-muted rounded-md">
                          <div className="text-2xl font-bold text-purple-600">
                            {semanticData.patrones_semanticos.total_chunks_analizados}
                          </div>
                          <div className="text-xs text-purple-400">Fragmentos</div>
                        </div>
                      )}
                      {semanticData.patrones_semanticos.temas_identificados && (
                        <div className="p-3 bg-muted rounded-md">
                          <div className="text-2xl font-bold text-purple-600">
                            {semanticData.patrones_semanticos.temas_identificados}
                          </div>
                          <div className="text-xs text-purple-400">Temas</div>
                        </div>
                      )}
                      <div className="p-3 bg-muted rounded-md">
                        <div className="text-2xl font-bold text-purple-600">
                          {semanticData.conceptos_centrales.length}
                        </div>
                        <div className="text-xs text-purple-400">Conceptos</div>
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
                        <div key={index} className="p-3 bg-purple-50 border border-purple-200 rounded-lg">
                          <p className="text-xs font-medium text-purple-800 mb-1">Brecha Identificada:</p>
                          <div className="text-sm text-purple-700"><ReactMarkdown remarkPlugins={[remarkGfm]}>{brecha}</ReactMarkdown></div>
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
          {analysis?.analysis_metadata && (
            <div className="space-y-2 text-xs text-muted-foreground mt-auto pt-3 border-t border-border/50">
              {analysis.analysis_metadata.tool_used && (
                <div className="mb-2">
                  <Badge variant="outline" className="text-xs font-mono bg-slate-50 text-slate-600 border-slate-200 dark:bg-slate-800 dark:text-slate-400 dark:border-slate-700">
                    {analysis.analysis_metadata.tool_used}
                  </Badge>
                </div>
              )}
              {analysis.analysis_metadata.created_at && (
                <div className="flex items-center gap-1">
                  <Calendar className="h-3 w-3" />
                  <span className="truncate">Creado: {new Date(analysis.analysis_metadata.created_at).toLocaleDateString('es-ES', {
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                  })}</span>
                </div>
              )}
            </div>
          )}
          <DialogFooter className="flex flex-col-reverse sm:flex-row sm:justify-end gap-2 mt-4">
            <Button variant="outline" onClick={() => onOpenChange(false)} className="w-full sm:w-auto">Cerrar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Diálogo secundario para mostrar detalles del tema transversal */}
      <Dialog open={isThemeDialogOpen} onOpenChange={setIsThemeDialogOpen}>
        <DialogContent className="max-w-lg w-full max-h-[90vh] p-4 sm:p-6">
          <DialogHeader>
            <DialogTitle className="text-lg sm:text-xl">Detalles del Tema Transversal</DialogTitle>
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
                          <div className="text-sm text-muted-foreground italic">&quot;{cita.cita}&quot;</div>
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
        <DialogContent className="max-w-lg w-full max-h-[90vh] p-4 sm:p-6">
          <DialogHeader>
            <DialogTitle className="text-lg sm:text-xl">Detalles del Concepto</DialogTitle>
          </DialogHeader>
          {selectedConcept && (
            <ScrollArea className="max-h-[60vh] pr-4">
              <div className="space-y-4">
                <div>
                  <h4 className="font-semibold text-lg mb-3">
                    {selectedConcept.split(':')[0]}
                  </h4>
                  <div className="p-4 bg-muted/50 rounded-lg">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {selectedConcept.split(':').slice(1).join(':').trim()}
                    </ReactMarkdown>
                  </div>
                </div>

                <div className="mt-6">
                  <h5 className="font-semibold mb-3 text-sm">Definición y contexto:</h5>
                  <div className="p-4 bg-purple-50/50 border-l-4 border-purple-200 rounded-r-lg">
                    {(() => {
                      // Parsear el concepto en formato "CONCEPTO: DEFINICIÓN"
                      const conceptParts = selectedConcept?.split(':');
                      if (conceptParts && conceptParts.length >= 2) {
                        const conceptName = conceptParts[0].trim();
                        const conceptDefinition = conceptParts.slice(1).join(':').trim();
                        return (
                          <div className="space-y-3">
                            <div>
                              <h6 className="font-medium text-sm text-purple-800 mb-1">Concepto:</h6>
                              <p className="text-sm font-semibold">{conceptName}</p>
                            </div>
                            <div>
                              <h6 className="font-medium text-sm text-purple-800 mb-1">Definición:</h6>
                              <ReactMarkdown remarkPlugins={[remarkGfm]}>{conceptDefinition}</ReactMarkdown>
                            </div>
                            <div className="mt-4 pt-3 border-t border-purple-200">
                              <p className="text-xs text-purple-600">
                                💡 Este concepto fue identificado como central en el análisis semántico de la colección.
                                Para profundizar, puedes realizar una búsqueda dirigida en la colección.
                              </p>
                            </div>
                          </div>
                        );
                      } else {
                        return (
                          <div className="space-y-3">
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>{selectedConcept}</ReactMarkdown>
                            <div className="mt-4 pt-3 border-t border-purple-200">
                              <p className="text-xs text-purple-600">
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
