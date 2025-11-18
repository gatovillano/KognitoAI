import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Analysis, AnalysisType, Insight, Question, CollectionAnalysis, DocumentAnalysisResult as SingleTextAnalysis, CollectionConnection, ThemeReference, ThemeQuote, CodeAnalysisResultFrontend } from '@/lib/models';
import { Lightbulb, Workflow, ScrollText, Megaphone, Target, BarChart3, TrendingUp, FlaskConical, Puzzle, Goal, LibraryBig, Bot, CircleCheck, Info, Sparkles, XCircle, FileWarning, HelpCircle, Brain, Network, Volume2, Loader2, Pause, Calendar, AlertTriangle, Expand, Atom, FileText, Settings, GitBranch } from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { QuestionSliderDialog } from '@/components/QuestionSliderDialog';
import { useTextToSpeech } from '@/hooks/useTextToSpeech';

const cleanAsterisks = (text: string) => {
  return text.replace(/^\*+|\*+$/g, '');
};

// import { processContentWithCitations } // Importa la función de procesamiento

interface AnalysisDetailDialogProps {
  analysis: Analysis | null;
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  // onGenerateQuestions?: (analysisId: string) => void; // Opcional
}

interface QuestionSliderDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  questions: string[];
  title: string;
}
interface ConceptDetailDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  concept: string | null;
}

const ConceptDetailDialog: React.FC<ConceptDetailDialogProps> = ({ isOpen, onOpenChange, concept }) => {
  if (!concept) return null;

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg w-full max-h-[90vh] rounded-3xl backdrop-blur-xl bg-card/95 border-0 shadow-2xl flex flex-col p-0">
        <DialogHeader className="p-6 pb-0">
          <DialogTitle className="text-xl font-bold text-foreground">Detalles del Concepto</DialogTitle>
        </DialogHeader>
        {concept && (
          <div className="flex-1 overflow-y-auto pr-4">
            <div className="space-y-4 pb-4">
              <div>
                <h4 className="font-semibold text-lg mb-3 text-foreground">
                  {concept.split(':')[0]}
                </h4>
                <div className="p-4 bg-muted/50 rounded-lg border border-border/50">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {concept.split(':').slice(1).join(':').trim()}
                  </ReactMarkdown>
                </div>
              </div>

              <div className="mt-6">
                <h5 className="font-semibold mb-3 text-sm text-foreground">Definición y contexto:</h5>
                <div className="p-4 bg-purple-50/50 border-l-4 border-purple-200 rounded-r-lg border border-border/50">
                  {(() => {
                    // Parsear el concepto en formato "CONCEPTO: DEFINICIÓN"
                    const conceptParts = concept?.split(':');
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
                          <p className="text-xs text-purple-600 mt-4 pt-3 border-t border-purple-200">
                            Para profundizar, puedes realizar una búsqueda dirigida en la colección.
                          </p>
                        </div>
                      );
                    } else {
                      return (
                        <div>
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>{concept}</ReactMarkdown>
                          <p>Concepto no parseado</p>
                        </div>
                      );
                    }
                  })()}
                </div>
              </div>
            </div>
          </div>
        )}
        <DialogFooter className="p-6 pt-0">
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cerrar</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

const getAnalysisIcon = (type: AnalysisType) => {
  switch (type) {
    case 'insight': return <Lightbulb className="text-yellow-500" />;
    case 'workflow_suggestion': return <Workflow className="text-blue-500" />;
    case 'document_summary': return <ScrollText className="text-purple-500" />;
    case 'announcement_draft': return <Megaphone className="text-red-500" />;
    case 'strategic_objective': return <Target className="text-green-500" />;
    case 'market_trend': return <TrendingUp className="text-orange-500" />;
    case 'experiment_proposal': return <FlaskConical className="text-indigo-500" />;
    case 'problem_statement': return <Puzzle className="text-gray-500" />;
    case 'goal_setting': return <Goal className="text-emerald-500" />;
    case 'knowledge_retrieval': return <LibraryBig className="text-cyan-500" />;
    case 'agent_response_improvement': return <Bot className="text-lime-500" />;
    case 'verification': return <CircleCheck className="text-green-600" />;
    case 'information': return <Info className="text-blue-600" />;
    case 'suggestion': return <Sparkles className="text-pink-500" />;
    case 'error': return <XCircle className="text-red-600" />;
    case 'warning': return <FileWarning className="text-yellow-600" />;
    case 'question': return <HelpCircle className="text-purple-600" />;
    case 'code': return <Brain className="text-cyan-600" />;
    case 'topic_analysis': return <Network className="text-indigo-600" />;
    case 'proactive_insight_manual': return <Atom className="text-pink-500" />;
    default: return null;
  }
};

const getAnalysisTypeLabel = (type: AnalysisType) => {
  switch (type) {
    case 'insight': return 'Insight';
    case 'workflow_suggestion': return 'Sugerencia de Flujo de Trabajo';
    case 'document_summary': return 'Resumen de Documento';
    case 'announcement_draft': return 'Borrador de Anuncio';
    case 'strategic_objective': return 'Objetivo Estratégico';
    case 'market_trend': return 'Tendencia de Mercado';
    case 'experiment_proposal': return 'Propuesta de Experimento';
    case 'problem_statement': return 'Declaración del Problema';
    case 'goal_setting': return 'Establecimiento de Metas';
    case 'knowledge_retrieval': return 'Recuperación de Conocimiento';
    case 'agent_response_improvement': return 'Mejora de Respuesta del Agente';
    case 'verification': return 'Verificación';
    case 'information': return 'Información';
    case 'suggestion': return 'Sugerencia';
    case 'error': return 'Error';
    case 'warning': return 'Advertencia';
    case 'question': return 'Pregunta';
    case 'code': return 'Análisis de Código';
    case 'topic_analysis': return 'Análisis por Tema';
    case 'proactive_insight_manual': return 'Insight Proactivo Manual';
    default: return 'Análisis Desconocido';
  }
};


