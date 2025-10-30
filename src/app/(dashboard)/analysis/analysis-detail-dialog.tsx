'use client';

import { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
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
  problematic_areas?: string[];
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
          <ScrollArea className="h-full pr-4">
            <motion.div
              className="space-y-6"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1, duration: 0.3 }}
            >
              <Card className="border-none shadow-none bg-transparent p-0">
                <CardHeader className="px-0 pt-0 pb-2">
                  <CardTitle className="flex items-center gap-2 text-lg font-semibold text-foreground">
                    <Lightbulb className="h-5 w-5 text-yellow-500" />
                    Insight Detectado
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-0">
                  <p className="text-sm text-muted-foreground leading-relaxed p-3 bg-muted rounded-md border border-border/50">{analysis.summary}</p>
                  {analysis.confidence_score && (
                    <div className="mt-4">
                      <Badge className="bg-yellow-500 text-white font-medium border border-border/50">
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
                  <Card className="border-none shadow-none bg-transparent p-0">
                    <CardHeader className="px-0 pt-0 pb-2">
                      <CardTitle className="flex items-center gap-2 text-lg font-semibold text-foreground">
                        <Target className="h-5 w-5 text-blue-500" />
                        Sugerencia de Acción
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="p-0">
                      <p className="text-sm text-muted-foreground leading-relaxed p-3 bg-muted rounded-md border border-border/50">{analysis.action_suggestion}</p>
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
                  <Card className="border-none shadow-none bg-transparent p-0">
                    <CardHeader className="px-0 pt-0 pb-2">
                      <CardTitle className="flex items-center gap-2 text-lg font-semibold text-foreground">
                        <Zap className="h-5 w-5" />
                        Elementos Relacionados
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="p-0">
                      <div className="space-y-3">
                        {analysis.related_items.map((item, index) => (
                          <motion.div
                            key={index}
                            className="p-3 bg-muted/30 rounded-2xl border border-border/50"
                            initial={{ opacity: 0, x: -10 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: 0.4 + index * 0.05, duration: 0.2 }}
                          >
                            <p className="font-medium text-foreground">{item.title || item.reference || 'Ítem sin título'}</p>
                            <p className="text-xs text-muted-foreground">Tipo: {item.type || 'N/A'}</p>
                          </motion.div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              )}
            </motion.div>
          </ScrollArea>
        );

      case 'code':
        const codeStructure = ensureArray(data?.code_structure);
        const designPatterns = ensureArray(data?.design_patterns);
        const dependencies = ensureArray(data?.dependencies);
        const potentialIssues = ensureArray(data?.potential_issues);
        const recommendations = ensureArray(data?.recommendations);

        return (
          <div className="flex flex-col">
          <Tabs defaultValue="overview" className="w-full flex flex-col">
            <TabsList className="grid w-full grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6 bg-transparent border-b border-border/50 mb-4">
              <TabsTrigger value="overview">Resumen</TabsTrigger>
              <TabsTrigger value="structure">Estructura</TabsTrigger>
              <TabsTrigger value="patterns">Patrones</TabsTrigger>
              <TabsTrigger value="dependencies">Dependencias</TabsTrigger>
              <TabsTrigger value="issues">Problemas</TabsTrigger>
              <TabsTrigger value="recommendations">Recomendaciones</TabsTrigger>
            </TabsList>
            
            <ScrollArea className="pr-4">
              <div className="space-y-6 pb-4">
              <TabsContent value="overview" className="space-y-4">
                <Card className="border-none shadow-none bg-transparent p-0">
                  <CardHeader className="px-0 pt-0 pb-2">
                    <CardTitle className="flex items-center gap-2 text-lg font-semibold text-foreground">
                      <FileText className="h-5 w-5" />
                      Resumen Ejecutivo
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-0">
                    <p className="text-sm text-muted-foreground whitespace-pre-wrap leading-relaxed p-3 bg-muted rounded-md border border-border/50">{data?.executive_summary || analysis.summary}</p>
                  </CardContent>
                </Card>
                
                {data?.formatted_result && (
                  <Card className="border-none shadow-none bg-transparent p-0">
                    <CardHeader className="px-0 pt-0 pb-2">
                      <CardTitle className="text-lg font-semibold text-foreground">Análisis Detallado</CardTitle>
                    </CardHeader>
                    <CardContent className="p-0">
                      <div className="prose prose-sm dark:prose-invert max-w-none p-3 bg-muted rounded-md border border-border/50">
                        <InlineMarkdownRenderer content={data.formatted_result} />
                      </div>
                    </CardContent>
                  </Card>
                )}
              </TabsContent>

              <TabsContent value="structure" className="space-y-4">
                <Card className="border-none shadow-none bg-transparent p-0">
                  <CardHeader className="px-0 pt-0 pb-2">
                    <CardTitle className="flex items-center gap-2 text-lg font-semibold text-foreground">
                      <GitBranch className="h-5 w-5" />
                      Estructura del Código ({codeStructure.length} componentes)
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-0">
                    {codeStructure.length > 0 ? (
                      <div className="space-y-3">
                        {codeStructure.map((item, i) => (
                          <div key={i} className="border-l-4 border-blue-500 pl-4 p-3 bg-muted rounded-md border border-border/50">
                            <h4 className="font-medium text-foreground">{item.component}</h4>
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

              <TabsContent value="patterns" className="space-y-4">
                <Card className="border-none shadow-none bg-transparent p-0">
                  <CardHeader className="px-0 pt-0 pb-2">
                    <CardTitle className="flex items-center gap-2 text-lg font-semibold text-foreground">
                      <Settings className="h-5 w-5" />
                      Patrones de Diseño ({designPatterns.length} patrones)
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-0">
                    {designPatterns.length > 0 ? (
                      <div className="space-y-3">
                        {designPatterns.map((item, i) => (
                          <div key={i} className="border-l-4 border-green-500 pl-4 p-3 bg-muted rounded-md border border-border/50">
                            <h4 className="font-medium text-foreground">{item.pattern}</h4>
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

              <TabsContent value="dependencies" className="space-y-4">
                <Card className="border-none shadow-none bg-transparent p-0">
                  <CardHeader className="px-0 pt-0 pb-2">
                    <CardTitle className="text-lg font-semibold text-foreground">Dependencias ({dependencies.length} bibliotecas)</CardTitle>
                  </CardHeader>
                  <CardContent className="p-0">
                    {dependencies.length > 0 ? (
                      <div className="grid gap-3">
                        {dependencies.map((item, i) => (
                          <div key={i} className="flex items-start gap-3 p-3 border rounded-lg border-border/50">
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

              <TabsContent value="issues" className="space-y-4">
                <Card className="border-none shadow-none bg-transparent p-0">
                  <CardHeader className="px-0 pt-0 pb-2">
                    <CardTitle className="flex items-center gap-2 text-lg font-semibold text-foreground">
                      <AlertTriangle className="h-5 w-5 text-orange-500" />
                      Problemas Potenciales ({potentialIssues.length} problemas)
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-0">
                    {potentialIssues.length > 0 ? (
                      <div className="space-y-3">
                        {potentialIssues.map((item, i) => (
                          <div key={i} className="border-l-4 border-orange-500 pl-4 p-3 bg-orange-50 dark:bg-orange-950/20 rounded-r-lg border border-border/50">
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

              <TabsContent value="recommendations" className="space-y-4">
                <Card className="border-none shadow-none bg-transparent p-0">
                  <CardHeader className="px-0 pt-0 pb-2">
                    <CardTitle className="flex items-center gap-2 text-lg font-semibold text-foreground">
                      <Lightbulb className="h-5 w-5 text-blue-500" />
                      Recomendaciones ({recommendations.length} sugerencias)
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-0">
                    {recommendations.length > 0 ? (
                      <div className="space-y-4">
                        {recommendations.map((item, i) => (
                          <div key={i} className="border rounded-lg p-4 space-y-2 border-border/50">
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
            </ScrollArea>
          </Tabs>
        </div>
        );

      default:
        // Para document, collection, mindmap, semantic
        const keyThemes = extractThemes(data?.key_themes || data?.temas_clave_avanzados || data?.grouped_topics);
        const centralConcepts = ensureArray(data?.central_concepts || data?.conceptos_centrales);
        const relationships = ensureArray(data?.concept_relationships || data?.relaciones_conceptos);
        const questions = getQuestions();

        return (
          <ScrollArea className="h-full pr-4">
            <motion.div 
              className="space-y-6"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1, duration: 0.3 }}
            >
            <Card className="border-none shadow-none bg-transparent p-0">
              <CardHeader className="px-0 pt-0 pb-2">
                <CardTitle className="flex items-center gap-2 text-lg font-semibold text-foreground">
                  <FileText className="h-5 w-5" />
                  Resumen Ejecutivo
                </CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <p className="text-sm text-muted-foreground whitespace-pre-wrap leading-relaxed p-3 bg-muted rounded-md border border-border/50">
                  {data?.executive_summary || data?.resumen_ejecutivo || analysis.summary}
                </p>
              </CardContent>
            </Card>

            {keyThemes.length > 0 && (
              <Card className="border-none shadow-none bg-transparent p-0">
                <CardHeader className="px-0 pt-0 pb-2">
                  <CardTitle className="text-lg font-semibold text-foreground">Temas Clave</CardTitle>
                </CardHeader>
                <CardContent className="p-0">
                  <div className="space-y-3">
                    {keyThemes.map((theme: any, i: number) => (
                      <div key={i} className="border rounded-lg p-3 bg-muted/30 border-border/50">
                        <Badge className="mb-2 bg-blue-100 text-blue-800 border border-blue-200">
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
              <Card className="border-none shadow-none bg-transparent p-0">
                <CardHeader className="px-0 pt-0 pb-2">
                  <CardTitle className="text-lg font-semibold text-foreground">Conceptos Centrales</CardTitle>
                </CardHeader>
                <CardContent className="p-0">
                  <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground p-3 bg-muted rounded-md border border-border/50">
                    {centralConcepts.map((concept: string, i: number) => (
                      <li key={i}><InlineMarkdownRenderer content={concept} /></li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            )}

            {relationships.length > 0 && (
              <Card className="border-none shadow-none bg-transparent p-0">
                <CardHeader className="px-0 pt-0 pb-2">
                  <CardTitle className="text-lg font-semibold text-foreground">Relaciones entre Conceptos</CardTitle>
                </CardHeader>
                <CardContent className="p-0">
                  <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground p-3 bg-muted rounded-md border border-border/50">
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
              <Card className="border-none shadow-none bg-transparent p-0">
                <CardHeader className="px-0 pt-0 pb-2">
                  <CardTitle className="flex items-center gap-2 text-lg font-semibold text-foreground">
                    <HelpCircle className="h-5 w-5 text-primary" />
                    Preguntas para explorar
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-0">
                  <Card
                    className="cursor-pointer hover:shadow-lg hover:scale-[1.02] transition-all duration-300 border border-border/50 group"
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
                </CardContent>
              </Card>
            )}

            {/* Sección de Problemáticas */}
            {ensureArray(data?.problematic_areas).length > 0 && (
              <Card className="border-none shadow-none bg-transparent p-0">
                <CardHeader className="px-0 pt-0 pb-2">
                  <CardTitle className="flex items-center gap-2 text-lg font-semibold text-foreground">
                    <AlertTriangle className="h-5 w-5 text-red-500" />
                    Problemáticas
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-0">
                  <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground p-3 bg-muted rounded-md border border-border/50">
                    {ensureArray(data?.problematic_areas).map((problem: string, i: number) => (
                      <li key={i}><InlineMarkdownRenderer content={problem} /></li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            )}

            {/* Renderizar campos adicionales de full_data como ítems individuales */}
            {Object.keys(data || {}).length > 0 && (() => {
              const excludedKeys = [
                'key_themes', 'temas_clave_avanzados', 'grouped_topics',
                'central_concepts', 'conceptos_centrales',
                'concept_relationships', 'relaciones_conceptos',
                'knowledge_gaps', 'preguntas_para_explorar', 'potential_issues',
                'executive_summary', 'resumen_ejecutivo',
                'code_structure', 'design_patterns', 'dependencies', 'recommendations', 'formatted_result',
                'problematic_areas' // Añadir problematic_areas a las claves excluidas
              ];
              const additionalDataKeys = Object.keys(data).filter(key => !excludedKeys.includes(key));

              if (additionalDataKeys.length === 0) return null;

              const renderAdditionalDataValue = (value: any) => {
                if (typeof value === 'string') {
                  return <InlineMarkdownRenderer content={value} />;
                } else if (Array.isArray(value)) {
                  return (
                    <ul className="list-disc list-inside space-y-1">
                      {value.map((item, idx) => (
                        <li key={idx}>{renderAdditionalDataValue(item)}</li>
                      ))}
                    </ul>
                  );
                } else if (typeof value === 'object' && value !== null) {
                  return (
                    <div className="ml-4 border-l pl-2">
                      {Object.entries(value).map(([subKey, subValue], idx) => (
                        <div key={idx}>
                          <span className="font-medium">{subKey.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}: </span>
                          {renderAdditionalDataValue(subValue)}
                        </div>
                      ))}
                    </div>
                  );
                } else {
                  return String(value);
                }
              };

              return (
                <>
                  {additionalDataKeys.map((key, i) => (
                    <Card key={i} className="border-none shadow-none bg-transparent p-0">
                      <CardHeader className="px-0 pt-0 pb-2">
                        <CardTitle className="text-lg font-semibold text-foreground">{key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</CardTitle>
                      </CardHeader>
                      <CardContent className="p-0">
                        <div className="text-sm text-muted-foreground whitespace-pre-wrap p-3 bg-muted rounded-md border border-border/50">
                          {renderAdditionalDataValue(data[key])}
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </>
              );
            })()}
            </motion.div>
          </ScrollArea>
        );
  };

  return (
    <>
      {isOpen && (
        <Dialog open={isOpen} onOpenChange={onOpenChange}>
          <DialogContent className="max-w-4xl w-full max-h-[90vh] rounded-3xl backdrop-blur-xl bg-card/95 border-0 shadow-2xl flex flex-col p-0 overflow-y-auto">
            <DialogHeader className="p-6 pb-4 border-b">
              <DialogTitle className="flex items-center gap-3 text-2xl font-bold">
                {getAnalysisIcon(analysis.type)}
                {getAnalysisTypeLabel(analysis.type)}
              </DialogTitle>
              <DialogDescription>
                {analysis.title}
              </DialogDescription>
            </DialogHeader>
            <div className="p-6 pb-4">
              {renderTypeSpecificContent()}
            </div>
            <DialogFooter className="p-6 pt-4 border-t">
              <Button variant="outline" onClick={() => onOpenChange(false)}>
                Cerrar
              </Button>
            </DialogFooter>
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
    </>
  );
}