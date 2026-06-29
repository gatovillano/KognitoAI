import { ShareAnalysisDialog } from '@/components/ShareAnalysisDialog';
import { MessageSquare } from 'lucide-react';
import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Analysis, AnalysisType, Insight, Question, CollectionAnalysis, DocumentAnalysisResult as SingleTextAnalysis, DocumentSummaryResult, CollectionConnection, ThemeReference, ThemeQuote, CodeAnalysisResultFrontend, NoteCollectionAnalysisResult, NoteAnalysisResult, DeepResearchAnalysisResult, ProactiveInsightResult, ComprehensiveWebAnalysisResult, ScopedRagAnalysisResult } from '@/lib/models';
import { Lightbulb, Workflow, ScrollText, Megaphone, Target, BarChart3, TrendingUp, FlaskConical, Puzzle, Goal, LibraryBig, Bot, CircleCheck, Info, Sparkles, XCircle, FileWarning, HelpCircle, Brain, Network, Volume2, Loader2, Pause, Calendar, AlertTriangle, Expand, Atom, FileText, Settings, GitBranch, Activity, Trash2, Zap, ExternalLink, Download } from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { QuestionSliderDialog } from '@/components/QuestionSliderDialog';
import { ContextualChat } from '@/components/ContextualChat';
import { useTextToSpeech } from '@/hooks/useTextToSpeech';
import apiClient from '@/lib/api';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';

// Import new analysis components
import SemanticAnalysis from './SemanticAnalysis';
import CollectionAnalysisComponent from './CollectionAnalysis';
import DocumentAnalysisComponent from './DocumentAnalysis';
import DocumentSummaryComponent from './DocumentSummary';
import CodeAnalysisComponent from './CodeAnalysis';
import NoteCollectionAnalysisComponent from './NoteCollectionAnalysis';
import NoteAnalysisComponent from './NoteAnalysis';
import DeepResearchAnalysis from './DeepResearchAnalysis';
import ProactiveInsightAnalysis from './ProactiveInsightAnalysis';
import ComprehensiveWebAnalysis from './ComprehensiveWebAnalysis';
import ScopedRagAnalysis from './ScopedRagAnalysis';
import NeuralInsightAnalysis from './NeuralInsightAnalysis';
import { DraftDetailDialog } from './draft-detail-dialog'; // NUEVO


const cleanAsterisks = (text: string) => {
  return text.replace(/^\*+|\*+$/g, '');
};

export interface GapSource {
  id: number | string;
  url: string;
  title?: string;
  snippet?: string;
  relevance?: number;
  type?: 'web' | 'document' | 'memory' | 'code' | 'database' | 'note' | 'graph';
}