interface AnalysisCommonFieldsProps {
  analysis: Analysis;
  processedOutput: {
    content: string;
    sources: { id: string; link?: string; title?: string }[];
  };
}

const AnalysisCommonFields: React.FC<AnalysisCommonFieldsProps> = ({ analysis, processedOutput }) => (
  <>
    {analysis.file_name && (
      <p className="text-sm text-muted-foreground mb-1"><strong>Archivo:</strong> {analysis.file_name}</p>
    )}
    {analysis.author && (
      <p className="text-sm text-muted-foreground mb-1"><strong>Autor:</strong> {analysis.author}</p>
    )}
    {analysis.created_at && (
      <p className="text-xs text-muted-foreground mb-1"><strong>Creado:</strong> {new Date(analysis.created_at).toLocaleString()}</p>
    )}
    {analysis.updated_at && analysis.updated_at !== analysis.created_at && (
      <p className="text-xs text-muted-foreground mb-4"><strong>Actualizado:</strong> {new Date(analysis.updated_at).toLocaleString()}</p>
    )}
    {processedOutput.sources.length > 0 && (
      <div className="mt-4 border-t pt-4">
        <h5 className="font-semibold mb-2">Fuentes:</h5>
        <ul className="list-disc pl-5 text-sm text-muted-foreground space-y-1">
          {processedOutput.sources.map((source: { id: string; link?: string; title?: string }, i: number) => (
            <li key={i}>
              {source.link ? (
                <a href={source.link} target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline">
                  {source.title || `Fuente ${source.id}`}
                </a>
              ) : (
                source.title || `Fuente ${source.id}`
              )}
            </li>
          ))}
        </ul>
      </div>
    )}
  </>
);

const InsightBlock: React.FC<{ insight: Insight }> = ({ insight }) => (
  <div className="border rounded-md p-4 mb-4 bg-background shadow-sm">
    <div className="flex items-center gap-2 mb-2">
      <h4 className="text-lg font-semibold">{insight.title}</h4>
      <Badge variant="secondary">{insight.type}</Badge>
    </div>
    <div className="text-sm text-muted-foreground mb-3"><ReactMarkdown remarkPlugins={[remarkGfm]} children={insight.description || ''}/></div>
    {insight.severity && (
      <p className="text-xs text-foreground mb-1"><strong>Severidad:</strong> {insight.severity}</p>
    )}
    {insight.priority && (
      <p className="text-xs text-foreground mb-1"><strong>Prioridad:</strong> {insight.priority}</p>
    )}
    {insight.status && (
      <p className="text-xs text-foreground mb-1"><strong>Estado:</strong> {insight.status}</p>
    )}
    {insight.recommendations && insight.recommendations.length > 0 && (
      <div className="mt-3">
        <h5 className="font-medium text-sm mb-1">Recomendaciones:</h5>
        <ul className="list-disc pl-5 text-sm text-foreground space-y-1">
          {insight.recommendations.map((rec: string, i: number) => (
            <li key={i}><div className="text-sm text-muted-foreground"><ReactMarkdown remarkPlugins={[remarkGfm]} children={rec}/></div></li>
          ))}
        </ul>
      </div>
    )}
  </div>
);


interface ThemeQuotesDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  theme: ThemeReference | null;
}

