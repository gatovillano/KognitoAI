'use client';

import { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { InlineMarkdownRenderer } from '@/components/InlineMarkdownRenderer';
import { motion, AnimatePresence } from 'framer-motion';
import { QuestionSliderDialog } from '@/components/QuestionSliderDialog';
import { 
  FileText, 
  FolderKanban, 
  Brain, 
  Lightbulb, 
  Code, 
  BarChart3,
  Calendar,
  HelpCircle,
  Expand,
  AlertTriangle,
  Settings,
  GitBranch,
  Target,
  Zap
} from 'lucide-react';

interface Analysis {
  id: string;
  type: string;
  title: string;
  summary: string;
  created_at: string;
  updated_at: string;
  source_table: string;
  tool_used?: string;
  confidence_score?: number;
  action_suggestion?: string;
  related_items?: any[];
  full_data: any;
}

interface AnalysisDetailDialogProps {
  analysis: Analysis | null;
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
}

const getAnalysisIcon = (type: string) => {
  switch (type) {
    case 'document':
      return <FileText className="h-5 w-5 text-blue-500" />;
    case 'collection':
      return <FolderKanban className="h-5 w-5 text-green-500" />;
    case 'mindmap':
      return <Brain className="h-5 w-5 text-purple-500" />;
    case 'insight':
      return <Lightbulb className="h-5 w-5 text-yellow-500" />;
    case 'code':
      return <Code className="h-5 w-5 text-orange-500" />;
    case 'semantic':
      return <BarChart3 className="h-5 w-5 text-indigo-500" />;
    default:
      return <FileText className="h-5 w-5 text-gray-500" />;
  }
};

const getAnalysisTypeLabel = (type: string) => {
  switch (type) {
    case 'document':
      return 'Análisis de Documento';
    case 'collection':
      return 'Análisis de Colección';
    case 'mindmap':
      return 'Mapa Mental';
    case 'insight':
      return 'Insight Proactivo';
    case 'code':
      return 'Análisis de Código';
    case 'semantic':
      return 'Análisis Semántico';
    default:
      return 'Análisis';
  }
};

const getAnalysisTypeBadgeColor = (type: string) => {
  switch (type) {
    case 'document':
      return 'bg-blue-100 text-blue-800 border-blue-200';
    case 'collection':
      return 'bg-green-100 text-green-800 border-green-200';
    case 'mindmap':
      return 'bg-purple-100 text-purple-800 border-purple-200';
    case 'insight':
      return 'bg-yellow-100 text-yellow-800 border-yellow-200';
    case 'code':
      return 'bg-orange-100 text-orange-800 border-orange-200';
    case 'semantic':
      return 'bg-indigo-100 text-indigo-800 border-indigo-200';
    default:
      return 'bg-gray-100 text-gray-800 border-gray-200';
  }
};

export function AnalysisDetailDialog({ analysis, isOpen, onOpenChange }: AnalysisDetailDialogProps) {
  const [isQuestionsDialogOpen, setIsQuestionsDialogOpen] = useState(false);

  if (!analysis) return null;

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('es-ES', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // Helper functions para manejar diferentes estructuras de datos
  const ensureArray = (value: any): any[] => {
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
      // Si es otro tipo de objeto (para compatibilidad con otros análisis)
      return {
        name: theme.topic || theme.component || theme.description || theme.name || 'Tema sin nombre',
        description: theme.description || theme.component || theme.topic || theme.name || '',
        quotes: theme.quotes || theme.related_quotes || []
      };
    });
  };

  const getQuestions = () => {
    const data = analysis.full_data;
    return ensureArray(
      data?.knowledge_gaps || 
      data?.preguntas_para_explorar || 
      data?.potential_issues || 
      []
    );
  };

  // Renderizar contenido específico por tipo
  const renderTypeSpecificContent = () => {
    const data = analysis.full_data;

    switch (analysis.type) {
      case 'insight':
        return (
          <motion.div 
            className="space-y-6"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1, duration: 0.3 }}
          >
            <Card className="border-slate-200 bg-slate-50/50 dark:border-slate-700 dark:bg-slate-800/30">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-foreground">
                  <Lightbulb className="h-5 w-5 text-yellow-500" />
                  Insight Detectado
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground leading-relaxed">{analysis.summary}</p>
                {analysis.confidence_score && (
                  <div className="mt-4">
                    <Badge className="bg-yellow-500 text-white font-medium">
                      Confianza: {(analysis.confidence_score * 100).toFixed(0)}%
                    </Badge>
                  </div>
                )}
              </CardContent>
            </Card>

            {analysis.action_suggestion && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2, duration: 0.2 }}
              >
                <Card className="border-slate-200 bg-slate-50/50 dark:border-slate-700 dark:bg-slate-800/30">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-foreground">
                      <Target className="h-5 w-5 text-blue-500" />
                      Sugerencia de Acción
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-muted-foreground leading-relaxed">{analysis.action_suggestion}</p>
                  </CardContent>
                </Card>
              </motion.div>
            )}

            {analysis.related_items && analysis.related_items.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3, duration: 0.2 }}
              >
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Zap className="h-4 w-4" />
                      Elementos Relacionados
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {analysis.related_items.map((item, index) => (
                        <motion.div 
                          key={index} 
                          className="p-3 bg-muted/30 rounded-2xl border border-border/50"
                          initial={{ opacity: 0, x: -10 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: 0.4 + index * 0.05, duration: 0.2 }}
                        >
                          <p className="font-medium">{item.title || item.reference || 'Ítem sin título'}</p>
                          <p className="text-xs text-muted-foreground">Tipo: {item.type || 'N/A'}</p>
                        </motion.div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            )}
          </motion.div>
        );

      case 'code':
        const codeStructure = ensureArray(data?.code_structure);
        const designPatterns = ensureArray(data?.design_patterns);
        const dependencies = ensureArray(data?.dependencies);
        const potentialIssues = ensureArray(data?.potential_issues);
        const recommendations = ensureArray(data?.recommendations);

        return (
          <Tabs defaultValue="overview" className="w-full">
            <TabsList className="grid w-full grid-cols-6">
              <TabsTrigger value="overview">Resumen</TabsTrigger>
              <TabsTrigger value="structure">Estructura</TabsTrigger>
              <TabsTrigger value="patterns">Patrones</TabsTrigger>
              <TabsTrigger value="dependencies">Dependencias</TabsTrigger>
              <TabsTrigger value="issues">Problemas</TabsTrigger>
              <TabsTrigger value="recommendations">Recomendaciones</TabsTrigger>
            </TabsList>
            
            <div className="mt-4 space-y-4">
              <TabsContent value="overview">
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <FileText className="h-4 w-4" />
                      Resumen Ejecutivo
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm whitespace-pre-wrap">{data?.executive_summary || analysis.summary}</p>
                  </CardContent>
                </Card>
                
                {data?.formatted_result && (
                  <Card>
                    <CardHeader>
                      <CardTitle>Análisis Detallado</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="prose prose-sm max-w-none">
                        <InlineMarkdownRenderer content={data.formatted_result} />
                      </div>
                    </CardContent>
                  </Card>
                )}
              </TabsContent>

              <TabsContent value="structure">
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <GitBranch className="h-4 w-4" />
                      Estructura del Código ({codeStructure.length} componentes)
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    {codeStructure.length > 0 ? (
                      <div className="space-y-3">
                        {codeStructure.map((item, i) => (
                          <div key={i} className="border-l-4 border-blue-500 pl-4">
                            <h4 className="font-medium">{item.component}</h4>
                            <p className="text-sm text-muted-foreground">{item.description}</p>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-sm text-muted-foreground">No se encontraron componentes de estructura.</p>
                    )}
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="patterns">
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Settings className="h-4 w-4" />
                      Patrones de Diseño ({designPatterns.length} patrones)
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    {designPatterns.length > 0 ? (
                      <div className="space-y-3">
                        {designPatterns.map((item, i) => (
                          <div key={i} className="border-l-4 border-green-500 pl-4">
                            <h4 className="font-medium">{item.pattern}</h4>
                            <p className="text-sm text-muted-foreground">{item.description}</p>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-sm text-muted-foreground">No se encontraron patrones de diseño específicos.</p>
                    )}
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="dependencies">
                <Card>
                  <CardHeader>
                    <CardTitle>Dependencias ({dependencies.length} bibliotecas)</CardTitle>
                  </CardHeader>
                  <CardContent>
                    {dependencies.length > 0 ? (
                      <div className="grid gap-3">
                        {dependencies.map((item, i) => (
                          <div key={i} className="flex items-start gap-3 p-3 border rounded-lg">
                            <Badge variant="secondary">{item.library}</Badge>
                            <p className="text-sm text-muted-foreground flex-1">{item.description}</p>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-sm text-muted-foreground">No se identificaron dependencias específicas.</p>
                    )}
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="issues">
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <AlertTriangle className="h-4 w-4 text-orange-500" />
                      Problemas Potenciales ({potentialIssues.length} problemas)
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    {potentialIssues.length > 0 ? (
                      <div className="space-y-3">
                        {potentialIssues.map((item, i) => (
                          <div key={i} className="border-l-4 border-orange-500 pl-4 p-3 bg-orange-50 dark:bg-orange-950/20 rounded-r-lg">
                            <h4 className="font-medium text-orange-800 dark:text-orange-200">{item.issue}</h4>
                            <p className="text-sm text-orange-700 dark:text-orange-300">{item.description}</p>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-sm text-muted-foreground">No se identificaron problemas potenciales.</p>
                    )}
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="recommendations">
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Lightbulb className="h-4 w-4 text-blue-500" />
                      Recomendaciones ({recommendations.length} sugerencias)
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    {recommendations.length > 0 ? (
                      <div className="space-y-4">
                        {recommendations.map((item, i) => (
                          <div key={i} className="border rounded-lg p-4 space-y-2">
                            <h4 className="font-medium text-blue-800 dark:text-blue-200">{item.recommendation}</h4>
                            {item.rationale && (
                              <p className="text-sm text-muted-foreground"><strong>Justificación:</strong> {item.rationale}</p>
                            )}
                            {item.application && (
                              <p className="text-sm text-muted-foreground"><strong>Aplicación:</strong> {item.application}</p>
                            )}
                            {item.implementation && (
                              <p className="text-sm text-muted-foreground"><strong>Implementación:</strong> {item.implementation}</p>
                            )}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-sm text-muted-foreground">No se generaron recomendaciones específicas.</p>
                    )}
                  </CardContent>
                </Card>
              </TabsContent>
            </div>
          </Tabs>
        );

      default:
        // Para document, collection, mindmap, semantic
        const keyThemes = extractThemes(data?.key_themes || data?.temas_clave_avanzados || data?.grouped_topics);
        const centralConcepts = ensureArray(data?.central_concepts || data?.conceptos_centrales);
        const relationships = ensureArray(data?.concept_relationships || data?.relaciones_conceptos);
        const questions = getQuestions();

        return (
          <motion.div 
            className="space-y-6"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1, duration: 0.3 }}
          >
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileText className="h-4 w-4" />
                  Resumen Ejecutivo
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                  {data?.executive_summary || data?.resumen_ejecutivo || analysis.summary}
                </p>
              </CardContent>
            </Card>

            {keyThemes.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle>Temas Clave</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {keyThemes.map((theme: any, i: number) => (
                      <div key={i} className="border rounded-lg p-3 bg-muted/30">
                        <Badge className="mb-2">
                          {theme.name || theme.description || 'Tema sin nombre'}
                        </Badge>
                        {theme.quotes && theme.quotes.length > 0 && (
                          <div className="mt-2 space-y-2">
                            <h4 className="text-sm font-medium text-muted-foreground">Citas relacionadas:</h4>
                            {theme.quotes.slice(0, 2).map((quote: any, qIndex: number) => (
                              <blockquote key={qIndex} className="text-xs italic text-muted-foreground border-l-2 border-primary/20 pl-3 py-1">
                                &quot;{quote.quote || quote}&quot;
                                {quote.document_title && (
                                  <cite className="block text-xs font-medium mt-1">
                                    &mdash; {quote.document_title}
                                  </cite>
                                )}
                              </blockquote>
                            ))}
                            {theme.quotes.length > 2 && (
                              <p className="text-xs text-muted-foreground">
                                +{theme.quotes.length - 2} citas más...
                              </p>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {centralConcepts.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle>Conceptos Centrales</CardTitle>
                </CardHeader>
                <CardContent>
                  <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
                    {centralConcepts.map((concept: string, i: number) => (
                      <li key={i}>{concept}</li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            )}

            {relationships.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle>Relaciones entre Conceptos</CardTitle>
                </CardHeader>
                <CardContent>
                  <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
                    {relationships.map((relation: string, i: number) => (
                      <li key={i}>
                        <InlineMarkdownRenderer content={relation} />
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            )}

            {questions.length > 0 && (
              <Card
                className="cursor-pointer hover:shadow-lg hover:scale-[1.02] transition-all duration-300 border-2 hover:border-primary/20 group"
                onClick={() => setIsQuestionsDialogOpen(true)}
              >
                <CardContent className="p-4">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <HelpCircle className="h-5 w-5 text-primary" />
                      <span className="font-medium text-sm">
                        {questions.length} pregunta{questions.length !== 1 ? 's' : ''} para explorar
                      </span>
                    </div>
                    <div className="opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                      <Expand className="h-4 w-4 text-muted-foreground" />
                    </div>
                  </div>
                  <p className="text-sm text-muted-foreground line-clamp-2 leading-relaxed">
                    {typeof questions[0] === 'string' ? questions[0] : questions[0]?.issue || questions[0]?.description || 'Ver preguntas'}
                  </p>
                  <div className="mt-3 text-xs text-primary/60 opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex items-center gap-1">
                    <Expand className="h-3 w-3" />
                    Haz clic para ver todas las preguntas
                  </div>
                </CardContent>
              </Card>
            )}
          </motion.div>
        );
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <Dialog open={isOpen} onOpenChange={onOpenChange}>
          <DialogContent className="max-w-4xl max-h-[90vh] rounded-3xl backdrop-blur-xl bg-card/95 border-0 shadow-2xl">
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              transition={{ duration: 0.2, ease: "easeOut" }}
            >
              <DialogHeader>
                <DialogTitle className="flex items-center gap-3">
                  {getAnalysisIcon(analysis.type)}
                  <span>{analysis.title}</span>
                  <Badge className={`${getAnalysisTypeBadgeColor(analysis.type)} rounded-full`}>
                    {getAnalysisTypeLabel(analysis.type)}
                  </Badge>
                </DialogTitle>
                <DialogDescription className="space-y-2">
                  <div className="flex items-center gap-4 text-sm">
                    <div className="flex items-center gap-1">
                      <Calendar className="h-3 w-3" />
                      <span>Creado: {formatDate(analysis.created_at)}</span>
                    </div>
                    {analysis.updated_at !== analysis.created_at && (
                      <div className="flex items-center gap-1">
                        <Calendar className="h-3 w-3" />
                        <span>Actualizado: {formatDate(analysis.updated_at)}</span>
                      </div>
                    )}
                  </div>
                  {analysis.tool_used && (
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="text-xs font-mono bg-slate-50 text-slate-600 border-slate-200 dark:bg-slate-800 dark:text-slate-400 dark:border-slate-700">
                        {analysis.tool_used}
                      </Badge>
                      <span className="text-xs text-muted-foreground">Herramienta utilizada</span>
                    </div>
                  )}
                </DialogDescription>
              </DialogHeader>

              <ScrollArea className="max-h-[60vh] pr-4">
                {renderTypeSpecificContent()}
              </ScrollArea>

              <div className="flex justify-end mt-6">
                <Button variant="outline" onClick={() => onOpenChange(false)}>
                  Cerrar
                </Button>
              </div>
            </motion.div>
          </DialogContent>
        </Dialog>
      )}

      {/* Diálogo para mostrar preguntas */}
      <QuestionSliderDialog
        isOpen={isQuestionsDialogOpen}
        onOpenChange={setIsQuestionsDialogOpen}
        questions={getQuestions().map(q => typeof q === 'string' ? q : q?.issue || q?.description || 'Pregunta sin contenido')}
        title="Preguntas para Explorar"
      />
    </AnimatePresence>
  );
}
