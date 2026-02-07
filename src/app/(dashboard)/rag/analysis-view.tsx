'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useState, useCallback, useRef, useMemo } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
    Loader2, Info, Filter, ChevronDown, Search, BarChart3, FileText, FolderKanban,
    Lightbulb, Code, Calendar, Eye, Plus, TrendingUp, AlertTriangle, HelpCircle,
    CheckCircle, Clock, XCircle, ArrowLeft, StickyNote, TrendingDown, Users,
    Activity, Target, PieChart, Sparkles, RefreshCcw, Zap, Network
} from 'lucide-react';
import { toast } from 'sonner';
import apiClient from '@/lib/api';
import {
    Analysis, AnalysisType, Insight, Question, AnalysisResponse,
    DashboardInsightsResponse, AnalysisStats, KeyTopic
} from '@/lib/models';
import { Badge } from '@/components/ui/badge';
import { Bar, BarChart, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import {
    DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger
} from '@/components/ui/dropdown-menu';
import {
    Tooltip as UITooltip, TooltipContent, TooltipProvider, TooltipTrigger
} from '@/components/ui/tooltip';
import {
    Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription as SheetDescriptionComp
} from '@/components/ui/sheet';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription
} from '@/components/ui/dialog';
import InsightGeneratorForm from '@/components/InsightGeneratorForm';
import { QuestionSlider } from '@/components/QuestionSlider';
import { KeyTopicSlider } from '@/components/KeyTopicSlider';
import { KeyTopicDetailDialog } from '@/components/KeyTopicDetailDialog';
import { AnalysisDetailDialog } from '@/app/(dashboard)/analysis/analysis-detail-dialog';
import { DeepResearchDetailDialog } from '@/app/(dashboard)/analysis/deep-research-detail-dialog';
import { InlineMarkdownRenderer } from '@/components/InlineMarkdownRenderer';

const getAnalysisIcon = (type: string) => {
    switch (type) {
        case 'document':
            return <FileText className="h-5 w-5 text-blue-500" />;
        case 'collection':
            return <FolderKanban className="h-5 w-5 text-green-500" />;
        case 'insight':
        case 'proactive_insight_manual':
            return <Lightbulb className="h-5 w-5 text-yellow-500" />;
        case 'code':
            return <Code className="h-5 w-5 text-orange-500" />;
        case 'semantic':
        case 'semantic_summary':
            return <BarChart3 className="h-5 w-5 text-indigo-500" />;
        case 'note_analysis':
            return <StickyNote className="h-5 w-5 text-amber-500" />;
        case 'note_collection_analysis':
            return <FolderKanban className="h-5 w-5 text-orange-500" />;
        case 'gap_development':
            return <Zap className="h-5 w-5 text-fuchsia-500" />;
        case 'deep_research':
            return <Search className="h-5 w-5 text-blue-500" />;
        case 'comprehensive_web_analysis':
            return <Network className="h-5 w-5 text-cyan-500" />;
        default:
            return <FileText className="h-5 w-5 text-gray-500" />;
    }
};

const getAnalysisTypeLabel = (type: string) => {
    switch (type) {
        case 'document': return 'Documento';
        case 'collection': return 'Colección';
        case 'insight':
        case 'proactive_insight_manual': return 'Insight';
        case 'code': return 'Código';
        case 'semantic': return 'Semántico';
        case 'semantic_summary': return 'Resumen Semántico';
        case 'custom': return 'Personalizado';
        case 'knowledge_graph': return 'Grafo de Conocimiento';
        case 'note_analysis': return 'Nota';
        case 'note_collection_analysis': return 'Colección de Notas';
        case 'gap_development': return 'Desarrollo de Brecha';
        case 'deep_research': return 'Investigación Profunda';
        case 'comprehensive_web_analysis': return 'Análisis Web Integral';
        default: return 'Análisis';
    }
};