const ThemeQuotesDialog: React.FC<ThemeQuotesDialogProps> = ({ isOpen, onOpenChange, theme }) => {
  if (!theme) return null;

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl rounded-lg">
        <DialogHeader>
          <DialogTitle>Citas para: {theme.theme}</DialogTitle>
          <DialogDescription>
            {`Fragmentos de texto relacionados con el tema "${theme.theme}" encontrados en los documentos.`}
          </DialogDescription>
        </DialogHeader>
        <div className="py-4 flex-1 overflow-y-auto max-h-[70vh]">
          {theme.related_quotes && theme.related_quotes.length > 0 ? (
            <ul className="list-disc pl-5 space-y-3 text-sm text-muted-foreground">
              {theme.related_quotes.map((quote: ThemeQuote, qIdx: number) => (
                <li key={qIdx} className="border-l-2 pl-3">
                  <div className="italic mb-1"><ReactMarkdown remarkPlugins={[remarkGfm]} children={`"${quote.quote}"`}/></div>
                  <p className="text-xs font-semibold text-gray-500">— {quote.document_title}</p>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-center text-muted-foreground">No se encontraron citas para este tema.</p>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cerrar</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export const AnalysisDetailDialog: React.FC<AnalysisDetailDialogProps> = ({ analysis, isOpen, onOpenChange }) => {
  const [isQuestionsDialogOpen, setIsQuestionsDialogOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('summary');
  const [selectedThemeForQuotes, setSelectedThemeForQuotes] = useState<ThemeReference | null>(null);
  const [isThemeQuotesDialogOpen, setIsThemeQuotesDialogOpen] = useState(false);
  const [isKnowledgeGapsDialogOpen, setIsKnowledgeGapsDialogOpen] = useState(false);
  const [selectedConcept, setSelectedConcept] = useState<string | null>(null);
  const [isConceptDialogOpen, setIsConceptDialogOpen] = useState(false);

  const { play, stop, isLoading, isPlaying, activeText } = useTextToSpeech();

  const handleThemeClick = useCallback((theme: ThemeReference) => {
    setSelectedThemeForQuotes(theme);
    setIsThemeQuotesDialogOpen(true);
  }, []);

  const handleConceptClick = useCallback((concept: string) => {
    setSelectedConcept(concept);
    setIsConceptDialogOpen(true);
  }, []);

  const semanticData = useMemo(() => {
    if (!analysis) {
      return {
        resumen_semantico: 'No hay resumen disponible',
        temas_transversales: [],
        conceptos_centrales: [],
        brechas_conocimiento: [],
        patrones_semanticos: {},
        problematic_areas: []
      };
    }
    return {
      resumen_semantico: analysis.result?.resumen_semantico || analysis.summary || 'No hay resumen disponible',
      temas_transversales: analysis.result?.temas_transversales || [],
      conceptos_centrales: analysis.result?.conceptos_centrales || [],
      brechas_conocimiento: analysis.result?.brechas_conocimiento || [],
      patrones_semanticos: analysis.result?.patrones_semanticos || {},
      problematic_areas: analysis.result?.problematic_areas || []
    };
  }, [analysis]);

  const textToRead = useMemo(() => {
    return `Resumen Semántico: ${semanticData.resumen_semantico}`;
  }, [semanticData]);

  const handlePlayPause = () => play(textToRead);
  const isCurrentlyPlaying = isPlaying && activeText === textToRead;
  const isCurrentlyLoading = isLoading && activeText === textToRead;

  useEffect(() => {
    if (isOpen) {
      setActiveTab('summary'); // Reset tab when dialog opens
      // Reiniciar estados de diálogos internos al abrir el principal
      setIsThemeQuotesDialogOpen(false);
      setIsKnowledgeGapsDialogOpen(false);
      setIsConceptDialogOpen(false);
    }
  }, [isOpen]);

  const getQuestions = useCallback((): (Question | string)[] => {
    if (!analysis) return [];

    const allQuestions: (Question | string)[] = [];

    // Prioridad 1: analysis.questions
    if (analysis.questions && analysis.questions.length > 0) {
      allQuestions.push(...analysis.questions);
    }

    // Prioridad 2: insights.questions
    if (analysis.insights) {
      analysis.insights.forEach(insight => {
        if (insight.questions && insight.questions.length > 0) {
          allQuestions.push(...insight.questions);
        }
      });
    }

    return allQuestions;
  }, [analysis]);

  const hasInsights = useMemo(() => analysis?.insights && analysis.insights.length > 0, [analysis]);
  const hasRawContent = useMemo(() => !!analysis?.rawContent, [analysis]);
  const hasQuestions = useMemo(() => getQuestions().length > 0, [getQuestions]);


  const renderTypeSpecificContent = useCallback(() => {
    if (!analysis) return null;

    let contentToProcess = analysis.summary || analysis.rawContent || '';
    let sources: { id: string; link?: string; title?: string }[] = [];

    // Adaptar fuentes si vienen en el nuevo formato `{id: string, link: string}`
    if (Array.isArray(analysis.sources) && analysis.sources.length > 0) {
      sources = analysis.sources.map(s => {
        if (typeof s === 'string') {
          return { id: s };
        } else {
          return s as { id: string; link?: string; title?: string };
        }
      });
    }

        const processedOutput = { content: contentToProcess, sources: sources };

    switch (analysis.type) {
      case 'semantic':
      case 'semantic_summary':
        return (
          <>
            <h3 className="text-xl font-bold mb-4">Detalle del Resumen Semántico</h3>

            {/* Botón de texto a voz */}
            <div className="mb-4 flex items-center gap-2">
              <Button
                onClick={handlePlayPause}
                variant="outline"
                size="sm"
                className="gap-2"
                disabled={isCurrentlyLoading}
              >
                {isCurrentlyLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : isCurrentlyPlaying ? (
                  <Pause className="h-4 w-4" />
                ) : (
                  <Volume2 className="h-4 w-4" />
                )}
                {isCurrentlyLoading ? 'Cargando...' : isCurrentlyPlaying ? 'Pausar' : 'Escuchar'}
              </Button>
            </div>

            {analysis.full_data?.resumen_semantico && (
              <div className="mb-4 p-3 bg-muted rounded-md border border-border/50">
                <h4 className="font-semibold text-lg mb-2">Resumen Semántico:</h4>
                <div className="text-sm text-muted-foreground whitespace-pre-wrap"><ReactMarkdown remarkPlugins={[remarkGfm]} children={analysis.full_data.resumen_semantico || ''}/></div>
              </div>
            )}

            {analysis.full_data?.temas_transversales && analysis.full_data.temas_transversales.length > 0 && (
              <div className="mb-4">
                <h4 className="font-semibold text-lg mb-2">Temas Transversales:</h4>
                <div className="flex flex-wrap gap-2">
                  {analysis.full_data.temas_transversales?.map((theme: ThemeReference, idx: number) => (
                    <Badge
                      key={idx}
                      className="cursor-pointer text-sm hover:bg-accent hover:text-accent-foreground transition-colors bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-100"
                      onClick={() => handleThemeClick(theme)}
                    >
                      {theme.theme}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {analysis.full_data?.patrones_semanticos && Object.keys(analysis.full_data.patrones_semanticos).length > 0 && (
              <div className="mb-4">
                <h4 className="font-semibold text-lg mb-2">Estadísticas del Análisis:</h4>
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4 text-center">
                  {analysis.full_data.patrones_semanticos.total_documentos && (
                    <div className="p-3 bg-muted rounded-md border border-border/50">
                      <div className="text-2xl font-bold text-purple-600">
                        {analysis.full_data.patrones_semanticos.total_documentos}
                      </div>
                      <div className="text-xs text-purple-400">Documentos</div>
                    </div>
                  )}
                  {analysis.full_data.patrones_semanticos.total_chunks_analizados && (
                    <div className="p-3 bg-muted rounded-md border border-border/50">
                      <div className="text-2xl font-bold text-purple-600">
                        {analysis.full_data.patrones_semanticos.total_chunks_analizados}
                      </div>
                      <div className="text-xs text-purple-400">Fragmentos</div>
                    </div>
                  )}
                  {analysis.full_data.patrones_semanticos.temas_identificados && (
                    <div className="p-3 bg-muted rounded-md border border-border/50">
                      <div className="text-2xl font-bold text-purple-600">
                        {analysis.full_data.patrones_semanticos.temas_identificados}
                      </div>
                      <div className="text-xs text-purple-400">Temas</div>
                    </div>
                  )}
                  <div className="p-3 bg-muted rounded-md border border-border/50">
                    <div className="text-2xl font-bold text-purple-600">
                      {analysis.full_data.conceptos_centrales.length}
                    </div>
                    <div className="text-xs text-purple-400">Conceptos</div>
                  </div>
                </div>
              </div>
            )}

            {analysis.full_data?.brechas_conocimiento && analysis.full_data.brechas_conocimiento.length > 0 && (
              <div className="mb-4">
                <h4 className="font-semibold text-lg mb-2">Brechas de Conocimiento:</h4>
                <ul className="list-disc pl-5 text-sm text-muted-foreground space-y-1">
                  {analysis.full_data.brechas_conocimiento?.map((gap: string, idx: number) => (
                    <li key={idx}><div className="text-sm text-muted-foreground"><ReactMarkdown remarkPlugins={[remarkGfm]} children={gap}/></div></li>
                  ))}
                </ul>
              </div>
            )}

            {analysis.full_data?.problematic_areas && analysis.full_data.problematic_areas.length > 0 && (
              <div className="mb-4">
                <h4 className="font-semibold text-lg mb-2 flex items-center gap-2">
                  <AlertTriangle className="h-5 w-5 text-red-500" />
                  Problemáticas:
                </h4>
                <ul className="list-disc pl-5 text-sm text-muted-foreground space-y-1">
                  {analysis.full_data.problematic_areas?.map((area: string, idx: number) => (
                    <li key={idx}><div className="text-sm text-muted-foreground"><ReactMarkdown remarkPlugins={[remarkGfm]} children={area}/></div></li>
                  ))}
                </ul>
              </div>
            )}

            {analysis.full_data?.exploration_questions && analysis.full_data.exploration_questions.length > 0 && (
              <div className="mb-4">
                <h4 className="font-semibold text-lg mb-2">Preguntas para Explorar:</h4>
                <ul className="list-disc pl-5 text-sm text-muted-foreground space-y-1">
                  {analysis.full_data.exploration_questions?.map((question: string, idx: number) => (
                    <li key={idx}><div className="text-sm text-muted-foreground"><ReactMarkdown remarkPlugins={[remarkGfm]} children={question}/></div></li>
                  ))}
                </ul>
              </div>
            )}

            {analysis.full_data?.final_reflections && analysis.full_data.final_reflections.length > 0 && (
              <div className="mb-4">
                <h4 className="font-semibold text-lg mb-2">Reflexiones Finales:</h4>
                <ul className="list-disc pl-5 text-sm text-muted-foreground space-y-1">
                  {analysis.full_data.final_reflections?.map((reflection: string, idx: number) => (
                    <li key={idx}><div className="text-sm text-muted-foreground"><ReactMarkdown remarkPlugins={[remarkGfm]} children={reflection}/></div></li>
                  ))}
                </ul>
              </div>
            )}

            <AnalysisCommonFields analysis={analysis} processedOutput={processedOutput} />
          </>
        );
      case 'insight':
        return (
          <>
            <h3 className="text-xl font-bold mb-4">Detalle del Insight</h3>
            {analysis.summary && (
              <div className="mb-4 p-3 bg-muted rounded-md border border-border/50">
                <h4 className="font-semibold text-lg mb-2">Resumen:</h4>
                <div className="text-sm text-muted-foreground whitespace-pre-wrap"><ReactMarkdown remarkPlugins={[remarkGfm]} children={analysis.summary || ''}/></div>
              </div>
            )}

            {analysis.action_suggestion && (
              <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                <h4 className="font-medium text-sm text-yellow-800 mb-1">Sugerencia de Acción:</h4>
                <div className="text-sm text-yellow-700"><ReactMarkdown remarkPlugins={[remarkGfm]} children={analysis.action_suggestion || ''}/></div>
              </div>
            )}
            {analysis.related_items && analysis.related_items.length > 0 && (
              <div className="mb-4">
                <h4 className="font-semibold text-lg mb-2">Elementos Relacionados:</h4>
                <div className="flex flex-wrap gap-2">
                  {analysis.related_items.map((item: { title?: string; name?: string }, idx: number) => (
                    <Badge key={idx} variant="secondary" className="text-sm">
                      {item.title || item.name || `Item ${idx + 1}`}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
            {analysis.tool_used && (
              <div className="mb-4">
                <h4 className="font-semibold text-lg mb-2">Herramienta Utilizada:</h4>
                <Badge variant="outline" className="text-sm font-mono bg-slate-50 text-slate-600 border-slate-200 dark:bg-slate-800 dark:text-slate-400 dark:border-slate-700">
                  {analysis.tool_used}
                </Badge>
              </div>
            )}
            {analysis.created_at && (
              <p className="text-xs text-muted-foreground mb-1"><strong>Creado:</strong> {new Date(analysis.created_at).toLocaleString()}</p>
            )}
            {analysis.updated_at && analysis.updated_at !== analysis.created_at && (
              <p className="text-xs text-muted-foreground mb-4"><strong>Actualizado:</strong> {new Date(analysis.updated_at).toLocaleString()}</p>
            )}
            <AnalysisCommonFields analysis={analysis} processedOutput={processedOutput} />
          </>
        );
      case 'collection':
        const collectionData = analysis.full_data as CollectionAnalysis; // Usar full_data para colecciones
        return (
          <>
            <h3 className="text-xl font-bold mb-4">Detalle de Análisis de Colección</h3>
            {collectionData?.collection_summary && (
              <div className="mb-4 p-3 bg-muted rounded-md border border-border/50">
                <h4 className="font-semibold text-lg mb-2">Resumen de la Colección:</h4>
                <div className="text-sm text-muted-foreground whitespace-pre-wrap"><ReactMarkdown remarkPlugins={[remarkGfm]} children={collectionData.collection_summary || ''}/></div>
              </div>
            )}
            {collectionData?.cross_cutting_themes && collectionData.cross_cutting_themes.length > 0 && (
              <div className="mb-4">
                <h4 className="font-semibold text-lg mb-2">Temas Transversales:</h4>
                <div className="flex flex-wrap gap-2">
                  {collectionData.cross_cutting_themes.map((theme: ThemeReference, idx: number) => (
                    <Badge
                      key={idx}
                      className="cursor-pointer text-sm hover:bg-accent hover:text-accent-foreground transition-colors bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-100"
                      onClick={() => handleThemeClick(theme)}
                    >
                      {theme.theme}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
            {collectionData?.central_concepts && collectionData.central_concepts.length > 0 && (
              <div className="mb-4">
                <h4 className="font-semibold text-lg mb-2">Conceptos Centrales:</h4>
                <div className="flex flex-wrap gap-2">
                  {collectionData.central_concepts.map((concept: string, idx: number) => (
                    <Badge
                      key={idx}
                      variant="outline"
                      className="cursor-pointer text-sm hover:bg-accent hover:text-accent-foreground transition-colors bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-100"
                      onClick={() => handleConceptClick(concept)}
                    >
                      {cleanAsterisks(concept.split(':')[0])}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
            {collectionData?.patrones_semanticos && Object.keys(collectionData.patrones_semanticos).length > 0 && (
                <div className="mb-4">
                  <h4 className="font-semibold text-lg mb-2">Estadísticas del Análisis:</h4>
                  <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4 text-center">
                    {collectionData.patrones_semanticos.total_documentos && (
                      <div className="p-3 bg-muted rounded-md border border-border/50">
                        <div className="text-2xl font-bold text-purple-600">
                          {collectionData.patrones_semanticos.total_documentos}
                        </div>
                        <div className="text-xs text-purple-400">Documentos</div>
                      </div>
                    )}
                    {collectionData.patrones_semanticos.total_chunks_analizados && (
                      <div className="p-3 bg-muted rounded-md border border-border/50">
                        <div className="text-2xl font-bold text-purple-600">
                          {collectionData.patrones_semanticos.total_chunks_analizados}
                        </div>
                        <div className="text-xs text-purple-400">Fragmentos</div>
                      </div>
                    )}
                    {collectionData.patrones_semanticos.temas_identificados && (
                      <div className="p-3 bg-muted rounded-md border border-border/50">
                        <div className="text-2xl font-bold text-purple-600">
                          {collectionData.patrones_semanticos.temas_identificados}
                        </div>
                        <div className="text-xs text-purple-400">Temas</div>
                      </div>
                    )}
                    <div className="p-3 bg-muted rounded-md border border-border/50">
                      <div className="text-2xl font-bold text-purple-600">
                        {collectionData.central_concepts.length}
                      </div>
                      <div className="text-xs text-purple-400">Conceptos</div>
                    </div>
                  </div>
                </div>
              )}
            {collectionData?.concept_relationships && collectionData.concept_relationships.length > 0 && (
              <div className="mb-4">
                <h4 className="font-semibold text-lg mb-2">Relaciones entre Conceptos:</h4>
                <ul className="list-disc pl-5 text-sm text-muted-foreground space-y-1">
                  {collectionData.concept_relationships.map((relationship: string, idx: number) => (
                    <li key={idx}><div className="text-sm text-muted-foreground"><ReactMarkdown remarkPlugins={[remarkGfm]} children={relationship}/></div></li>
                  ))}
                </ul>
              </div>
            )}
            {collectionData?.identified_connections && collectionData.identified_connections.length > 0 && (
              <div className="mb-4">
                <h4 className="font-semibold text-lg mb-2">Conexiones Identificadas:</h4>
                <ul className="list-disc pl-5 text-sm text-muted-foreground space-y-1">
                  {collectionData.identified_connections.map((connection: CollectionConnection, idx: number) => (
                    <li key={idx}>
                      <p className="font-semibold">{connection.document_titles.join(', ')}</p>
                      <div className="text-sm text-muted-foreground"><ReactMarkdown remarkPlugins={[remarkGfm]} children={connection.insight}/></div>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {collectionData?.emergent_knowledge_gaps && collectionData.emergent_knowledge_gaps.length > 0 && (
              <div className="mb-4">
                <h4 className="font-semibold text-lg mb-2">Brechas de Conocimiento Emergentes:</h4>
                <ul className="list-disc pl-5 text-sm text-muted-foreground space-y-1">
                  {collectionData.emergent_knowledge_gaps.map((gap: string, idx: number) => (
                    <li key={idx}><div className="text-sm text-muted-foreground"><ReactMarkdown remarkPlugins={[remarkGfm]} children={gap}/></div></li>
                  ))}
                </ul>
              </div>
            )}
            {collectionData?.exploration_questions && collectionData.exploration_questions.length > 0 && (
              <div className="mb-4">
                <h4 className="font-semibold text-lg mb-2">Preguntas para Explorar:</h4>
                <ul className="list-disc pl-5 text-sm text-muted-foreground space-y-1">
                  {collectionData.exploration_questions.map((question: string, idx: number) => (
                    <li key={idx}><div className="text-sm text-muted-foreground"><ReactMarkdown remarkPlugins={[remarkGfm]} children={question}/></div></li>
                  ))}
                </ul>
              </div>
            )}
            {collectionData?.problematic_areas && collectionData.problematic_areas.length > 0 && (
              <div className="mb-4">
                <h4 className="font-semibold text-lg mb-2 flex items-center gap-2">
                  <AlertTriangle className="h-5 w-5 text-red-500" />
                  Problemáticas:
                </h4>
                <ul className="list-disc pl-5 text-sm text-muted-foreground space-y-1">
                  {collectionData.problematic_areas.map((area: string, idx: number) => (
                    <li key={idx}><div className="text-sm text-muted-foreground"><ReactMarkdown remarkPlugins={[remarkGfm]} children={area}/></div></li>
                  ))}
                </ul>
              </div>
            )}
            {collectionData?.final_reflections && collectionData.final_reflections.length > 0 && (
              <div className="mb-4">
                <h4 className="font-semibold text-lg mb-2">Reflexiones Finales:</h4>
                <ul className="list-disc pl-5 text-sm text-muted-foreground space-y-1">
                  {collectionData.final_reflections.map((reflection: string, idx: number) => (
                    <li key={idx}><div className="text-sm text-muted-foreground"><ReactMarkdown remarkPlugins={[remarkGfm]} children={reflection}/></div></li>
                  ))}
                </ul>
              </div>
            )}
            {collectionData?.collection_insights && collectionData.collection_insights.length > 0 && (
              <div className="mb-4">
                <h4 className="font-semibold text-lg mb-2">Insights de la Colección:</h4>
                <ul className="list-disc pl-5 text-sm text-muted-foreground space-y-1">
                  {collectionData.collection_insights.map((insight: string, idx: number) => (
                    <li key={idx}><div className="text-sm text-muted-foreground"><ReactMarkdown remarkPlugins={[remarkGfm]} children={insight}/></div></li>
                  ))}
                </ul>
              </div>
            )}
            {collectionData?.methodological_notes && collectionData.methodological_notes.length > 0 && (
              <div className="mb-4">
                <h4 className="font-semibold text-lg mb-2">Notas Metodológicas:</h4>
                <ul className="list-disc pl-5 text-sm text-muted-foreground space-y-1">
                  {collectionData.methodological_notes.map((note: string, idx: number) => (
                    <li key={idx}><div className="text-sm text-muted-foreground"><ReactMarkdown remarkPlugins={[remarkGfm]} children={note}/></div></li>
                  ))}
                </ul>
              </div>
            )}
            <AnalysisCommonFields analysis={analysis} processedOutput={processedOutput} />
          </>
        );
      case 'code':
        const codeResult = analysis.result as CodeAnalysisResultFrontend;
        return (
          <>
            <h3 className="text-xl font-bold mb-4">Análisis de Código Fuente</h3>

            {codeResult?.executive_summary && (
              <div className="mb-4 p-3 bg-muted rounded-md border border-border/50">
                <h4 className="font-semibold text-lg mb-2">Resumen Ejecutivo:</h4>
                <div className="text-sm text-muted-foreground whitespace-pre-wrap"><ReactMarkdown remarkPlugins={[remarkGfm]} children={codeResult.executive_summary || ''}/></div>
              </div>
            )}

            {codeResult?.code_structure && codeResult.code_structure.length > 0 && (
              <div className="mb-4">
                <h4 className="font-semibold text-lg mb-2">Estructura del Código:</h4>
                <ul className="list-disc pl-5 text-sm text-muted-foreground space-y-1">
                  {codeResult.code_structure.map((item: { component: string; description: string }, idx: number) => (
                    <li key={idx}>
                      <p className="font-semibold">{item.component}</p>
                      <ReactMarkdown remarkPlugins={[remarkGfm]} children={item.description}/>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {codeResult?.design_patterns && codeResult.design_patterns.length > 0 && (
              <div className="mb-4">
                <h4 className="font-semibold text-lg mb-2">Patrones de Diseño Identificados:</h4>
                <ul className="list-disc pl-5 text-sm text-muted-foreground space-y-1">
                  {codeResult.design_patterns.map((item: { pattern: string; description: string }, idx: number) => (
                    <li key={idx}>
                      <p className="font-semibold">{item.pattern}</p>
                      <ReactMarkdown remarkPlugins={[remarkGfm]} children={item.description}/>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {codeResult?.dependencies && codeResult.dependencies.length > 0 && (
              <div className="mb-4">
                <h4 className="font-semibold text-lg mb-2">Dependencias Clave:</h4>
                <ul className="list-disc pl-5 text-sm text-muted-foreground space-y-1">
                  {codeResult.dependencies.map((item: { library: string; description: string }, idx: number) => (
                    <li key={idx}>
                      <p className="font-semibold">{item.library}</p>
                      <ReactMarkdown remarkPlugins={[remarkGfm]} children={item.description}/>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {codeResult?.potential_issues && codeResult.potential_issues.length > 0 && (
              <div className="mb-4">
                <h4 className="font-semibold text-lg mb-2 flex items-center gap-2">
                  <AlertTriangle className="h-5 w-5 text-red-500" />
                  Problemas Potenciales:
                </h4>
                <ul className="list-disc pl-5 text-sm text-muted-foreground space-y-1">
                  {codeResult.potential_issues.map((item: { issue: string; description: string }, idx: number) => (
                    <li key={idx}>
                      <p className="font-semibold">{item.issue}</p>
                      <ReactMarkdown remarkPlugins={[remarkGfm]} children={item.description}/>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {codeResult?.recommendations && codeResult.recommendations.length > 0 && (
              <div className="mb-4">
                <h4 className="font-semibold text-lg mb-2">Recomendaciones:</h4>
                <ul className="list-disc pl-5 text-sm text-muted-foreground space-y-1">
                  {codeResult.recommendations.map((item: { recommendation: string; rationale: string; application: string; implementation: string }, idx: number) => (
                    <li key={idx}>
                      <p className="font-semibold">{item.recommendation}</p>
                      <p className="text-xs text-muted-foreground">**Justificación:** <ReactMarkdown remarkPlugins={[remarkGfm]} children={item.rationale}/></p>
                      <p className="text-xs text-muted-foreground">**Aplicación:** <ReactMarkdown remarkPlugins={[remarkGfm]} children={item.application}/></p>
                      <p className="text-xs text-muted-foreground">**Implementación:** <ReactMarkdown remarkPlugins={[remarkGfm]} children={item.implementation}/></p>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            
            <AnalysisCommonFields analysis={analysis} processedOutput={processedOutput} />
          </>
        );
      case 'document':
      case 'document_summary':
        const documentResult = analysis.result as SingleTextAnalysis;
        return (
          <>
            <h3 className="text-xl font-bold mb-4">Detalle del Documento Analizado</h3>

            {documentResult?.executive_summary && (
              <div className="mb-4 p-3 bg-muted rounded-md border border-border/50">
                <h4 className="font-semibold text-lg mb-2">Resumen Ejecutivo:</h4>
                <div className="text-sm text-muted-foreground whitespace-pre-wrap"><ReactMarkdown remarkPlugins={[remarkGfm]} children={documentResult.executive_summary || ''}/></div>
              </div>
            )}

            {documentResult?.general_analysis && (
              <div className="mb-4 p-3 bg-muted rounded-md border border-border/50">
                <h4 className="font-semibold text-lg mb-2">Análisis General:</h4>
                <div className="text-sm text-muted-foreground whitespace-pre-wrap"><ReactMarkdown remarkPlugins={[remarkGfm]} children={documentResult.general_analysis || ''}/></div>
              </div>
            )}

            {documentResult?.authorial_tone && (
              <p className="text-sm text-muted-foreground mb-1"><strong>Tono Autorial:</strong> {documentResult.authorial_tone}</p>
            )}

            {documentResult?.discipline && documentResult.discipline.length > 0 && (
              <div className="mb-4">
                <h4 className="font-semibold text-lg mb-2">Disciplina:</h4>
                <div className="flex flex-wrap gap-2">
                  {documentResult.discipline?.map((disc: string, idx: number) => (
                    <Badge key={idx} variant="outline" className="text-sm">
                      {disc}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {documentResult?.key_themes && documentResult.key_themes.length > 0 && (
              <div className="mb-4">
                <h4 className="font-semibold text-lg mb-2">Temas Clave:</h4>
                <div className="flex flex-wrap gap-2">
                  {documentResult.key_themes?.map((theme: ThemeReference, idx: number) => (
                    <Badge
                      key={idx}
                      variant="secondary"
                      className="cursor-pointer text-sm hover:bg-accent hover:text-accent-foreground transition-colors"
                      onClick={() => handleThemeClick(theme)}
                    >
                      {theme.theme}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {documentResult?.central_concepts && documentResult.central_concepts.length > 0 && (
              <div className="mb-4">
                <h4 className="font-semibold text-lg mb-2">Conceptos Centrales:</h4>
                <ul className="list-disc pl-5 text-sm text-muted-foreground space-y-1">
                  {documentResult.central_concepts?.map((concept: string, idx: number) => (
                    <li key={idx}><div className="text-sm text-muted-foreground"><ReactMarkdown remarkPlugins={[remarkGfm]} children={cleanAsterisks(concept)}/></div></li>
                  ))}
                </ul>
              </div>
            )}

            {documentResult?.knowledge_gaps && documentResult.knowledge_gaps.length > 0 && (
              <div className="mb-4">
                <h4 className="font-semibold text-lg mb-2">Brechas de Conocimiento:</h4>
                <ul className="list-disc pl-5 text-sm text-muted-foreground space-y-1">
                  {documentResult.knowledge_gaps?.map((gap: string, idx: number) => (
                    <li key={idx}><div className="text-sm text-muted-foreground"><ReactMarkdown remarkPlugins={[remarkGfm]} children={gap}/></div></li>
                  ))}
                </ul>
              </div>
            )}

            {documentResult?.exploration_questions && documentResult.exploration_questions.length > 0 && (
              <div className="mb-4">
                <h4 className="font-semibold text-lg mb-2">Preguntas para Explorar:</h4>
                <ul className="list-disc pl-5 text-sm text-muted-foreground space-y-1">
                  {documentResult.exploration_questions?.map((question: string, idx: number) => (
                    <li key={idx}><div className="text-sm text-muted-foreground"><ReactMarkdown remarkPlugins={[remarkGfm]} children={question}/></div></li>
                  ))}
                </ul>
              </div>
            )}

            {documentResult?.problematic_areas && documentResult.problematic_areas.length > 0 && (
              <div className="mb-4">
                <h4 className="font-semibold text-lg mb-2">Áreas Problemáticas:</h4>
                <ul className="list-disc pl-5 text-sm text-muted-foreground space-y-1">
                  {documentResult.problematic_areas?.map((area: string, idx: number) => (
                    <li key={idx}><div className="text-sm text-muted-foreground"><ReactMarkdown remarkPlugins={[remarkGfm]} children={area}/></div></li>
                  ))}
                </ul>
              </div>
            )}

            {documentResult?.final_reflections && documentResult.final_reflections.length > 0 && (
              <div className="mb-4">
                <h4 className="font-semibold text-lg mb-2">Reflexiones Finales:</h4>
                <ul className="list-disc pl-5 text-sm text-muted-foreground space-y-1">
                  {documentResult.final_reflections?.map((reflection: string, idx: number) => (
                    <li key={idx}><div className="text-sm text-muted-foreground"><ReactMarkdown remarkPlugins={[remarkGfm]} children={reflection}/></div></li>
                  ))}
                </ul>
              </div>
            )}

            <AnalysisCommonFields analysis={analysis} processedOutput={processedOutput} />
          </>
        );
      case 'announcement_draft':
      case 'strategic_objective':
      case 'market_trend':
      case 'experiment_proposal':
      case 'problem_statement':
      case 'goal_setting':
      case 'knowledge_retrieval':
      case 'agent_response_improvement':
      case 'verification':
      case 'information':
      case 'suggestion':
      case 'error':
      case 'warning':
      case 'question':
      case 'proactive_insight_manual':
      case 'topic_analysis': // topic_analysis también usará esta visualización genérica
        return (
          <>
            <h3 className="text-xl font-bold mb-4">Detalle del Análisis ({getAnalysisTypeLabel(analysis.type)})</h3>
            {analysis.summary && (
              <div className="mb-4 p-3 bg-muted rounded-md border border-border/50">
                <h4 className="font-semibold text-lg mb-2">Resumen:</h4>
                <div className="text-sm text-muted-foreground whitespace-pre-wrap"><ReactMarkdown remarkPlugins={[remarkGfm]} children={analysis.summary || ''}/></div>
              </div>
            )}
            {analysis.rawContent && !analysis.summary && ( // Mostrar rawContent si no hay summary
              <div className="mb-4 p-3 bg-muted rounded-md border border-border/50">
                <h4 className="font-semibold text-lg mb-2">Contenido:</h4>
                <div className="text-sm text-muted-foreground whitespace-pre-wrap"><ReactMarkdown remarkPlugins={[remarkGfm]} children={analysis.rawContent || ''}/></div>
              </div>
            )}
            {analysis.result && typeof analysis.result === 'string' && ( // Para topic_analysis que devuelve un string en result
              <div className="mb-4 p-3 bg-muted rounded-md border border-border/50">
                <h4 className="font-semibold text-lg mb-2">Resultado:</h4>
                <div className="text-sm text-muted-foreground whitespace-pre-wrap"><ReactMarkdown remarkPlugins={[remarkGfm]} children={analysis.result || ''}/></div>
              </div>
            )}

            <AnalysisCommonFields analysis={analysis} processedOutput={processedOutput} />

            {analysis.type === 'question' && analysis.questions && analysis.questions.length > 0 && (
              <div className="mt-6 p-4 border rounded-md bg-accent/20">
                <h4 className="font-bold mb-2 flex items-center gap-2"><HelpCircle className="h-5 w-5"/>Preguntas Relacionadas</h4>
                <ul className="list-disc pl-5 text-sm space-y-1">
                  {analysis.questions.map((q: Question | string, i: number) => (
                    <li key={i}>{typeof q === 'string' ? q : q.issue || q.description || `Pregunta ${i+1}`}</li>
                  ))}
                </ul>
              </div>
            )}
          </>
        );
      case 'workflow_suggestion':
        return (
          <>
            <h3 className="text-xl font-bold mb-4">Sugerencia de Flujo de Trabajo</h3>
            {analysis.workflow_steps && analysis.workflow_steps.length > 0 ? (
              <ol className="list-decimal pl-5 space-y-2 text-foreground">
                {analysis.workflow_steps.map((step: { title: string; description: string }, index: number) => (
                  <li key={index}>
                    <p className="font-semibold">{step.title}</p>
                    <div className="text-sm text-muted-foreground"><ReactMarkdown remarkPlugins={[remarkGfm]} children={step.description}/></div>
                  </li>
                ))}
              </ol>
            ) : (
              <div className="prose dark:prose-invert max-w-none"><ReactMarkdown remarkPlugins={[remarkGfm]} children={processedOutput.content || ''}/></div>
            )}
            <AnalysisCommonFields analysis={analysis} processedOutput={processedOutput} />
          </>
        );
      default:
        return (
          <>
            <div className="prose dark:prose-invert max-w-none"><ReactMarkdown remarkPlugins={[remarkGfm]} children={processedOutput.content || ''}/></div>
            <AnalysisCommonFields analysis={analysis} processedOutput={processedOutput} />
          </>
        );
    }
  }, [analysis, handleThemeClick, handleConceptClick, handlePlayPause, isCurrentlyLoading, isCurrentlyPlaying, textToRead]);

  if (!analysis) return null;

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
            <div className="p-6 pb-4 flex-1 overflow-y-auto">
              {hasInsights ? (
                <Tabs defaultValue="summary" className="w-full" onValueChange={setActiveTab} value={activeTab}>
                  <TabsList className="grid w-full grid-cols-3">
                    <TabsTrigger value="summary">Resumen</TabsTrigger>
                    {hasRawContent && <TabsTrigger value="rawContent">Contenido Original</TabsTrigger>}
                    {hasQuestions && <TabsTrigger value="questions">Preguntas</TabsTrigger>}
                  </TabsList>
                  <TabsContent value="summary" className="mt-4">
                    {renderTypeSpecificContent()}
                  </TabsContent>
                  {hasRawContent && (
                    <TabsContent value="rawContent" className="mt-4">
                      <div className="p-4 border rounded-md bg-background">
                        <pre className="whitespace-pre-wrap text-sm text-foreground">
                          {analysis.rawContent}
                        </pre>
                      </div>
                    </TabsContent>
                  )}
                  {hasQuestions && (
                    <TabsContent value="questions" className="mt-4">
                      <div className="p-4 border rounded-md bg-background">
                        <h4 className="font-bold mb-3">Preguntas generadas:</h4>
                        <ul className="list-disc pl-5 text-sm space-y-2">
                          {getQuestions().map((q: Question | string, i: number) => (
                            <li key={i}>{typeof q === 'string' ? q : q.issue || q.description || `Pregunta ${i+1}`}</li>
                          ))}
                        </ul>
                        <Button
                          onClick={() => setIsQuestionsDialogOpen(true)}
                          className="mt-4 w-full"
                        >
                          Ver Preguntas en Modo Slider
                        </Button>
                      </div>
                    </TabsContent>
                  )}
                </Tabs>
              ) : (
                renderTypeSpecificContent()
              )}
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

      {/* Nuevo diálogo para mostrar citas de temas */}
      <ThemeQuotesDialog
        isOpen={isThemeQuotesDialogOpen}
        onOpenChange={setIsThemeQuotesDialogOpen}
        theme={selectedThemeForQuotes}
      />

      {/* Nuevo diálogo para mostrar detalles de conceptos */}
      <ConceptDetailDialog
        isOpen={isConceptDialogOpen}
        onOpenChange={setIsConceptDialogOpen}
        concept={selectedConcept}
      />
    </>
  );
}