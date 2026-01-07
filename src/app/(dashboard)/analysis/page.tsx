// src/app/(dashboard)/analysis/page.tsx
'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useState, useCallback, useRef, useMemo } from 'react';

import { useAuth } from '@/contexts/AuthContext'; // Tu hook de autenticación

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';

import { Button } from '@/components/ui/button';

import { Input } from '@/components/ui/input';

import { Network } from 'lucide-react';
import { Loader2, Info, Filter, ChevronDown, Search, BarChart3, FileText, FolderKanban, Lightbulb, Code, Calendar, Eye, Plus, TrendingUp, AlertTriangle, HelpCircle, CheckCircle, Clock, XCircle, ArrowLeft, StickyNote, TrendingDown, Users, Activity, Target, PieChart, Sparkles, RefreshCcw, Zap } from 'lucide-react'; // Añadidos iconos para el dashboard

import { toast } from 'sonner';

import apiClient from '@/lib/api';

import { Analysis, AnalysisType, Insight, Question, AnalysisResponse, DashboardInsightsResponse, AnalysisStats, KeyTopic } from '@/lib/models'; // Importar nuevos modelos

import { Badge } from '@/components/ui/badge';

import { Bar, BarChart, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer } from 'recharts';

import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';

import { Tooltip as UITooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription as SheetDescriptionComp } from '@/components/ui/sheet'; // Importar Sheet y renombrar SheetDescription para evitar conflicto

import { motion, AnimatePresence } from 'framer-motion';

import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog'; // Importar componentes de Dialog

import InsightGeneratorForm from '@/components/InsightGeneratorForm'; // Importar el nuevo componente

import { QuestionSlider } from '@/components/QuestionSlider'; // Importar QuestionSlider

import { KeyTopicSlider } from '@/components/KeyTopicSlider'; // Importar KeyTopicSlider

import { KeyTopicDetailDialog } from '@/components/KeyTopicDetailDialog'; // Importar KeyTopicDetailDialog

import { AnalysisDetailDialog } from './analysis-detail-dialog'; // Importar AnalysisDetailDialog
import { DeepResearchDetailDialog } from './deep-research-detail-dialog'; // Importar DeepResearchDetailDialog


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
    case 'document':
      return 'Documento';
    case 'collection':
      return 'Colección';
    case 'insight':
    case 'proactive_insight_manual':
    case 'neural_insight':
      return 'Insight';
    case 'code':
      return 'Código';
    case 'semantic':
      return 'Semántico';
    case 'semantic_summary':
      return 'Resumen Semántico';
    case 'custom':
      return 'Personalizado';
    case 'knowledge_graph':
      return 'Grafo de Conocimiento';
    case 'note_analysis':
      return 'Nota';
    case 'note_collection_analysis':
      return 'Colección de Notas';
    case 'gap_development':
      return 'Desarrollo de Brecha';
    case 'deep_research':
      return 'Investigación Profunda';
    case 'comprehensive_web_analysis':
      return 'Análisis Web Integral';
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
    case 'proactive_insight_manual':
    case 'neural_insight':
      return 'bg-yellow-100 text-yellow-800 border-yellow-200';
    case 'code':
      return 'bg-orange-100 text-orange-800 border-orange-200';
    case 'semantic':
    case 'semantic_summary':
      return 'bg-indigo-100 text-indigo-800 border-indigo-200';
    case 'note_analysis':
      return 'bg-amber-100 text-amber-800 border-amber-200';
    case 'note_collection_analysis':
      return 'bg-orange-100 text-orange-800 border-orange-200';
    case 'gap_development':
      return 'bg-fuchsia-100 text-fuchsia-800 border-fuchsia-200';
    case 'deep_research':
      return 'bg-blue-100 text-blue-800 border-blue-200';
    case 'comprehensive_web_analysis':
      return 'bg-cyan-100 text-cyan-800 border-cyan-200';
    default:
      return 'bg-gray-100 text-gray-800 border-gray-200';
  }
};

