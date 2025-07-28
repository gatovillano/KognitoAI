// En: src/app/(dashboard)/rag/analysis-result-dialog.tsx
'use client';

import { useState } from 'react';

import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
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

  // Map backend field names to frontend expected field names
  const mappedAnalysis = {
    resumen_ejecutivo: analysis.executive_summary || analysis.resumen_ejecutivo || 'No summary available',
<<<<<<< HEAD
    analisis_general: analysis.general_analysis || analysis.analisis_general || 'No hay análisis general disponible',
    temas_clave_avanzados: extractThemes(analysis.key_themes || analysis.temas_clave_avanzados || analysis.code_structure),
=======
    temas_clave_avanzados: ensureArray(analysis.key_themes || analysis.temas_clave_avanzados || analysis.code_structure),
>>>>>>> parent of 8b033aa (Feat: Implement workspace-level data filtering and enhance analysis)
    conceptos_centrales: ensureArray(analysis.central_concepts || analysis.conceptos_centrales || analysis.design_patterns),
    relaciones_conceptos: ensureArray(analysis.concept_relationships || analysis.relaciones_conceptos || analysis.dependencies),
    preguntas_para_explorar: ensureArray(analysis.knowledge_gaps || analysis.preguntas_para_explorar || analysis.potential_issues),
    recomendaciones: ensureArray(analysis.recommendations)
  };

  return (
    <>
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
<<<<<<< HEAD
                    <h3 className="font-semibold mb-2">Análisis General</h3>
                    <div className="text-sm text-muted-foreground p-3 bg-muted border-l-4 border-blue-200 rounded-md">
                        <InlineMarkdownRenderer content={mappedAnalysis.analisis_general} />
                    </div>
                </div>
                <div>
                    <h3 className="font-semibold mb-2">Temas Clave</h3>
                    <div className="space-y-3">
=======
                    <h3 className="font-semibold mb-2">Temas Clave Avanzados</h3>
                    <div className="flex flex-wrap gap-2">
>>>>>>> parent of 8b033aa (Feat: Implement workspace-level data filtering and enhance analysis)
                        {Array.isArray(mappedAnalysis.temas_clave_avanzados) && mappedAnalysis.temas_clave_avanzados.length > 0 ? (
                            mappedAnalysis.temas_clave_avanzados.map((topic: any, i: number) => (
                                <div key={i} className="border rounded-lg p-3 bg-muted/30">
                                    <Badge className="mb-2">
                                        {topic.name || topic.description || 'Tema sin nombre'}
                                    </Badge>
                                    {topic.quotes && topic.quotes.length > 0 && (
                                        <div className="mt-2 space-y-2">
                                            <h4 className="text-sm font-medium text-muted-foreground">Citas relacionadas:</h4>
                                            {topic.quotes.slice(0, 2).map((quote: any, qIndex: number) => (
                                                <blockquote key={qIndex} className="text-xs italic text-muted-foreground border-l-2 border-primary/20 pl-3 py-1">
                                                    "{quote.quote || quote}"
                                                    {quote.document_title && (
                                                        <cite className="block text-xs font-medium mt-1">
                                                            — {quote.document_title}
                                                        </cite>
                                                    )}
                                                </blockquote>
                                            ))}
                                            {topic.quotes.length > 2 && (
                                                <p className="text-xs text-muted-foreground">
                                                    +{topic.quotes.length - 2} citas más...
                                                </p>
                                            )}
                                        </div>
                                    )}
                                </div>
                            ))
                        ) : (
                            <p className="text-sm text-muted-foreground">No hay temas clave disponibles.</p>
                        )}
                    </div>
                </div>
                <div>
                    <h3 className="font-semibold mb-2">Conceptos Centrales</h3>
                    <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
                        {Array.isArray(mappedAnalysis.conceptos_centrales) && mappedAnalysis.conceptos_centrales.length > 0 ? (
                            mappedAnalysis.conceptos_centrales.map((concept: string, i: number) => <li key={i}>{concept}</li>)
                        ) : (
                            <li className="text-sm text-muted-foreground">No hay conceptos centrales disponibles.</li>
                        )}
                    </ul>
                </div>
                <div>
                    <h3 className="font-semibold mb-2">Relaciones entre Conceptos</h3>
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
                </div>
                <div>
                    <h3 className="font-semibold mb-4">Problemas Potenciales o Preguntas para Explorar</h3>
                    {Array.isArray(mappedAnalysis.preguntas_para_explorar) && mappedAnalysis.preguntas_para_explorar.length > 0 ? (
                      <Card
                        className="cursor-pointer hover:shadow-lg hover:scale-[1.02] transition-all duration-300 border-2 hover:border-primary/20 group"
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
                </div>
                <div>
                    <h3 className="font-semibold mb-2">Recomendaciones</h3>
                    <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
                        {Array.isArray(mappedAnalysis.recomendaciones) && mappedAnalysis.recomendaciones.length > 0 ? (
                            mappedAnalysis.recomendaciones.map((rec: string, i: number) => <li key={i}>{rec}</li>)
                        ) : (
                            <li className="text-sm text-muted-foreground">No hay recomendaciones disponibles.</li>
                        )}
                    </ul>
                </div>
<<<<<<< HEAD
                {mappedAnalysis.reflexiones_finales.length > 0 && (
                    <div>
                        <h3 className="font-semibold mb-2">Reflexiones Finales</h3>
                        <div className="space-y-2">
                            {mappedAnalysis.reflexiones_finales.map((reflection: string, i: number) => (
                                <div key={i} className="text-sm text-muted-foreground p-3 bg-muted-50 border-l-4 border-green-200 rounded-md">
                                    <InlineMarkdownRenderer content={reflection} />
                                </div>
                            ))}
                        </div>
                    </div>
                )}
=======
>>>>>>> parent of 8b033aa (Feat: Implement workspace-level data filtering and enhance analysis)
            </div>
        </ScrollArea>
        <div className="flex justify-between mt-4">
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
        </div>
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