const getAnalysisTypeBadgeColor = (type: string) => {
    switch (type) {
        case 'document': return 'bg-blue-100 text-blue-800 border-blue-200';
        case 'collection': return 'bg-green-100 text-green-800 border-green-200';
        case 'insight':
        case 'proactive_insight_manual': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
        case 'code': return 'bg-orange-100 text-orange-800 border-orange-200';
        case 'semantic':
        case 'semantic_summary': return 'bg-indigo-100 text-indigo-800 border-indigo-200';
        case 'note_analysis': return 'bg-amber-100 text-amber-800 border-amber-200';
        case 'note_collection_analysis': return 'bg-orange-100 text-orange-800 border-orange-200';
        case 'gap_development': return 'bg-fuchsia-100 text-fuchsia-800 border-fuchsia-200';
        case 'deep_research': return 'bg-blue-100 text-blue-800 border-blue-200';
        case 'comprehensive_web_analysis': return 'bg-cyan-100 text-cyan-800 border-cyan-200';
        default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
};

export function AnalysisView() {
    const router = useRouter();
    const { user, token } = useAuth();

    const [analyses, setAnalyses] = useState<Analysis[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const [topicKeywords, setTopicKeywords] = useState<string>('');

    const [debouncedSearchQuery, setDebouncedSearchQuery] = useState('');
    const [debouncedTopicKeywords, setDebouncedTopicKeywords] = useState('');
    const searchTimeoutRef = useRef<number | null>(null);
    const keywordsTimeoutRef = useRef<number | null>(null);
    const [selectedType, setSelectedType] = useState<string | null>(null);
    const [selectedAnalysis, setSelectedAnalysis] = useState<Analysis | null>(null);
    const [showInsightFormModal, setShowInsightFormModal] = useState(false);
    const [dashboardData, setDashboardData] = useState<DashboardInsightsResponse | null>(null);
    const [isLoadingDashboard, setIsLoadingDashboard] = useState(true);
    const [isKeyTopicDetailDialogOpen, setIsKeyTopicDetailDialogOpen] = useState(false);
    const [selectedKeyTopic, setSelectedKeyTopic] = useState<KeyTopic | null>(null);
    const [isInfoSheetOpen, setIsInfoSheetOpen] = useState(false);
    const offsetRef = useRef(0);
    const [hasMore, setHasMore] = useState(false);
    const [isLoadingMore, setIsLoadingMore] = useState(false);
    const [lastUpdateTime, setLastUpdateTime] = useState<Date>(new Date());

    const fetchAnalyses = useCallback(async (reset = false, searchQuery?: string, keywords?: string) => {
        if (reset) {
            setIsLoading(true);
            offsetRef.current = 0;
            setAnalyses([]);
        } else {
            setIsLoadingMore(true);
        }

        try {
            const currentOffset = offsetRef.current;
            const keywordsArray = keywords ? keywords.split(',').map(keyword => keyword.trim()) : undefined;

            const response = await apiClient.post('/api/get-all-analysis', {
                limit: 20,
                offset: currentOffset,
                analysis_type: selectedType,
                search_query: searchQuery || undefined,
                topic_keywords: keywordsArray
            });

            const data: AnalysisResponse = response.data;
            if (reset) {
                setAnalyses(data.analysis);
            } else {
                setAnalyses(prev => [...prev, ...data.analysis]);
            }

            setHasMore(!!data.has_more && data.analysis.length > 0);
            offsetRef.current = currentOffset + data.analysis.length;
        } catch (error) {
            toast.error('Error al cargar los análisis');
            setHasMore(false);
        } finally {
            setIsLoading(false);
            setIsLoadingMore(false);
        }
    }, [selectedType]);

    const fetchDashboardData = useCallback(async () => {
        if (!user?.account_id) {
            setIsLoadingDashboard(false);
            return;
        }

        setIsLoadingDashboard(true);
        try {
            const response = await apiClient.post<DashboardInsightsResponse>('/api/dashboard-insights', {});
            setDashboardData(response.data);
            setLastUpdateTime(new Date());
        } catch (error) {
            toast.error('Error al cargar los datos del dashboard');
        } finally {
            setIsLoadingDashboard(false);
        }
    }, [user?.account_id]);

    const handleRefreshDashboard = useCallback(() => {
        fetchDashboardData();
        toast.success('Datos del dashboard actualizados');
    }, [fetchDashboardData]);

    const updateSearchQuery = useCallback((query: string) => {
        setSearchQuery(query);
        if (searchTimeoutRef.current) clearTimeout(searchTimeoutRef.current);
        searchTimeoutRef.current = setTimeout(() => {
            setDebouncedSearchQuery(query);
            if (user && token) fetchAnalyses(true, query, debouncedTopicKeywords);
        }, 500) as unknown as number;
    }, [user, token, fetchAnalyses, debouncedTopicKeywords]);

    const updateTopicKeywords = useCallback((keywords: string) => {
        setTopicKeywords(keywords);
        if (keywordsTimeoutRef.current) clearTimeout(keywordsTimeoutRef.current);
        keywordsTimeoutRef.current = setTimeout(() => {
            setDebouncedTopicKeywords(keywords);
            if (user && token) fetchAnalyses(true, debouncedSearchQuery, keywords);
        }, 500) as unknown as number;
    }, [user, token, fetchAnalyses, debouncedSearchQuery]);

    useEffect(() => {
        if (user && token) {
            fetchAnalyses(true, debouncedSearchQuery, debouncedTopicKeywords);
            fetchDashboardData();
        }
    }, [user, token, selectedType]);

    useEffect(() => {
        if (user && token) fetchDashboardData();
    }, [user, token, fetchDashboardData]);

    useEffect(() => {
        return () => {
            if (searchTimeoutRef.current) clearTimeout(searchTimeoutRef.current);
            if (keywordsTimeoutRef.current) clearTimeout(keywordsTimeoutRef.current);
        };
    }, []);

    const handleSearch = (e: React.FormEvent) => {
        e.preventDefault();
        fetchAnalyses(true, debouncedSearchQuery, debouncedTopicKeywords);
    };

    const handleViewDetails = (analysis: Analysis) => {
        setSelectedAnalysis(analysis);
    };

    const handleLoadMore = () => {
        if (!isLoadingMore && hasMore) {
            fetchAnalyses(false, debouncedSearchQuery, debouncedTopicKeywords);
        }
    };

    const handleAnalysisDeleted = useCallback((deletedAnalysisId: string) => {
        setAnalyses(prev => prev.filter(analysis => analysis.id !== deletedAnalysisId));
        toast.success('Análisis eliminado correctamente');
    }, []);

    const formatDate = (dateString: string) => {
        return new Date(dateString).toLocaleDateString('es-ES', {
            year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
        });
    };

    const getCleanSummary = (analysis: Analysis) => {
        if (!analysis.summary) return '';

        const summaryText = analysis.summary.trim();

        // Si parece un objeto (JSON o Diccionario de Python)
        if (summaryText.startsWith('{') || summaryText.startsWith('[')) {
            try {
                // 1. Intentar parseo JSON estándar
                const parsed = JSON.parse(summaryText);
                return extractFromObject(parsed);
            } catch (e) {
                // 2. Si falla, intentar extraer campos clave con Regex (más seguro para strings de Python)
                // Buscar "final_report": "..." o 'final_report': '...'
                const finalReportMatch = summaryText.match(/['"]final_report['"]\s*:\s*['"]([\s\S]*?)['"](?=\s*,\s*['"]|\s*})/);
                if (finalReportMatch && finalReportMatch[1]) {
                    return cleanExtractedText(finalReportMatch[1]);
                }

                const summaryMatch = summaryText.match(/['"]summary['"]\s*:\s*['"]([\s\S]*?)['"](?=\s*,\s*['"]|\s*})/);
                if (summaryMatch && summaryMatch[1]) {
                    return cleanExtractedText(summaryMatch[1]);
                }

                const errorMatch = summaryText.match(/['"]error['"]\s*:\s*['"]([\s\S]*?)['"](?=\s*,\s*['"]|\s*})/);
                if (errorMatch && errorMatch[1]) {
                    return cleanExtractedText(errorMatch[1]);
                }

                // 3. Último recurso: Intento de conversión agresiva a JSON
                try {
                    const fixedJson = summaryText
                        .replace(/'/g, '"')
                        .replace(/None/g, 'null')
                        .replace(/True/g, 'true')
                        .replace(/False/g, 'false');
                    const parsed = JSON.parse(fixedJson);
                    return extractFromObject(parsed);
                } catch (e2) {
                    return summaryText; // Devolver original si nada funciona
                }
            }
        }

        return summaryText;
    };

    const extractFromObject = (obj: any) => {
        if (obj.final_report) return obj.final_report;
        if (obj.error) return obj.error;
        if (obj.summary) return obj.summary;

        const values = Object.values(obj);
        const longText = values.find(v => typeof v === 'string' && v.length > 10);
        return longText ? (longText as string) : JSON.stringify(obj);
    };

    const cleanExtractedText = (text: string) => {
        return text
            .replace(/\\n/g, '\n')
            .replace(/\\'/g, "'")
            .replace(/\\"/g, '"')
            .trim();
    };

    const analysisTypes = [
        { value: null, label: 'Todos los tipos' },
        { value: 'document', label: 'Documentos' },
        { value: 'collection', label: 'Colecciones' },
        { value: 'insight', label: 'Insights Proactivos' },
        { value: 'proactive_insight_manual', label: 'Insights Manuales' },
        { value: 'note_analysis', label: 'Notas' },
        { value: 'note_collection_analysis', label: 'Colecciones de Notas' },
        { value: 'code', label: 'Código' },
        { value: 'semantic', label: 'Semántico' },
        { value: 'semantic_summary', label: 'Resumen Semántico' },
        { value: 'gap_development', label: 'Desarrollo de Brecha' },
        { value: 'deep_research', label: 'Investigación Profunda' },
        { value: 'comprehensive_web_analysis', label: 'Análisis Web Integral' }
    ];

    const chartData = useMemo(() => {
        if (!dashboardData?.analysis_stats_by_type) return [];
        return dashboardData.analysis_stats_by_type.map(stat => ({
            name: getAnalysisTypeLabel(stat.type),
            Completados: stat.completed,
            Fallidos: stat.failed,
        }));
    }, [dashboardData]);

    const systemStats = useMemo(() => {
        if (!dashboardData) return null;
        const totalProcessed = dashboardData.analysis_stats_by_type?.reduce((acc, stat) => acc + stat.completed + stat.failed, 0) || 0;
        const successRate = totalProcessed > 0 ? (dashboardData.analysis_stats_by_type?.reduce((acc, stat) => acc + stat.completed, 0) || 0) / totalProcessed * 100 : 0;
        return {
            totalProcessed,
            successRate: Math.round(successRate),
            activeInsights: dashboardData.total_proactive_insights || 0,
            lastUpdate: lastUpdateTime
        };
    }, [dashboardData, lastUpdateTime]);

    if (isLoading || isLoadingDashboard) {
        return (
            <div className="flex py-20 w-full items-center justify-center">
                <div className="flex flex-col items-center gap-2">
                    <Loader2 className="h-8 w-8 animate-spin text-primary" />
                    <p className="text-muted-foreground">Cargando centro de análisis...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-10 animate-in fade-in duration-700">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
                <div className="space-y-1">
                    <div className="flex items-center gap-3">
                        <h2 className="text-4xl font-black tracking-tighter bg-gradient-to-r from-foreground to-foreground/70 bg-clip-text text-transparent">Centro de Análisis</h2>
                        <Button variant="ghost" size="icon" className="h-10 w-10 rounded-2xl bg-primary/5 text-primary hover:bg-primary/10 transition-all" onClick={() => setIsInfoSheetOpen(true)}>
                            <Info className="h-5 w-5" />
                        </Button>
                    </div>
                    <p className="text-muted-foreground font-medium">Explora y gestiona la inteligencia generada por Kognito AI.</p>
                </div>
                <div className="flex gap-3">
                    <Button variant="outline" onClick={handleRefreshDashboard} disabled={isLoadingDashboard} className="h-12 px-6 rounded-2xl bg-card/40 backdrop-blur-md border-border/40 hover:bg-primary/5 transition-all gap-2 font-bold">
                        <RefreshCcw className={`h-4 w-4 ${isLoadingDashboard ? 'animate-spin' : ''}`} />
                        Actualizar
                    </Button>
                    <Button onClick={() => setShowInsightFormModal(true)} className="h-12 px-6 rounded-2xl bg-primary shadow-lg shadow-primary/20 hover:shadow-primary/40 transition-all gap-2 font-bold">
                        <Plus className="h-5 w-5" />
                        Generar Insight
                    </Button>
                </div>
            </div>

            {dashboardData && systemStats && (
                <>
                    <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
                        <Card className="group relative overflow-hidden border-border/40 bg-card/40 backdrop-blur-xl rounded-[2rem] transition-all duration-500 hover:shadow-2xl hover:shadow-blue-500/10 hover:-translate-y-1">
                            <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                            <CardHeader className="flex flex-row items-center justify-between pb-2 relative z-10">
                                <CardTitle className="text-xs font-black uppercase tracking-widest text-muted-foreground/70">Total Análisis</CardTitle>
                                <div className="p-2.5 rounded-xl bg-blue-500/10 text-blue-500 shadow-lg shadow-blue-500/20 group-hover:scale-110 transition-transform duration-500">
                                    <BarChart3 className="h-5 w-5" />
                                </div>
                            </CardHeader>
                            <CardContent className="relative z-10">
                                <div className="text-4xl font-black tracking-tighter bg-gradient-to-br from-blue-600 to-blue-400 bg-clip-text text-transparent">{dashboardData.total_analysis_tasks}</div>
                                <p className="text-[10px] font-bold text-muted-foreground/60 uppercase tracking-wider mt-1">{dashboardData.total_proactive_insights} insights proactivos</p>
                            </CardContent>
                        </Card>

                        <Card className="group relative overflow-hidden border-border/40 bg-card/40 backdrop-blur-xl rounded-[2rem] transition-all duration-500 hover:shadow-2xl hover:shadow-green-500/10 hover:-translate-y-1">
                            <div className="absolute inset-0 bg-gradient-to-br from-green-500/5 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                            <CardHeader className="flex flex-row items-center justify-between pb-2 relative z-10">
                                <CardTitle className="text-xs font-black uppercase tracking-widest text-muted-foreground/70">Tasa de Éxito</CardTitle>
                                <div className="p-2.5 rounded-xl bg-green-500/10 text-green-500 shadow-lg shadow-green-500/20 group-hover:scale-110 transition-transform duration-500">
                                    <Activity className="h-5 w-5" />
                                </div>
                            </CardHeader>
                            <CardContent className="relative z-10">
                                <div className="text-4xl font-black tracking-tighter bg-gradient-to-br from-green-600 to-green-400 bg-clip-text text-transparent">{systemStats.successRate}%</div>
                                <p className="text-[10px] font-bold text-muted-foreground/60 uppercase tracking-wider mt-1">Sistema operativo</p>
                            </CardContent>
                        </Card>

                        <Card className="group relative overflow-hidden border-border/40 bg-card/40 backdrop-blur-xl rounded-[2rem] transition-all duration-500 hover:shadow-2xl hover:shadow-orange-500/10 hover:-translate-y-1">
                            <div className="absolute inset-0 bg-gradient-to-br from-orange-500/5 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                            <CardHeader className="flex flex-row items-center justify-between pb-2 relative z-10">
                                <CardTitle className="text-xs font-black uppercase tracking-widest text-muted-foreground/70">Procesados</CardTitle>
                                <div className="p-2.5 rounded-xl bg-orange-500/10 text-orange-500 shadow-lg shadow-orange-500/20 group-hover:scale-110 transition-transform duration-500">
                                    <FileText className="h-5 w-5" />
                                </div>
                            </CardHeader>
                            <CardContent className="relative z-10">
                                <div className="text-4xl font-black tracking-tighter bg-gradient-to-br from-orange-600 to-orange-400 bg-clip-text text-transparent">{systemStats.totalProcessed}</div>
                                <p className="text-[10px] font-bold text-muted-foreground/60 uppercase tracking-wider mt-1">Documentos y tareas</p>
                            </CardContent>
                        </Card>

                        <Card className="group relative overflow-hidden border-border/40 bg-card/40 backdrop-blur-xl rounded-[2rem] transition-all duration-500 hover:shadow-2xl hover:shadow-yellow-500/10 hover:-translate-y-1">
                            <div className="absolute inset-0 bg-gradient-to-br from-yellow-500/5 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                            <CardHeader className="flex flex-row items-center justify-between pb-2 relative z-10">
                                <CardTitle className="text-xs font-black uppercase tracking-widest text-muted-foreground/70">Insights Activos</CardTitle>
                                <div className="p-2.5 rounded-xl bg-yellow-500/10 text-yellow-500 shadow-lg shadow-yellow-500/20 group-hover:scale-110 transition-transform duration-500">
                                    <Sparkles className="h-5 w-5" />
                                </div>
                            </CardHeader>
                            <CardContent className="relative z-10">
                                <div className="text-4xl font-black tracking-tighter bg-gradient-to-br from-yellow-600 to-yellow-400 bg-clip-text text-transparent">{systemStats.activeInsights}</div>
                                <p className="text-[10px] font-bold text-muted-foreground/60 uppercase tracking-wider mt-1">Generados por KAI</p>
                            </CardContent>
                        </Card>
                    </div>

                    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                        <QuestionSlider
                            title="Brechas de Conocimiento"
                            questions={dashboardData.emergent_knowledge_gaps || []}
                            icon={<AlertTriangle className="h-5 w-5 text-amber-500" />}
                            emptyMessage="No se detectaron brechas recientes."
                            autoSlide={true}
                            slideInterval={5000}
                            showCounter={false}
                            onDevelopClick={() => { }}
                        />

                        <KeyTopicSlider
                            title="Temas Clave"
                            keyTopics={dashboardData.key_topics || []}
                            icon={<TrendingUp className="h-5 w-5 text-blue-500" />}
                            emptyMessage="No hay temas clave recientes."
                            autoSlide={true}
                            slideInterval={7000}
                            onKeyTopicClick={(topic) => {
                                setSelectedKeyTopic(topic);
                                setIsKeyTopicDetailDialogOpen(true);
                            }}
                        />

                        <QuestionSlider
                            title="Preguntas para Explorar"
                            questions={dashboardData.exploration_questions || []}
                            icon={<HelpCircle className="h-5 w-5 text-indigo-500" />}
                            emptyMessage="No hay preguntas para explorar recientes."
                            autoSlide={true}
                            slideInterval={6000}
                            onDevelopClick={() => { }}
                        />
                    </div>

                    <Card className="border-none shadow-md">
                        <CardHeader>
                            <CardTitle className="text-lg">Distribución de Análisis</CardTitle>
                            <CardDescription>Actividad por categoría y estado.</CardDescription>
                        </CardHeader>
                        <CardContent>
                            <div className="h-[300px] w-full">
                                <ResponsiveContainer width="100%" height="100%">
                                    <BarChart data={chartData}>
                                        <XAxis dataKey="name" fontSize={12} tickLine={false} axisLine={false} />
                                        <YAxis fontSize={12} tickLine={false} axisLine={false} />
                                        <Tooltip
                                            contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1)' }}
                                        />
                                        <Legend />
                                        <Bar dataKey="Completados" stackId="a" fill="hsl(var(--primary))" radius={[0, 0, 0, 0]} />
                                        <Bar dataKey="Fallidos" stackId="a" fill="#fa8072" radius={[4, 4, 0, 0]} />
                                    </BarChart>
                                </ResponsiveContainer>
                            </div>
                        </CardContent>
                    </Card>
                </>
            )}

            <div className="space-y-6">
                <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center">
                    <form onSubmit={handleSearch} className="flex gap-3 flex-1 w-full">
                        <div className="relative flex-1 group">
                            <div className="absolute -inset-0.5 bg-gradient-to-r from-primary/20 to-secondary/20 rounded-2xl blur opacity-0 group-focus-within:opacity-100 transition duration-500" />
                            <div className="relative">
                                <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground group-focus-within:text-primary transition-colors" />
                                <Input
                                    placeholder="Buscar en la inteligencia de KAI..."
                                    value={searchQuery}
                                    onChange={(e) => updateSearchQuery(e.target.value)}
                                    className="pl-12 h-12 bg-card/40 backdrop-blur-md border-border/40 rounded-2xl focus-visible:ring-primary/20 transition-all"
                                />
                            </div>
                        </div>
                        <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                                <Button variant="outline" className="gap-2 h-12 px-6 bg-card/40 backdrop-blur-md border-border/40 rounded-2xl hover:bg-primary/5 transition-all">
                                    <Filter className="h-4 w-4 text-primary" />
                                    <span className="hidden sm:inline font-semibold">{selectedType ? getAnalysisTypeLabel(selectedType) : 'Filtrar por Tipo'}</span>
                                    <ChevronDown className="h-4 w-4 opacity-50" />
                                </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end" className="w-56 bg-card/95 backdrop-blur-xl border-border/40 rounded-2xl p-2">
                                {analysisTypes.map((type) => (
                                    <DropdownMenuItem
                                        key={type.value || 'all'}
                                        onClick={() => setSelectedType(type.value)}
                                        className="rounded-xl focus:bg-primary/10 focus:text-primary cursor-pointer py-2.5"
                                    >
                                        {type.label}
                                    </DropdownMenuItem>
                                ))}
                            </DropdownMenuContent>
                        </DropdownMenu>
                    </form>
                </div>

                {analyses.length === 0 ? (
                    <div className="text-center py-24 border-2 border-dashed border-border/40 rounded-[2rem] bg-card/20 backdrop-blur-sm">
                        <div className="bg-primary/10 w-20 h-20 rounded-full flex items-center justify-center mx-auto mb-6">
                            <BarChart3 className="h-10 w-10 text-primary/40" />
                        </div>
                        <h3 className="text-xl font-bold tracking-tight">No se encontraron análisis</h3>
                        <p className="text-muted-foreground max-w-xs mx-auto mt-2">Intenta ajustar tus filtros o realiza una nueva búsqueda para explorar tu conocimiento.</p>
                    </div>
                ) : (
                    <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                        <AnimatePresence mode="popLayout">
                            {analyses.map((analysis, index) => (
                                <motion.div
                                    key={analysis.id}
                                    layout
                                    initial={{ opacity: 0, scale: 0.9 }}
                                    animate={{ opacity: 1, scale: 1 }}
                                    exit={{ opacity: 0, scale: 0.9 }}
                                    transition={{ duration: 0.3, delay: index * 0.05 }}
                                >
                                    <Card
                                        className="group relative cursor-pointer overflow-hidden border-border/40 bg-card/40 backdrop-blur-xl hover:bg-card/60 transition-all duration-500 rounded-[2rem] flex flex-col h-full shadow-sm hover:shadow-2xl hover:shadow-primary/5 hover:-translate-y-1"
                                        onClick={() => handleViewDetails(analysis)}
                                    >
                                        {/* Efecto de resplandor en el hover */}
                                        <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />

                                        <CardHeader className="pb-3 relative z-10">
                                            <div className="flex items-center justify-between mb-3">
                                                <div className="p-3 rounded-2xl bg-background/50 border border-border/40 shadow-inner group-hover:scale-110 transition-transform duration-500">
                                                    {getAnalysisIcon(analysis.type)}
                                                </div>
                                                <Badge variant="outline" className={`text-[10px] font-bold uppercase tracking-wider px-3 py-1 rounded-full border-none ${getAnalysisTypeBadgeColor(analysis.type)}`}>
                                                    {getAnalysisTypeLabel(analysis.type)}
                                                </Badge>
                                            </div>
                                            <CardTitle className="text-lg font-bold line-clamp-2 group-hover:text-primary transition-colors leading-tight tracking-tight">
                                                {analysis.title}
                                            </CardTitle>
                                        </CardHeader>
                                        <CardContent className="flex-grow relative z-10">
                                            <div className="text-xs text-muted-foreground/80 line-clamp-3 leading-relaxed font-medium">
                                                <InlineMarkdownRenderer content={getCleanSummary(analysis)} />
                                            </div>
                                            <div className="mt-6 pt-4 border-t border-border/20 flex items-center justify-between text-[10px] font-bold text-muted-foreground/60 uppercase tracking-widest">
                                                <div className="flex items-center gap-2">
                                                    <div className="w-1.5 h-1.5 rounded-full bg-primary/40" />
                                                    {formatDate(analysis.created_at || new Date().toISOString())}
                                                </div>
                                                <div className="flex items-center gap-1 group-hover:text-primary transition-colors">
                                                    <span>Detalles</span>
                                                    <Eye className="h-3.5 w-3.5" />
                                                </div>
                                            </div>
                                        </CardContent>
                                    </Card>
                                </motion.div>
                            ))}
                        </AnimatePresence>
                    </div>
                )}

                {hasMore && (
                    <div className="flex justify-center pt-4">
                        <Button onClick={handleLoadMore} disabled={isLoadingMore} variant="ghost" size="sm">
                            {isLoadingMore ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                            Cargar más análisis
                        </Button>
                    </div>
                )}
            </div>

            {/* Diálogos y Modales */}
            {selectedAnalysis && selectedAnalysis.type !== 'deep_research' && (
                <AnalysisDetailDialog
                    analysis={selectedAnalysis}
                    isOpen={!!selectedAnalysis}
                    onOpenChange={(open) => !open && setSelectedAnalysis(null)}
                    onAnalysisDeleted={handleAnalysisDeleted}
                />
            )}

            {selectedAnalysis && selectedAnalysis.type === 'deep_research' && (
                <DeepResearchDetailDialog
                    analysis={selectedAnalysis}
                    isOpen={!!selectedAnalysis}
                    onOpenChange={(open) => !open && setSelectedAnalysis(null)}
                />
            )}

            <Dialog open={showInsightFormModal} onOpenChange={setShowInsightFormModal}>
                <DialogContent className="sm:max-w-[425px]">
                    <DialogHeader>
                        <DialogTitle>Generar Insight Manual</DialogTitle>
                        <DialogDescription>Inicia un análisis específico sobre tus datos.</DialogDescription>
                    </DialogHeader>
                    {user?.account_id && <InsightGeneratorForm accountId={user.account_id} />}
                </DialogContent>
            </Dialog>

            <KeyTopicDetailDialog
                isOpen={isKeyTopicDetailDialogOpen}
                onOpenChange={setIsKeyTopicDetailDialogOpen}
                keyTopic={selectedKeyTopic}
            />

            <Sheet open={isInfoSheetOpen} onOpenChange={setIsInfoSheetOpen}>
                <SheetContent side="right" className="w-full sm:max-w-md">
                    <SheetHeader>
                        <SheetTitle>Centro de Análisis</SheetTitle>
                        <SheetDescriptionComp>
                            Gestiona y visualiza todos los análisis generados por Kognito AI.
                        </SheetDescriptionComp>
                    </SheetHeader>
                    <div className="py-6 space-y-4 text-sm">
                        <p>Este panel centraliza toda la inteligencia extraída de tus documentos y colecciones.</p>
                        <div className="space-y-2">
                            <h4 className="font-bold">Funciones clave:</h4>
                            <ul className="list-disc pl-5 space-y-1 text-muted-foreground">
                                <li>Historial completo de análisis realizados.</li>
                                <li>Detección automática de brechas de conocimiento.</li>
                                <li>Identificación de temas clave recurrentes.</li>
                                <li>Generación manual de insights proactivos.</li>
                            </ul>
                        </div>
                    </div>
                </SheetContent>
            </Sheet>
        </div>
    );
}