// Nuevas funciones auxiliares para colores de análisis
const getAnalysisTypeColor = (type: string) => {
  switch (type) {
    case 'document':
      return 'bg-blue-500';
    case 'collection':
      return 'bg-green-500';
    case 'insight':
    case 'proactive_insight_manual':
    case 'neural_insight':
      return 'bg-yellow-500';
    case 'code':
      return 'bg-orange-500';
    case 'semantic':
    case 'semantic_summary':
      return 'bg-indigo-500';
    case 'note_analysis':
      return 'bg-amber-500';
    case 'note_collection_analysis':
      return 'bg-red-500';
    case 'gap_development':
      return 'bg-fuchsia-500';
    case 'deep_research':
      return 'bg-blue-500';
    case 'comprehensive_web_analysis':
      return 'bg-cyan-500';
    default:
      return 'bg-gray-500';
  }
};

const getAnalysisTypeProgressColor = (type: string) => {
  switch (type) {
    case 'document':
      return 'bg-blue-500';
    case 'collection':
      return 'bg-green-500';
    case 'insight':
    case 'proactive_insight_manual':
    case 'neural_insight':
      return 'bg-yellow-500';
    case 'code':
      return 'bg-orange-500';
    case 'semantic':
    case 'semantic_summary':
      return 'bg-indigo-500';
    case 'note_analysis':
      return 'bg-amber-500';
    case 'note_collection_analysis':
      return 'bg-red-500';
    case 'gap_development':
      return 'bg-fuchsia-500';
    case 'deep_research':
      return 'bg-blue-500';
    case 'comprehensive_web_analysis':
      return 'bg-cyan-500';
    default:
      return 'bg-gray-500';
  }
};