export const GapSourceButton: React.FC<{ source: GapSource; citationNumber: number }> = ({ source, citationNumber }) => {
  const getIcon = () => {
    switch (source.type) {
      case 'web':
        return <ExternalLink className="h-3 w-3 mr-1" />;
      default:
        return <ExternalLink className="h-3 w-3 mr-1" />;
    }
  };

  return (
    <Dialog>
      <DialogTrigger asChild>
        <button className="inline-flex items-center text-xl bg-fuchsia-100 text-fuchsia-800 font-bold rounded-full px-2 mx-0.5 focus:outline-none focus:ring-2 focus:ring-fuchsia-500 leading-normal flex-shrink-0 hover:bg-fuchsia-200 transition-colors">
          {getIcon()}
          {citationNumber}
        </button>
      </DialogTrigger>
      <DialogContent className="w-80 text-sm">
        <div className="flex items-center gap-2 mb-2">
          {getIcon()}
          <div className="font-bold whitespace-normal break-words">{source.title || source.url}</div>
        </div>
        {source.type && (
          <div className="text-xs text-muted-foreground mb-2 capitalize">
            Tipo: {source.type}
          </div>
        )}
        {source.snippet && (
          <p className="text-muted-foreground">
            {source.snippet}
          </p>
        )}
        {source.relevance && (
          <div className="text-xs text-primary/80 mt-2">
            Relevancia: {source.relevance}/10
          </div>
        )}
        {source.url && (
          <div className="text-xs text-muted-foreground mt-2 break-all">
            Fuente: <a href={source.url} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">{source.url}</a>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
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
    case 'code_security':
    case 'code_performance':
    case 'code_refactoring':
    case 'code_documentation':
    case 'code_structure':
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
    case 'proactive_insight':
    case 'neural_insight':
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
    case 'comprehensive_web_analysis':
      return {
        color: 'sky',
        cardBg: 'bg-sky-50/50 border-sky-100 dark:bg-sky-900/10 dark:border-sky-900/50',
        cardTitle: 'text-sky-900 dark:text-sky-100',
        icon: 'text-sky-600',
        alertGradient: 'from-sky-50 to-cyan-50 border-sky-200 dark:from-sky-950/30 dark:to-cyan-950/30 dark:border-sky-800',
        alertIcon: 'text-sky-600 dark:text-sky-400',
        alertTitle: 'text-sky-800 dark:text-sky-300',
        alertDesc: 'text-sky-900/90 dark:text-sky-200/90',
        hoverBorder: 'hover:border-sky-200'
      };
    case 'scoped_rag_analysis':
      return {
        color: 'rose',
        cardBg: 'bg-rose-50/50 border-rose-100 dark:bg-rose-900/10 dark:border-rose-900/50',
        cardTitle: 'text-rose-900 dark:text-rose-100',
        icon: 'text-rose-600',
        alertGradient: 'from-rose-50 to-pink-50 border-rose-200 dark:from-rose-950/30 dark:to-pink-950/30 dark:border-rose-800',
        alertIcon: 'text-rose-600 dark:text-rose-400',
        alertTitle: 'text-rose-800 dark:text-rose-300',
        alertDesc: 'text-rose-900/90 dark:text-rose-200/90',
        hoverBorder: 'hover:border-rose-200'
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
    case 'repository_update':
      return {
        color: 'teal',
        cardBg: 'bg-teal-50/50 border-teal-100 dark:bg-teal-900/10 dark:border-teal-900/50',
        cardTitle: 'text-teal-900 dark:text-teal-100',
        icon: 'text-teal-600',
        alertGradient: 'from-teal-50 to-cyan-50 border-teal-200 dark:from-teal-950/30 dark:to-cyan-950/30 dark:border-teal-800',
        alertIcon: 'text-teal-600 dark:text-teal-400',
        alertTitle: 'text-teal-800 dark:text-teal-300',
        alertDesc: 'text-teal-900/90 dark:text-teal-200/90',
        hoverBorder: 'hover:border-teal-200'
      };
    case 'gap_development':
      return {
        color: 'fuchsia',
        cardBg: 'bg-fuchsia-50/50 border-fuchsia-100 dark:bg-fuchsia-900/10 dark:border-fuchsia-900/50',
        cardTitle: 'text-fuchsia-900 dark:text-fuchsia-100',
        icon: 'text-fuchsia-600',
        alertGradient: 'from-fuchsia-50 to-pink-50 border-fuchsia-200 dark:from-fuchsia-950/30 dark:to-pink-950/30 dark:border-fuchsia-800',
        alertIcon: 'text-fuchsia-600 dark:text-fuchsia-400',
        alertTitle: 'text-fuchsia-800 dark:text-fuchsia-300',
        alertDesc: 'text-fuchsia-900/90 dark:text-fuchsia-200/90',
        hoverBorder: 'hover:border-fuchsia-200'
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
    case 'code_security':
    case 'code_performance':
    case 'code_refactoring':
    case 'code_documentation':
    case 'code_structure':
      return 'bg-cyan-100 text-cyan-800 dark:bg-cyan-900 dark:text-cyan-100 border-cyan-200 dark:border-cyan-800';
    case 'insight':
    case 'proactive_insight_manual':
    case 'proactive_insight':
      return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-100 border-yellow-200 dark:border-yellow-800';
    case 'comprehensive_web_analysis':
      return 'bg-sky-100 text-sky-800 dark:bg-sky-900 dark:text-sky-100 border-sky-200 dark:border-sky-800';
    case 'scoped_rag_analysis':
      return 'bg-rose-100 text-rose-800 dark:bg-rose-900 dark:text-rose-100 border-rose-200 dark:border-rose-800';
    case 'note_analysis':
      return 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-100 border-amber-200 dark:border-amber-800';
    case 'note_collection_analysis':
      return 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-100 border-orange-200 dark:border-orange-800';
    case 'knowledge_graph_analysis':
      return 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-100 border-purple-200 dark:border-purple-800';
    case 'custom_analysis':
      return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-100 border-red-200 dark:border-red-800';
    case 'repository_update':
      return 'bg-teal-100 text-teal-800 dark:bg-teal-900 dark:text-teal-100 border-teal-200 dark:border-teal-800';
    case 'gap_development':
      return 'bg-fuchsia-100 text-fuchsia-800 dark:bg-fuchsia-900 dark:text-fuchsia-100 border-fuchsia-200 dark:border-fuchsia-800';
    default:
      return 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-100 border-gray-200 dark:border-gray-700';
  }
};

// import { processContentWithCitations } // Importa la función de procesamiento

interface AnalysisDetailDialogProps {
  analysis: Analysis | null;
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  onAnalysisDeleted?: (analysisId: string) => void;
  // onGenerateQuestions?: (analysisId: string) => void; // Opcional
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
    case 'code':
    case 'code_security':
    case 'code_performance':
    case 'code_refactoring':
    case 'code_documentation':
    case 'code_structure':
      return <Brain className="text-cyan-600" />;
    case 'topic_analysis': return <Network className="text-indigo-600" />;
    case 'proactive_insight_manual': return <Atom className="text-pink-500" />;
    case 'knowledge_graph_analysis': return <Network className="text-purple-500" />;
    case 'custom_analysis': return <FlaskConical className="text-red-500" />;
    case 'repository_update': return <GitBranch className="text-teal-500" />;
    case 'gap_development': return <Zap className="text-fuchsia-500" />;
    case 'document': return <FileText className="text-blue-500" />;
    case 'collection': return <LibraryBig className="text-green-500" />;
    case 'semantic': return <Network className="text-indigo-500" />;
    case 'semantic_summary': return <ScrollText className="text-indigo-500" />;
    case 'note_analysis': return <FileText className="text-amber-500" />;
    case 'note_collection_analysis': return <LibraryBig className="text-orange-500" />;
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
    case 'code_security': return 'Análisis de Seguridad';
    case 'code_performance': return 'Análisis de Rendimiento';
    case 'code_refactoring': return 'Refactorización';
    case 'code_documentation': return 'Documentación';
    case 'code_structure': return 'Arquitectura';
    case 'topic_analysis': return 'Análisis por Tema';
    case 'proactive_insight_manual': return 'Insight Proactivo Manual';
    case 'proactive_insight': return 'Insight Proactivo';
    case 'comprehensive_web_analysis': return 'Análisis Web Completo';
    case 'scoped_rag_analysis': return 'Análisis RAG Enfocado';
    case 'knowledge_graph_analysis': return 'Análisis de Grafo de Conocimiento';
    case 'custom_analysis': return 'Análisis Personalizado';
    case 'repository_update': return 'Actualización de Repositorio';
    case 'document': return 'Análisis de Documento';
    case 'collection': return 'Análisis de Colección';
    case 'semantic': return 'Análisis Semántico';
    case 'semantic_summary': return 'Resumen Semántico';
    case 'note_analysis': return 'Análisis de Nota';
    case 'note_collection_analysis': return 'Análisis de Colección de Notas';
    case 'gap_development': return 'Investigación Profunda';
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
      <DialogContent className="max-w-xl rounded-2xl bg-card/95 backdrop-blur-xl border shadow-2xl">
        <DialogHeader>
          <div className="w-12 h-12 rounded-full bg-indigo-100 dark:bg-indigo-900/30 flex items-center justify-center mb-4">
            <ScrollText className="w-6 h-6 text-indigo-600 dark:text-indigo-400" />
          </div>
          <DialogTitle className="text-2xl font-bold">Citas para: {theme.theme}</DialogTitle>
          <DialogDescription className="text-muted-foreground">
            {`Fragmentos de texto relacionados con el tema "${theme.theme}" encontrados en los documentos.`}
          </DialogDescription>
        </DialogHeader>
        <div className="py-4 flex-1 overflow-y-auto max-h-[60vh] pr-2 custom-scrollbar">
          {theme.related_quotes && theme.related_quotes.length > 0 ? (
            <div className="space-y-4">
              {theme.related_quotes.map((quote: ThemeQuote, qIdx: number) => (
                <div key={qIdx} className="p-4 rounded-xl bg-muted/30 border border-muted hover:bg-muted/50 transition-colors">
                  <div className="italic text-sm leading-relaxed mb-3">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{`"${typeof quote.quote === 'string' ? quote.quote : JSON.stringify(quote.quote)}"`}</ReactMarkdown>
                  </div>
                  <div className="flex items-center gap-2 text-[10px] font-bold text-muted-foreground uppercase tracking-wider">
                    <div className="w-1 h-1 rounded-full bg-indigo-500" />
                    {quote.document_title}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-10 text-muted-foreground italic">
              No se encontraron citas para este tema.
            </div>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} className="rounded-xl">Cerrar</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};


interface SimpleListDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  items: string[];
  icon: React.ReactNode;
  colorClass: string;
}

const SimpleListDialog: React.FC<SimpleListDialogProps> = ({ isOpen, onOpenChange, title, description, items, icon, colorClass }) => {
  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl rounded-2xl bg-card/95 backdrop-blur-xl border shadow-2xl">
        <DialogHeader>
          <div className={cn("w-12 h-12 rounded-full flex items-center justify-center mb-4", colorClass)}>
            {icon}
          </div>
          <DialogTitle className="text-2xl font-bold">{title}</DialogTitle>
          <DialogDescription className="text-muted-foreground">
            {description}
          </DialogDescription>
        </DialogHeader>
        <div className="py-4 flex-1 overflow-y-auto max-h-[60vh] pr-2 custom-scrollbar">
          <div className="space-y-3">
            {items.map((item, index) => (
              <div key={index} className="p-4 rounded-xl bg-muted/30 border border-muted hover:bg-muted/50 transition-colors flex gap-3">
                <div className="mt-1 flex-shrink-0 w-5 h-5 rounded-full bg-primary/10 text-primary flex items-center justify-center text-[10px] font-bold">
                  {index + 1}
                </div>
                <p className="text-sm leading-relaxed">{item}</p>
              </div>
            ))}
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} className="rounded-xl">Cerrar</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};


interface SectionTTSButtonProps {
  text: string;
  play: (text: string) => void;
  isLoading: boolean;
  isPlaying: boolean;
  activeText: string | null;
}

export const SectionTTSButton: React.FC<SectionTTSButtonProps> = ({
  text,
  play,
  isLoading,
  isPlaying,
  activeText
}) => {
  const isThisPlaying = isPlaying && activeText === text;

  return (
    <Button
      variant="ghost"
      size="sm"
      className={cn(
        "h-8 w-8 p-0 rounded-full transition-all duration-300",
        isThisPlaying ? "text-primary bg-primary/10" : "text-muted-foreground hover:text-primary hover:bg-primary/10"
      )}
      onClick={(e) => {
        e.stopPropagation();
        play(text);
      }}
      disabled={isLoading}
      title={isThisPlaying ? "Pausar lectura" : "Escuchar esta sección"}
    >
      {isLoading && activeText === text ? (
        <Loader2 className="h-4 w-4 animate-spin" />
      ) : isThisPlaying ? (
        <Pause className="h-4 w-4" />
      ) : (
        <Volume2 className="h-4 w-4" />
      )}
    </Button>
  );
};


export const AnalysisDetailDialog: React.FC<AnalysisDetailDialogProps> = ({ analysis: initialAnalysis, isOpen, onOpenChange, onAnalysisDeleted }) => {
  const [currentAnalysis, setCurrentAnalysis] = useState<Analysis | null>(initialAnalysis);
  const [isQuestionsDialogOpen, setIsQuestionsDialogOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('summary');
  const [selectedThemeForQuotes, setSelectedThemeForQuotes] = useState<ThemeReference | null>(null);
  const [isThemeQuotesDialogOpen, setIsThemeQuotesDialogOpen] = useState(false);
  const [isKnowledgeGapsDialogOpen, setIsKnowledgeGapsDialogOpen] = useState(false);
  const [selectedConcept, setSelectedConcept] = useState<string | null>(null);
  const [isConceptDialogOpen, setIsConceptDialogOpen] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [sliderQuestions, setSliderQuestions] = useState<string[]>([]);
  const [sliderTitle, setSliderTitle] = useState('');

  // Estado para el diálogo de compartir análisis
  const [isShareDialogOpen, setIsShareDialogOpen] = useState(false);

  // Estados para el diálogo simple de notas
  const [isSimpleListDialogOpen, setIsSimpleListDialogOpen] = useState(false);
  const [simpleListTitle, setSimpleListTitle] = useState("");
  const [simpleListDescription, setSimpleListDescription] = useState("");
  const [simpleListItems, setSimpleListItems] = useState<string[]>([]);
  const [simpleListIcon, setSimpleListIcon] = useState<React.ReactNode>(null);
  const [simpleListColor, setSimpleListColor] = useState("");

  const { play, stop, isLoading, isPlaying, activeText } = useTextToSpeech();
  const [isPdfExporting, setIsPdfExporting] = useState(false);

  const exportToPdf = async () => {
    if (!currentAnalysis) return;
    setIsPdfExporting(true);
    try {
      const token = typeof window !== 'undefined' ? localStorage.getItem('token') : '';

      // Map generic analysis data to the expected format for the Deep Research PDF endpoint
      let content = currentAnalysis.summary || "";
      let recommendations: string[] = [];
      let sources: any[] = [];

      // Helper to extract fields from a data object
      const extractFromObject = (obj: any) => {
        if (!obj) return;
        if (obj.final_report) content = obj.final_report;
        else if (obj.executive_summary && !content) content = obj.executive_summary;

        if (obj.recommendations && Array.isArray(obj.recommendations) && obj.recommendations.length > 0) {
          recommendations = obj.recommendations;
        }
        if (obj.sources && Array.isArray(obj.sources) && obj.sources.length > 0) {
          sources = obj.sources;
        }
      };

      // 1. Try result
      if (currentAnalysis.result) {
        extractFromObject(currentAnalysis.result);
        if ((currentAnalysis.result as any).report) {
          extractFromObject((currentAnalysis.result as any).report);
        }
      }

      // 2. Try full_data (often contains the complete structure for gap_development/deep_research)
      if (currentAnalysis.full_data) {
        let fd = currentAnalysis.full_data;
        if (typeof fd === 'string') {
          try { fd = JSON.parse(fd); } catch (e) { console.error("Error parsing full_data", e); }
        }

        if (typeof fd === 'object') {
          extractFromObject(fd);
          if (fd.report) {
            extractFromObject(fd.report);
          }
        }
      }

      if (!content) {
        toast.error("No se encontró contenido detallado para exportar.");
        setIsPdfExporting(false);
        return;
      }

      const response = await apiClient.post('/api/deep_research/export_pdf', {
        title: currentAnalysis.title || "Informe de Análisis",
        final_report: content,
        sources: sources,
        recommendations: recommendations
      });

      const data = response.data;
      if (data.url) {
        window.open(data.url, '_blank');
      } else {
        toast.error("No se pudo generar el PDF");
      }
    } catch (error) {
      console.error("Error exporting PDF:", error);
      toast.error("Error al exportar PDF");
    } finally {
      setIsPdfExporting(false);
    }
  };


  const getAnalysisTextForSpeech = useCallback(() => {
    if (!currentAnalysis) return '';

    const data = currentAnalysis.full_data || currentAnalysis.result;
    if (!data) return currentAnalysis.summary || '';

    // Intentar extraer el resumen más relevante según el tipo
    if (typeof data === 'string') return data;

    return data.executive_summary ||
      data.collection_summary ||
      data.semantic_summary ||
      data.summary ||
      currentAnalysis.summary ||
      '';
  }, [currentAnalysis]);

  const handlePlayPauseMainSummary = () => {
    const text = getAnalysisTextForSpeech();
    if (!text) return;

    if (isPlaying && activeText === text) {
      stop();
    } else {
      play(text);
    }
  };

  const isMainSummaryPlaying = isPlaying && activeText === getAnalysisTextForSpeech();
  const isMainSummaryLoading = isLoading && activeText === getAnalysisTextForSpeech();

  useEffect(() => {
    setCurrentAnalysis(initialAnalysis);
  }, [initialAnalysis]);

  useEffect(() => {
    if (isOpen && currentAnalysis?.status === 'in_progress') {
      const intervalId = setInterval(async () => {
        try {
          const response = await apiClient.get(`/api/get-analysis/${currentAnalysis.id}`);
          const updatedAnalysis = response.data;
          setCurrentAnalysis(updatedAnalysis);

          if (updatedAnalysis.status !== 'in_progress') {
            clearInterval(intervalId);
            toast.success(`Análisis "${updatedAnalysis.title}" completado.`);
          }
        } catch (error) {
          console.error('Error fetching analysis update:', error);
          // Optionally stop polling on error
          // clearInterval(intervalId);
        }
      }, 5000); // Poll every 5 seconds

      return () => clearInterval(intervalId);
    }
  }, [isOpen, currentAnalysis]);

  const handleThemeClick = useCallback((theme: ThemeReference) => {
    setSelectedThemeForQuotes(theme);
    setIsThemeQuotesDialogOpen(true);
  }, []);

  const handleConceptClick = useCallback((concept: string) => {
    setSelectedConcept(concept);
    setIsConceptDialogOpen(true);
  }, []);

  const openGapsSlider = useCallback((gaps: any[], title: string) => {
    if (!gaps || gaps.length === 0) return;
    const formattedGaps = gaps.map(gap => {
      if (typeof gap === 'string') return gap;
      // Manejar diferentes estructuras posibles del backend
      const gapTitle = gap.gap_title || gap.gap || gap.title || "";
      const explanation = gap.explanation || gap.description || "";
      const context = gap.related_context || gap.context || "";

      // Si el objeto ya es un string formateado por algún motivo, lo devolvemos
      if (typeof gapTitle !== 'string' && typeof explanation !== 'string') {
        return JSON.stringify(gap);
      }

      return `**${gapTitle}**\n\n${explanation}${context ? `\n\n*Contexto*: ${context}` : ""}`;
    });
    setSliderQuestions(formattedGaps);
    setSliderTitle(title);
    setIsKnowledgeGapsDialogOpen(true);
  }, []);

  const openQuestionsSlider = useCallback((questions: any[], title: string) => {
    if (!questions || questions.length === 0) return;
    const formattedQuestions = questions.map(q => {
      if (typeof q === 'string') return q;
      return q.issue || q.description || q.question || "Pregunta sin contenido";
    });
    setSliderQuestions(formattedQuestions);
    setSliderTitle(title);
    setIsQuestionsDialogOpen(true);
  }, []);

  const openSimpleListDialog = useCallback((items: string[], title: string, description: string, icon: React.ReactNode, colorClass: string) => {
    setSimpleListItems(items);
    setSimpleListTitle(title);
    setSimpleListDescription(description);
    setSimpleListIcon(icon);
    setSimpleListColor(colorClass);
    setIsSimpleListDialogOpen(true);
  }, []);

  // Función para eliminar análisis
  const handleDeleteAnalysis = useCallback(async () => {
    if (!currentAnalysis?.id) return;

    setIsDeleting(true);
    setDeleteError(null);

    try {
      if (currentAnalysis.type === 'insight' || currentAnalysis.type === 'neural_insight' || currentAnalysis.type === 'proactive_insight') {
        await apiClient.delete('/api/delete-proactive-insight', {
          data: { insight_id: currentAnalysis.id }
        });
      } else {
        await apiClient.delete('/api/delete-analysis', {
          data: { task_id: currentAnalysis.id }
        });
      }

      // Llamar al callback para actualizar la lista
      onAnalysisDeleted?.(currentAnalysis.id);

      // Cerrar el diálogo
      onOpenChange(false);
      toast.success('Análisis eliminado correctamente');

    } catch (error: any) {
      console.error('Error deleting analysis:', error);
      const errorMessage = error.response?.data?.detail || error.message || 'Error desconocido al eliminar';
      setDeleteError(errorMessage);
      toast.error(`Error al eliminar: ${errorMessage}`);
    } finally {
      setIsDeleting(false);
    }
  }, [currentAnalysis, onAnalysisDeleted, onOpenChange]);

  // Función para confirmar eliminación
  const handleConfirmDelete = useCallback(() => {
    setShowDeleteConfirm(true);
  }, []);

  // Función para cancelar eliminación
  const handleCancelDelete = useCallback(() => {
    setShowDeleteConfirm(false);
    setDeleteError(null);
  }, []);

  const handleDevelopGapOrQuestion = useCallback(async (question: string) => {
    if (!currentAnalysis?.id) {
      toast.error("No se pudo iniciar el desarrollo: ID de análisis no disponible.");
      return;
    }

    try {
      toast.info("Iniciando desarrollo de la brecha/pregunta...", { id: "develop-gap-toast" });
      const response = await apiClient.post('/api/gap-development/', {
        gap_id: currentAnalysis.id, // Usamos el analysis.id como gap_id para vincularlo
        context: question,
        depth: 3, // Profundidad de investigación por defecto
        parent_analysis_id: currentAnalysis.id // El análisis actual es el padre
      });

      if (response.status === 200) {
        toast.success("Desarrollo iniciado con éxito. Revisa la sección de Insights Proactivos.", { id: "develop-gap-toast" });
        // Opcional: Cerrar el diálogo o actualizar algún estado
      } else {
        toast.error(`Error al iniciar el desarrollo: ${response.data?.message || response.statusText}`, { id: "develop-gap-toast" });
      }
    } catch (error) {
      console.error("Error calling gap-development API:", error);
      toast.error("Error de conexión al iniciar el desarrollo.", { id: "develop-gap-toast" });
    }
  }, [currentAnalysis?.id]);

  const semanticData = useMemo(() => {
    if (!currentAnalysis) {
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
      resumen_semantico: currentAnalysis.result?.resumen_semantico || currentAnalysis.summary || 'No hay resumen disponible',
      temas_transversales: currentAnalysis.result?.temas_transversales || [],
      conceptos_centrales: currentAnalysis.result?.conceptos_centrales || [],
      brechas_conocimiento: currentAnalysis.result?.brechas_conocimiento || [],
      patrones_semanticos: currentAnalysis.result?.patrones_semanticos || {},
      problematic_areas: currentAnalysis.result?.problematic_areas || []
    };
  }, [currentAnalysis]);

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
    if (!currentAnalysis) return [];

    const allQuestions: (Question | string)[] = [];

    // Prioridad 1: analysis.questions
    if (currentAnalysis.questions && currentAnalysis.questions.length > 0) {
      allQuestions.push(...currentAnalysis.questions);
    }

    // Prioridad 2: insights.questions
    if (currentAnalysis.insights) {
      currentAnalysis.insights.forEach(insight => {
        if (insight.questions && insight.questions.length > 0) {
          allQuestions.push(...insight.questions);
        }
      });
    }

    return allQuestions;
  }, [currentAnalysis]);

  const hasInsights = useMemo(() => currentAnalysis?.insights && currentAnalysis.insights.length > 0, [currentAnalysis]);
  const hasRawContent = useMemo(() => !!currentAnalysis?.rawContent, [currentAnalysis]);
  const hasQuestions = useMemo(() => getQuestions().length > 0, [getQuestions]);


  const renderTypeSpecificContent = useCallback(() => {
    if (!currentAnalysis) return null;

    let contentToProcess = currentAnalysis.summary || currentAnalysis.rawContent || '';
    let sources: { id: string; link?: string; title?: string }[] = [];

    // Adaptar fuentes si vienen en el nuevo formato `{id: string, link: string}`
    if (Array.isArray(currentAnalysis.sources) && currentAnalysis.sources.length > 0) {
      sources = currentAnalysis.sources.map(s => {
        if (typeof s === 'string') {
          return { id: s };
        } else {
          return s as { id: string; link?: string; title?: string };
        }
      });
    }

    const processedOutput = { content: contentToProcess, sources: sources };

    switch (currentAnalysis.type) {
      case 'semantic':
      case 'semantic_summary':
        const semanticColors = getAnalysisColorScheme(currentAnalysis.type);
        return (
          <SemanticAnalysis
            analysis={currentAnalysis}
            semanticColors={semanticColors}
            handleThemeClick={handleThemeClick}
            handleConceptClick={handleConceptClick}
            openGapsSlider={openGapsSlider}
            openQuestionsSlider={openQuestionsSlider}
            play={play}
            isLoading={isLoading}
            isPlaying={isPlaying}
            activeText={activeText || ""}
          />
        );

      case 'collection':
        const colColors = getAnalysisColorScheme(currentAnalysis.type);
        return (
          <CollectionAnalysisComponent
            analysis={currentAnalysis.full_data as CollectionAnalysis}
            colColors={colColors}
            handleThemeClick={handleThemeClick}
            handleConceptClick={handleConceptClick}
            openGapsSlider={openGapsSlider}
            openQuestionsSlider={openQuestionsSlider}
            play={play}
            isLoading={isLoading}
            isPlaying={isPlaying}
            activeText={activeText || ""}
          />
        );

      case 'document':
        const docColors = getAnalysisColorScheme(currentAnalysis.type);
        return (
          <DocumentAnalysisComponent
            analysis={currentAnalysis.full_data as SingleTextAnalysis}
            docColors={docColors}
            handleThemeClick={handleThemeClick}
            handleConceptClick={handleConceptClick}
            openGapsSlider={openGapsSlider}
            openQuestionsSlider={openQuestionsSlider}
            play={play}
            isLoading={isLoading}
            isPlaying={isPlaying}
            activeText={activeText || ""}
            documentTitle={currentAnalysis.title}
          />
        );

      case 'document_summary':
        const summaryColors = getAnalysisColorScheme(currentAnalysis.type);
        return (
          <DocumentSummaryComponent
            summary={currentAnalysis.full_data as DocumentSummaryResult}
            docColors={summaryColors}
            play={play}
            isLoading={isLoading}
            isPlaying={isPlaying}
            activeText={activeText || ""}
            documentTitle={currentAnalysis.title}
          />
        );

      case 'code':
      case 'code_security':
      case 'code_performance':
      case 'code_refactoring':
      case 'code_documentation':
      case 'code_structure':
        const codeColors = getAnalysisColorScheme(currentAnalysis.type);
        return (
          <CodeAnalysisComponent
            analysis={currentAnalysis.full_data as CodeAnalysisResultFrontend}
            codeColors={codeColors}
          />
        );

      case 'note_collection_analysis':
        const noteCollectionColors = getAnalysisColorScheme(currentAnalysis.type);
        return (
          <NoteCollectionAnalysisComponent
            analysis={currentAnalysis.full_data as NoteCollectionAnalysisResult}
            noteCollectionColors={noteCollectionColors}
            handleThemeClick={handleThemeClick}
            handleConceptClick={handleConceptClick}
            openGapsSlider={openGapsSlider}
            openQuestionsSlider={openQuestionsSlider}
            openSimpleListDialog={openSimpleListDialog}
            play={play}
            isLoading={isLoading}
            isPlaying={isPlaying}
            activeText={activeText || ""}
          />
        );

      case 'note_analysis':
        const noteColors = getAnalysisColorScheme(currentAnalysis.type);
        return (
          <NoteAnalysisComponent
            analysis={currentAnalysis.full_data as NoteAnalysisResult}
            noteColors={noteColors}
            handleThemeClick={handleThemeClick}
            handleConceptClick={handleConceptClick}
            openGapsSlider={openGapsSlider}
            openQuestionsSlider={openQuestionsSlider}
            openSimpleListDialog={openSimpleListDialog}
            play={play}
            isLoading={isLoading}
            isPlaying={isPlaying}
            activeText={activeText || ""}
          />
        );

      case 'gap_development':
        let gapData = currentAnalysis.full_data || currentAnalysis.result;

        // Ensure gapData is an object if it's a JSON string
        if (typeof gapData === 'string') {
          try {
            gapData = JSON.parse(gapData);
          } catch (e) {
            console.error("Failed to parse gapData JSON:", e);
          }
        }

        // El backend a veces envuelve el resultado en un objeto 'report'
        const actualGapData = (gapData && typeof gapData === 'object' && 'report' in gapData)
          ? gapData.report
          : gapData;

        // NUEVO: Verificar el modo para decidir qué componente mostrar
        if (actualGapData?.mode === 'draft') {
          return (
            <DraftDetailDialog
              analysis={currentAnalysis}
              isOpen={isOpen}
              onOpenChange={onOpenChange}
            />
          );
        }

        return (
          <DeepResearchAnalysis
            analysis={actualGapData as DeepResearchAnalysisResult}
            play={play}
            isLoading={isLoading}
            isPlaying={isPlaying}
            activeText={activeText || ""}
          />
        );

      case 'insight':
      case 'proactive_insight_manual':
      case 'proactive_insight':
        let insightData = currentAnalysis.full_data || currentAnalysis.result;
        let actualInsightResult: ProactiveInsightResult;

        // Si insightData es un objeto y tiene una propiedad 'insight', la usamos.
        // Esto maneja el caso en que el backend lo envuelve.
        if (typeof insightData === 'object' && insightData !== null && 'insight' in insightData) {
          actualInsightResult = insightData.insight as ProactiveInsightResult;
        } else {
          actualInsightResult = insightData as ProactiveInsightResult;
        }

        return (
          <ProactiveInsightAnalysis
            analysis={actualInsightResult}
            play={play}
            isLoading={isLoading}
            isPlaying={isPlaying}
            activeText={activeText}
          />
        );

      case 'comprehensive_web_analysis':
        const analysisData = currentAnalysis.full_data;
        // Handle both string (legacy/direct) and object (new structured) formats
        const reportContent = typeof analysisData === 'string'
          ? analysisData
          : (analysisData as any)?.report || '';

        return (
          <ComprehensiveWebAnalysis
            analysis={reportContent}
            parentAnalysis={currentAnalysis}
            play={play}
            isLoading={isLoading}
            isPlaying={isPlaying}
            activeText={activeText}
          />
        );

      case 'scoped_rag_analysis':
        return (
          <ScopedRagAnalysis
            analysis={currentAnalysis.full_data as ScopedRagAnalysisResult}
            parentAnalysis={currentAnalysis}
            play={play}
            isLoading={isLoading}
            isPlaying={isPlaying}
            activeText={activeText}
          />
        );

      case 'neural_insight':
        return (
          <NeuralInsightAnalysis
            analysis={currentAnalysis}
            play={play}
            isLoading={isLoading}
            isPlaying={isPlaying}
            activeText={activeText || undefined}
          />
        );

      default:
        return (
          <div className="text-center py-10">
            <p className="text-muted-foreground">No hay una vista detallada para este tipo de análisis.</p>
          </div>
        );
    }
  }, [currentAnalysis, isLoading, isPlaying, activeText, textToRead, play, handleThemeClick, handleConceptClick, openGapsSlider, openQuestionsSlider, openSimpleListDialog, isOpen, onOpenChange]);

  if (!currentAnalysis) {
    return (
      <Dialog open={isOpen} onOpenChange={onOpenChange}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Cargando...</DialogTitle>
          </DialogHeader>
          <div className="flex items-center justify-center p-10">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        </DialogContent>
      </Dialog>
    );
  }

  const colors = getAnalysisColorScheme(currentAnalysis.type);

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent
        className="max-w-4xl w-full max-h-[90vh] rounded-2xl bg-card/95 backdrop-blur-xl border shadow-2xl flex flex-col overflow-hidden"
        onPointerDownOutside={(e) => {
          const target = e.target as HTMLElement;
          if (target.closest('.contextual-chat-container')) {
            e.preventDefault();
          }
        }}
        onInteractOutside={(e) => {
          const target = e.target as HTMLElement;
          if (target.closest('.contextual-chat-container')) {
            e.preventDefault();
          }
        }}
        onFocusOutside={(e) => {
          const target = e.target as HTMLElement;
          if (target.closest('.contextual-chat-container')) {
            e.preventDefault();
          }
          stop(); // Detener la reproducción de TTS al interactuar fuera del diálogo
        }}
      >
        <DialogHeader className="px-8 pt-8 pb-4 border-b">
          <div className="flex items-start justify-between gap-4">
            <div>
              <Badge className={`mb-2 ${getAnalysisTypeBadgeColor(currentAnalysis.type)}`}>
                {getAnalysisTypeLabel(currentAnalysis.type)}
              </Badge>
              <div className="flex items-center gap-2">
                <DialogTitle className="text-3xl font-extrabold tracking-tight leading-tight break-words">
                  {currentAnalysis.title}
                </DialogTitle>
                <Button
                  variant="ghost"
                  size="sm"
                  className={cn(
                    "h-8 w-8 p-0 rounded-full transition-all duration-300",
                    isMainSummaryPlaying ? "text-primary bg-primary/10" : "text-muted-foreground hover:text-primary hover:bg-primary/10"
                  )}
                  onClick={(e) => {
                    e.stopPropagation();
                    handlePlayPauseMainSummary();
                  }}
                  disabled={isMainSummaryLoading}
                  title={isMainSummaryPlaying ? "Pausar lectura del resumen" : "Escuchar resumen"}
                >
                  {isMainSummaryLoading ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : isMainSummaryPlaying ? (
                    <Pause className="h-4 w-4" />
                  ) : (
                    <Volume2 className="h-4 w-4" />
                  )}
                </Button>
              </div>
              <DialogDescription className="mt-2 text-md text-muted-foreground" asChild>
                <div className="break-words">
                  {currentAnalysis.type === 'gap_development' ? (
                    <span>{currentAnalysis.title}</span>
                  ) : (
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {currentAnalysis.summary || "Detalles del análisis."}
                    </ReactMarkdown>
                  )}
                </div>
              </DialogDescription>
            </div>
            <div className="flex-shrink-0 flex items-center gap-1">

              {showDeleteConfirm ? (
                <div className="flex items-center gap-2">
                  <Button variant="destructive" size="sm" onClick={handleDeleteAnalysis} disabled={isDeleting}>
                    {isDeleting ? <Loader2 className="h-4 w-4 animate-spin" /> : "Confirmar"}
                  </Button>
                  <Button variant="ghost" size="sm" onClick={handleCancelDelete} disabled={isDeleting}>
                    Cancelar
                  </Button>
                </div>
              ) : (
                <div className="flex items-center gap-1">
                  <Button variant="ghost" size="icon" onClick={() => setIsChatOpen(true)} className="text-muted-foreground hover:text-primary hover:bg-primary/10" title="Chatear con este análisis">
                    <MessageSquare className="h-4 w-4" />
                  </Button>
                  <Button variant="ghost" size="icon" onClick={() => setIsShareDialogOpen(true)} className="text-muted-foreground hover:text-primary hover:bg-primary/10" title="Compartir análisis">
                    <ExternalLink className="h-4 w-4" />
                  </Button>
                  {onAnalysisDeleted && (
                    <Button variant="ghost" size="icon" onClick={handleConfirmDelete} className="text-muted-foreground hover:text-destructive hover:bg-destructive/10">
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  )}
                </div>
              )}
            </div>
          </div>
          {deleteError && (
            <Alert variant="destructive" className="mt-4">
              <AlertTriangle className="h-4 w-4" />
              <AlertTitle>Error al eliminar</AlertTitle>
              <AlertDescription>{deleteError}</AlertDescription>
            </Alert>
          )}
        </DialogHeader>

        <div className="flex-1 flex overflow-hidden">
          <ScrollArea className="flex-1 custom-scrollbar">
            <div className="p-8">
              {currentAnalysis.status === 'in_progress' ? (
                <div className="flex flex-col items-center justify-center h-64 gap-4">
                  <Loader2 className="h-12 w-12 animate-spin text-primary" />
                  <p className="text-lg font-medium text-muted-foreground">Análisis en curso...</p>
                  <p className="text-sm text-muted-foreground">El resultado aparecerá aquí cuando esté listo.</p>
                </div>
              ) : currentAnalysis.status === 'failed' ? (
                <Alert variant="destructive" className="my-4">
                  <AlertTriangle className="h-4 w-4" />
                  <AlertTitle>Análisis Fallido</AlertTitle>
                  <AlertDescription>
                    {currentAnalysis.error_message || "Ocurrió un error durante el análisis."}
                  </AlertDescription>
                </Alert>
              ) : (
                <div className="w-full max-w-full min-w-0 overflow-hidden">
                  {renderTypeSpecificContent()}
                </div>
              )}
            </div>
          </ScrollArea>
        </div>

        <DialogFooter className="px-8 py-4 border-t">
          <div className="flex w-full justify-between items-center">
            <div className="text-xs text-muted-foreground">
              ID: {currentAnalysis.id}
            </div>
            <div className="flex gap-2">
              {hasQuestions && (
                <Button
                  variant="outline"
                  onClick={() => openQuestionsSlider(getQuestions(), "Preguntas Generadas")}
                >
                  <HelpCircle className="mr-2 h-4 w-4" />
                  Ver Preguntas
                </Button>
              )}
              <Button
                variant="outline"
                onClick={exportToPdf}
                disabled={isPdfExporting}
                className="gap-2"
              >
                {isPdfExporting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
                Exportar PDF
              </Button>
              {currentAnalysis && (currentAnalysis.type === 'neural_insight' || currentAnalysis.type === 'proactive_insight') ? (
                <>
                  <Button 
                    variant="outline" 
                    className="border-green-200 hover:bg-green-50 dark:border-green-900/30 dark:hover:bg-green-950/30 text-green-600 dark:text-green-400 gap-2"
                    onClick={() => onOpenChange(false)}
                  >
                    <CircleCheck className="h-4 w-4" />
                    Aceptar
                  </Button>
                  <Button 
                    variant="outline" 
                    className="border-red-200 hover:bg-red-50 dark:border-red-900/30 dark:hover:bg-red-950/30 text-red-600 dark:text-red-400 gap-2"
                    onClick={async () => {
                      if (confirm('¿Estás seguro de que deseas rechazar y eliminar este insight?')) {
                        try {
                          if (currentAnalysis.type === 'insight' || currentAnalysis.type === 'neural_insight' || currentAnalysis.type === 'proactive_insight') {
                            await apiClient.delete('/api/delete-proactive-insight', { 
                              data: { insight_id: currentAnalysis.id } 
                            });
                          } else {
                            await apiClient.delete('/api/delete-analysis', { 
                              data: { task_id: currentAnalysis.id } 
                            });
                          }
                          toast.success('Insight rechazado y eliminado.');
                          onOpenChange(false);
                          if (onAnalysisDeleted) onAnalysisDeleted(currentAnalysis.id);
                        } catch (error) {
                          toast.error('No se pudo eliminar el insight.');
                        }
                      }
                    }}
                  >
                    <XCircle className="h-4 w-4" />
                    Rechazar
                  </Button>
                </>
              ) : (
                <Button onClick={() => onOpenChange(false)}>Cerrar</Button>
              )}
            </div>
          </div>
        </DialogFooter>

        {/* Chat Contextual para el Análisis - Movido dentro de DialogContent */}
        {currentAnalysis && (
          <ContextualChat
            isOpen={isChatOpen}
            onClose={() => setIsChatOpen(false)}
            context={{
              type: 'analysis',
              id: currentAnalysis.id,
              snapshot: {
                ...currentAnalysis,
                // Asegurar que el contexto incluya los datos procesados para que la IA los vea
                processed_data: currentAnalysis.full_data || currentAnalysis.result
              }
            }}
            title={currentAnalysis.title}
          />
        )}
      </DialogContent>

      {/* Diálogos para sliders y detalles */}
      <QuestionSliderDialog
        isOpen={isQuestionsDialogOpen}
        onOpenChange={setIsQuestionsDialogOpen}
        questions={sliderQuestions}
        title={sliderTitle}
        onDevelopClick={handleDevelopGapOrQuestion}
        analysisId={currentAnalysis.id}
      />
      <QuestionSliderDialog
        isOpen={isKnowledgeGapsDialogOpen}
        onOpenChange={setIsKnowledgeGapsDialogOpen}
        questions={sliderQuestions}
        title={sliderTitle}
        onDevelopClick={handleDevelopGapOrQuestion}
        analysisId={currentAnalysis.id}
      />
      <ThemeQuotesDialog
        isOpen={isThemeQuotesDialogOpen}
        onOpenChange={setIsThemeQuotesDialogOpen}
        theme={selectedThemeForQuotes}
      />
      <ConceptDetailDialog
        isOpen={isConceptDialogOpen}
        onOpenChange={setIsConceptDialogOpen}
        concept={selectedConcept}
      />
      <SimpleListDialog
        isOpen={isSimpleListDialogOpen}
        onOpenChange={setIsSimpleListDialogOpen}
        title={simpleListTitle}
        description={simpleListDescription}
        items={simpleListItems}
        icon={simpleListIcon}
        colorClass={simpleListColor}
      />

      {/* Diálogo de compartir análisis */}
      <ShareAnalysisDialog
        isOpen={isShareDialogOpen}
        onOpenChange={setIsShareDialogOpen}
        analysisId={currentAnalysis.id}
        analysisTitle={currentAnalysis.title}
      />

    </Dialog>
  );
};
