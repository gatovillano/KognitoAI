import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Analysis, AnalysisType, Insight, Question, CollectionAnalysis, DocumentAnalysisResult as SingleTextAnalysis, CollectionConnection, ThemeReference, ThemeQuote, CodeAnalysisResultFrontend, NoteCollectionAnalysisResult, NoteAnalysisResult } from '@/lib/models';
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

// Helper function to get color scheme for each analysis type
const getAnalysisColorScheme = (type: AnalysisType) => {
  switch (type) {
    case 'document':
    case 'document_summary':
      return {
        color: 'blue',
        cardBg: 'bg-blue-50/50 border-blue-100 dark:bg-blue-900/10 dark:border-blue-900/50',
        cardTitle: 'text-blue-900 dark:text-blue-100',
        icon: 'text-blue-600',
        alertGradient: 'from-blue-50 to-indigo-50 border-blue-200 dark:from-blue-950/30 dark:to-indigo-950/30 dark:border-blue-800',
        alertIcon: 'text-blue-600 dark:text-blue-400',
        alertTitle: 'text-blue-800 dark:text-blue-300',
        alertDesc: 'text-blue-900/90 dark:text-blue-200/90',
        hoverBorder: 'hover:border-blue-200'
      };
    case 'collection':
      return {
        color: 'green',
        cardBg: 'bg-green-50/50 border-green-100 dark:bg-green-900/10 dark:border-green-900/50',
        cardTitle: 'text-green-900 dark:text-green-100',
        icon: 'text-green-600',
        alertGradient: 'from-green-50 to-emerald-50 border-green-200 dark:from-green-950/30 dark:to-emerald-950/30 dark:border-green-800',
        alertIcon: 'text-green-600 dark:text-green-400',
        alertTitle: 'text-green-800 dark:text-green-300',
        alertDesc: 'text-green-900/90 dark:text-green-200/90',
        hoverBorder: 'hover:border-green-200'
      };
    case 'semantic':
    case 'semantic_summary':
      return {
        color: 'indigo',
        cardBg: 'bg-indigo-50/50 border-indigo-100 dark:bg-indigo-900/10 dark:border-indigo-900/50',
        cardTitle: 'text-indigo-900 dark:text-indigo-100',
        icon: 'text-indigo-600',
        alertGradient: 'from-indigo-50 to-purple-50 border-indigo-200 dark:from-indigo-950/30 dark:to-purple-950/30 dark:border-indigo-800',
        alertIcon: 'text-indigo-600 dark:text-indigo-400',
        alertTitle: 'text-indigo-800 dark:text-indigo-300',
        alertDesc: 'text-indigo-900/90 dark:text-indigo-200/90',
        hoverBorder: 'hover:border-indigo-200'
      };
    case 'code':
      return {
        color: 'cyan',
        cardBg: 'bg-cyan-50/50 border-cyan-100 dark:bg-cyan-900/10 dark:border-cyan-900/50',
        cardTitle: 'text-cyan-900 dark:text-cyan-100',
        icon: 'text-cyan-600',
        alertGradient: 'from-cyan-50 to-blue-50 border-cyan-200 dark:from-cyan-950/30 dark:to-blue-950/30 dark:border-cyan-800',
        alertIcon: 'text-cyan-600 dark:text-cyan-400',
        alertTitle: 'text-cyan-800 dark:text-cyan-300',
        alertDesc: 'text-cyan-900/90 dark:text-cyan-200/90',
        hoverBorder: 'hover:border-cyan-200'
      };
    case 'insight':
    case 'proactive_insight_manual':
      return {
        color: 'yellow',
        cardBg: 'bg-yellow-50/50 border-yellow-100 dark:bg-yellow-900/10 dark:border-yellow-900/50',
        cardTitle: 'text-yellow-900 dark:text-yellow-100',
        icon: 'text-yellow-600',
        alertGradient: 'from-yellow-50 to-amber-50 border-yellow-200 dark:from-yellow-950/30 dark:to-amber-950/30 dark:border-yellow-800',
        alertIcon: 'text-yellow-600 dark:text-yellow-400',
        alertTitle: 'text-yellow-800 dark:text-yellow-300',
        alertDesc: 'text-yellow-900/90 dark:text-yellow-200/90',
        hoverBorder: 'hover:border-yellow-200'
      };
    case 'note_analysis':
      return {
        color: 'amber',
        cardBg: 'bg-amber-50/50 border-amber-100 dark:bg-amber-900/10 dark:border-amber-900/50',
        cardTitle: 'text-amber-900 dark:text-amber-100',
        icon: 'text-amber-600',
        alertGradient: 'from-amber-50 to-yellow-50 border-amber-200 dark:from-amber-950/30 dark:to-yellow-950/30 dark:border-amber-800',
        alertIcon: 'text-amber-600 dark:text-amber-400',
        alertTitle: 'text-amber-800 dark:text-amber-300',
        alertDesc: 'text-amber-900/90 dark:text-amber-200/90',
        hoverBorder: 'hover:border-amber-200'
      };
    case 'note_collection_analysis':
      return {
        color: 'orange',
        cardBg: 'bg-orange-50/50 border-orange-100 dark:bg-orange-900/10 dark:border-orange-900/50',
        cardTitle: 'text-orange-900 dark:text-orange-100',
        icon: 'text-orange-600',
        alertGradient: 'from-orange-50 to-red-50 border-orange-200 dark:from-orange-950/30 dark:to-red-950/30 dark:border-orange-800',
        alertIcon: 'text-orange-600 dark:text-orange-400',
        alertTitle: 'text-orange-800 dark:text-orange-300',
        alertDesc: 'text-orange-900/90 dark:text-orange-200/90',
        hoverBorder: 'hover:border-orange-200'
      };
    case 'knowledge_graph_analysis':
      return {
        color: 'purple',
        cardBg: 'bg-purple-50/50 border-purple-100 dark:bg-purple-900/10 dark:border-purple-900/50',
        cardTitle: 'text-purple-900 dark:text-purple-100',
        icon: 'text-purple-600',
        alertGradient: 'from-purple-50 to-pink-50 border-purple-200 dark:from-purple-950/30 dark:to-pink-950/30 dark:border-purple-800',
        alertIcon: 'text-purple-600 dark:text-purple-400',
        alertTitle: 'text-purple-800 dark:text-purple-300',
        alertDesc: 'text-purple-900/90 dark:text-purple-200/90',
        hoverBorder: 'hover:border-purple-200'
      };
    case 'custom_analysis':
      return {
        color: 'red',
        cardBg: 'bg-red-50/50 border-red-100 dark:bg-red-900/10 dark:border-red-900/50',
        cardTitle: 'text-red-900 dark:text-red-100',
        icon: 'text-red-600',
        alertGradient: 'from-red-50 to-rose-50 border-red-200 dark:from-red-950/30 dark:to-rose-950/30 dark:border-red-800',
        alertIcon: 'text-red-600 dark:text-red-400',
        alertTitle: 'text-red-800 dark:text-red-300',
        alertDesc: 'text-red-900/90 dark:text-red-200/90',
        hoverBorder: 'hover:border-red-200'
      };
    default:
      return {
        color: 'gray',
        cardBg: 'bg-gray-50/50 border-gray-100 dark:bg-gray-900/10 dark:border-gray-900/50',
        cardTitle: 'text-gray-900 dark:text-gray-100',
        icon: 'text-gray-600',
        alertGradient: 'from-gray-50 to-slate-50 border-gray-200 dark:from-gray-950/30 dark:to-slate-950/30 dark:border-gray-800',
        alertIcon: 'text-gray-600 dark:text-gray-400',
        alertTitle: 'text-gray-800 dark:text-gray-300',
        alertDesc: 'text-gray-900/90 dark:text-gray-200/90',
        hoverBorder: 'hover:border-gray-200'
      };
  }
};