export default function AnalysisPage() {
  const router = useRouter();

  const { user, token } = useAuth();

  console.log('AnalysisPage: user', user);
  console.log('AnalysisPage: token', token);

  const [analyses, setAnalyses] = useState<Analysis[]>([]);

  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [topicKeywords, setTopicKeywords] = useState<string>(''); // Nuevo estado para palabras clave

  // Estados para debounce de búsqueda
  const [debouncedSearchQuery, setDebouncedSearchQuery] = useState('');
  const [debouncedTopicKeywords, setDebouncedTopicKeywords] = useState('');
  const searchTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const keywordsTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const [selectedType, setSelectedType] = useState<string | null>(null);
  const [selectedAnalysis, setSelectedAnalysis] = useState<Analysis | null>(null);

  const [showInsightFormModal, setShowInsightFormModal] = useState(false);

  const [dashboardData, setDashboardData] = useState<DashboardInsightsResponse | null>(null); // Nuevo estado para datos del dashboard

  const [isLoadingDashboard, setIsLoadingDashboard] = useState(true); // Nuevo estado de carga para el dashboard

  const [isKeyTopicDetailDialogOpen, setIsKeyTopicDetailDialogOpen] = useState(false); // Nuevo estado para el diálogo de detalles de tema clave

  const [selectedKeyTopic, setSelectedKeyTopic] = useState<KeyTopic | null>(null); // Nuevo estado para el tema clave seleccionado

  const [isInfoSheetOpen, setIsInfoSheetOpen] = useState(false); // Nuevo estado para controlar la visibilidad del Sheet

  const offsetRef = useRef(0);

  const [hasMore, setHasMore] = useState(false);

  const [isLoadingMore, setIsLoadingMore] = useState(false);

  const [lastUpdateTime, setLastUpdateTime] = useState<Date>(new Date()); // Estado para trackear última actualización




  // Función fetchAnalyses sin dependencias problemáticas
  const fetchAnalyses = useCallback(async (reset = false, searchQuery?: string, keywords?: string) => {
    console.log('fetchAnalyses: Iniciando', { reset, selectedType, searchQuery, keywords });

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
      console.log('fetchAnalyses: Datos recibidos', data);

      if (reset) {
        setAnalyses(data.analysis);
      } else {
        setAnalyses(prev => [...prev, ...data.analysis]);
      }

      if (data.has_more && data.analysis.length === 0) {
        setHasMore(false);
      } else {
        setHasMore(!!data.has_more);
      }

      offsetRef.current = currentOffset + data.analysis.length;

    } catch (error) {
      toast.error('Error al cargar los análisis');
      console.error('fetchAnalyses: Error al cargar análisis', error);
      setHasMore(false);
    } finally {
      setIsLoading(false);
      setIsLoadingMore(false);
      console.log('fetchAnalyses: Finalizado', { isLoading: false, isLoadingMore: false });
    }
  }, [selectedType]);

  const fetchDashboardData = useCallback(async () => {
    console.log('fetchDashboardData: Iniciando');
    console.log('fetchDashboardData: user?.account_id', user?.account_id);

    if (!user?.account_id) {
      console.log('fetchDashboardData: No user account ID, returning early but setting loading to false');
      setIsLoadingDashboard(false);
      return;
    }

    setIsLoadingDashboard(true);

    try {
      const response = await apiClient.post<DashboardInsightsResponse>('/api/dashboard-insights', {});
      console.log('fetchDashboardData: Datos recibidos', response.data);

      setDashboardData(response.data);
      setLastUpdateTime(new Date()); // Actualizar timestamp

    } catch (error) {
      toast.error('Error al cargar los datos del dashboard');
      console.error('fetchDashboardData: Error al cargar datos del dashboard', error);
    } finally {
      setIsLoadingDashboard(false);
      console.log('fetchDashboardData: Finalizado', { isLoadingDashboard: false });
    }
  }, [user?.account_id]);

  // Función para actualizar datos manualmente
  const handleRefreshDashboard = useCallback(() => {
    fetchDashboardData();
    toast.success('Datos del dashboard actualizados');
  }, [fetchDashboardData]);

  // Función para actualizar búsqueda con debounce Y búsqueda automática
  const updateSearchQuery = useCallback((query: string) => {
    setSearchQuery(query);

    // Limpiar timeout anterior
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current);
    }

    // Establecer nuevo timeout
    searchTimeoutRef.current = setTimeout(() => {
      setDebouncedSearchQuery(query);
      // Ejecutar búsqueda automáticamente después del debounce
      if (user && token) {
        fetchAnalyses(true, query, debouncedTopicKeywords);
      }
    }, 500); // 500ms de delay
  }, [user, token, fetchAnalyses, debouncedTopicKeywords]);

  // Función para actualizar palabras clave con debounce Y búsqueda automática
  const updateTopicKeywords = useCallback((keywords: string) => {
    setTopicKeywords(keywords);

    // Limpiar timeout anterior
    if (keywordsTimeoutRef.current) {
      clearTimeout(keywordsTimeoutRef.current);
    }

    // Establecer nuevo timeout
    keywordsTimeoutRef.current = setTimeout(() => {
      setDebouncedTopicKeywords(keywords);
      // Ejecutar búsqueda automáticamente después del debounce
      if (user && token) {
        fetchAnalyses(true, debouncedSearchQuery, keywords);
      }
    }, 500); // 500ms de delay
  }, [user, token, fetchAnalyses, debouncedSearchQuery]);

  // useEffect solo para carga inicial y cambios de filtros (no búsqueda de texto)
  useEffect(() => {
    console.log('useEffect inicial: user, token, selectedType changed', {
      user: !!user,
      token: !!token,
      selectedType
    });
    if (user && token) {
      fetchAnalyses(true, debouncedSearchQuery, debouncedTopicKeywords);
      fetchDashboardData();
    }
  }, [user, token, selectedType]);

  // useEffect separado para cambios en valores debounced (solo dashboard)
  useEffect(() => {
    if (user && token) {
      // Solo actualizar dashboard, NO fetchAnalyses aquí
      fetchDashboardData();
    }
  }, [user, token, fetchDashboardData]);

  // Cleanup timeouts on unmount
  useEffect(() => {
    return () => {
      if (searchTimeoutRef.current) {
        clearTimeout(searchTimeoutRef.current);
      }
      if (keywordsTimeoutRef.current) {
        clearTimeout(keywordsTimeoutRef.current);
      }
    };
  }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    fetchAnalyses(true, debouncedSearchQuery, debouncedTopicKeywords);
  };

  const handleViewDetails = (analysis: Analysis) => {
    console.log('handleViewDetails: Abriendo diálogo para tipo de análisis:', analysis.type, analysis);
    setSelectedAnalysis(analysis);
  };

  const handleLoadMore = () => {
    if (!isLoadingMore && hasMore) {
      fetchAnalyses(false, debouncedSearchQuery, debouncedTopicKeywords);
    }
  };

  // Función para manejar la eliminación de análisis
  const handleAnalysisDeleted = useCallback((deletedAnalysisId: string) => {
    console.log('handleAnalysisDeleted: Eliminando análisis con ID:', deletedAnalysisId);
    // Remover el análisis de la lista
    setAnalyses(prev => prev.filter(analysis => analysis.id !== deletedAnalysisId));
    // Mostrar mensaje de éxito
    toast.success('Análisis eliminado correctamente');
  }, []);

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('es-ES', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
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

  // Calcular estadísticas adicionales
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
      <div className="flex h-screen w-full items-center justify-center">
        <div className="flex flex-col items-center gap-2">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-muted-foreground">Cargando análisis...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-8 max-w-7xl mx-auto overflow-x-hidden space-y-8">
      {/* Header y título */}
      <div className="spacing-component">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="icon" onClick={() => router.push('/rag')} className="h-8 w-8 text-muted-foreground flex-shrink-0">
              <ArrowLeft className="h-5 w-5" />
            </Button>
            <h1 className="text-2xl sm:text-3xl md:text-5xl font-bold tracking-tight bg-gradient-to-r from-foreground to-muted-foreground bg-clip-text text-transparent spacing-tight truncate">
              Centro de Análisis
            </h1>
            <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground flex-shrink-0" onClick={() => setIsInfoSheetOpen(true)}>
              <Info className="h-5 w-5" />
            </Button>
          </div>
          <div className="flex gap-2 w-full sm:w-auto">
            <Button variant="outline" size="sm" onClick={handleRefreshDashboard} disabled={isLoadingDashboard} className="flex-1 sm:flex-none text-xs sm:text-sm">
              <RefreshCcw className={`h-3.5 w-3.5 mr-1.5 sm:mr-2 ${isLoadingDashboard ? 'animate-spin' : ''}`} />
              Actualizar
            </Button>
            <Button size="sm" onClick={() => setShowInsightFormModal(true)} className="flex-1 sm:flex-none gap-1.5 sm:gap-2 text-xs sm:text-sm">
              <Plus className="h-3.5 w-3.5" />
              <span className="hidden xs:inline">Generar Insight</span>
              <span className="xs:hidden">Insight</span>
            </Button>
          </div>
        </div>
      </div>

      {/* Sección de Dashboard/Resumen */}
      {dashboardData && systemStats && (
        <>
          {/* Tarjetas principales de estadísticas */}
          <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
            {/* Tarjeta 1: Total de Análisis */}
            <Card className="relative overflow-hidden">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Total de Análisis</CardTitle>
                <BarChart3 className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{dashboardData.total_analysis_tasks}</div>
                <p className="text-xs text-muted-foreground">
                  {dashboardData.total_proactive_insights} insights proactivos
                </p>
                <div className="absolute bottom-0 left-0 w-full h-1 bg-gradient-to-r from-blue-500 to-purple-500"></div>
              </CardContent>
            </Card>

            {/* Tarjeta 2: Estado del Sistema */}
            <Card className="relative overflow-hidden">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Estado del Sistema</CardTitle>
                <Activity className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                  <span className="text-sm font-medium">Sistema Activo</span>
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  {systemStats.successRate}% tasa de éxito
                </p>
                <div className="absolute bottom-0 left-0 w-full h-1 bg-gradient-to-r from-green-500 to-emerald-500"></div>
              </CardContent>
            </Card>

            {/* Tarjeta 3: Documentos Procesados */}
            <Card className="relative overflow-hidden">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Documentos Procesados</CardTitle>
                <FileText className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {dashboardData.analysis_stats_by_type?.reduce((acc, stat) => acc + stat.completed + stat.failed, 0) || 0}
                </div>
                <p className="text-xs text-muted-foreground">
                  {dashboardData.analysis_stats_by_type?.filter(stat => stat.type === 'document').reduce((acc, stat) => acc + stat.completed, 0) || 0} documentos analizados
                </p>
                <div className="absolute bottom-0 left-0 w-full h-1 bg-gradient-to-r from-orange-500 to-red-500"></div>
              </CardContent>
            </Card>

            {/* Tarjeta 4: Insights Activos */}
            <Card className="relative overflow-hidden">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Insights Activos</CardTitle>
                <Sparkles className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{systemStats.activeInsights}</div>
                <p className="text-xs text-muted-foreground">
                  Generados automáticamente
                </p>
                <div className="absolute bottom-0 left-0 w-full h-1 bg-gradient-to-r from-yellow-500 to-amber-500"></div>
              </CardContent>
            </Card>
          </div>

          {/* Tarjetas de información dinámica */}
          <div className="grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
            {/* Tarjeta: Brechas de Conocimiento */}
            <QuestionSlider
              title="Brechas de Conocimiento"
              questions={dashboardData.emergent_knowledge_gaps || []}
              icon={<AlertTriangle className="h-5 w-5 text-muted-foreground" />}
              emptyMessage="No se detectaron brechas recientes."
              autoSlide={true}
              slideInterval={5000}
              showCounter={false}
              onDevelopClick={() => { }}
            />

            {/* Tarjeta: Temas Clave */}
            <KeyTopicSlider
              title="Temas Clave"
              keyTopics={dashboardData.key_topics || []}
              icon={<TrendingUp className="h-5 w-5 text-muted-foreground" />}
              emptyMessage="No hay temas clave recientes."
              autoSlide={true}
              slideInterval={7000}
              onKeyTopicClick={(topic) => {
                setSelectedKeyTopic(topic);
                setIsKeyTopicDetailDialogOpen(true);
              }}
            />

            {/* Tarjeta: Preguntas para Explorar */}
            <QuestionSlider
              title="Preguntas para Explorar"
              questions={dashboardData.exploration_questions || []}
              icon={<HelpCircle className="h-5 w-5 text-muted-foreground" />}
              emptyMessage="No hay preguntas para explorar recientes."
              autoSlide={true}
              slideInterval={6000}
              onDevelopClick={() => { }}
            />
          </div>
        </>
      )}

      {/* Estadísticas por tipo de análisis */}
      {dashboardData && dashboardData.analysis_stats_by_type.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Estadísticas por Tipo de Análisis</CardTitle>
            <CardDescription>Resumen de la actividad de análisis por categoría.</CardDescription>
          </CardHeader>
          <CardContent className="px-1 sm:px-6">
            <ResponsiveContainer width="100%" height={250} className="sm:h-[300px]">
              <BarChart
                data={chartData}
                margin={{
                  top: 20, right: 30, left: 20, bottom: 5,
                }}
              >
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="Completados" stackId="a" fill="#82ca9d" />
                <Bar dataKey="Fallidos" stackId="a" fill="#fa8072" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {/* --- SECCIÓN DE LISTA DE ANÁLISIS EXISTENTE --- */}
      <>
        {/* Filtros y búsqueda */}
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
            <Input
              placeholder="Palabras clave..."
              value={topicKeywords}
              onChange={(e) => updateTopicKeywords(e.target.value)}
              className="flex-1 h-10 text-sm"
            />
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
                    <DropdownMenuItem
                      key={type.value || 'all'}
                      onClick={() => setSelectedType(type.value)}
                    >
                      {type.label}
                    </DropdownMenuItem>
                  ))}
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </form>
        </div>

        {/* Lista de análisis */}
        {analyses.length === 0 ? (
          <div className="text-center py-20 px-8">
            <BarChart3 className="mx-auto h-16 w-16 text-muted-foreground/50 mb-6" />
            <h3 className="text-xl font-semibold mb-4">No se encontraron análisis</h3>
            <p className="text-muted-foreground mb-8 max-w-md mx-auto">
              {searchQuery || selectedType
                ? 'No hay análisis que coincidan con tus filtros o búsqueda. Intenta ajustar la consulta.'
                : 'Aún no tienes análisis. ¡Comienza analizando documentos o colecciones para ver resultados aquí!'
              }
            </p>
          </div>
        ) : (
          <div className="grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
            <AnimatePresence>
              {analyses.map((analysis, index) => (
                <motion.div
                  key={analysis.id}
                  layout
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.8 }}
                  transition={{ type: "spring", stiffness: 300, damping: 30, delay: index * 0.05 }}
                  className="h-full"
                >
                  <Card className="group cursor-pointer hover:shadow-xl hover:scale-[1.02] transition-all duration-200 border-2 hover:border-primary/20 flex flex-col h-full">
                    <CardHeader className="pb-3">
                      <div className="flex items-start justify-between gap-3">
                        <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                          {getAnalysisIcon(analysis.type)}
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleViewDetails(analysis)}
                          className="opacity-0 group-hover:opacity-100 transition-opacity gap-1 h-8 px-2"
                        >
                          <Eye className="h-3 w-3" />
                          <span className="text-xs">Ver</span>
                        </Button>
                      </div>
                      <div className="space-y-3">
                        <CardTitle className="text-lg leading-tight line-clamp-2">{analysis.title}</CardTitle>
                        <div className="flex flex-wrap items-center gap-2">
                          <Badge className={`text-xs ${getAnalysisTypeBadgeColor(analysis.type)}`}>
                            {getAnalysisTypeLabel(analysis.type)}
                          </Badge>
                          {analysis.confidence_score && (
                            <Badge variant="outline" className="text-xs">
                              Confianza: {(analysis.confidence_score * 100).toFixed(0)}%
                            </Badge>
                          )}
                        </div>
                      </div>
                    </CardHeader>
                    <CardContent className="pt-0 flex-grow flex flex-col">
                      <p className="text-sm text-muted-foreground line-clamp-6 mb-4 flex-grow leading-relaxed">
                        {analysis.summary}
                      </p>

                      {analysis.action_suggestion && (
                        <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                          <p className="text-xs font-medium text-yellow-800 mb-1">Sugerencia:</p>
                          <p className="text-xs text-yellow-700 line-clamp-2">{analysis.action_suggestion}</p>
                        </div>
                      )}

                      {analysis.related_items && analysis.related_items.length > 0 && (
                        <div className="mb-4">
                          <p className="text-xs font-medium text-muted-foreground mb-2">
                            Elementos relacionados ({analysis.related_items.length})
                          </p>
                          <div className="flex flex-wrap gap-1">
                            {analysis.related_items.slice(0, 3).map((item, idx) => (
                              <Badge key={idx} variant="secondary" className="text-xs">
                                {item.title || item.name || `Item ${idx + 1}`}
                              </Badge>
                            ))}
                            {analysis.related_items.length > 3 && (
                              <Badge variant="outline" className="text-xs">
                                +{analysis.related_items.length - 3} más
                              </Badge>
                            )}
                          </div>
                        </div>
                      )}
                      <div className="space-y-2 text-xs text-muted-foreground mt-auto pt-3 border-t border-border/50">
                        {analysis.tool_used && (
                          <div className="mb-2">
                            <Badge variant="outline" className="text-xs font-mono bg-slate-50 text-slate-600 border-slate-200 dark:bg-slate-800 dark:text-slate-400 dark:border-slate-700">
                              {analysis.tool_used}
                            </Badge>
                          </div>
                        )}
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-1">
                            <Calendar className="h-3 w-3" />
                            <TooltipProvider>
                              <UITooltip>
                                <TooltipTrigger asChild>
                                  <span className="truncate">Creado: {analysis.created_at ? formatDate(analysis.created_at) : 'N/A'}</span>
                                </TooltipTrigger>
                                <TooltipContent>
                                  <p>Fecha de creación del análisis.</p>
                                </TooltipContent>
                              </UITooltip>
                            </TooltipProvider>
                          </div>
                        </div>

                        {analysis.updated_at !== analysis.created_at && (
                          <div className="flex items-center gap-1">
                            <Calendar className="h-3 w-3" />
                            <TooltipProvider>
                              <UITooltip>
                                <TooltipTrigger asChild>
                                  <span className="truncate">Actualizado: {analysis.updated_at ? formatDate(analysis.updated_at) : 'N/A'}</span>
                                </TooltipTrigger>
                                <TooltipContent>
                                  <p>Última actualización del análisis.</p>
                                </TooltipContent>
                              </UITooltip>
                            </TooltipProvider>
                          </div>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              ))}
            </AnimatePresence>

            {/* Botón cargar más */}
            {hasMore && (
              <div className="text-center pt-6">
                <Button
                  onClick={handleLoadMore}
                  disabled={isLoadingMore}
                  variant="outline"
                  className="gap-2"
                >
                  {isLoadingMore ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Cargando...
                    </>
                  ) : (
                    'Cargar más análisis'
                  )}
                </Button>
              </div>
            )}
          </div>
        )}
      </>

      {/* DIÁLOGOS DE RESULTADOS DE ANÁLISIS */}
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

      {/* Modal para generar insights */}
      <Dialog open={showInsightFormModal} onOpenChange={setShowInsightFormModal}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Generar Insights Proactivos</DialogTitle>
            <DialogDescription>
              Configura los parámetros para iniciar un análisis manual de insights.
            </DialogDescription>
          </DialogHeader>
          {user?.account_id ? (
            <InsightGeneratorForm accountId={user.account_id} />
          ) : (
            <p className="text-center text-red-500">Error: No se pudo obtener el ID de la cuenta.</p>
          )}
        </DialogContent>
      </Dialog>

      {/* Diálogo de detalles del Tema Clave */}
      <KeyTopicDetailDialog
        isOpen={isKeyTopicDetailDialogOpen}
        onOpenChange={setIsKeyTopicDetailDialogOpen}
        keyTopic={selectedKeyTopic}
      />

      <Sheet open={isInfoSheetOpen} onOpenChange={setIsInfoSheetOpen}>
        <SheetContent side="right" className="w-full sm:max-w-md overflow-y-auto">
          <SheetHeader>
            <SheetTitle className="text-xl font-bold text-primary">Centro de Análisis</SheetTitle>
            <SheetDescriptionComp className="text-sm text-muted-foreground">
              Gestiona y visualiza todos los análisis generados por Kognito AI de tus documentos, colecciones e interacciones.
            </SheetDescriptionComp>
          </SheetHeader>
          <div className="py-4 text-sm text-gray-700 dark:text-gray-300 space-y-4">
            <p><strong>¿Qué puedes hacer en el Centro de Análisis?</strong></p>
            <ul className="list-disc pl-5 space-y-2">
              <li><strong>Visualizar Análisis:</strong> Accede a informes detallados de documentos, colecciones, código e insights semánticos.</li>
              <li><strong>Generar Insights Manuales:</strong> Inicia análisis específicos sobre tus datos para descubrir conexiones y brechas de conocimiento.</li>
              <li><strong>Estadísticas Generales:</strong> Obtén un resumen visual de la actividad de análisis, incluyendo el total de tareas y la distribución por tipo.</li>
              <li><strong>Brechas de Conocimiento:</strong> Identifica automáticamente áreas donde tu información es incompleta o requiere mayor exploración.</li>
              <li><strong>Temas Clave:</strong> Descubre los temas más relevantes y recurrentes en tu base de conocimiento.</li>
              <li><strong>Preguntas para Explorar:</strong> Sugerencias de preguntas que pueden ayudar a profundizar en el conocimiento y generar nuevos insights.</li>
            </ul>

            <p><strong>Interacción con IA:</strong></p>
            <p>El Centro de Análisis es el corazón de la inteligencia de Kognito. Puedes interactuar con él a través del chat de IA para:</p>
            <ul className="list-disc pl-5 space-y-2">
              <li>Solicitar análisis de documentos o colecciones específicas.</li>
              <li>Pedir resúmenes de análisis existentes o profundizar en un tema.</li>
              <li>Generar nuevos insights proactivos o manuales sobre tu información.</li>
              <li>Consultar estadísticas de tus análisis o el estado de tareas pendientes.</li>
            </ul>

            <p><strong>Beneficios Clave:</strong></p>
            <ul className="list-disc pl-5 space-y-2">
              <li><strong>Visión Unificada:</strong> Todos tus análisis en un solo lugar para una gestión centralizada.</li>
              <li><strong>Descubrimiento de Conocimiento:</strong> Transforma tus datos brutos en insights accionables.</li>
              <li><strong>Toma de Decisiones Mejorada:</strong> Fundamenta tus decisiones en análisis profundos y objetivos.</li>
              <li><strong>Potenciado por IA:</strong> Aprovecha el poder de la IA para un análisis automático y proactivo.</li>
            </ul>

            <p>¡Convierte tus datos en conocimiento estratégico con el Centro de Análisis!</p>
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
}