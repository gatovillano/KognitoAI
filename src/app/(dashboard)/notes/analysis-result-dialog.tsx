'use client';

import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { InlineMarkdownRenderer } from '@/components/InlineMarkdownRenderer';
import { Lightbulb, FileText, GitBranch, AlertTriangle } from 'lucide-react';

interface AnalysisResultDialogProps {
  analysis: any; // Aquí pasaremos el analysisResult
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
}

export function AnalysisResultDialog({ analysis, isOpen, onOpenChange }: AnalysisResultDialogProps) {
  if (!analysis) return null;

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-5xl w-full max-h-[95vh] sm:max-h-[90vh] p-4 sm:p-6">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-lg sm:text-xl">
            <Lightbulb className="h-5 w-5" />
            Resultados del Análisis de Notas
          </DialogTitle>
          <DialogDescription>
            Aquí tienes el análisis detallado de tus notas, organizado por secciones.
          </DialogDescription>
        </DialogHeader>

        <Tabs defaultValue="summary" className="w-full">
          <TabsList className="grid w-full grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
            <TabsTrigger value="summary">Resumen</TabsTrigger>
            {analysis && (analysis.cross_cutting_themes?.length > 0 || analysis.key_themes?.length > 0) && (
              <TabsTrigger value="themes">Temas</TabsTrigger>
            )}
            {analysis && (analysis.central_concepts?.length > 0 || analysis.concept_relationships?.length > 0) && (
              <TabsTrigger value="concepts">Conceptos</TabsTrigger>
            )}
            {analysis && analysis.identified_connections?.length > 0 && (
              <TabsTrigger value="connections">Conexiones</TabsTrigger>
            )}
            {analysis && (analysis.emergent_knowledge_gaps?.length > 0 || analysis.knowledge_gaps?.length > 0) && (
              <TabsTrigger value="gaps">Brechas</TabsTrigger>
            )}
            {analysis && (analysis.final_reflections?.length > 0 || analysis.collection_insights?.length > 0 || analysis.methodological_notes?.length > 0) && (
              <TabsTrigger value="reflections">Reflexiones</TabsTrigger>
            )}
            {analysis && (analysis.general_analysis || analysis.discipline?.length > 0 || analysis.authorial_tone) && (
              <TabsTrigger value="details">Detalles</TabsTrigger>
            )}
          </TabsList>

          <ScrollArea className="h-[70vh] sm:h-[60vh] mt-4">
            {/* Contenido de las pestañas se añadirá aquí */}
            <TabsContent value="summary" className="space-y-4">
              {analysis && (analysis.collection_summary || analysis.executive_summary) && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <FileText className="h-4 w-4" />
                      Resumen
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    {analysis.collection_summary && (
                      <div className="mb-4">
                        <h4 className="font-semibold mb-1">Resumen de la Colección:</h4>
                        <InlineMarkdownRenderer content={analysis.collection_summary} />
                      </div>
                    )}
                    {analysis.executive_summary && (
                      <div>
                        <h4 className="font-semibold mb-1">Resumen Ejecutivo:</h4>
                        <InlineMarkdownRenderer content={analysis.executive_summary} />
                      </div>
                    )}
                  </CardContent>
                </Card>
              )}
            </TabsContent>

            <TabsContent value="themes" className="space-y-4">
              {analysis && analysis.cross_cutting_themes?.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Lightbulb className="h-4 w-4" />
                      Temas Transversales
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      {analysis.cross_cutting_themes.map((theme: any, index: number) => (
                        <div key={index} className="border-l-4 border-blue-500 pl-4">
                          <h4 className="font-medium">{theme.theme}</h4>
                          {theme.related_quotes && theme.related_quotes.map((quote: any, qIndex: number) => (
                            <blockquote key={qIndex} className="mt-2 border-l-2 pl-4 italic text-muted-foreground">
                              <InlineMarkdownRenderer content={quote.quote} />
                              {quote.document_title && <footer className="text-xs mt-1">— {quote.document_title}</footer>}
                            </blockquote>
                          ))}
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              {analysis && analysis.key_themes?.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Lightbulb className="h-4 w-4" />
                      Temas Clave
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      {analysis.key_themes.map((theme: any, index: number) => (
                        <div key={index} className="border-l-4 border-green-500 pl-4">
                          <h4 className="font-medium">{theme.theme}</h4>
                          {theme.related_quotes && theme.related_quotes.map((quote: any, qIndex: number) => (
                            <blockquote key={qIndex} className="mt-2 border-l-2 pl-4 italic text-muted-foreground">
                              <InlineMarkdownRenderer content={quote.quote} />
                              {quote.document_title && <footer className="text-xs mt-1">— {quote.document_title}</footer>}
                            </blockquote>
                          ))}
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}
            </TabsContent>

            <TabsContent value="concepts" className="space-y-4">
              {analysis && analysis.central_concepts?.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Lightbulb className="h-4 w-4" />
                      Conceptos Centrales
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="list-disc pl-5 space-y-1">
                      {analysis.central_concepts.map((concept: string, index: number) => (
                        <li key={index}><InlineMarkdownRenderer content={concept} /></li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              )}

              {analysis && analysis.concept_relationships?.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <GitBranch className="h-4 w-4" />
                      Relaciones entre Conceptos
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="list-disc pl-5 space-y-1">
                      {analysis.concept_relationships.map((rel: string, index: number) => (
                        <li key={index}><InlineMarkdownRenderer content={rel} /></li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              )}
            </TabsContent>

            <TabsContent value="connections" className="space-y-4">
              {analysis && analysis.identified_connections?.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Lightbulb className="h-4 w-4" />
                      Conexiones Identificadas
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      {analysis.identified_connections.map((conn: any, index: number) => (
                        <div key={index} className="border-l-4 border-purple-500 pl-4">
                          <h4 className="font-medium">Documentos: {conn.document_titles.join(', ')}</h4>
                          <p className="text-sm text-muted-foreground"><InlineMarkdownRenderer content={conn.insight} /></p>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}
            </TabsContent>

            <TabsContent value="gaps" className="space-y-4">
              {analysis && analysis.emergent_knowledge_gaps?.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <AlertTriangle className="h-4 w-4 text-orange-500" />
                      Brechas de Conocimiento Emergentes
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="list-disc pl-5 space-y-1">
                      {analysis.emergent_knowledge_gaps.map((gap: string, index: number) => (
                        <li key={index}><InlineMarkdownRenderer content={gap} /></li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              )}

              {analysis && analysis.knowledge_gaps?.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <AlertTriangle className="h-4 w-4 text-orange-500" />
                      Brechas de Conocimiento
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="list-disc pl-5 space-y-1">
                      {analysis.knowledge_gaps.map((gap: string, index: number) => (
                        <li key={index}><InlineMarkdownRenderer content={gap} /></li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              )}
            </TabsContent>

            <TabsContent value="reflections" className="space-y-4">
              {analysis && analysis.final_reflections?.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Lightbulb className="h-4 w-4" />
                      Reflexiones Finales
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="list-disc pl-5 space-y-1">
                      {analysis.final_reflections.map((reflection: string, index: number) => (
                        <li key={index}><InlineMarkdownRenderer content={reflection} /></li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              )}

              {analysis && analysis.collection_insights?.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Lightbulb className="h-4 w-4" />
                      Insights de la Colección
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="list-disc pl-5 space-y-1">
                      {analysis.collection_insights.map((insight: string, index: number) => (
                        <li key={index}><InlineMarkdownRenderer content={insight} /></li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              )}

              {analysis && analysis.methodological_notes?.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Lightbulb className="h-4 w-4" />
                      Notas Metodológicas
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="list-disc pl-5 space-y-1">
                      {analysis.methodological_notes.map((note: string, index: number) => (
                        <li key={index}><InlineMarkdownRenderer content={note} /></li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              )}
            </TabsContent>

            <TabsContent value="details" className="space-y-4">
              {analysis && analysis.general_analysis && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <FileText className="h-4 w-4" />
                      Análisis General
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <InlineMarkdownRenderer content={analysis.general_analysis} />
                  </CardContent>
                </Card>
              )}

              {analysis && analysis.discipline?.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <FileText className="h-4 w-4" />
                      Disciplina
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="list-disc pl-5 space-y-1">
                      {analysis.discipline.map((disc: string, index: number) => (
                        <li key={index}><InlineMarkdownRenderer content={disc} /></li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              )}

              {analysis && analysis.authorial_tone && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <FileText className="h-4 w-4" />
                      Tono Autoral
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <InlineMarkdownRenderer content={analysis.authorial_tone} />
                  </CardContent>
                </Card>
              )}
            </TabsContent>

          </ScrollArea>
        </Tabs>

        <div className="flex flex-col sm:flex-row justify-end mt-4 gap-2">
          <Button onClick={() => onOpenChange(false)}>
            Cerrar
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
