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

const getAnalysisIcon = (type: string) => {
    switch (type) {
        case 'document':
            return <FileText className="h-5 w-5 text-blue-500" />;
        case 'collection':
            return <FolderKanban className="h-5 w-5 text-green-500" />;
        case 'insight':
        case 'proactive_insight_manual':
        case 'neural_insight':
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
        case 'neural_insight': return 'Neural Insight';
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
        case 'proactive_insight_manual':
        case 'neural_insight': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
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

export function AnalysisResults() {
    const router = useRouter();
    const { user, token } = useAuth();

    const [analyses, setAnalyses] = useState<Analysis[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const [topicKeywords, setTopicKeywords] = useState<string>('');

    const [debouncedSearchQuery, setDebouncedSearchQuery] = useState('');
    const [debouncedTopicKeywords, setDebouncedTopicKeywords] = useState('');
    const searchTimeoutRef = useRef<NodeJS.Timeout | null>(null);
    const keywordsTimeoutRef = useRef<NodeJS.Timeout | null>(null);
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
        }, 500);
    }, [user, token, fetchAnalyses, debouncedTopicKeywords]);

    const updateTopicKeywords = useCallback((keywords: string) => {
        setTopicKeywords(keywords);
        if (keywordsTimeoutRef.current) clearTimeout(keywordsTimeoutRef.current);
        keywordsTimeoutRef.current = setTimeout(() => {
            setDebouncedTopicKeywords(keywords);
            if (user && token) fetchAnalyses(true, debouncedSearchQuery, keywords);
        }, 500);
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

    const analysisTypes = [
        { value: null, label: 'Todos los tipos' },
        { value: 'document', label: 'Documentos' },
        { value: 'collection', label: 'Colecciones' },
        { value: 'insight', label: 'Insights Proactivos' },
        { value: 'proactive_insight_manual', label: 'Insights Manuales' },
        { value: 'neural_insight', label: 'Neural Insights' },
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
        <div className="space-y-8 animate-in fade-in duration-500">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div className="flex items-center gap-2">
                    <h2 className="text-xl sm:text-3xl font-bold tracking-tight truncate">Centro de Análisis</h2>
                    <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground flex-shrink-0" onClick={() => setIsInfoSheetOpen(true)}>
                        <Info className="h-5 w-5" />
                    </Button>
                </div>
                <div className="flex gap-2 w-full sm:w-auto">
                    <Button variant="outline" size="sm" onClick={handleRefreshDashboard} disabled={isLoadingDashboard} className="flex-1 sm:flex-none text-xs sm:text-sm">
                        <RefreshCcw className={`h-3.5 w-3.5 mr-1.5 sm:mr-2 ${isLoadingDashboard ? 'animate-spin' : ''}`} />
                        Actualizar
                    </Button>
                    <Button onClick={() => setShowInsightFormModal(true)} size="sm" className="flex-1 sm:flex-none gap-1.5 sm:gap-2 text-xs sm:text-sm">
                        <Plus className="h-3.5 w-3.5" />
                        <span className="hidden xs:inline">Generar Insight</span>
                        <span className="xs:hidden">Insight</span>
                    </Button>
                </div>
            </div>

            {dashboardData && systemStats && (
                <>
                    <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
                        <Card className="relative overflow-hidden border-none shadow-md bg-gradient-to-br from-blue-500/5 to-purple-500/5">
                            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                                <CardTitle className="text-sm font-medium">Total de Análisis</CardTitle>
                                <BarChart3 className="h-4 w-4 text-blue-500" />
                            </CardHeader>
                            <CardContent>
                                <div className="text-2xl font-bold">{dashboardData.total_analysis_tasks}</div>
                                <p className="text-xs text-muted-foreground">{dashboardData.total_proactive_insights} insights proactivos</p>
                            </CardContent>
                        </Card>

                        <Card className="relative overflow-hidden border-none shadow-md bg-gradient-to-br from-green-500/5 to-emerald-500/5">
                            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                                <CardTitle className="text-sm font-medium">Tasa de Éxito</CardTitle>
                                <Activity className="h-4 w-4 text-green-500" />
                            </CardHeader>
                            <CardContent>
                                <div className="text-2xl font-bold">{systemStats.successRate}%</div>
                                <p className="text-xs text-muted-foreground">Sistema operativo</p>
                            </CardContent>
                        </Card>

                        <Card className="relative overflow-hidden border-none shadow-md bg-gradient-to-br from-orange-500/5 to-red-500/5">
                            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                                <CardTitle className="text-sm font-medium">Procesados</CardTitle>
                                <FileText className="h-4 w-4 text-orange-500" />
                            </CardHeader>
                            <CardContent>
                                <div className="text-2xl font-bold">{systemStats.totalProcessed}</div>
                                <p className="text-xs text-muted-foreground">Documentos y tareas</p>
                            </CardContent>
                        </Card>

                        <Card className="relative overflow-hidden border-none shadow-md bg-gradient-to-br from-yellow-500/5 to-amber-500/5">
                            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                                <CardTitle className="text-sm font-medium">Insights Activos</CardTitle>
                                <Sparkles className="h-4 w-4 text-yellow-500" />
                            </CardHeader>
                            <CardContent>
                                <div className="text-2xl font-bold">{systemStats.activeInsights}</div>
                                <p className="text-xs text-muted-foreground">Generados por KAI</p>
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
                        <CardContent className="px-1 sm:px-6">
                            <div className="h-[250px] sm:h-[300px] w-full">
                                <ResponsiveContainer width="100%" height="100%">
                                    <BarChart data={chartData}>
                                        <XAxis dataKey="name" fontSize={10} tickLine={false} axisLine={false} />
                                        <YAxis fontSize={10} tickLine={false} axisLine={false} />
                                        <Tooltip
                                            contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1)' }}
                                        />
                                        <Legend wrapperStyle={{ fontSize: '10px' }} />
                                        <Bar dataKey="Completados" stackId="a" fill="hsl(var(--primary))" radius={[0, 0, 0, 0]} />
                                        <Bar dataKey="Fallidos" stackId="a" fill="#fa8072" radius={[4, 4, 0, 0]} />
                                    </BarChart>
                                </ResponsiveContainer>
                            </div>
                        </CardContent>
                    </Card>
                </>
            )}

            <div className="space-y-4">
                <div className="flex flex-col gap-4">
                    <form onSubmit={handleSearch} className="flex flex-col sm:flex-row gap-2 w-full">
                        <div className="relative flex-1">
                            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                            <Input
                                placeholder="Buscar en análisis..."
                                value={searchQuery}
                                onChange={(e) => updateSearchQuery(e.target.value)}
                                className="pl-10 h-10 text-sm"
                            />
                        </div>
                        <div className="flex gap-2">
                            <Button type="submit" variant="outline" className="flex-1 sm:flex-none h-10 text-sm">
                                Buscar
                            </Button>
                            <DropdownMenu>
                                <DropdownMenuTrigger asChild>
                                    <Button variant="outline" className="flex-1 sm:flex-none gap-2 h-10 text-sm">
                                        <Filter className="h-4 w-4" />
                                        <span className="truncate max-w-[100px]">
                                            {selectedType ? getAnalysisTypeLabel(selectedType) : 'Tipo'}
                                        </span>
                                        <ChevronDown className="h-4 w-4" />
                                    </Button>
                                </DropdownMenuTrigger>
                                <DropdownMenuContent align="end" className="max-h-[300px] overflow-y-auto">
                                    {analysisTypes.map((type) => (
                                        <DropdownMenuItem key={type.value || 'all'} onClick={() => setSelectedType(type.value)}>
                                            {type.label}
                                        </DropdownMenuItem>
                                    ))}
                                </DropdownMenuContent>
                            </DropdownMenu>
                        </div>
                    </form>
                </div>

                {analyses.length === 0 ? (
                    <div className="text-center py-20 border-2 border-dashed rounded-xl bg-muted/10">
                        <BarChart3 className="mx-auto h-12 w-12 text-muted-foreground/30 mb-4" />
                        <h3 className="text-lg font-medium">No se encontraron análisis</h3>
                        <p className="text-sm text-muted-foreground">Intenta ajustar tus filtros o búsqueda.</p>
                    </div>
                ) : (
                    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                        <AnimatePresence>
                            {analyses.map((analysis, index) => (
                                <motion.div
                                    key={analysis.id}
                                    initial={{ opacity: 0, y: 20 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ delay: index * 0.05 }}
                                >
                                    <Card
                                        className="group cursor-pointer hover:shadow-lg transition-all border-none shadow-sm bg-card/50 hover:bg-card flex flex-col h-full"
                                        onClick={() => handleViewDetails(analysis)}
                                    >
                                        <CardHeader className="pb-2">
                                            <div className="flex items-center justify-between mb-2">
                                                <div className="p-2 rounded-lg bg-primary/5">
                                                    {getAnalysisIcon(analysis.type)}
                                                </div>
                                                <Badge variant="outline" className={`text-[10px] ${getAnalysisTypeBadgeColor(analysis.type)}`}>
                                                    {getAnalysisTypeLabel(analysis.type)}
                                                </Badge>
                                            </div>
                                            <CardTitle className="text-base line-clamp-2 group-hover:text-primary transition-colors">
                                                {analysis.title}
                                            </CardTitle>
                                        </CardHeader>
                                        <CardContent className="flex-grow">
                                            <p className="text-xs text-muted-foreground line-clamp-3 leading-relaxed">
                                                {analysis.summary}
                                            </p>
                                            <div className="mt-4 pt-3 border-t flex items-center justify-between text-[10px] text-muted-foreground">
                                                <div className="flex items-center gap-1">
                                                    <Clock className="h-3 w-3" />
                                                    {analysis.created_at ? formatDate(analysis.created_at) : 'N/A'}
                                                </div>
                                                <Eye className="h-3 w-3 opacity-0 group-hover:opacity-100 transition-opacity" />
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
