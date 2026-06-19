'use client';

import { useEffect, useState, useMemo } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Bar, BarChart, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import apiClient from '@/lib/api';
import { toast } from 'sonner';
import { InsightDetailDialog } from '@/components/InsightDetailDialog';
import { HelpCircle, Bot, Library, FileText, FolderKanban, Search, BrainCircuit, Sparkles, ArrowLeft, LayoutDashboard, RefreshCcw, Info, ChevronRight, Clock } from 'lucide-react';
import Link from 'next/link';
import { InlineMarkdownRenderer } from '@/components/InlineMarkdownRenderer';
import { QuestionSlider } from '@/components/QuestionSlider';
import { CustomChartTooltip } from '@/components/CustomChartTooltip';
import { DashboardHelpCarousel } from '@/components/DashboardHelpCarousel';
import { HeartbeatMonitor } from '@/components/HeartbeatMonitor';
import { AnalysisDetailDialog } from '@/app/(dashboard)/analysis/analysis-detail-dialog';
import { type Analysis } from '@/lib/models';
import { Button } from '@/components/ui/button';
import dynamic from 'next/dynamic';
import { motion } from 'framer-motion';

const WelcomeDialog = dynamic(() => import('@/components/WelcomeDialog').then(mod => mod.WelcomeDialog), { ssr: false });

// Tipos para los datos que esperamos de la API
const CustomYAxisTick = (props: any) => {
  const { x, y, payload } = props;
  return (
    <g transform={`translate(${x},${y})`}>
      <foreignObject x={-200} y={-32} width={195} height={64}>
        <div
          style={{
            width: '100%',
            height: '100%',
            display: 'flex',
            justifyContent: 'flex-end',
            alignItems: 'center',
            textAlign: 'right',
            paddingRight: '5px',
            fontSize: '12px',
            color: 'hsl(var(--muted-foreground))',
            lineHeight: '1.2'
          }}
        >
          <span className="line-clamp-2">
            <InlineMarkdownRenderer content={payload.value} />
          </span>
        </div>
      </foreignObject>
    </g>
  );
};

interface DashboardData {
  key_topics: { topic: string; mentions: number }[];
  proactive_insights: Insight[];
}

interface Insight {
  id: string;
  type: string;
  summary: string;
  created_at: string,
  related_items: any[];
  action_suggestion?: string;
  synthetic_name?: string;
}

interface Conversation {
  id: string;
  title: string;
  isPinned: boolean;
  platform: string;
  workspace_id: string | null;
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [viewingInsight, setViewingInsight] = useState<Insight | null>(null);
  const [analysisData, setAnalysisData] = useState<Analysis[]>([]);
  const [viewingAnalysis, setViewingAnalysis] = useState<Analysis | null>(null);
  const [isWelcomeDialogOpen, setIsWelcomeDialogOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [isUpdatingTopics, setIsUpdatingTopics] = useState(false);

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(e.target.value);
  };

  useEffect(() => {
    const fetchInsights = async () => {
      setIsLoading(true);
      try {
        const [insightsResponse, analysesResponse, conversationsResponse] = await Promise.all([
          apiClient.post('/api/dashboard-insights', { all: false }),
          apiClient.post('/api/get-all-analysis', { limit: 12, offset: 0 }),
          apiClient.get('/api/threads')
        ]);

        const transformedInsights = (insightsResponse.data.proactive_insights || []).map((insight: any) => ({
          ...insight,
          related_items: insight.related_items || []
        }));

        let fetchedConversations = conversationsResponse.data;
        if (fetchedConversations && typeof fetchedConversations === 'object' && fetchedConversations.threads) {
          fetchedConversations = fetchedConversations.threads;
        }
        if (!Array.isArray(fetchedConversations)) {
          fetchedConversations = [];
        }

        setData({
          ...insightsResponse.data,
          proactive_insights: transformedInsights
        });
        setAnalysisData(analysesResponse.data.analysis || []);
        setConversations(fetchedConversations);

        const hasVisited = localStorage.getItem('hasVisitedDashboard');
        if (!hasVisited) {
          setIsWelcomeDialogOpen(true);
          localStorage.setItem('hasVisitedDashboard', 'true');
        }
      } catch (error) {
        toast.error('No se pudieron cargar los datos del dashboard.');
        console.error("Dashboard fetch error:", error);
      } finally {
        setIsLoading(false);
      }
    };
    fetchInsights();
  }, []);