const getAnalysisTypeBadgeColor = (type: AnalysisType) => {
  switch (type) {
    case 'document':
    case 'document_summary':
      return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-100 border-blue-200 dark:border-blue-800';
    case 'collection':
      return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100 border-green-200 dark:border-green-800';
    case 'semantic':
    case 'semantic_summary':
      return 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-100 border-indigo-200 dark:border-indigo-800';
    case 'code':
      return 'bg-cyan-100 text-cyan-800 dark:bg-cyan-900 dark:text-cyan-100 border-cyan-200 dark:border-cyan-800';
    case 'insight':
    case 'proactive_insight_manual':
      return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-100 border-yellow-200 dark:border-yellow-800';
    case 'note_analysis':
      return 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-100 border-amber-200 dark:border-amber-800';
    case 'note_collection_analysis':
      return 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-100 border-orange-200 dark:border-orange-800';
    case 'knowledge_graph_analysis':
      return 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-100 border-purple-200 dark:border-purple-800';
    case 'custom_analysis':
      return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-100 border-red-200 dark:border-red-800';
    default:
      return 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-100 border-gray-200 dark:border-gray-700';
  }
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

  // Parsear el concepto en formato "CONCEPTO: DEFINICIÓN"
  const conceptParts = concept.split(':');
  const conceptName = conceptParts[0]?.trim() || '';
  const conceptDefinition = conceptParts.slice(1).join(':').trim() || '';

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl w-full max-h-[80vh] rounded-lg bg-card border shadow-lg flex flex-col overflow-hidden">
        <DialogHeader className="px-6 pt-6 pb-4">
          <DialogTitle className="text-xl font-bold text-foreground">
            Detalles del Concepto
          </DialogTitle>
        </DialogHeader>

        <ScrollArea className="flex-1 px-6 py-2">
          <div className="space-y-4 pb-4">
            {/* Concepto Principal */}
            <div>
              <h4 className="text-lg font-semibold text-foreground mb-2">
                {conceptName}
              </h4>
            </div>

            {/* Definición */}
            <div>
              <div className="prose prose-sm max-w-none dark:prose-invert
                prose-headings:text-foreground prose-headings:font-semibold
                prose-p:text-muted-foreground prose-p:leading-relaxed
                prose-strong:text-foreground prose-strong:font-semibold
                prose-ul:text-muted-foreground prose-li:text-muted-foreground
                prose-a:text-blue-600 dark:prose-a:text-blue-400 prose-a:underline">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {conceptDefinition}
                </ReactMarkdown>
              </div>
            </div>

            {/* Nota informativa */}
            <div className="pt-4 text-xs text-muted-foreground italic border-t">
              Para profundizar en este concepto, puedes realizar una búsqueda dirigida en la colección.
            </div>
          </div>
        </ScrollArea>

        <DialogFooter className="px-6 py-4 border-t">
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
          >
            Cerrar
          </Button>
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
    case 'knowledge_graph_analysis': return <Network className="text-purple-500" />;
    case 'custom_analysis': return <FlaskConical className="text-red-500" />;
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
    case 'knowledge_graph_analysis': return 'Análisis de Grafo de Conocimiento';
    case 'custom_analysis': return 'Análisis Personalizado';
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
    <div className="text-sm text-muted-foreground mb-3"><ReactMarkdown remarkPlugins={[remarkGfm]}>{typeof insight.description === 'string' ? insight.description : JSON.stringify(insight.description || '')}</ReactMarkdown></div>
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
            <li key={i}><div className="text-sm text-muted-foreground"><ReactMarkdown remarkPlugins={[remarkGfm]}>{typeof rec === 'string' ? rec : JSON.stringify(rec)}</ReactMarkdown></div></li>
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
                  <div className="italic mb-1"><ReactMarkdown remarkPlugins={[remarkGfm]}>{`"${typeof quote.quote === 'string' ? quote.quote : JSON.stringify(quote.quote)}"`}</ReactMarkdown></div>
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

  const handlePlayPause = useCallback(() => {
    play(textToRead);
  }, [play, textToRead]);
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
        const semanticColors = getAnalysisColorScheme(analysis.type);
        return (
          <>
            <h3 className="text-xl font-bold mb-4">Detalle del Resumen Semántico - KAI Exocerebro</h3>

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
              <Card className={`mb-4 ${semanticColors.cardBg}`}>
                <CardHeader className="pb-2">
                  <CardTitle className={`text-lg font-semibold ${semanticColors.cardTitle} flex items-center gap-2`}>
                    <ScrollText className="w-5 h-5" />
                    Resumen Semántico
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="prose prose-sm max-w-none dark:prose-invert text-muted-foreground">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{analysis.full_data.resumen_semantico}</ReactMarkdown>
                  </div>
                </CardContent>
              </Card>
            )}

            {analysis.full_data?.temas_transversales && analysis.full_data.temas_transversales.length > 0 && (
              <div className="mb-4">
                <h4 className={`font-semibold text-lg mb-2 flex items-center gap-2 ${semanticColors.icon}`}>
                  <Target className="w-5 h-5" />
                  Temas Transversales
                </h4>
                <div className="flex flex-wrap gap-2">
                  {analysis.full_data.temas_transversales?.map((theme: ThemeReference, idx: number) => (
                    <Badge
                      key={idx}
                      className={`cursor-pointer text-sm transition-colors border ${getAnalysisTypeBadgeColor(analysis.type)}`}
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
                <h4 className={`font-semibold text-lg mb-2 flex items-center gap-2 ${semanticColors.icon}`}>
                  <BarChart3 className="w-5 h-5" />
                  Estadísticas del Análisis
                </h4>
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4 text-center">
                  {analysis.full_data.patrones_semanticos.total_documentos && (
                    <div className="p-3 bg-muted rounded-md border border-border/50">
                      <div className={`text-2xl font-bold ${semanticColors.icon}`}>
                        {analysis.full_data.patrones_semanticos.total_documentos}
                      </div>
                      <div className="text-xs text-muted-foreground">Documentos</div>
                    </div>
                  )}
                  {analysis.full_data.patrones_semanticos.total_chunks_analizados && (
                    <div className="p-3 bg-muted rounded-md border border-border/50">
                      <div className={`text-2xl font-bold ${semanticColors.icon}`}>
                        {analysis.full_data.patrones_semanticos.total_chunks_analizados}
                      </div>
                      <div className="text-xs text-muted-foreground">Fragmentos</div>
                    </div>
                  )}
                  {analysis.full_data.patrones_semanticos.temas_identificados && (
                    <div className="p-3 bg-muted rounded-md border border-border/50">
                      <div className={`text-2xl font-bold ${semanticColors.icon}`}>
                        {analysis.full_data.patrones_semanticos.temas_identificados}
                      </div>
                      <div className="text-xs text-muted-foreground">Temas</div>
                    </div>
                  )}
                  <div className="p-3 bg-muted rounded-md border border-border/50">
                    <div className={`text-2xl font-bold ${semanticColors.icon}`}>
                      {analysis.full_data.conceptos_centrales.length}
                    </div>
                    <div className="text-xs text-muted-foreground">Conceptos</div>
                  </div>
                </div>
              </div>
            )}

            {analysis.full_data?.brechas_conocimiento && analysis.full_data.brechas_conocimiento.length > 0 && (
              <div className="mb-4">
                <h4 className={`font-semibold text-lg mb-2 flex items-center gap-2 ${semanticColors.icon}`}>
                  <AlertTriangle className="w-5 h-5" />
                  Brechas de Conocimiento
                </h4>
                <ul className="list-disc pl-5 text-sm text-muted-foreground space-y-1">
                  {analysis.full_data.brechas_conocimiento?.map((gap: string, idx: number) => (
                    <li key={idx}><div className="text-sm text-muted-foreground"><ReactMarkdown remarkPlugins={[remarkGfm]}>{gap}</ReactMarkdown></div></li>
                  ))}
                </ul>
              </div>
            )}

            {analysis.full_data?.problematic_areas && analysis.full_data.problematic_areas.length > 0 && (
              <div className="mb-4">
                <h4 className="font-semibold text-lg mb-2 flex items-center gap-2 text-red-600">
                  <AlertTriangle className="w-5 h-5" />
                  Problemáticas
                </h4>
                <ul className="list-disc pl-5 text-sm text-muted-foreground space-y-1">
                  {analysis.full_data.problematic_areas?.map((area: string, idx: number) => (
                    <li key={idx}><div className="text-sm text-muted-foreground"><ReactMarkdown remarkPlugins={[remarkGfm]}>{area}</ReactMarkdown></div></li>
                  ))}
                </ul>
              </div>
            )}

            {analysis.full_data?.exploration_questions && analysis.full_data.exploration_questions.length > 0 && (
              <div className="mb-4">
                <h4 className={`font-semibold text-lg mb-2 flex items-center gap-2 ${semanticColors.icon}`}>
                  <HelpCircle className="w-5 h-5" />
                  Preguntas para Explorar
                </h4>
                <ul className="list-disc pl-5 text-sm text-muted-foreground space-y-1">
                  {analysis.full_data.exploration_questions?.map((question: string, idx: number) => (
                    <li key={idx}><div className="text-sm text-muted-foreground"><ReactMarkdown remarkPlugins={[remarkGfm]}>{question}</ReactMarkdown></div></li>
                  ))}
                </ul>
              </div>
            )}

            {analysis.full_data?.final_reflections && analysis.full_data.final_reflections.length > 0 && (
              <div className="mb-4">
                <h4 className={`font-semibold text-lg mb-2 flex items-center gap-2 ${semanticColors.icon}`}>
                  <Sparkles className="w-5 h-5" />
                  Reflexiones Finales
                </h4>
                <ul className="list-disc pl-5 text-sm text-muted-foreground space-y-1">
                  {analysis.full_data.final_reflections?.map((reflection: string, idx: number) => (
                    <li key={idx}><div className="text-sm text-muted-foreground"><ReactMarkdown remarkPlugins={[remarkGfm]}>{reflection}</ReactMarkdown></div></li>
                  ))}
                </ul>
              </div>
            )}

            <AnalysisCommonFields analysis={analysis} processedOutput={processedOutput} />
          </>
        );
      case 'insight':
        const insightColors = getAnalysisColorScheme(analysis.type);
        return (
          <>
            <h3 className="text-xl font-bold mb-4">Detalle del Insight - KAI Exocerebro</h3>

            {analysis.summary && (
              <Card className={`mb-4 ${insightColors.cardBg}`}>
                <CardHeader className="pb-2">
                  <CardTitle className={`text-lg font-semibold ${insightColors.cardTitle} flex items-center gap-2`}>
                    <Lightbulb className="w-5 h-5" />
                    Resumen del Insight
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="prose prose-sm max-w-none dark:prose-invert text-muted-foreground">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{analysis.summary}</ReactMarkdown>
                  </div>
                </CardContent>
              </Card>
            )}

            {analysis.action_suggestion && (
              <Alert className={`mb-4 bg-gradient-to-r ${insightColors.alertGradient}`}>
                <Goal className={`h-5 w-5 ${insightColors.alertIcon}`} />
                <AlertTitle className={`${insightColors.alertTitle} font-semibold mb-2`}>Sugerencia de Acción</AlertTitle>
                <AlertDescription className={`${insightColors.alertDesc}`}>
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{analysis.action_suggestion}</ReactMarkdown>
                </AlertDescription>
              </Alert>
            )}

            {analysis.related_items && analysis.related_items.length > 0 && (
              <div className="mb-4">
                <h4 className={`font-semibold text-lg mb-3 flex items-center gap-2 ${insightColors.icon}`}>
                  <Network className="w-5 h-5" />
                  Elementos Relacionados
                </h4>
                <div className="flex flex-wrap gap-2">
                  {analysis.related_items.map((item: { title?: string; name?: string }, idx: number) => (
                    <Badge key={idx} variant="secondary" className={getAnalysisTypeBadgeColor(analysis.type)}>
                      {item.title || item.name || `Item ${idx + 1}`}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {analysis.tool_used && (
              <div className="mb-4">
                <h4 className={`font-semibold text-lg mb-3 flex items-center gap-2 ${insightColors.icon}`}>
                  <Settings className="w-5 h-5" />
                  Herramienta Utilizada
                </h4>
                <Badge variant="outline" className="text-sm font-mono bg-slate-50 text-slate-600 border-slate-200 dark:bg-slate-800 dark:text-slate-400 dark:border-slate-700">
                  {analysis.tool_used}
                </Badge>
              </div>
            )}

            {(analysis.created_at || analysis.updated_at) && (
              <div className="mb-4 text-xs text-muted-foreground space-y-1">
                {analysis.created_at && (
                  <p className="flex items-center gap-2">
                    <Calendar className="w-3 h-3" />
                    <strong>Creado:</strong> {new Date(analysis.created_at).toLocaleString()}
                  </p>
                )}
                {analysis.updated_at && analysis.updated_at !== analysis.created_at && (
                  <p className="flex items-center gap-2">
                    <Calendar className="w-3 h-3" />
                    <strong>Actualizado:</strong> {new Date(analysis.updated_at).toLocaleString()}
                  </p>
                )}
              </div>
            )}

            <AnalysisCommonFields analysis={analysis} processedOutput={processedOutput} />
          </>
        );
      case 'collection':
        const collectionData = analysis.full_data as CollectionAnalysis;
        const colColors = getAnalysisColorScheme(analysis.type);
        return (
          <>
            <h3 className="text-xl font-bold mb-4">Detalle de Análisis de Colección - KAI Exocerebro</h3>

            {collectionData?.collection_summary && (
              <Card className={`mb-4 ${colColors.cardBg}`}>
                <CardHeader className="pb-2">
                  <CardTitle className={`text-lg font-semibold ${colColors.cardTitle} flex items-center gap-2`}>
                    <ScrollText className="w-5 h-5" />
                    Resumen de la Colección
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="prose prose-sm max-w-none dark:prose-invert text-muted-foreground">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{collectionData.collection_summary}</ReactMarkdown>
                  </div>
                </CardContent>
              </Card>
            )}

            {collectionData?.kai_synthesis && (
              <Alert className={`mb-4 bg-gradient-to-r ${colColors.alertGradient}`}>
                <Sparkles className={`h-5 w-5 ${colColors.alertIcon}`} />
                <AlertTitle className={`${colColors.alertTitle} font-semibold mb-2`}>Síntesis de KAI</AlertTitle>
                <AlertDescription className={`${colColors.alertDesc} italic`}>
                  "{collectionData.kai_synthesis}"
                </AlertDescription>
              </Alert>
            )}

            {collectionData?.cross_cutting_themes && collectionData.cross_cutting_themes.length > 0 && (
              <div className="mb-4">
                <h4 className={`font-semibold text-lg mb-2 flex items-center gap-2 ${colColors.icon}`}>
                  <Target className="w-5 h-5" />
                  Temas Transversales
                </h4>
                <div className="flex flex-wrap gap-2">
                  {collectionData.cross_cutting_themes.map((theme: ThemeReference, idx: number) => (
                    <Badge
                      key={idx}
                      className={`cursor-pointer text-sm transition-colors border ${getAnalysisTypeBadgeColor(analysis.type)}`}
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
                <h4 className={`font-semibold text-lg mb-2 flex items-center gap-2 ${colColors.icon}`}>
                  <Lightbulb className="w-5 h-5" />
                  Conceptos Centrales
                </h4>
                <div className="flex flex-wrap gap-2">
                  {collectionData.central_concepts.map((concept: string, idx: number) => (
                    <Badge
                      key={idx}
                      variant="outline"
                      className={`cursor-pointer text-sm transition-colors border hover:bg-accent hover:text-accent-foreground ${getAnalysisTypeBadgeColor(analysis.type)}`}
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
                <h4 className={`font-semibold text-lg mb-2 flex items-center gap-2 ${colColors.icon}`}>
                  <BarChart3 className="w-5 h-5" />
                  Estadísticas del Análisis
                </h4>
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4 text-center">
                  {collectionData.patrones_semanticos.total_documentos && (
                    <div className="p-3 bg-muted rounded-md border border-border/50">
                      <div className={`text-2xl font-bold ${colColors.icon}`}>
                        {collectionData.patrones_semanticos.total_documentos}
                      </div>
                      <div className="text-xs text-muted-foreground">Documentos</div>
                    </div>
                  )}
                  {collectionData.patrones_semanticos.total_chunks_analizados && (
                    <div className="p-3 bg-muted rounded-md border border-border/50">
                      <div className={`text-2xl font-bold ${colColors.icon}`}>
                        {collectionData.patrones_semanticos.total_chunks_analizados}
                      </div>
                      <div className="text-xs text-muted-foreground">Fragmentos</div>
                    </div>
                  )}
                  {collectionData.patrones_semanticos.temas_identificados && (
                    <div className="p-3 bg-muted rounded-md border border-border/50">
                      <div className={`text-2xl font-bold ${colColors.icon}`}>
                        {collectionData.patrones_semanticos.temas_identificados}
                      </div>
                      <div className="text-xs text-muted-foreground">Temas</div>
                    </div>
                  )}
                  <div className="p-3 bg-muted rounded-md border border-border/50">
                    <div className={`text-2xl font-bold ${colColors.icon}`}>
                      {collectionData.central_concepts.length}
                    </div>
                    <div className="text-xs text-muted-foreground">Conceptos</div>
                  </div>
                </div>
              </div>
            )}

            {collectionData?.concept_relationships && collectionData.concept_relationships.length > 0 && (
              <div className="mb-4">
                <h4 className={`font-semibold text-lg mb-2 flex items-center gap-2 ${colColors.icon}`}>
                  <Network className="w-5 h-5" />
                  Relaciones entre Conceptos
                </h4>
                <ul className="list-disc pl-5 text-sm text-muted-foreground space-y-1">
                  {collectionData.concept_relationships.map((relationship: string, idx: number) => (
                    <li key={idx}><div className="text-sm text-muted-foreground"><ReactMarkdown remarkPlugins={[remarkGfm]}>{relationship}</ReactMarkdown></div></li>
                  ))}
                </ul>
              </div>
            )}

            {collectionData?.identified_connections && collectionData.identified_connections.length > 0 && (
              <div className="mb-4">
                <h4 className={`font-semibold text-lg mb-2 flex items-center gap-2 ${colColors.icon}`}>
                  <GitBranch className="w-5 h-5" />
                  Conexiones Identificadas
                </h4>
                <ul className="list-disc pl-5 text-sm text-muted-foreground space-y-1">
                  {collectionData.identified_connections.map((connection: CollectionConnection, idx: number) => (
                    <li key={idx}>
                      <p className="font-semibold">{connection.document_titles.join(', ')}</p>
                      <div className="text-sm text-muted-foreground"><ReactMarkdown remarkPlugins={[remarkGfm]}>{connection.insight}</ReactMarkdown></div>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {collectionData?.emergent_knowledge_gaps && collectionData.emergent_knowledge_gaps.length > 0 && (
              <div className="mb-4">
                <h4 className={`font-semibold text-lg mb-2 flex items-center gap-2 ${colColors.icon}`}>
                  <AlertTriangle className="w-5 h-5" />
                  Brechas de Conocimiento Emergentes
                </h4>
                <ul className="list-disc pl-5 text-sm text-muted-foreground space-y-1">
                  {collectionData.emergent_knowledge_gaps.map((gap: string, idx: number) => (
                    <li key={idx}><div className="text-sm text-muted-foreground"><ReactMarkdown remarkPlugins={[remarkGfm]}>{gap}</ReactMarkdown></div></li>
                  ))}
                </ul>
              </div>
            )}

            {collectionData?.exploration_questions && collectionData.exploration_questions.length > 0 && (
              <div className="mb-4">
                <h4 className={`font-semibold text-lg mb-2 flex items-center gap-2 ${colColors.icon}`}>
                  <HelpCircle className="w-5 h-5" />
                  Preguntas para Explorar
                </h4>
                <ul className="list-disc pl-5 text-sm text-muted-foreground space-y-1">
                  {collectionData.exploration_questions.map((question: string, idx: number) => (
                    <li key={idx}><div className="text-sm text-muted-foreground"><ReactMarkdown remarkPlugins={[remarkGfm]}>{question}</ReactMarkdown></div></li>
                  ))}
                </ul>
              </div>
            )}

            {collectionData?.problematic_areas && collectionData.problematic_areas.length > 0 && (
              <div className="mb-4">
                <h4 className="font-semibold text-lg mb-2 flex items-center gap-2 text-red-600">
                  <AlertTriangle className="w-5 h-5" />
                  Problemáticas
                </h4>
                <ul className="list-disc pl-5 text-sm text-muted-foreground space-y-1">
                  {collectionData.problematic_areas.map((area: string, idx: number) => (
                    <li key={idx}><div className="text-sm text-muted-foreground"><ReactMarkdown remarkPlugins={[remarkGfm]}>{area}</ReactMarkdown></div></li>
                  ))}
                </ul>
              </div>
            )}

            {collectionData?.final_reflections && collectionData.final_reflections.length > 0 && (
              <div className="mb-4">
                <h4 className={`font-semibold text-lg mb-2 flex items-center gap-2 ${colColors.icon}`}>
                  <Sparkles className="w-5 h-5" />
                  Reflexiones Finales
                </h4>
                <ul className="list-disc pl-5 text-sm text-muted-foreground space-y-1">
                  {collectionData.final_reflections.map((reflection: string, idx: number) => (
                    <li key={idx}><div className="text-sm text-muted-foreground"><ReactMarkdown remarkPlugins={[remarkGfm]}>{reflection}</ReactMarkdown></div></li>
                  ))}
                </ul>
              </div>
            )}

            {collectionData?.collection_insights && collectionData.collection_insights.length > 0 && (
              <div className="mb-4">
                <h4 className={`font-semibold text-lg mb-2 flex items-center gap-2 ${colColors.icon}`}>
                  <Lightbulb className="w-5 h-5" />
                  Insights de la Colección
                </h4>
                <ul className="list-disc pl-5 text-sm text-muted-foreground space-y-1">
                  {collectionData.collection_insights.map((insight: string, idx: number) => (
                    <li key={idx}><div className="text-sm text-muted-foreground"><ReactMarkdown remarkPlugins={[remarkGfm]}>{insight}</ReactMarkdown></div></li>
                  ))}
                </ul>
              </div>
            )}

            {collectionData?.methodological_notes && collectionData.methodological_notes.length > 0 && (
              <div className="mb-4">
                <h4 className={`font-semibold text-lg mb-2 flex items-center gap-2 ${colColors.icon}`}>
                  <FileText className="w-5 h-5" />
                  Notas Metodológicas
                </h4>
                <ul className="list-disc pl-5 text-sm text-muted-foreground space-y-1">
                  {collectionData.methodological_notes.map((note: string, idx: number) => (
                    <li key={idx}><div className="text-sm text-muted-foreground"><ReactMarkdown remarkPlugins={[remarkGfm]}>{note}</ReactMarkdown></div></li>
                  ))}
                </ul>
              </div>
            )}

            <AnalysisCommonFields analysis={analysis} processedOutput={processedOutput} />
          </>
        );
      case 'code':
        const codeResult = (analysis.result || analysis.full_data) as CodeAnalysisResultFrontend;
        const codeColors = getAnalysisColorScheme(analysis.type);

        return (
          <>
            <h3 className="text-xl font-bold mb-4">Análisis de Código Fuente - KAI Exocerebro</h3>

            <Tabs defaultValue="overview" className="w-full">
              <TabsList className="grid w-full grid-cols-2 md:grid-cols-3 lg:grid-cols-6 mb-4">
                <TabsTrigger value="overview">Resumen</TabsTrigger>
                <TabsTrigger value="structure">Estructura</TabsTrigger>
                <TabsTrigger value="patterns">Patrones</TabsTrigger>
                <TabsTrigger value="dependencies">Dependencias</TabsTrigger>
                <TabsTrigger value="issues">Problemas</TabsTrigger>
                <TabsTrigger value="recommendations">Recomendaciones</TabsTrigger>
              </TabsList>

              <TabsContent value="overview" className="space-y-4">
                {codeResult?.executive_summary && (
                  <Card className={`${codeColors.cardBg}`}>
                    <CardHeader className="pb-2">
                      <CardTitle className={`text-lg font-semibold ${codeColors.cardTitle} flex items-center gap-2`}>
                        <FileText className="w-5 h-5" />
                        Resumen Ejecutivo
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="prose prose-sm max-w-none dark:prose-invert text-muted-foreground">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{codeResult.executive_summary}</ReactMarkdown>
                      </div>
                    </CardContent>
                  </Card>
                )}
              </TabsContent>

              <TabsContent value="structure" className="space-y-4">
                {codeResult?.code_structure && codeResult.code_structure.length > 0 ? (
                  <Card className="border-none shadow-none bg-transparent p-0">
                    <CardHeader className="px-0 pt-0 pb-2">
                      <CardTitle className={`flex items-center gap-2 text-lg font-semibold ${codeColors.cardTitle}`}>
                        <GitBranch className="h-5 w-5" />
                        Estructura del Código ({codeResult.code_structure.length} componentes)
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="p-0">
                      <div className="space-y-3">
                        {codeResult.code_structure.map((item: { component: string; description: string }, idx: number) => (
                          <div key={idx} className={`border-l-4 border-blue-500 pl-4 p-3 bg-muted rounded-md border border-border/50 ${codeColors.hoverBorder}`}>
                            <h4 className="font-medium">{item.component}</h4>
                            <div className="text-sm text-muted-foreground"><ReactMarkdown remarkPlugins={[remarkGfm]}>{item.description}</ReactMarkdown></div>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                ) : (
                  <p className="text-sm text-muted-foreground">No se encontraron componentes de estructura.</p>
                )}
              </TabsContent>

              <TabsContent value="patterns" className="space-y-4">
                {codeResult?.design_patterns && codeResult.design_patterns.length > 0 ? (
                  <Card className="border-none shadow-none bg-transparent p-0">
                    <CardHeader className="px-0 pt-0 pb-2">
                      <CardTitle className={`flex items-center gap-2 text-lg font-semibold ${codeColors.cardTitle}`}>
                        <Settings className="h-5 w-5" />
                        Patrones de Diseño ({codeResult.design_patterns.length} patrones)
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="p-0">
                      <div className="space-y-3">
                        {codeResult.design_patterns.map((item: { pattern: string; description: string }, idx: number) => (
                          <div key={idx} className={`border-l-4 border-green-500 pl-4 p-3 bg-muted rounded-md border border-border/50 ${codeColors.hoverBorder}`}>
                            <h4 className="font-medium">{item.pattern}</h4>
                            <div className="text-sm text-muted-foreground"><ReactMarkdown remarkPlugins={[remarkGfm]}>{item.description}</ReactMarkdown></div>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                ) : (
                  <p className="text-sm text-muted-foreground">No se encontraron patrones de diseño específicos.</p>
                )}
              </TabsContent>

              <TabsContent value="dependencies" className="space-y-4">
                {codeResult?.dependencies && codeResult.dependencies.length > 0 ? (
                  <Card className="border-none shadow-none bg-transparent p-0">
                    <CardHeader className="px-0 pt-0 pb-2">
                      <CardTitle className={`flex items-center gap-2 text-lg font-semibold ${codeColors.cardTitle}`}>
                        <LibraryBig className="h-5 w-5" />
                        Dependencias ({codeResult.dependencies.length} bibliotecas)
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="p-0">
                      <div className="grid gap-3">
                        {codeResult.dependencies.map((item: { library: string; description: string }, idx: number) => (
                          <div key={idx} className={`flex flex-col sm:flex-row items-start sm:items-center gap-2 sm:gap-3 p-3 border rounded-lg border-border/50 ${codeColors.hoverBorder}`}>
                            <Badge variant="secondary">{item.library}</Badge>
                            <div className="text-sm text-muted-foreground flex-1"><ReactMarkdown remarkPlugins={[remarkGfm]}>{item.description}</ReactMarkdown></div>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                ) : (
                  <p className="text-sm text-muted-foreground">No se identificaron dependencias específicas.</p>
                )}
              </TabsContent>

              <TabsContent value="issues" className="space-y-4">
                {codeResult?.potential_issues && codeResult.potential_issues.length > 0 ? (
                  <Card className="border-none shadow-none bg-transparent p-0">
                    <CardHeader className="px-0 pt-0 pb-2">
                      <CardTitle className="flex items-center gap-2 text-lg font-semibold text-orange-600 dark:text-orange-400">
                        <AlertTriangle className="h-5 w-5" />
                        Problemas Potenciales ({codeResult.potential_issues.length} problemas)
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="p-0">
                      <div className="space-y-3">
                        {codeResult.potential_issues.map((item: { issue: string; description: string }, idx: number) => (
                          <div key={idx} className="border-l-4 border-orange-500 pl-4 p-3 bg-orange-50 dark:bg-orange-950/20 rounded-r-lg border border-border/50">
                            <h4 className="font-medium text-orange-800 dark:text-orange-200">{item.issue}</h4>
                            <div className="text-sm text-orange-700 dark:text-orange-300"><ReactMarkdown remarkPlugins={[remarkGfm]}>{item.description}</ReactMarkdown></div>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                ) : (
                  <p className="text-sm text-muted-foreground">No se identificaron problemas potenciales.</p>
                )}
              </TabsContent>

              <TabsContent value="recommendations" className="space-y-4">
                {codeResult?.recommendations && codeResult.recommendations.length > 0 ? (
                  <Card className="border-none shadow-none bg-transparent p-0">
                    <CardHeader className="px-0 pt-0 pb-2">
                      <CardTitle className={`flex items-center gap-2 text-lg font-semibold ${codeColors.cardTitle}`}>
                        <Lightbulb className="h-5 w-5" />
                        Recomendaciones ({codeResult.recommendations.length} sugerencias)
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="p-0">
                      <div className="space-y-4">
                        {codeResult.recommendations.map((item: { recommendation: string; rationale: string; application: string; implementation: string }, idx: number) => (
                          <div key={idx} className={`border rounded-lg p-4 space-y-2 border-border/50 ${codeColors.hoverBorder}`}>
                            <h4 className={`font-medium ${codeColors.cardTitle}`}>{item.recommendation}</h4>
                            {item.rationale && (
                              <div className="text-sm text-muted-foreground"><strong>Justificación:</strong> <ReactMarkdown remarkPlugins={[remarkGfm]}>{item.rationale}</ReactMarkdown></div>
                            )}
                            {item.application && (
                              <div className="text-sm text-muted-foreground"><strong>Aplicación:</strong> <ReactMarkdown remarkPlugins={[remarkGfm]}>{item.application}</ReactMarkdown></div>
                            )}
                            {item.implementation && (
                              <div className="text-sm text-muted-foreground"><strong>Implementación:</strong> <ReactMarkdown remarkPlugins={[remarkGfm]}>{item.implementation}</ReactMarkdown></div>
                            )}
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                ) : (
                  <p className="text-sm text-muted-foreground">No se generaron recomendaciones específicas.</p>
                )}
              </TabsContent>
            </Tabs>

            <AnalysisCommonFields analysis={analysis} processedOutput={processedOutput} />
          </>
        );
      case 'note_collection_analysis':
        const collectionNoteResult = (analysis.result || analysis.full_data) as NoteCollectionAnalysisResult;
        const ncColors = getAnalysisColorScheme(analysis.type);

        return (
          <>
            <h3 className="text-xl font-bold mb-4">Análisis de Colección de Notas - KAI Exocerebro</h3>

            {collectionNoteResult?.collection_summary && (
              <Card className={`mb-4 ${ncColors.cardBg}`}>
                <CardHeader className="pb-2">
                  <CardTitle className={`text-lg font-semibold ${ncColors.cardTitle} flex items-center gap-2`}>
                    <ScrollText className="w-5 h-5" />
                    Resumen de la Colección
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="prose prose-sm max-w-none dark:prose-invert text-muted-foreground">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{collectionNoteResult.collection_summary}</ReactMarkdown>
                  </div>
                </CardContent>
              </Card>
            )}

            {collectionNoteResult?.kai_synthesis && (
              <Alert className={`mb-4 bg-gradient-to-r ${ncColors.alertGradient}`}>
                <Sparkles className={`h-5 w-5 ${ncColors.alertIcon}`} />
                <AlertTitle className={`${ncColors.alertTitle} font-semibold mb-2`}>Síntesis de KAI</AlertTitle>
                <AlertDescription className={`${ncColors.alertDesc} italic`}>
                  "{collectionNoteResult.kai_synthesis}"
                </AlertDescription>
              </Alert>
            )}


            {collectionNoteResult?.cross_cutting_themes && collectionNoteResult.cross_cutting_themes.length > 0 && (
              <div className="mb-4">
                <h4 className={`font-semibold text-lg mb-3 flex items-center gap-2 ${ncColors.icon}`}>
                  <Target className="w-5 h-5" />
                  Temas Transversales
                </h4>
                <div className="flex flex-wrap gap-2">
                  {collectionNoteResult.cross_cutting_themes.map((theme: string | { theme: string; description: string }, idx: number) => (
                    <Badge key={idx} variant="secondary" className="bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-100 border-orange-200 dark:border-orange-800">
                      {typeof theme === 'string' ? theme : theme.theme}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {collectionNoteResult?.synthesized_insights && collectionNoteResult.synthesized_insights.length > 0 && (
              <div className="mb-4">
                <h4 className={`font-semibold text-lg mb-3 flex items-center gap-2 ${ncColors.icon}`}>
                  <Lightbulb className="w-5 h-5" />
                  Insights Sintetizados
                </h4>
                <div className="space-y-3">
                  {collectionNoteResult.synthesized_insights.map((insight: any, idx: number) => (
                    <Card key={idx} className="bg-card border-border/50">
                      <CardContent className="p-3">
                        <div className="text-sm">
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {typeof insight === 'string' ? insight : (insight.insight || insight.description || JSON.stringify(insight))}
                          </ReactMarkdown>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </div>
            )}

            {collectionNoteResult?.strategic_recommendations && collectionNoteResult.strategic_recommendations.length > 0 && (
              <div className="mb-4">
                <h4 className={`font-semibold text-lg mb-3 flex items-center gap-2 ${ncColors.icon}`}>
                  <Goal className="w-5 h-5" />
                  Recomendaciones Estratégicas
                </h4>
                <div className="grid gap-3">
                  {collectionNoteResult.strategic_recommendations.map((rec: any, idx: number) => (
                    <div key={idx} className={`flex items-start gap-3 p-3 rounded-lg bg-card border border-border/50 ${ncColors.hoverBorder} transition-colors`}>
                      <CircleCheck className="w-5 h-5 text-green-500 mt-0.5 shrink-0" />
                      <span className="text-sm">
                        {typeof rec === 'string' ? rec : (
                          <span>
                            <strong>{rec.recommendation}</strong>
                            {rec.description && <span className="block text-muted-foreground mt-1">{rec.description}</span>}
                          </span>
                        )}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {collectionNoteResult?.knowledge_gaps && collectionNoteResult.knowledge_gaps.length > 0 && (
              <div className="mb-4">
                <h4 className={`font-semibold text-lg mb-3 flex items-center gap-2 ${ncColors.icon}`}>
                  <AlertTriangle className="w-5 h-5" />
                  Brechas de Conocimiento
                </h4>
                <ul className="space-y-2 list-disc list-inside text-sm text-muted-foreground">
                  {collectionNoteResult.knowledge_gaps.map((gap: any, idx: number) => (
                    <li key={idx}>
                      {typeof gap === 'string' ? gap : (
                        <span>
                          <strong>{gap.gap}</strong>
                          {gap.description && <span className="block text-muted-foreground ml-4 mt-1">{gap.description}</span>}
                        </span>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <AnalysisCommonFields analysis={analysis} processedOutput={processedOutput} />
          </>
        );

      case 'note_analysis':
        const noteResult = (analysis.result || analysis.full_data) as NoteAnalysisResult;
        const noteColors = getAnalysisColorScheme(analysis.type);

        return (
          <>
            <h3 className="text-xl font-bold mb-4">Análisis de Nota - KAI Exocerebro</h3>

            {noteResult?.executive_summary && (
              <Card className={`mb-4 ${noteColors.cardBg}`}>
                <CardHeader className="pb-2">
                  <CardTitle className={`text-lg font-semibold ${noteColors.cardTitle} flex items-center gap-2`}>
                    <ScrollText className="w-5 h-5" />
                    Resumen Ejecutivo
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="prose prose-sm max-w-none dark:prose-invert text-muted-foreground">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{noteResult.executive_summary}</ReactMarkdown>
                  </div>
                </CardContent>
              </Card>
            )}

            {noteResult?.key_themes && noteResult.key_themes.length > 0 && (
              <div className="mb-4">
                <h4 className={`font-semibold text-lg mb-3 flex items-center gap-2 ${noteColors.icon}`}>
                  <Target className="w-5 h-5" />
                  Temas Clave
                </h4>
                <ul className="space-y-2 list-disc list-inside text-sm text-muted-foreground">
                  {noteResult.key_themes.map((point: string, idx: number) => (
                    <li key={idx}><ReactMarkdown remarkPlugins={[remarkGfm]}>{point}</ReactMarkdown></li>
                  ))}
                </ul>
              </div>
            )}

            {noteResult?.action_suggestions && noteResult.action_suggestions.length > 0 && (
              <div className="mb-4">
                <h4 className={`font-semibold text-lg mb-3 flex items-center gap-2 ${noteColors.icon}`}>
                  <Goal className="w-5 h-5" />
                  Acciones Sugeridas
                </h4>
                <div className="grid gap-3">
                  {noteResult.action_suggestions.map((item: string, idx: number) => (
                    <div key={idx} className={`flex items-start gap-3 p-3 rounded-lg bg-card border border-border/50 ${noteColors.hoverBorder} transition-colors`}>
                      <CircleCheck className="w-5 h-5 text-green-500 mt-0.5 shrink-0" />
                      <span className="text-sm"><ReactMarkdown remarkPlugins={[remarkGfm]}>{item}</ReactMarkdown></span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {noteResult?.potential_implications && noteResult.potential_implications.length > 0 && (
              <div className="mb-4">
                <h4 className={`font-semibold text-lg mb-3 flex items-center gap-2 ${noteColors.icon}`}>
                  <AlertTriangle className="w-5 h-5" />
                  Implicaciones Potenciales
                </h4>
                <ul className="space-y-2 list-disc list-inside text-sm text-muted-foreground">
                  {noteResult.potential_implications.map((implication: string, idx: number) => (
                    <li key={idx}><ReactMarkdown remarkPlugins={[remarkGfm]}>{implication}</ReactMarkdown></li>
                  ))}
                </ul>
              </div>
            )}

            {noteResult?.related_concepts && noteResult.related_concepts.length > 0 && (
              <div className="mb-4">
                <h4 className={`font-semibold text-lg mb-3 flex items-center gap-2 ${noteColors.icon}`}>
                  <Lightbulb className="w-5 h-5" />
                  Conceptos Relacionados
                </h4>
                <ul className="space-y-2 list-disc list-inside text-sm text-muted-foreground">
                  {noteResult.related_concepts.map((concept: string, idx: number) => (
                    <li key={idx}><ReactMarkdown remarkPlugins={[remarkGfm]}>{concept}</ReactMarkdown></li>
                  ))}
                </ul>
              </div>
            )}

            {noteResult?.kai_insight && (
              <Alert className={`mb-4 bg-gradient-to-r ${noteColors.alertGradient}`}>
                <Sparkles className={`h-5 w-5 ${noteColors.alertIcon}`} />
                <AlertTitle className={`${noteColors.alertTitle} font-semibold mb-2`}>Insight de KAI</AlertTitle>
                <AlertDescription className={`${noteColors.alertDesc} italic`}>
                  "{noteResult.kai_insight}"
                </AlertDescription>
              </Alert>
            )}

            <AnalysisCommonFields analysis={analysis} processedOutput={processedOutput} />
          </>
        );

      case 'document':
      case 'document_summary':
        const documentResult = (analysis.result || analysis.full_data) as SingleTextAnalysis;
        const docColors = getAnalysisColorScheme(analysis.type);
        return (
          <>
            <h3 className="text-xl font-bold mb-4">Análisis de Documento - KAI Exocerebro</h3>

            {documentResult?.executive_summary && (
              <Card className={`mb-4 ${docColors.cardBg}`}>
                <CardHeader className="pb-2">
                  <CardTitle className={`text-lg font-semibold ${docColors.cardTitle} flex items-center gap-2`}>
                    <ScrollText className="w-5 h-5" />
                    Resumen Ejecutivo
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="prose prose-sm max-w-none dark:prose-invert text-muted-foreground">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{documentResult.executive_summary}</ReactMarkdown>
                  </div>
                </CardContent>
              </Card>
            )}

            {documentResult?.kai_synthesis && (
              <Alert className={`mb-4 bg-gradient-to-r ${docColors.alertGradient}`}>
                <Sparkles className={`h-5 w-5 ${docColors.alertIcon}`} />
                <AlertTitle className={`${docColors.alertTitle} font-semibold mb-2`}>Síntesis de KAI</AlertTitle>
                <AlertDescription className={`${docColors.alertDesc} italic`}>
                  "{documentResult.kai_synthesis}"
                </AlertDescription>
              </Alert>
            )}

            {documentResult?.general_analysis && (
              <Card className="mb-4 bg-muted/50 border-border/50">
                <CardHeader className="pb-2">
                  <CardTitle className="text-lg font-semibold flex items-center gap-2">
                    <FileText className="w-5 h-5" />
                    Análisis General
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="prose prose-sm max-w-none dark:prose-invert text-muted-foreground">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{documentResult.general_analysis}</ReactMarkdown>
                  </div>
                </CardContent>
              </Card>
            )}

            {documentResult?.authorial_tone && (
              <div className="mb-4 flex items-center gap-2 text-sm text-muted-foreground">
                <Volume2 className="w-4 h-4" />
                <strong>Tono Autorial:</strong> {documentResult.authorial_tone}
              </div>
            )}

            {documentResult?.discipline && documentResult.discipline.length > 0 && (
              <div className="mb-4">
                <h4 className="font-semibold text-lg mb-2 flex items-center gap-2">
                  <LibraryBig className="w-5 h-5 text-blue-600" />
                  Disciplina
                </h4>
                <div className="flex flex-wrap gap-2">
                  {documentResult.discipline.map((disc: string, idx: number) => (
                    <Badge key={idx} variant="outline" className="text-sm">
                      {disc}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {documentResult?.key_themes && documentResult.key_themes.length > 0 && (
              <div className="mb-4">
                <h4 className={`font-semibold text-lg mb-2 flex items-center gap-2 ${docColors.icon}`}>
                  <Target className="w-5 h-5" />
                  Temas Clave
                </h4>
                <div className="flex flex-wrap gap-2">
                  {documentResult.key_themes.map((theme: ThemeReference, idx: number) => (
                    <Badge
                      key={idx}
                      variant="secondary"
                      className={`cursor-pointer text-sm transition-colors border ${getAnalysisTypeBadgeColor(analysis.type)}`}
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
                <h4 className={`font-semibold text-lg mb-2 flex items-center gap-2 ${docColors.icon}`}>
                  <Lightbulb className="w-5 h-5" />
                  Conceptos Centrales
                </h4>
                <div className="flex flex-wrap gap-2">
                  {documentResult.central_concepts.map((concept: string, idx: number) => (
                    <Button
                      key={idx}
                      variant="outline"
                      className={`h-auto py-2 px-3 text-sm justify-start font-normal transition-all shadow-sm hover:bg-accent hover:text-accent-foreground`}
                      onClick={() => handleConceptClick(concept)}
                    >
                      <Lightbulb className={`w-4 h-4 mr-2 shrink-0 ${docColors.icon}`} />
                      <span>{cleanAsterisks(concept.split(':')[0])}</span>
                    </Button>
                  ))}
                </div>
              </div>
            )}

            {documentResult?.knowledge_gaps && documentResult.knowledge_gaps.length > 0 && (
              <div className="mb-4">
                <h4 className={`font-semibold text-lg mb-2 flex items-center gap-2 ${docColors.icon}`}>
                  <AlertTriangle className="w-5 h-5" />
                  Brechas de Conocimiento
                </h4>
                <Card
                  className={`cursor-pointer hover:shadow-lg hover:scale-[1.02] transition-all duration-300 border border-border/50 group ${docColors.hoverBorder}`}
                  onClick={() => setIsKnowledgeGapsDialogOpen(true)}
                >
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <AlertTriangle className={`h-5 w-5 ${docColors.icon}`} />
                        <span className="font-medium text-sm">
                          {documentResult.knowledge_gaps.length} brecha{documentResult.knowledge_gaps.length !== 1 ? 's' : ''} de conocimiento
                        </span>
                      </div>
                      <div className="opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                        <Expand className="h-4 w-4 text-muted-foreground" />
                      </div>
                    </div>
                    <div className="text-sm text-muted-foreground line-clamp-2 leading-relaxed">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{documentResult.knowledge_gaps[0].gap}</ReactMarkdown>
                    </div>
                    <div className="mt-3 text-xs text-primary/60 opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex items-center gap-1">
                      <Expand className="h-3 w-3" />
                      Haz clic para ver todas las brechas
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}

            {documentResult?.exploration_questions && documentResult.exploration_questions.length > 0 && (
              <div className="mb-4">
                <h4 className={`font-semibold text-lg mb-2 flex items-center gap-2 ${docColors.icon}`}>
                  <HelpCircle className="w-5 h-5" />
                  Preguntas para Explorar
                </h4>
                <Card
                  className={`cursor-pointer hover:shadow-lg hover:scale-[1.02] transition-all duration-300 border border-border/50 group ${docColors.hoverBorder}`}
                  onClick={() => setIsQuestionsDialogOpen(true)}
                >
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <HelpCircle className={`h-5 w-5 ${docColors.icon}`} />
                        <span className="font-medium text-sm">
                          {documentResult.exploration_questions.length} pregunta{documentResult.exploration_questions.length !== 1 ? 's' : ''} para explorar
                        </span>
                      </div>
                      <div className="opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                        <Expand className="h-4 w-4 text-muted-foreground" />
                      </div>
                    </div>
                    <div className="text-sm text-muted-foreground line-clamp-2 leading-relaxed">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{documentResult.exploration_questions[0]}</ReactMarkdown>
                    </div>
                    <div className="mt-3 text-xs text-primary/60 opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex items-center gap-1">
                      <Expand className="h-3 w-3" />
                      Haz clic para ver todas las preguntas
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}

            {documentResult?.problematic_areas && documentResult.problematic_areas.length > 0 && (
              <div className="mb-4">
                <h4 className="font-semibold text-lg mb-2 flex items-center gap-2 text-red-600">
                  <AlertTriangle className="w-5 h-5" />
                  Áreas Problemáticas
                </h4>
                <ul className="list-disc pl-5 text-sm text-muted-foreground space-y-1">
                  {documentResult.problematic_areas.map((area: string, idx: number) => (
                    <li key={idx}><div className="text-sm text-muted-foreground"><ReactMarkdown remarkPlugins={[remarkGfm]}>{area}</ReactMarkdown></div></li>
                  ))}
                </ul>
              </div>
            )}

            {documentResult?.final_reflections && documentResult.final_reflections.length > 0 && (
              <div className="mb-4">
                <h4 className={`font-semibold text-lg mb-2 flex items-center gap-2 ${docColors.icon}`}>
                  <Sparkles className="w-5 h-5" />
                  Reflexiones Finales
                </h4>
                <ul className="list-disc pl-5 text-sm text-muted-foreground space-y-1">
                  {documentResult.final_reflections.map((reflection: string, idx: number) => (
                    <li key={idx}><div className="text-sm text-muted-foreground"><ReactMarkdown remarkPlugins={[remarkGfm]}>{reflection}</ReactMarkdown></div></li>
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
                <div className="text-sm text-muted-foreground whitespace-pre-wrap"><ReactMarkdown remarkPlugins={[remarkGfm]}>{typeof analysis.summary === 'string' ? analysis.summary : JSON.stringify(analysis.summary || '')}</ReactMarkdown></div>
              </div>
            )}
            {analysis.rawContent && !analysis.summary && ( // Mostrar rawContent si no hay summary
              <div className="mb-4 p-3 bg-muted rounded-md border border-border/50">
                <h4 className="font-semibold text-lg mb-2">Contenido:</h4>
                <div className="text-sm text-muted-foreground whitespace-pre-wrap"><ReactMarkdown remarkPlugins={[remarkGfm]}>{typeof analysis.rawContent === 'string' ? analysis.rawContent : JSON.stringify(analysis.rawContent || '')}</ReactMarkdown></div>
              </div>
            )}
            {analysis.result && typeof analysis.result === 'string' && ( // Para topic_analysis que devuelve un string en result
              <div className="mb-4 p-3 bg-muted rounded-md border border-border/50">
                <h4 className="font-semibold text-lg mb-2">Resultado:</h4>
                <div className="text-sm text-muted-foreground whitespace-pre-wrap"><ReactMarkdown remarkPlugins={[remarkGfm]}>{typeof analysis.result === 'string' ? analysis.result : JSON.stringify(analysis.result || '')}</ReactMarkdown></div>
              </div>
            )}

            <AnalysisCommonFields analysis={analysis} processedOutput={processedOutput} />

            {analysis.type === 'question' && analysis.questions && analysis.questions.length > 0 && (
              <div className="mt-6 p-4 border rounded-md bg-accent/20">
                <h4 className="font-bold mb-2 flex items-center gap-2"><HelpCircle className="h-5 w-5" />Preguntas Relacionadas</h4>
                <ul className="list-disc pl-5 text-sm space-y-1">
                  {analysis.questions.map((q: Question | string, i: number) => (
                    <li key={i}>{typeof q === 'string' ? q : q.issue || q.description || `Pregunta ${i + 1}`}</li>
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
                    <div className="text-sm text-muted-foreground"><ReactMarkdown remarkPlugins={[remarkGfm]}>{typeof step.description === 'string' ? step.description : JSON.stringify(step.description)}</ReactMarkdown></div>
                  </li>
                ))}
              </ol>
            ) : (
              <div className="prose dark:prose-invert max-w-none"><ReactMarkdown remarkPlugins={[remarkGfm]}>{typeof processedOutput.content === 'string' ? processedOutput.content : JSON.stringify(processedOutput.content || '')}</ReactMarkdown></div>
            )}
            <AnalysisCommonFields analysis={analysis} processedOutput={processedOutput} />
          </>
        );
      default:
        return (
          <>
            <div className="prose dark:prose-invert max-w-none"><ReactMarkdown remarkPlugins={[remarkGfm]}>{typeof processedOutput.content === 'string' ? processedOutput.content : JSON.stringify(processedOutput.content || '')}</ReactMarkdown></div>
            <AnalysisCommonFields analysis={analysis} processedOutput={processedOutput} />
          </>
        );
    }
  }, [analysis, handleThemeClick, handleConceptClick, handlePlayPause, isCurrentlyLoading, isCurrentlyPlaying]);

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
                            <li key={i}>{typeof q === 'string' ? q : q.issue || q.description || `Pregunta ${i + 1}`}</li>
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