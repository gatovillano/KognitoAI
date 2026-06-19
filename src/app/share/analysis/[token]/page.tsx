'use client';

import React, { useEffect, useState, useMemo } from 'react';
import { useParams } from 'next/navigation';
import { Loader2, Lock, Copy, Check, AlertTriangle, ScrollText, Network, Zap, Target, Brain, FileText, LibraryBig, ExternalLink, Lightbulb } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';
import { SourcesTab } from '@/components/SourcesTab';
import { QuestionSliderDialog } from '@/components/QuestionSliderDialog';
import { MarkdownRenderer } from '@/components/MarkdownRenderer';
import { Source, ContentPart, SourceButton } from '@/components/SourceButton';
import { processMessageWithCitations, collectSourcesFromMessage, getSourceIdentityKey } from '@/lib/chatUtils';
import CodeAnalysis from '@/app/(dashboard)/analysis/CodeAnalysis';
import { CodeAnalysisResultFrontend } from '@/lib/models';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { ChevronDown } from 'lucide-react';

// Helper function to get color scheme for each analysis type
const getAnalysisColorScheme = (type: string) => {
    switch (type) {
        case 'document':
        case 'document_summary':
            return { color: 'blue', cardBg: 'bg-blue-50/50 border-blue-100 dark:bg-blue-900/10 dark:border-blue-900/50', cardTitle: 'text-blue-900 dark:text-blue-100', icon: 'text-blue-600', tag: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-100' };
        case 'collection':
            return { color: 'green', cardBg: 'bg-green-50/50 border-green-100 dark:bg-green-900/10 dark:border-green-900/50', cardTitle: 'text-green-900 dark:text-green-100', icon: 'text-green-600', tag: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100' };
        case 'semantic':
        case 'semantic_summary':
            return { color: 'indigo', cardBg: 'bg-indigo-50/50 border-indigo-100 dark:bg-indigo-900/10 dark:border-indigo-900/50', cardTitle: 'text-indigo-900 dark:text-indigo-100', icon: 'text-indigo-600', tag: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-100' };
        case 'code':
            return { color: 'cyan', cardBg: 'bg-cyan-50/50 border-cyan-100 dark:bg-cyan-900/10 dark:border-cyan-900/50', cardTitle: 'text-cyan-900 dark:text-cyan-100', icon: 'text-cyan-600', tag: 'bg-cyan-100 text-cyan-800 dark:bg-cyan-900 dark:text-cyan-100' };
        case 'insight':
        case 'proactive_insight_manual':
        case 'proactive_insight':
        case 'neural_insight':
            return { color: 'yellow', cardBg: 'bg-yellow-50/50 border-yellow-100 dark:bg-yellow-900/10 dark:border-yellow-900/50', cardTitle: 'text-yellow-900 dark:text-yellow-100', icon: 'text-yellow-600', tag: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-100' };
        case 'comprehensive_web_analysis':
            return { color: 'sky', cardBg: 'bg-sky-50/50 border-sky-100 dark:bg-sky-900/10 dark:border-sky-900/50', cardTitle: 'text-sky-900 dark:text-sky-100', icon: 'text-sky-600', tag: 'bg-sky-100 text-sky-800 dark:bg-sky-900 dark:text-sky-100' };
        case 'scoped_rag_analysis':
            return { color: 'rose', cardBg: 'bg-rose-50/50 border-rose-100 dark:bg-rose-900/10 dark:border-rose-900/50', cardTitle: 'text-rose-900 dark:text-rose-100', icon: 'text-rose-600', tag: 'bg-rose-100 text-rose-800 dark:bg-rose-900 dark:text-rose-100' };
        case 'note_analysis':
            return { color: 'amber', cardBg: 'bg-amber-50/50 border-amber-100 dark:bg-amber-900/10 dark:border-amber-900/50', cardTitle: 'text-amber-900 dark:text-amber-100', icon: 'text-amber-600', tag: 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-100' };
        case 'note_collection_analysis':
            return { color: 'orange', cardBg: 'bg-orange-50/50 border-orange-100 dark:bg-orange-900/10 dark:border-orange-900/50', cardTitle: 'text-orange-900 dark:text-orange-100', icon: 'text-orange-600', tag: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-100' };
        case 'knowledge_graph_analysis':
            return { color: 'purple', cardBg: 'bg-purple-50/50 border-purple-100 dark:bg-purple-900/10 dark:border-purple-900/50', cardTitle: 'text-purple-900 dark:text-purple-100', icon: 'text-purple-600', tag: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-100' };
        case 'custom_analysis':
            return { color: 'red', cardBg: 'bg-red-50/50 border-red-100 dark:bg-red-900/10 dark:border-red-900/50', cardTitle: 'text-red-900 dark:text-red-100', icon: 'text-red-600', tag: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-100' };
        case 'repository_update':
            return { color: 'teal', cardBg: 'bg-teal-50/50 border-teal-100 dark:bg-teal-900/10 dark:border-teal-900/50', cardTitle: 'text-teal-900 dark:text-teal-100', icon: 'text-teal-600', tag: 'bg-teal-100 text-teal-800 dark:bg-teal-900 dark:text-teal-100' };
        case 'gap_development':
            return { color: 'fuchsia', cardBg: 'bg-fuchsia-50/50 border-fuchsia-100 dark:bg-fuchsia-900/10 dark:border-fuchsia-900/50', cardTitle: 'text-fuchsia-900 dark:text-fuchsia-100', icon: 'text-fuchsia-600', tag: 'bg-fuchsia-100 text-fuchsia-800 dark:bg-fuchsia-900 dark:text-fuchsia-100' };
        default:
            return { color: 'gray', cardBg: 'bg-gray-50/50 border-gray-100 dark:bg-gray-900/10 dark:border-gray-900/50', cardTitle: 'text-gray-900 dark:text-gray-100', icon: 'text-gray-600', tag: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-100' };
    }
};

const getAnalysisTypeBadgeColor = (type: string) => {
    switch (type) {
        case 'document': case 'document_summary': return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-100 border-blue-200 dark:border-blue-800';
        case 'collection': return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100 border-green-200 dark:border-green-800';
        case 'semantic': case 'semantic_summary': return 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-100 border-indigo-200 dark:border-indigo-800';
        case 'code': return 'bg-cyan-100 text-cyan-800 dark:bg-cyan-900 dark:text-cyan-100 border-cyan-200 dark:border-cyan-800';
        case 'insight': case 'proactive_insight_manual': case 'proactive_insight': return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-100 border-yellow-200 dark:border-yellow-800';
        case 'comprehensive_web_analysis': return 'bg-sky-100 text-sky-800 dark:bg-sky-900 dark:text-sky-100 border-sky-200 dark:border-sky-800';
        case 'scoped_rag_analysis': return 'bg-rose-100 text-rose-800 dark:bg-rose-900 dark:text-rose-100 border-rose-200 dark:border-rose-800';
        case 'note_analysis': return 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-100 border-amber-200 dark:border-amber-800';
        case 'note_collection_analysis': return 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-100 border-orange-200 dark:border-orange-800';
        case 'knowledge_graph_analysis': return 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-100 border-purple-200 dark:border-purple-800';
        case 'custom_analysis': return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-100 border-red-200 dark:border-red-800';
        case 'repository_update': return 'bg-teal-100 text-teal-800 dark:bg-teal-900 dark:text-teal-100 border-teal-200 dark:border-teal-800';
        case 'gap_development': return 'bg-fuchsia-100 text-fuchsia-800 dark:bg-fuchsia-900 dark:text-fuchsia-100 border-fuchsia-200 dark:border-fuchsia-800';
        default: return 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-100 border-gray-200 dark:border-gray-700';
    }
};

const getAnalysisTypeLabel = (type: string) => {
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

// Interface for theme quotes
interface ThemeQuote {
    quote: string;
    document_title: string;
}

interface ThemeReferenceExtended {
    theme: string;
    related_quotes?: ThemeQuote[];
}

// Concept Detail Dialog Component
const ConceptDetailDialog: React.FC<{ isOpen: boolean; onOpenChange: (open: boolean) => void; concept: string | null }> = ({ isOpen, onOpenChange, concept }) => {
    if (!concept) return null;
    const conceptParts = concept.split(':');
    const conceptName = conceptParts[0]?.trim() || '';
    const conceptDefinition = conceptParts.slice(1).join(':').trim() || '';
    return (
        <Dialog open={isOpen} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-2xl w-full max-h-[80vh] rounded-lg bg-card border shadow-lg flex flex-col overflow-hidden">
                <DialogHeader className="px-6 pt-6 pb-4">
                    <DialogTitle className="text-xl font-bold text-foreground">Detalles del Concepto</DialogTitle>
                </DialogHeader>
                <ScrollArea className="flex-1 px-6 py-2">
                    <div className="space-y-4 pb-4">
                        <h4 className="text-lg font-semibold text-foreground mb-2">{conceptName}</h4>
                        <div className="prose prose-sm max-w-none dark:prose-invert prose-headings:text-foreground prose-headings:font-semibold prose-p:text-muted-foreground prose-p:leading-relaxed prose-strong:text-foreground prose-strong:font-semibold prose-ul:text-muted-foreground prose-li:text-muted-foreground prose-a:text-blue-600 dark:prose-a:text-blue-400 prose-a:underline">
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>{conceptDefinition}</ReactMarkdown>
                        </div>
                        <div className="pt-4 text-xs text-muted-foreground italic border-t">
                            Para profundizar en este concepto, puedes realizar una búsqueda dirigida en la colección.
                        </div>
                    </div>
                </ScrollArea>
                <div className="px-6 py-4 border-t">
                    <Button variant="outline" onClick={() => onOpenChange(false)}>Cerrar</Button>
                </div>
            </DialogContent>
        </Dialog>
    );
};

// Theme Quotes Dialog Component
const ThemeQuotesDialog: React.FC<{ isOpen: boolean; onOpenChange: (open: boolean) => void; theme: ThemeReferenceExtended | null }> = ({ isOpen, onOpenChange, theme }) => {
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
                        Fragmentos de texto relacionados con el tema "{theme.theme}" encontrados en los documentos.
                    </DialogDescription>
                </DialogHeader>
                <div className="py-4 flex-1 overflow-y-auto max-h-[60vh] pr-2 custom-scrollbar">
                    {theme.related_quotes && theme.related_quotes.length > 0 ? (
                        <div className="space-y-4">
                            {theme.related_quotes.map((quote: ThemeQuote, qIdx: number) => {
                                const quoteContent = typeof quote.quote === 'string' ? quote.quote : JSON.stringify(quote.quote);
                                return (
                                    <div key={qIdx} className="p-4 rounded-xl bg-muted/30 border border-muted hover:bg-muted/50 transition-colors">
                                        <div className="italic text-sm leading-relaxed mb-3">
                                            <ReactMarkdown remarkPlugins={[remarkGfm]}>{`"${quoteContent}"`}</ReactMarkdown>
                                        </div>
                                        <div className="flex items-center gap-2 text-[10px] font-bold text-muted-foreground uppercase tracking-wider">
                                            <div className="w-1 h-1 rounded-full bg-indigo-500" />
                                            {quote.document_title}
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    ) : (
                        <div className="text-center py-10 text-muted-foreground italic">No se encontraron citas para este tema.</div>
                    )}
                </div>
                <div className="px-6 py-4 border-t">
                    <Button variant="outline" onClick={() => onOpenChange(false)} className="rounded-xl">Cerrar</Button>
                </div>
            </DialogContent>
        </Dialog>
    );
};

// Deep Research / Gap Development Content Component
interface DeepResearchContentProps {
    resultPayload: any;
    fullData: any;
    type: string;
    summary?: string;
}

const DeepResearchContent: React.FC<DeepResearchContentProps> = ({ resultPayload, fullData, type, summary: propSummary }) => {
    // Get the data based on type
    // Debug: Verificar estructura de datos
    console.log('DeepResearchContent - Datos:', {
        type,
        resultPayload,
        fullData
    });
    
    const reportData = getDeepResearchData(resultPayload, fullData, type);
    
    console.log('DeepResearchContent - Datos procesados:', {
        reportData
    });
    
     const finalReport = reportData?.final_report || reportData?.summary || '';
    const summary = reportData?.summary || finalReport.slice(0, 1000) + "...";
    const findings = reportData?.findings || (fullData?.findings || (propSummary ? [propSummary] : [finalReport]));
    const sources = reportData?.sources || [];
    const recommendations = reportData?.recommendations || [];

    // Process sources using the same utility as DeepResearchDetailDialog
    const { citationSources, additionalSources } = useMemo(() => {
        return collectSourcesFromMessage(sources as any[]);
    }, [sources]);

    const { contentParts: summaryContentParts, citedSources: citedSourcesSummary, uncitedSources: uncitedSourcesSummary, resolvedSources: resolvedSummarySources } = useMemo(() => {
        return processMessageWithCitations(summary, citationSources);
    }, [summary, citationSources]);

    const { contentParts: findingsContentParts, citedSources: citedSourcesFindings, uncitedSources: uncitedSourcesFindings } = useMemo(() => {
        return processMessageWithCitations(findings, citationSources);
    }, [findings, citationSources]);

    const { contentParts: recommendationsContentParts, citedSources: citedSourcesRecommendations, uncitedSources: uncitedSourcesRecommendations } = useMemo(() => {
        return processMessageWithCitations(recommendations.join("\n\n"), citationSources);
    }, [recommendations, citationSources]);

    const displaySources = resolvedSummarySources.length > 0 ? resolvedSummarySources : additionalSources;
    const citationNumberBySource = useMemo(() => {
        return new Map(displaySources.map((source, index) => [getSourceIdentityKey(source), index + 1]));
    }, [displaySources]);

    const handleSourceClick = (source: Source) => {
        console.log('Source clicked:', source);
    };

    if (!finalReport) {
        return (
            <Card className="border-0 shadow-none bg-transparent">
                <CardContent className="p-0">
                    <p className="text-muted-foreground text-center py-8">No hay contenido disponible.</p>
                </CardContent>
            </Card>
        );
    }

     // Procesar contenido de resumen y hallazgos para markdown



    return (
        <Tabs defaultValue="summary" className="w-full">
            <TabsList className="grid w-full grid-cols-4 h-12 bg-muted/50 rounded-xl p-1">
                <TabsTrigger value="summary" className="gap-2">
                    <FileText className="h-4 w-4" />Resumen
                </TabsTrigger>
                <TabsTrigger value="findings" className="gap-2">
                    <Target className="h-4 w-4" />Hallazgos
                </TabsTrigger>
                <TabsTrigger value="sources" className="gap-2">
                    <ExternalLink className="h-4 w-4" />Fuentes
                </TabsTrigger>
                <TabsTrigger value="recommendations" className="gap-2">
                    <Lightbulb className="h-4 w-4" />Acciones
                </TabsTrigger>
            </TabsList>

            <div className="mt-6">
                <TabsContent value="summary">
                    <Card className="border-0 shadow-none bg-transparent">
                        <CardContent className="p-0">
                            <h3 className="text-lg font-semibold mb-2">Resumen General</h3>
                            <div className="text-foreground leading-relaxed">
                                <MarkdownRenderer
                                    contentParts={summaryContentParts}
                                    content={summary}
                                    fontSize="text-sm sm:text-base"
                                />
                            </div>

                            {/* Fuentes section at the end of summary - ChatMessage style */}
                            {(citedSourcesSummary?.length > 0 || uncitedSourcesSummary?.length > 0) && (
                                <div className="mt-8 pt-6 border-t border-border/10">
                                    <div className="flex items-center gap-2 mb-4">
                                        <div className="p-1 rounded-md bg-primary/10">
                                            <ExternalLink className="h-3 w-3 text-primary" />
                                        </div>
                                        <span className="text-[10px] font-black text-muted-foreground uppercase tracking-widest">
                                            Fuentes y Resultados RAG ({citedSourcesSummary?.length || 0} citadas de {displaySources.length} totales)
                                        </span>
                                    </div>
                                    {/* Fuentes Citadas (Siempre visibles) */}
                                    {citedSourcesSummary && citedSourcesSummary.length > 0 && (
                                        <div className="flex flex-wrap gap-2 mb-2">
                                            {citedSourcesSummary.map((source: Source, idx: number) => (
                                                <SourceButton
                                                    key={source.id || idx}
                                                    source={source}
                                                    citationNumber={citationNumberBySource.get(getSourceIdentityKey(source)) || idx + 1}
                                                    onSourceClick={handleSourceClick}
                                                />
                                            ))}
                                        </div>
                                    )}
                                    {/* Fuentes No Citadas (Colapsable) */}
                                    {uncitedSourcesSummary && uncitedSourcesSummary.length > 0 && (
                                        <Collapsible>
                                            <CollapsibleTrigger asChild>
                                                <Button variant="ghost" size="sm">
                                                    <ChevronDown className="h-3 w-3" />
                                                    <span>{uncitedSourcesSummary.length} fuente(s) adicional(es) no citada(s)</span>
                                                </Button>
                                            </CollapsibleTrigger>
                                            <CollapsibleContent>
                                                <div className="flex flex-wrap gap-2">
                                                    {uncitedSourcesSummary.map((source: Source, idx: number) => (
                                                        <SourceButton key={`uncited-${source.id || idx}`} source={source} citationNumber={-1} onSourceClick={handleSourceClick} />
                                                    ))}
                                                </div>
                                            </CollapsibleContent>
                                        </Collapsible>
                                    )}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="findings">
                    <Card className="border-0 shadow-none bg-transparent">
                        <CardContent className="p-0">
                            <h3 className="text-lg font-semibold mb-2">Hallazgos y Análisis</h3>
                            <div className="text-foreground leading-relaxed">
                                <MarkdownRenderer
                                    contentParts={findingsContentParts}
                                    content={findings}
                                    fontSize="text-sm sm:text-base"
                                />
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="sources">
                    <div className="pt-2">
                        <SourcesTab sources={displaySources} onSourceClick={handleSourceClick} />
                    </div>
                </TabsContent>

                <TabsContent value="recommendations">
                    <div className="space-y-4">
                        {recommendations?.length > 0 ? recommendations.map((rec: string, index: number) => (
                            <div key={index} className="p-4 rounded-xl bg-green-500/5 border border-green-500/20 flex gap-4">
                                <Lightbulb className="h-5 w-5 text-green-600 flex-shrink-0" />
                                <p className="text-sm text-green-800 dark:text-green-300 leading-relaxed whitespace-pre-wrap">{rec}</p>
                            </div>
                        )) : (
                            <p className="text-muted-foreground text-center py-8">No hay recomendaciones disponibles.</p>
                        )}
                    </div>
                </TabsContent>
            </div>
        </Tabs>
    );
};

// Helper to render any content as markdown or structured data
const renderRichContent = (content: any, title: string, colorScheme: any): React.ReactNode => {
    if (typeof content === 'string') {
        return <div className="prose prose-sm dark:prose-invert max-w-none"><ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown></div>;
    }
    if (Array.isArray(content)) {
        return (
            <div className="space-y-3">
                {content.map((item: any, idx: number) => (
                    <div key={idx} className={cn("p-4 rounded-lg border", colorScheme.cardBg)}>
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{typeof item === 'string' ? item : JSON.stringify(item, null, 2)}</ReactMarkdown>
                    </div>
                ))}
            </div>
        );
    }
    if (typeof content === 'object' && content !== null) {
        return (
            <div className="space-y-4">
                {Object.entries(content).map(([key, value]) => {
                    if (['title', 'summary', 'executive_summary', 'collection_summary', 'semantic_summary'].includes(key)) return null;
                    if (value === null || value === undefined) return null;
                    if (typeof value === 'object' && Object.keys(value).length === 0) return null;

                    return (
                        <div key={key} className={cn("p-4 rounded-lg border", colorScheme.cardBg)}>
                            <h4 className={cn("font-semibold mb-2 capitalize", colorScheme.cardTitle)}>{key.replace(/_/g, ' ')}</h4>
                            <div className="prose prose-sm dark:prose-invert max-w-none">
                                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                    {typeof value === 'string' ? value : JSON.stringify(value, null, 2)}
                                </ReactMarkdown>
                            </div>
                        </div>
                    );
                })}
            </div>
        );
    }
    return <pre className="p-4 bg-muted rounded-lg overflow-auto">{JSON.stringify(content, null, 2)}</pre>;
};

// Helper function to check if analysis is deep_research or gap_development
const isDeepResearchOrGapDevelopment = (type: string): boolean => {
    return type === 'deep_research' || type === 'gap_development';
};

// Get the result data for deep research or gap development
const getDeepResearchData = (resultPayload: any, fullData: any, type: string) => {
    // Para gap_development: el reporte está en result_payload.report o fullData.report
    if (type === 'gap_development') {
        if (resultPayload?.report) {
            return resultPayload.report;
        }
        if (fullData?.report) {
            return fullData.report;
        }
    }
    
    // Para deep_research: el reporte está en result_payload o result_payload.report
    if (type === 'deep_research') {
        if (resultPayload?.report) {
            return resultPayload.report;
        }
        return resultPayload;
    }
    
    // Por defecto, intenta encontrar el reporte en alguna parte
    return resultPayload?.report || fullData?.report || resultPayload;
};

export default function SharedAnalysisPage() {
    const params = useParams();
    const token = params?.token as string;

    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [passwordRequired, setPasswordRequired] = useState(false);
    const [password, setPassword] = useState('');
    const [analysis, setAnalysis] = useState<any>(null);
    const [copied, setCopied] = useState(false);

    // Dialog states for internal analysis dialogs
    const [isQuestionsDialogOpen, setIsQuestionsDialogOpen] = useState(false);
    const [sliderQuestions, setSliderQuestions] = useState<string[]>([]);
    const [sliderTitle, setSliderTitle] = useState('');
    const [selectedConcept, setSelectedConcept] = useState<string | null>(null);
    const [isConceptDialogOpen, setIsConceptDialogOpen] = useState(false);
    const [selectedThemeForQuotes, setSelectedThemeForQuotes] = useState<ThemeReferenceExtended | null>(null);
    const [isThemeQuotesDialogOpen, setIsThemeQuotesDialogOpen] = useState(false);

    const fetchAnalysis = async (submitPassword?: string) => {
        setLoading(true);
        setError(null);
        setPasswordRequired(false);
        try {
            const payload: { password?: string } = {};
            if (submitPassword) payload.password = submitPassword;
            const response = await fetch(`/api/analysis/share/access/${token}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            if (response.status === 401) {
                setPasswordRequired(true);
                setLoading(false);
                return;
            }
            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.detail || 'Error al cargar el análisis');
            }
            const data = await response.json();
            setAnalysis(data);
        } catch (e: any) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (token) fetchAnalysis();
    }, [token]);

    const handlePasswordSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        fetchAnalysis(password);
    };

    const copyLink = () => {
        navigator.clipboard.writeText(window.location.href);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    const formatDate = (dateString: string) => {
        return new Date(dateString).toLocaleDateString('es-ES', {
            year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit'
        });
    };

    const handleThemeClick = (theme: ThemeReferenceExtended) => {
        setSelectedThemeForQuotes(theme);
        setIsThemeQuotesDialogOpen(true);
    };

    const handleConceptClick = (concept: string) => {
        setSelectedConcept(concept);
        setIsConceptDialogOpen(true);
    };

    const openGapsSlider = (gaps: any[], title: string) => {
        if (!gaps || gaps.length === 0) return;
        const formattedGaps = gaps.map(gap => {
            if (typeof gap === 'string') return gap;
            const gapTitle = gap.gap_title || gap.gap || gap.title || "";
            const explanation = gap.explanation || gap.description || "";
            const context = gap.related_context || gap.context || "";
            if (typeof gapTitle !== 'string' && typeof explanation !== 'string') {
                return JSON.stringify(gap);
            }
            return `**${gapTitle}**\n\n${explanation}${context ? `\n\n*Contexto*: ${context}` : ""}`;
        });
        setSliderQuestions(formattedGaps);
        setSliderTitle(title);
        setIsQuestionsDialogOpen(true);
    };

    if (loading) {
        return (
            <div className="min-h-screen bg-background flex items-center justify-center">
                <div className="flex flex-col items-center gap-4">
                    <Loader2 className="h-12 w-12 animate-spin text-primary" />
                    <p className="text-muted-foreground">Cargando análisis compartido...</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="min-h-screen bg-background flex items-center justify-center p-4">
                <Alert variant="destructive" className="max-w-md">
                    <AlertTriangle className="h-4 w-4" />
                    <AlertTitle>Error</AlertTitle>
                    <AlertDescription>{error}</AlertDescription>
                </Alert>
            </div>
        );
    }

    if (passwordRequired) {
        return (
            <div className="min-h-screen bg-background flex items-center justify-center p-4">
                <Card className="w-full max-w-sm">
                    <CardHeader className="text-center">
                        <div className="mx-auto bg-muted p-3 rounded-full w-fit mb-4">
                            <Lock className="h-6 w-6 text-muted-foreground" />
                        </div>
                        <CardTitle>Análisis Protegido</CardTitle>
                        <DialogDescription>Introduce la contraseña para acceder a este análisis.</DialogDescription>
                    </CardHeader>
                    <CardContent>
                        <form onSubmit={handlePasswordSubmit} className="space-y-4">
                            <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Contraseña" required />
                            <Button type="submit" className="w-full">Acceder</Button>
                        </form>
                    </CardContent>
                </Card>
            </div>
        );
    }

    if (!analysis) return null;

    const resultPayload = analysis.analysis.result_payload || {};
    const fullData = analysis.analysis.full_data || {};
    const summary = analysis.analysis.summary || '';
    const title = analysis.analysis.title || 'Análisis';
    const type = analysis.analysis.type || 'analysis';
    const createdAt = analysis.analysis.created_at || '';
    const sources = resultPayload.sources || [];
    const colorScheme = getAnalysisColorScheme(type);

    return (
        <div className="min-h-screen bg-background">
            <div className="max-w-4xl mx-auto p-6">
                <div className="mb-8">
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
                        <div>
                            <h1 className="text-3xl font-bold tracking-tight">{title}</h1>
                            <p className="text-muted-foreground mt-2">Compartido desde Kognito AI</p>
                        </div>
                        <div className="flex items-center gap-2">
                            <Button variant="outline" size="sm" onClick={copyLink}>
                                {copied ? <Check className="h-4 w-4 mr-2" /> : <Copy className="h-4 w-4 mr-2" />}
                                {copied ? 'Copiado' : 'Copiar Enlace'}
                            </Button>
                        </div>
                    </div>
                    <div className="flex flex-wrap gap-3 text-sm text-muted-foreground">
                        <span className={cn("px-3 py-1 rounded-full capitalize", getAnalysisTypeBadgeColor(type))}>
                            {getAnalysisTypeLabel(type)}
                        </span>
                        {createdAt && <span>Creado: {formatDate(createdAt)}</span>}
                    </div>
                </div>

                <ScrollArea className="h-[calc(100vh-200px)]">
                    <div className="space-y-6 pr-4">
                        {/* Check if it's deep_research or gap_development - use special format */}
                        {isDeepResearchOrGapDevelopment(type) ? (
                            <DeepResearchContent
                                resultPayload={resultPayload}
                                fullData={fullData}
                                type={type}
                                summary={summary}
                            />
                        ) : type === 'code' ? (
                            <CodeAnalysis 
                                analysis={resultPayload as CodeAnalysisResultFrontend}
                                codeColors={colorScheme}
                            />
                        ) : (
                            <>
                                {/* Summary Card */}
                                {summary && (
                                    <Card className={cn(colorScheme.cardBg)}>
                                        <CardHeader>
                                            <CardTitle className={cn(colorScheme.cardTitle)}>Resumen</CardTitle>
                                        </CardHeader>
                                        <CardContent>
                                            <div className="prose prose-sm dark:prose-invert max-w-none">
                                                <ReactMarkdown remarkPlugins={[remarkGfm]}>{summary}</ReactMarkdown>
                                            </div>
                                        </CardContent>
                                    </Card>
                                )}

                                {/* Render full_data content */}
                                {Object.keys(fullData).length > 0 && (
                                    <Card className={cn(colorScheme.cardBg)}>
                                        <CardHeader>
                                            <CardTitle className={cn(colorScheme.cardTitle)}>Detalles del Análisis</CardTitle>
                                        </CardHeader>
                                        <CardContent>
                                            {Object.entries(fullData).map(([key, value]) => {
                                                if (['title', 'summary', 'executive_summary', 'collection_summary', 'semantic_summary', 'sources'].includes(key)) return null;
                                                if (value === null || value === undefined) return null;
                                                if (typeof value === 'object' && Object.keys(value as object).length === 0) return null;

                                                return (
                                                    <div key={key} className="mb-4 last:mb-0">
                                                        <h4 className={cn("font-semibold mb-2 capitalize text-lg", colorScheme.cardTitle)}>
                                                            {key.replace(/_/g, ' ')}
                                                        </h4>
                                                        {renderRichContent(value, key, colorScheme)}
                                                    </div>
                                                );
                                            })}
                                        </CardContent>
                                    </Card>
                                )}

                                {/* Render result_payload content (excluding summary and sources) */}
                                {Object.keys(resultPayload).length > 0 && (
                                    <Card className={cn(colorScheme.cardBg)}>
                                        <CardHeader>
                                            <CardTitle className={cn(colorScheme.cardTitle)}>Resultados Adicionales</CardTitle>
                                        </CardHeader>
                                        <CardContent>
                                            {Object.entries(resultPayload).map(([key, value]) => {
                                                if (['title', 'summary', 'executive_summary', 'collection_summary', 'semantic_summary', 'sources'].includes(key)) return null;
                                                if (value === null || value === undefined) return null;
                                                if (typeof value === 'object' && Object.keys(value as object).length === 0) return null;

                                                return (
                                                    <div key={key} className="mb-4 last:mb-0">
                                                        <h4 className={cn("font-semibold mb-2 capitalize text-lg", colorScheme.cardTitle)}>
                                                            {key.replace(/_/g, ' ')}
                                                        </h4>
                                                        {renderRichContent(value, key, colorScheme)}
                                                    </div>
                                                );
                                            })}
                                        </CardContent>
                                    </Card>
                                )}

                                {/* Sources Tab */}
                                {sources && sources.length > 0 && (
                                    <Card>
                                        <CardHeader>
                                            <CardTitle>Fuentes</CardTitle>
                                        </CardHeader>
                                        <CardContent>
                                            <SourcesTab sources={sources} />
                                        </CardContent>
                                    </Card>
                                )}
                            </>
                        )}
                    </div>
                </ScrollArea>
            </div>

            {/* Knowledge Gaps / Questions Slider Dialog */}
            <QuestionSliderDialog
                isOpen={isQuestionsDialogOpen}
                onOpenChange={setIsQuestionsDialogOpen}
                questions={sliderQuestions}
                title={sliderTitle}
                hideDevelopButtons={true}
            />

            {/* Concept Detail Dialog */}
            <ConceptDetailDialog
                isOpen={isConceptDialogOpen}
                onOpenChange={setIsConceptDialogOpen}
                concept={selectedConcept}
            />

            {/* Theme Quotes Dialog */}
            <ThemeQuotesDialog
                isOpen={isThemeQuotesDialogOpen}
                onOpenChange={setIsThemeQuotesDialogOpen}
                theme={selectedThemeForQuotes}
            />
        </div>
    );
}