  const randomizedKnowledgeGaps = useMemo(() => {
    const allGaps = analysisData
      .filter(a => a.type === 'collection')
      .flatMap(a => (a.full_data?.emergent_knowledge_gaps || a.result?.emergent_knowledge_gaps) || []);

    for (let i = allGaps.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [allGaps[i], allGaps[j]] = [allGaps[j], allGaps[i]];
    }

    return allGaps.slice(0, 20);
  }, [analysisData]);

  const randomizedExplorationQuestions = useMemo(() => {
    const allQuestions = analysisData
      .filter(a => a.type === 'document')
      .flatMap(a => (a.full_data?.knowledge_gaps || a.result?.knowledge_gaps) || [])
      .map((gapObject: any) => (typeof gapObject === 'string' ? gapObject : gapObject.gap));

    for (let i = allQuestions.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [allQuestions[i], allQuestions[j]] = [allQuestions[j], allQuestions[i]];
    }

    return allQuestions.slice(0, 20);
  }, [analysisData]);

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'Reciente';
    return new Date(dateString).toLocaleDateString('es-ES', {
      day: 'numeric', month: 'short'
    });
  };

  if (isLoading) {
    return (
      <div className="flex h-[80vh] items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <RefreshCcw className="h-10 w-10 animate-spin text-primary" />
          <p className="text-muted-foreground animate-pulse">Cargando dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-8 max-w-7xl mx-auto space-y-8 animate-in fade-in duration-700">

      {/* 1. Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="h-12 w-12 rounded-2xl bg-primary/10 flex items-center justify-center shadow-inner">
            <LayoutDashboard className="h-6 w-6 text-primary" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Escritorio</h1>
            <p className="text-muted-foreground text-sm">Kognito está encontrando patrones y conexiones en tu conocimiento.</p>
          </div>
        </div>
      </div>

      {/* 2. Search Bar */}
      <div className="relative group">
        <div className="absolute -inset-0.5 bg-gradient-to-r from-primary/20 to-secondary/20 rounded-full blur opacity-20 group-hover:opacity-40 transition duration-500"></div>
        <div className="relative">
          <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 h-5 w-5 text-muted-foreground group-hover:text-primary transition-colors" />
          <Input
            type="text"
            placeholder="Buscar en el dashboard..."
            value={searchTerm}
            onChange={handleSearchChange}
            className="pl-12 h-14 rounded-full bg-card/80 backdrop-blur-sm border-muted/40 shadow-sm focus:ring-2 focus:ring-primary/20 text-lg transition-all"
          />
        </div>
      </div>

      {/* 2.5 Resolution Board Promo Banner */}
      <motion.div 
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="relative overflow-hidden rounded-3xl p-6 bg-gradient-to-br from-primary/10 via-secondary/5 to-background border border-primary/20 shadow-lg group"
      >
        <div className="absolute -right-16 -top-16 w-32 h-32 bg-primary/10 rounded-full blur-2xl group-hover:bg-primary/20 transition-all duration-700" />
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 relative">
          <div className="space-y-1.5">
            <span className="inline-flex items-center gap-1 bg-primary/15 text-primary px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wider">
              Nuevo: Tablero de Resolución
            </span>
            <h3 className="text-lg font-bold tracking-tight text-foreground">
              De la Identificación a la Acción y Verificación
            </h3>
            <p className="text-muted-foreground text-sm max-w-2xl">
              Tus insights recurrentes se traducen automáticamente en tareas con límites estrictos de 48 horas. Monitorea y toma decisiones de escalación en tiempo real.
            </p>
          </div>
          <Link href="/resolution-board">
            <Button className="bg-primary hover:bg-primary/95 text-primary-foreground font-semibold rounded-2xl">
              Ir al Tablero <ChevronRight className="ml-1.5 h-4 w-4 group-hover:translate-x-1 transition-transform" />
            </Button>
          </Link>
        </div>
      </motion.div>

      {/* 3. Temas Principales (Bar Chart) */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold flex items-center gap-2">
            <Library className="h-5 w-5 text-primary" />
            Temas Principales
          </h2>
        </div>

        <Card className="border-none shadow-lg bg-gradient-to-br from-card to-card/50 backdrop-blur-sm overflow-hidden">
          <CardContent className="pt-6">
            <div className="flex justify-end mb-4">
              <Button
                size="sm"
                variant="outline"
                className="gap-2 bg-background/50"
                onClick={async () => {
                  setIsUpdatingTopics(true);
                  try {
                    const triggerResponse = await apiClient.post('/api/update-semantic-topics');
                    const taskId = triggerResponse.data.task_id;
                    toast.info('Análisis semántico iniciado en segundo plano.');

                    let taskStatus = 'pending';
                    while (taskStatus === 'pending' || taskStatus === 'processing') {
                      await new Promise(resolve => setTimeout(resolve, 2000));
                      const statusResponse = await apiClient.get(`/api/get-analysis-result/${taskId}`);
                      taskStatus = statusResponse.data.status;
                      if (taskStatus === 'completed') {
                        const dataResponse = await apiClient.post('/api/dashboard-insights', { all: false });
                        setData(dataResponse.data);
                        toast.success('Temas actualizados.');
                        break;
                      } else if (taskStatus === 'failed') {
                        toast.error('Error en el análisis semántico.');
                        break;
                      }
                    }
                  } catch (error) {
                    toast.error('Error al iniciar análisis semántico.');
                  } finally {
                    setIsUpdatingTopics(false);
                  }
                }}
                disabled={isUpdatingTopics}
              >
                <RefreshCcw className={`h-3.5 w-3.5 ${isUpdatingTopics ? 'animate-spin' : ''}`} />
                {isUpdatingTopics ? 'Actualizando...' : 'Actualizar Temas'}
              </Button>
            </div>

            {data && data.key_topics.length > 0 ? (
              <div className="h-[400px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={data.key_topics} layout="vertical" margin={{ left: 10, right: 30, top: 10, bottom: 10 }}>
                    <defs>
                      <linearGradient id="barGradient" x1="0" y1="0" x2="1" y2="0">
                        <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity={0.8} />
                        <stop offset="100%" stopColor="hsl(var(--primary))" />
                      </linearGradient>
                    </defs>
                    <XAxis type="number" hide />
                    <YAxis
                      dataKey="topic"
                      type="category"
                      stroke="hsl(var(--muted-foreground))"
                      fontSize={12}
                      tickLine={false}
                      axisLine={false}
                      width={180}
                      interval={0}
                      tick={<CustomYAxisTick />}
                    />
                    <Tooltip
                      cursor={{ fill: 'hsl(var(--muted)/0.2)' }}
                      content={(props) => <CustomChartTooltip {...props} />}
                    />
                    <Bar
                      dataKey="mentions"
                      fill="url(#barGradient)"
                      radius={[0, 4, 4, 0]}
                      barSize={32}
                      animationDuration={1500}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="h-[300px] flex flex-col items-center justify-center text-muted-foreground">
                <Library className="h-12 w-12 mb-4 opacity-20" />
                <p>No hay temas principales disponibles.</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* 4. Grid: Ayuda, Conversaciones y Heartbeats */}
      <div className="grid gap-8 lg:grid-cols-3">
        {/* Ayuda */}
        <Card className="border-none shadow-lg bg-card/50 backdrop-blur-sm h-full flex flex-col">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <HelpCircle className="h-5 w-5 text-primary" />
              Ayuda y Capacidades
            </CardTitle>
            <CardDescription>Descubre todo lo que Kognito puede hacer por ti.</CardDescription>
          </CardHeader>
          <CardContent className="flex-1 p-0 overflow-hidden rounded-b-xl">
            <DashboardHelpCarousel />
          </CardContent>
        </Card>

        {/* Conversaciones */}
        <Card className="border-none shadow-lg bg-card/50 backdrop-blur-sm h-full flex flex-col">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Bot className="h-5 w-5 text-primary" />
              Últimas Conversaciones
            </CardTitle>
            <CardDescription>Tus interacciones más recientes.</CardDescription>
          </CardHeader>
          <CardContent className="flex-1">
            {conversations.length > 0 ? (
              <div className="space-y-3">
                {conversations.slice(0, 5).map(conv => (
                  <Link
                    href={`/chat/${conv.id}`}
                    key={conv.id}
                    className="flex items-center gap-3 p-3 rounded-xl bg-background/50 hover:bg-primary/5 border border-transparent hover:border-primary/10 transition-all group"
                  >
                    <div className="h-8 w-8 rounded-lg bg-primary/10 flex items-center justify-center group-hover:bg-primary/20 transition-colors">
                      <Bot className="h-4 w-4 text-primary" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate group-hover:text-primary transition-colors">
                        {conv.title || 'Conversación sin título'}
                      </p>
                      <p className="text-xs text-muted-foreground truncate">
                        ID: {conv.id.substring(0, 8)}...
                      </p>
                    </div>
                    <ChevronRight className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-all -translate-x-2 group-hover:translate-x-0" />
                  </Link>
                ))}
              </div>
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-muted-foreground py-8">
                <Bot className="h-10 w-10 mb-3 opacity-20" />
                <p>No hay conversaciones recientes.</p>
              </div>
            )}
            {conversations.length > 5 && (
              <div className="mt-4 text-right">
                <Link href="/chat" className="text-xs font-medium text-primary hover:underline">
                  Ver todas
                </Link>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Heartbeats */}
        <HeartbeatMonitor />
      </div>

      {/* 5. Últimos Análisis */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold flex items-center gap-2">
            <BrainCircuit className="h-5 w-5 text-primary" />
            Últimos Análisis Realizados
          </h2>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {analysisData.slice(0, 6).map(analysis => (
            <Card
              key={analysis.id}
              className="group cursor-pointer hover:shadow-lg transition-all border-none bg-card/40 hover:bg-card hover:-translate-y-1 duration-300"
              onClick={() => setViewingAnalysis(analysis)}
            >
              <CardHeader className="pb-3">
                <div className="flex items-center gap-3">
                  <div className="h-8 w-8 rounded-lg bg-primary/10 flex items-center justify-center group-hover:bg-primary/20 transition-colors">
                    <FileText className="h-4 w-4 text-primary" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <CardTitle className="text-sm font-semibold truncate group-hover:text-primary transition-colors" title={analysis.title || analysis.file_name}>
                      {analysis.title || analysis.file_name}
                    </CardTitle>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="pt-0">
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    {formatDate(analysis.created_at)}
                  </span>
                  <span className="opacity-0 group-hover:opacity-100 transition-opacity text-primary font-medium">Ver detalles</span>
                </div>
              </CardContent>
            </Card>
          ))}
          {analysisData.length === 0 && (
            <div className="col-span-full text-center py-12 text-muted-foreground bg-card/30 rounded-xl border border-dashed">
              <BrainCircuit className="h-10 w-10 mx-auto mb-3 opacity-20" />
              <p>No se han encontrado análisis recientes.</p>
            </div>
          )}
        </div>
      </div>

      {/* 6. Preguntas de Análisis (Sliders) */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold flex items-center gap-2">
            <Search className="h-5 w-5 text-primary" />
            Preguntas de Análisis
          </h2>
        </div>
        <div className="grid gap-6 md:grid-cols-2">
          <QuestionSlider
            title="Brechas de Conocimiento"
            questions={randomizedKnowledgeGaps}
            icon={<Search className="h-5 w-5 text-primary" />}
            emptyMessage="No hay brechas de conocimiento disponibles."
            onReload={async () => {
              setIsLoading(true);
              try {
                const analysesResponse = await apiClient.post('/api/get-all-analysis', { limit: 12, offset: 0 });
                setAnalysisData(analysesResponse.data.analysis || []);
                toast.success('Datos recargados.');
              } catch (error) {
                toast.error('Error al recargar.');
              } finally {
                setIsLoading(false);
              }
            }}
            isLoading={isLoading}
            autoSlide={true}
            slideInterval={5000}
          />
          <QuestionSlider
            title="Preguntas para Explorar"
            questions={randomizedExplorationQuestions}
            icon={<BrainCircuit className="h-5 w-5 text-primary" />}
            emptyMessage="No hay preguntas para explorar disponibles."
            onReload={async () => {
              setIsLoading(true);
              try {
                const analysesResponse = await apiClient.post('/api/get-saved-analyses', { all: true });
                setAnalysisData(analysesResponse.data);
                toast.success('Datos recargados.');
              } catch (error) {
                toast.error('Error al recargar.');
              } finally {
                setIsLoading(false);
              }
            }}
            isLoading={isLoading}
            autoSlide={true}
            slideInterval={6000}
          />
        </div>
      </div>

      <WelcomeDialog isOpen={isWelcomeDialogOpen} onOpenChange={setIsWelcomeDialogOpen} />

      <InsightDetailDialog
        isOpen={!!viewingInsight}
        onOpenChange={(open: boolean) => !open && setViewingInsight(null)}
        insight={viewingInsight}
      />

      <AnalysisDetailDialog
        isOpen={!!viewingAnalysis}
        onOpenChange={(open: boolean) => !open && setViewingAnalysis(null)}
        analysis={viewingAnalysis}
      />
    </div>
  );
}
