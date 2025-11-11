// En: src/app/(dashboard)/rag/analysis-result-dialog.tsx
'use client';

import { useState } from 'react';

import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { InlineMarkdownRenderer } from '@/components/InlineMarkdownRenderer';
import { Expand, HelpCircle } from 'lucide-react';
import { QuestionSliderDialog } from '@/components/QuestionSliderDialog';
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
  const [isQuestionsDialogOpen, setIsQuestionsDialogOpen] = useState(false);
  const [selectedThemeForDialog, setSelectedThemeForDialog] = useState<any>(null);
  const [isThemeQuotesDialogOpen, setIsThemeQuotesDialogOpen] = useState(false);

  if (!analysis) return null;

  // Log the analysis object for debugging
  console.log("Analysis object:", analysis);

  // Helper function to ensure array
  const ensureArray = (value: any): string[] => {
    if (Array.isArray(value)) return value;
    if (typeof value === 'string') return [value];
    return [];
  };

  // Helper function to extract themes from ThemeReference objects
  const extractThemes = (themes: any): any[] => {
    if (!Array.isArray(themes)) return [];
    return themes.map(theme => {
      // Si es un objeto ThemeReference con estructura {theme: string, related_quotes: [...]}
      if (typeof theme === 'object' && theme.theme) {
        return {
          name: theme.theme,
          quotes: theme.related_quotes || [],
          description: theme.theme // Para compatibilidad con el frontend
        };
      }
      // Si es un string simple
      if (typeof theme === 'string') {
        return { name: theme, description: theme, quotes: [] };
      }
      // Si es otro tipo de objeto
      return {
        name: theme.component || theme.description || theme.name || 'Tema sin nombre',
        description: theme.description || theme.component || theme.name || '',
        quotes: theme.quotes || theme.related_quotes || []
      };
    });
  };

  const handleThemeClick = (theme: any) => {
    setSelectedThemeForDialog(theme);
    setIsThemeQuotesDialogOpen(true);
  };

  // Map backend field names to frontend expected field names
  const mappedAnalysis = {
    resumen_ejecutivo: analysis.executive_summary || analysis.resumen_ejecutivo || 'No summary available',
    temas_clave_avanzados: extractThemes(analysis.key_themes || analysis.temas_clave_avanzados || analysis.code_structure),
    conceptos_centrales: ensureArray(analysis.central_concepts || analysis.conceptos_centrales || analysis.design_patterns),
    relaciones_conceptos: ensureArray(analysis.concept_relationships || analysis.relaciones_conceptos || analysis.dependencies),
    preguntas_para_explorar: ensureArray(analysis.knowledge_gaps || analysis.preguntas_para_explorar || analysis.potential_issues),
    recomendaciones: ensureArray(analysis.recommendations),
    analisis_general: analysis.general_analysis || analysis.analisis_general || 'No general analysis available',
    reflexiones_finales: ensureArray(analysis.final_reflections || analysis.reflexiones_finales)
  };

  return (
    <>
    <Dialog open={isOpen} onOpenChange={onOpenChange}>

      <DialogContent className="max-w-4xl w-full max-h-[90vh] rounded-3xl backdrop-blur-xl bg-card/95 border-0 shadow-2xl flex flex-col p-0">
        <DialogHeader className="p-6 pb-4 border-b">
          <DialogTitle className="text-2xl font-bold text-foreground">Resultados del Análisis</DialogTitle>
          <DialogDescription className="text-muted-foreground truncate">
            Para el documento: {document?.file_name || 'Nombre no disponible'}
          </DialogDescription>
        </DialogHeader>
        <ScrollArea className="flex-1 p-6">
          <div className="space-y-6 pb-4">
            <Card className="border-none shadow-none bg-transparent p-0">
              <CardHeader className="px-0 pt-0 pb-2">
                <h3 className="font-semibold text-lg text-foreground">Resumen Ejecutivo por IA</h3>
              </CardHeader>
              <CardContent className="p-0">
                <p className="text-sm text-muted-foreground whitespace-pre-wrap leading-relaxed p-3 bg-muted rounded-md border border-border/50">{mappedAnalysis.resumen_ejecutivo}</p>
              </CardContent>
            </Card>
            <Card className="border-none shadow-none bg-transparent p-0">
              <CardHeader className="px-0 pt-0 pb-2">
                <h3 className="font-semibold text-lg text-foreground">Análisis General</h3>
              </CardHeader>
              <CardContent className="p-0">
                <div className="text-sm text-muted-foreground p-3 bg-muted border-l-4 border-blue-200 rounded-md border border-border/50">
                  <InlineMarkdownRenderer content={mappedAnalysis.analisis_general} />
                </div>
              </CardContent>
            </Card>
            <Card className="border-none shadow-none bg-transparent p-0">
              <CardHeader className="px-0 pt-0 pb-2">
                <h3 className="font-semibold text-lg text-foreground">Temas Clave</h3>
              </CardHeader>
              <CardContent className="p-0">
                <div className="flex flex-wrap gap-2">
                  {Array.isArray(mappedAnalysis.temas_clave_avanzados) && mappedAnalysis.temas_clave_avanzados.length > 0 ? (
                    mappedAnalysis.temas_clave_avanzados.map((topic: any, i: number) => (
                      <Badge
                        key={i}
                        className="text-xs cursor-pointer bg-blue-100 text-blue-800 border border-blue-200 hover:bg-blue-200 transition-colors"
                        onClick={() => handleThemeClick(topic)}
                      >
                        {topic.name || topic.description || 'Tema sin nombre'}
                      </Badge>
                    ))
                  ) : (
                    <p className="text-sm text-muted-foreground">No hay temas clave disponibles.</p>
                  )}
                </div>
              </CardContent>
            </Card>
            <Card className="border-none shadow-none bg-transparent p-0">
              <CardHeader className="px-0 pt-0 pb-2">
                <h3 className="font-semibold text-lg text-foreground">Conceptos Centrales</h3>
              </CardHeader>
              <CardContent className="p-0">
                <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
                  {Array.isArray(mappedAnalysis.conceptos_centrales) && mappedAnalysis.conceptos_centrales.length > 0 ? (
                    mappedAnalysis.conceptos_centrales.map((concept: string, i: number) => (
                      <li key={i}>
                        <InlineMarkdownRenderer content={concept} />
                      </li>
                    ))
                  ) : (
                    <li className="text-sm text-muted-foreground">No hay conceptos centrales disponibles.</li>
                  )}
                </ul>
              </CardContent>
            </Card>
            <Card className="border-none shadow-none bg-transparent p-0">
              <CardHeader className="px-0 pt-0 pb-2">
                <h3 className="font-semibold text-lg text-foreground">Relaciones entre Conceptos</h3>
              </CardHeader>
              <CardContent className="p-0">
                <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
                  {Array.isArray(mappedAnalysis.relaciones_conceptos) && mappedAnalysis.relaciones_conceptos.length > 0 ? (
                    mappedAnalysis.relaciones_conceptos.map((relation: string, i: number) => (
                      <li key={i}>
                        <InlineMarkdownRenderer content={relation} />
                      </li>
                    ))
                  ) : (
                    <li className="text-sm text-muted-foreground">No hay relaciones entre conceptos disponibles.</li>
                  )}
                </ul>
              </CardContent>
            </Card>
            <Card className="border-none shadow-none bg-transparent p-0">
              <CardHeader className="px-0 pt-0 pb-2">
                <h3 className="font-semibold text-lg text-foreground">Problemas Potenciales o Preguntas para Explorar</h3>
              </CardHeader>
              <CardContent className="p-0">
                {Array.isArray(mappedAnalysis.preguntas_para_explorar) && mappedAnalysis.preguntas_para_explorar.length > 0 ? (
                  <Card
                    className="cursor-pointer hover:shadow-lg hover:scale-[1.02] transition-all duration-300 border border-border/50 group"
                    onClick={() => setIsQuestionsDialogOpen(true)}
                  >
                    <CardContent className="p-4">
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <HelpCircle className="h-5 w-5 text-primary" />
                          <span className="font-medium text-sm">
                            {mappedAnalysis.preguntas_para_explorar.length} pregunta{mappedAnalysis.preguntas_para_explorar.length !== 1 ? 's' : ''} para explorar
                          </span>
                        </div>
                        <div className="opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                          <Expand className="h-4 w-4 text-muted-foreground" />
                        </div>
                      </div>
                      <p className="text-sm text-muted-foreground line-clamp-2 leading-relaxed">
                        {mappedAnalysis.preguntas_para_explorar[0]}
                      </p>
                      <div className="mt-3 text-xs text-primary/60 opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex items-center gap-1">
                        <Expand className="h-3 w-3" />
                        Haz clic para ver todas las preguntas
                      </div>
                    </CardContent>
                  </Card>
                ) : (
                  <p className="text-sm text-muted-foreground">No hay preguntas para explorar disponibles.</p>
                )}
              </CardContent>
            </Card>
            <Card className="border-none shadow-none bg-transparent p-0">
              <CardHeader className="px-0 pt-0 pb-2">
                <h3 className="font-semibold text-lg text-foreground">Recomendaciones</h3>
              </CardHeader>
              <CardContent className="p-0">
                <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
                  {Array.isArray(mappedAnalysis.recomendaciones) && mappedAnalysis.recomendaciones.length > 0 ? (
                    mappedAnalysis.recomendaciones.map((rec: string, i: number) => <li key={i}><InlineMarkdownRenderer content={rec} /></li>)
                  ) : (
                    <li className="text-sm text-muted-foreground">No hay recomendaciones disponibles.</li>
                  )}
                </ul>
              </CardContent>
            </Card>
            {mappedAnalysis.reflexiones_finales.length > 0 && (
              <Card className="border-none shadow-none bg-transparent p-0">
                <CardHeader className="px-0 pt-0 pb-2">
                  <h3 className="font-semibold text-lg text-foreground">Reflexiones Finales</h3>
                </CardHeader>
                <CardContent className="p-0">
                  <div className="space-y-2">
                    {mappedAnalysis.reflexiones_finales.map((reflection: string, i: number) => (
                      <div key={i} className="text-sm text-muted-foreground p-3 bg-muted border-l-4 border-green-200 rounded-md border border-border/50">
                        <InlineMarkdownRenderer content={reflection} />
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </ScrollArea>
        <DialogFooter className="p-6 pt-4 border-t gap-2">
          <Button
            variant="destructive"
            onClick={async () => {
              try {
                await apiClient.post('/api/delete-analysis', { task_id: analysis.id });
                toast.success('Análisis eliminado correctamente');
                onOpenChange(false);
              } catch (error) {
                toast.error('Error al eliminar el análisis');
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
        </DialogFooter>
      </DialogContent>
    </Dialog>

    {/* Diálogo secundario para mostrar citas relacionadas con el tema */}
    <Dialog open={isThemeQuotesDialogOpen} onOpenChange={setIsThemeQuotesDialogOpen}>
      <DialogContent className="max-w-xl w-full max-h-[90vh] rounded-3xl backdrop-blur-xl bg-card/95 border-0 shadow-2xl flex flex-col p-0">
        <DialogHeader className="p-6 pb-4 border-b">
          <DialogTitle className="text-xl font-bold text-foreground">Detalles del Tema</DialogTitle>
        </DialogHeader>
        <ScrollArea className="flex-1 p-6">
          {selectedThemeForDialog && (
            <div className="space-y-4">
              <p className="text-base font-semibold">{selectedThemeForDialog.name || selectedThemeForDialog.description || 'Tema sin nombre'}</p>
              {selectedThemeForDialog.quotes && selectedThemeForDialog.quotes.length > 0 && (
                <div>
                  <h4 className="font-semibold">Citas Relacionadas:</h4>
                  <ul className="list-disc list-inside text-sm text-muted-foreground space-y-2">
                    {selectedThemeForDialog.quotes.map((quote: any, i: number) => (
                      <li key={i}>
                        <strong>{quote.document_title || 'Documento desconocido'}</strong>: {quote.quote || quote}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </ScrollArea>
        <DialogFooter className="p-6 pt-4 border-t">
          <Button variant="outline" onClick={() => setIsThemeQuotesDialogOpen(false)}>Cerrar</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    {/* Diálogo para mostrar las preguntas para explorar en grande */}
    <QuestionSliderDialog
      isOpen={isQuestionsDialogOpen}
      onOpenChange={setIsQuestionsDialogOpen}
      questions={mappedAnalysis.preguntas_para_explorar || []}
      title="Preguntas para Explorar"
    />
  </>
  );
}