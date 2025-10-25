// En: src/app/(dashboard)/rag/collection-analysis-dialog.tsx
'use client';

import { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Expand, HelpCircle, FileText, Network, Lightbulb, Link, Search, BarChart3 } from 'lucide-react';
import { QuestionSliderDialog } from '@/components/QuestionSliderDialog';
import { InlineMarkdownRenderer } from '@/components/InlineMarkdownRenderer';

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
  const [isKnowledgeGapsDialogOpen, setIsKnowledgeGapsDialogOpen] = useState(false);

  if (!analysis) {
    console.log("❌ CollectionAnalysisDialog: No analysis data provided");
    return null;
  }

  console.log("📁 CollectionAnalysisDialog - Analysis object:", analysis);
  console.log("📁 CollectionAnalysisDialog - Topic:", topic);

  // Map backend field names to frontend expected field names
  const mappedAnalysis = {
    resumen_general_coleccion: analysis.collection_summary || 'No summary available',
    temas_transversales: analysis.cross_cutting_themes || [],
    conceptos_centrales: analysis.central_concepts || [],
    relaciones_conceptos: analysis.concept_relationships || [],
    conexiones_identificadas: analysis.identified_connections || [],
    brechas_conocimiento: analysis.emergent_knowledge_gaps || [],
    reflexiones_finales: analysis.final_reflections || [],
    insights_coleccion: analysis.collection_insights || [],
    notas_metodologicas: analysis.methodological_notes || []
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
        <DialogContent className="max-w-5xl w-full max-h-[90vh] rounded-3xl backdrop-blur-xl bg-card/95 border-0 shadow-2xl flex flex-col p-0">
          <DialogHeader className="p-6 pb-0">
            <DialogTitle className="flex items-center gap-2 text-2xl font-bold text-foreground">
              <BarChart3 className="h-6 w-6" />
              Análisis Completo de la Colección &quot;{topic}&quot;
            </DialogTitle>
            <DialogDescription className="text-muted-foreground">
              Análisis profundo e interactivo de la colección con temas transversales, conexiones y brechas de conocimiento
            </DialogDescription>
          </DialogHeader>

          <div className="p-6 pt-0 flex flex-col flex-grow">
            <Tabs defaultValue="overview" className="w-full flex flex-col flex-grow">
              <TabsList className="grid w-full grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-8 text-xs bg-transparent border-b border-border/50 mb-4">
                <TabsTrigger value="overview">Resumen</TabsTrigger>
                <TabsTrigger value="themes">Temas</TabsTrigger>
                <TabsTrigger value="concepts">Conceptos</TabsTrigger>
                <TabsTrigger value="connections">Conexiones</TabsTrigger>
                <TabsTrigger value="relationships">Relaciones</TabsTrigger>
                <TabsTrigger value="insights">Insights</TabsTrigger>
                <TabsTrigger value="reflections">Reflexiones</TabsTrigger>
                <TabsTrigger value="gaps">Brechas</TabsTrigger>
              </TabsList>

              <ScrollArea className="flex-1 pr-4">
                <div className="space-y-6 pb-4"> {/* Añadido pb-4 para espacio al final del scroll */}
              {/* Pestaña de Resumen */}
              <TabsContent value="overview" className="space-y-3">
                <Card className="border-none shadow-none bg-transparent p-0">
                  <CardHeader className="px-0 pt-0 pb-2">
                    <CardTitle className="flex items-center gap-2 text-lg font-semibold text-foreground">
                      <FileText className="h-5 w-5" />
                      Resumen General de la Colección
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-0">
                    <div className="text-sm text-muted-foreground whitespace-pre-wrap leading-relaxed p-3 bg-muted rounded-md border border-border/50">
                      <InlineMarkdownRenderer content={mappedAnalysis.resumen_general_coleccion} />
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>
              {/* Pestaña de Temas Transversales */}
              <TabsContent value="themes" className="space-y-3">
                <Card className="border-none shadow-none bg-transparent p-0">
                  <CardHeader className="px-0 pt-0 pb-2">
                    <CardTitle className="flex items-center gap-2 text-lg font-semibold text-foreground">
                      <Network className="h-5 w-5" />
                      Temas Transversales
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-0">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {mappedAnalysis.temas_transversales?.map((t: any, index: number) => (
                        <div
                          key={index}
                          className="p-4 border rounded-lg hover:bg-muted/50 cursor-pointer transition-colors border-border/50"
                          onClick={() => handleThemeClick(t)}
                        >
                          <div className="font-medium mb-2 text-foreground">
                            {typeof t === 'string' ? t : t.theme}
                          </div>
                          {typeof t !== 'string' && t.related_quotes && (
                            <div className="text-xs text-muted-foreground">
                              {t.related_quotes.length} citas relacionadas
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>
              {/* Pestaña de Conceptos Centrales */}
              <TabsContent value="concepts" className="space-y-3">
                <Card className="border-none shadow-none bg-transparent p-0">
                  <CardHeader className="px-0 pt-0 pb-2">
                    <CardTitle className="flex items-center gap-2 text-lg font-semibold text-foreground">
                      <Lightbulb className="h-5 w-5" />
                      Conceptos Centrales
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-0">
                    <div className="space-y-3">
                      {mappedAnalysis.conceptos_centrales?.map((concepto: string, index: number) => (
                        <div key={index} className="p-3 bg-muted rounded-md border border-border/50">
                          <InlineMarkdownRenderer content={concepto} />
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>

              {/* Pestaña de Conexiones */}
              <TabsContent value="connections" className="space-y-3">
                <Card className="border-none shadow-none bg-transparent p-0">
                  <CardHeader className="px-0 pt-0 pb-2">
                    <CardTitle className="flex items-center gap-2 text-lg font-semibold text-foreground">
                      <Link className="h-5 w-5" />
                      Conexiones Identificadas
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-0">
                    <div className="space-y-3">
                      {mappedAnalysis.conexiones_identificadas?.map((conn: any, index: number) => (
                        <div
                          key={index}
                          className="p-3 border rounded-lg cursor-pointer hover:bg-muted/50 transition-colors border-border/50"
                          onClick={() => handleConnectionClick(conn)}
                        >
                          <div className="font-semibold text-sm mb-1 text-foreground">
                            {conn.documentos.join(' ↔ ')}
                          </div>
                          <InlineMarkdownRenderer content={conn.insight} />
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>

              {/* Pestaña de Relaciones */}
              <TabsContent value="relationships" className="space-y-3">
                <Card className="border-none shadow-none bg-transparent p-0">
                  <CardHeader className="px-0 pt-0 pb-2">
                    <CardTitle className="flex items-center gap-2 text-lg font-semibold text-foreground">
                      <Network className="h-5 w-5" />
                      Relaciones entre Conceptos
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-0">
                    <div className="space-y-3">
                      {mappedAnalysis.relaciones_conceptos?.map((relacion: string, index: number) => (
                        <div key={index} className="p-3 bg-muted rounded-md border border-border/50">
                          <InlineMarkdownRenderer content={relacion} />
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>

              {/* Pestaña de Insights */}
              <TabsContent value="insights" className="space-y-3">
                <Card className="border-none shadow-none bg-transparent p-0">
                  <CardHeader className="px-0 pt-0 pb-2">
                    <CardTitle className="flex items-center gap-2 text-lg font-semibold text-foreground">
                      <Lightbulb className="h-5 w-5" />
                      Insights de la Colección
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-0">
                    <div className="space-y-4">
                      {mappedAnalysis.insights_coleccion?.map((insight: string, index: number) => (
                        <div key={index} className="p-3 bg-blue-50 border-l-4 border-blue-200 rounded-r-lg border border-border/50">
                          <InlineMarkdownRenderer content={insight} />
                        </div>
                      ))}
                      {mappedAnalysis.notas_metodologicas && mappedAnalysis.notas_metodologicas.length > 0 && (
                        <div className="mt-6">
                          <h4 className="font-semibold mb-3 text-sm text-foreground">Notas Metodológicas</h4>
                          <div className="space-y-2">
                            {mappedAnalysis.notas_metodologicas.map((nota: string, index: number) => (
                              <div key={index} className="p-3 bg-gray-50 border-l-4 border-gray-200 rounded-r-lg border border-border/50">
                                <InlineMarkdownRenderer content={nota} />
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>

              {/* Pestaña de Reflexiones */}
              <TabsContent value="reflections" className="space-y-3">
                <Card className="border-none shadow-none bg-transparent p-0">
                  <CardHeader className="px-0 pt-0 pb-2">
                    <CardTitle className="flex items-center gap-2 text-lg font-semibold text-foreground">
                      <HelpCircle className="h-5 w-5" />
                      Reflexiones Finales
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-0">
                    <div className="space-y-4">
                      {mappedAnalysis.reflexiones_finales?.map((reflexion: string, index: number) => (
                        <div key={index} className="p-3 bg-green-50 border-l-4 border-green-200 rounded-r-lg border border-border/50">
                          <InlineMarkdownRenderer content={reflexion} />
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>

              {/* Pestaña de Brechas de Conocimiento */}
              <TabsContent value="gaps" className="space-y-3">
                <Card className="border-none shadow-none bg-transparent p-0">
                  <CardHeader className="px-0 pt-0 pb-2">
                    <CardTitle className="flex items-center gap-2 text-lg font-semibold text-foreground">
                      <Search className="h-5 w-5" />
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
                  <CardContent className="p-0">
                    {mappedAnalysis.brechas_conocimiento && mappedAnalysis.brechas_conocimiento.length > 0 ? (
                      <div className="space-y-3">
                        {mappedAnalysis.brechas_conocimiento.slice(0, 5).map((brecha: string, index: number) => (
                          <div key={index} className="p-3 bg-orange-50 border-l-4 border-orange-200 rounded-r-lg border border-border/50">
                            <InlineMarkdownRenderer content={brecha} />
                          </div>
                        ))}
                        {mappedAnalysis.brechas_conocimiento.length > 5 && (
                          <div className="text-center pt-4">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => setIsKnowledgeGapsDialogOpen(true)}
                            >
                              Ver todas las {mappedAnalysis.brechas_conocimiento.length} brechas
                            </Button>
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="text-center text-muted-foreground py-8">
                        No se identificaron brechas de conocimiento
                      </div>
                    )}
                  </CardContent>
                </Card>
              </TabsContent>
                </div>
              </ScrollArea>
            </Tabs>
          </div>

          <DialogFooter className="p-6 pt-0">
            <Button variant="outline" onClick={() => onOpenChange(false)} className="w-full sm:w-auto">Cerrar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>


      {/* Diálogo secundario para mostrar detalles de la conexión */}
      <Dialog open={isConnectionDialogOpen} onOpenChange={setIsConnectionDialogOpen}>
        <DialogContent className="max-w-xl w-full max-h-[90vh] rounded-3xl backdrop-blur-xl bg-card/95 border-0 shadow-2xl flex flex-col">
          <DialogHeader>
            <DialogTitle className="text-xl font-bold text-foreground">Detalles de la Conexión</DialogTitle>
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
        <DialogContent className="max-w-xl w-full max-h-[90vh] rounded-3xl backdrop-blur-xl bg-card/95 border-0 shadow-2xl flex flex-col">
          <DialogHeader>
            <DialogTitle className="text-xl font-bold text-foreground">Detalles del Tema Transversal</DialogTitle>
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

      {/* Diálogo para mostrar las brechas de conocimiento en grande */}
      <QuestionSliderDialog
        isOpen={isKnowledgeGapsDialogOpen}
        onOpenChange={setIsKnowledgeGapsDialogOpen}
        questions={mappedAnalysis.brechas_conocimiento || []}
        title="Brechas de Conocimiento"
      />
    </>
  );
}
