// En: src/app/(dashboard)/dashboard/page.tsx

'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Bar, BarChart, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import apiClient from '@/lib/api';
import { toast } from 'sonner';
import { Badge } from '@/components/ui/badge';
import { InsightDetailDialog } from '@/components/InsightDetailDialog';
import { HelpCircle, Bot, Library, FileText, FolderKanban, Notebook, Calendar, Search, ScanSearch, BrainCircuit } from 'lucide-react';
import Link from 'next/link';
import { InlineMarkdownRenderer } from '@/components/InlineMarkdownRenderer';
import { Button } from '@/components/ui/button';
import { QuestionSlider } from '@/components/QuestionSlider';
import { CustomChartTooltip } from '@/components/CustomChartTooltip';
import { TopicGroupDialog } from '@/components/TopicGroupDialog';
import { DashboardHelpCarousel } from '@/components/DashboardHelpCarousel';
import { WelcomeDialog } from '@/components/WelcomeDialog';

// Tipos para los datos que esperamos de la API
const CustomYAxisTick = (props: any) => {
  const { x, y, payload } = props;
  return (
    <g transform={`translate(${x},${y})`}>
      <foreignObject x={-200} y={-12} width={195} height={24}>
        <div
          style={{
            width: '100%',
            height: '100%',
            display: 'flex',
            justifyContent: 'flex-end',
            alignItems: 'center',
            textAlign: 'right',
            paddingRight: '5px',
            fontSize: '16px',
            color: 'hsl(var(--foreground))'
          }}
        >
          <InlineMarkdownRenderer content={payload.value} />
        </div>
      </foreignObject>
    </g>
  );
};

interface DashboardData {
  key_topics: { topic: string; mentions: number }[];
  proactive_insights: Insight[];
}

interface AnalysisData {
  id: string;
  file_name: string;
  result_payload: any;
  created_at: string;
}

interface Insight {
  id: string; 
  type: string; 
  summary: string; 
  created_at: string, 
  related_items: any[];
  action_suggestion?: string;
  synthetic_name?: string; // Nuevo campo para el nombre sintético
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [viewingInsight, setViewingInsight] = useState<Insight | null>(null);
  const [analysisData, setAnalysisData] = useState<AnalysisData[]>([]);
  const [isWelcomeDialogOpen, setIsWelcomeDialogOpen] = useState(false);

  useEffect(() => {
    const fetchInsights = async () => {
      setIsLoading(true);
      try {
        const [insightsResponse, analysesResponse] = await Promise.all([
          apiClient.post('/api/dashboard-insights', { all: false }),
          apiClient.post('/api/get-saved-analyses', { all: true })
        ]);
        setData(insightsResponse.data);
        setAnalysisData(analysesResponse.data);

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

  const getInsightIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case 'pattern':
        return <Bot className="h-5 w-5 text-primary" />;
      case 'connection':
        return <Library className="h-5 w-5 text-primary" />;
      case 'project':
        return <FolderKanban className="h-5 w-5 text-primary" />;
      default:
        return <FileText className="h-5 w-5 text-primary" />;
    }
  };

  if (isLoading) { return <div className="p-6 text-center">Cargando dashboard...</div>; }

  if (!data || (data.key_topics.length === 0 && data.proactive_insights.length === 0)) {
    return (
      <div className="p-6 text-center">
        <p className="text-muted-foreground">No hay datos disponibles en este momento.</p>
      </div>
    );
  }

  return (
    <>
      <div className="p-8 mx-4 space-y-8">
        {/* Header moderno */}
        <div className="spacing-component">
          <h1 className="text-5xl font-bold tracking-tight bg-gradient-to-r from-foreground to-muted-foreground bg-clip-text text-transparent spacing-tight">
            Dashboard de Insights
          </h1>
          <p className="typography-body-large text-muted-foreground max-w-2xl">
            Kognito está encontrando patrones y conexiones en tu conocimiento de forma inteligente.
          </p>
        </div>

        <div className="grid gap-8 lg:grid-cols-2 px-2">
          {/* Gráfico de Temas Principales */}
          <Card className="modern-card border-0 shadow-medium hover:shadow-strong transition-all duration-300">
            <CardHeader className="pb-4">
              <CardTitle className="text-2xl font-bold flex items-center gap-3 mb-3">
                <div className="w-3 h-3 rounded-full bg-primary"></div>
                Temas Principales
              </CardTitle>
              <CardDescription className="space-y-2">
                <span className="text-base">Tópicos más frecuentes en tu base de conocimiento.</span>
                <div className="text-xs text-muted-foreground bg-primary/10 px-3 py-1.5 rounded-full inline-block border border-primary/20">
                  ✨ Agrupados por similitud semántica
                </div>
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-6">
              <div className="flex justify-end mb-6 space-x-2">
                <button
                  className="px-6 py-3 gradient-primary text-white rounded-xl font-medium shadow-medium hover:shadow-strong transition-all duration-300 flex items-center gap-2 hover:scale-105"
                  onClick={async () => {
                    setIsLoading(true);
                    try {
                      // Trigger semantic analysis process
                      const triggerResponse = await apiClient.post('/api/update-semantic-topics');
                      const taskId = triggerResponse.data.task_id;
                      toast.info('Análisis semántico iniciado en segundo plano.', {
                        description: 'Recibirás una notificación cuando haya terminado.',
                      });
                      
                      // Poll for task status
                      let taskStatus = 'pending';
                      while (taskStatus === 'pending' || taskStatus === 'processing') {
                        await new Promise(resolve => setTimeout(resolve, 2000)); // Wait 2 seconds
                        const statusResponse = await apiClient.get(`/api/get-analysis-result/${taskId}`);
                        taskStatus = statusResponse.data.status;
                        if (taskStatus === 'completed') {
                          // Refresh dashboard data after analysis is complete
                          const dataResponse = await apiClient.post('/api/dashboard-insights');
                          setData(dataResponse.data);
                          toast.success('Análisis semántico completado.', {
                            description: 'Los temas principales han sido actualizados con éxito.',
                          });
                          break;
                        } else if (taskStatus === 'failed') {
                          toast.error('Error en el análisis semántico.', {
                            description: statusResponse.data.error || 'Ocurrió un error desconocido durante el análisis.',
                          });
                          break;
                        }
                      }
                    } catch (error) {
                      toast.error('Error al iniciar análisis semántico.');
                      console.error("Update semantic topics error:", error);
                    } finally {
                      setIsLoading(false);
                    }
                  }}
                  disabled={isLoading}
                >
                  {isLoading ? (
                    <svg className="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                  ) : (
                    'Actualizar'
                  )}
                </button>
              </div>
              <ResponsiveContainer width="100%" height={600}>
                <BarChart data={data.key_topics} layout="vertical" margin={{ left: 10, right: 30, top: 30, bottom: 30 }}>
                  <defs>
                    <linearGradient id="barGradient" x1="0" y1="0" x2="1" y2="0">
                      <stop offset="0%" stopColor="hsl(220 100% 60%)" />
                      <stop offset="100%" stopColor="hsl(200 100% 50%)" />
                    </linearGradient>
                  </defs>
                  <XAxis type="number" hide />
                  <YAxis dataKey="topic" type="category" stroke="hsl(var(--foreground))" fontSize={16} tickLine={false} axisLine={false} width={200} interval={0} tick={<CustomYAxisTick />} />
                  <Tooltip
                    cursor={{ fill: 'hsl(var(--muted))' }}
                    content={(props) => <CustomChartTooltip {...props} />}
                  />
                  <Bar dataKey="mentions" fill="url(#barGradient)" radius={[0, 8, 8, 0]} barSize={40} />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* Carrusel de Ayuda */}
          <Card className="modern-card border-0 shadow-medium hover:shadow-strong transition-all duration-300 h-full">
            <CardHeader className="pb-4">
              <CardTitle className="text-2xl font-bold flex items-center gap-3 mb-2">
                <div className="w-3 h-3 rounded-full bg-primary"></div>
                <HelpCircle className="h-6 w-6 text-primary" />
                Ayuda y Capacidades
              </CardTitle>
              <CardDescription className="text-lg">Un tour rápido por las funciones clave de Kognito.</CardDescription>
            </CardHeader>
            <CardContent className="p-0 h-[calc(100%-7rem)]">
              <DashboardHelpCarousel />
            </CardContent>
          </Card>
        </div>

        {/* Galería de Tarjetas de Insights */}
        <div className="spacing-section mt-16">
          <div className="flex justify-between items-center spacing-component mb-10">
            <h2 className="text-4xl font-bold tracking-tight">Descubrimientos Proactivos</h2>
            <Link href="/dashboard/insights" className="typography-body-small font-medium text-primary hover:text-primary/80 transition-colors">
              Ver todo
            </Link>
          </div>
          <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3 px-2">
            {data.proactive_insights.slice(0, 6).map(insight => ( // Limitar a 6 en el dashboard
              <Card key={insight.id} className="modern-card border-0 shadow-medium hover:shadow-strong transition-all duration-300 cursor-pointer hover:scale-105 group" onClick={() => setViewingInsight(insight)}>
                <CardHeader className="pb-3">
                  <div className="flex items-center gap-3">
                     <div className="w-1.5 h-1.5 rounded-full bg-primary"></div>
                     {getInsightIcon(insight.type)}
                     <CardTitle className="text-lg font-semibold group-hover:text-primary transition-colors">
                       {insight.type.charAt(0).toUpperCase() + insight.type.slice(1)}
                     </CardTitle>
                  </div>
                </CardHeader>
                <CardContent className="pt-0">
                  <p className="text-sm text-muted-foreground line-clamp-3 mb-4 leading-relaxed">{insight.summary}</p>
                  <div className="text-xs space-y-2">
                    <p className="font-semibold text-foreground">Ítems Relacionados:</p>
                    {insight.related_items.slice(0, 2).map((item, idx) => (
                      <p key={idx} className="flex items-center gap-2 text-muted-foreground truncate">
                        <FileText className="h-3 w-3 text-primary/60" />
                        <span className="truncate">{item.title || item.reference}</span>
                      </p>
                    ))}
                  </div>
                </CardContent>
              </Card>
            ))}
            {data.proactive_insights.length === 0 && (
              <p className="text-center text-muted-foreground py-10 col-span-full">Kognito aún no ha encontrado descubrimientos proactivos.</p>
            )}
          </div>
        </div>

        {/* Nueva Sección para Preguntas de Análisis */}
        <div className="spacing-section mt-16">
          <h2 className="text-4xl font-bold tracking-tight mb-10 bg-gradient-to-r from-foreground to-muted-foreground bg-clip-text text-transparent">
            Preguntas de Análisis
          </h2>
          <div className="grid gap-6 md:grid-cols-2 px-2">
            <QuestionSlider
              title="Brechas de Conocimiento"
              questions={analysisData
                .filter(a => a.file_name.startsWith('Colección:'))
                .flatMap(a => a.result_payload.emergent_knowledge_gaps || [])
                .slice(0, 10)
              }
              icon={<Search className="h-5 w-5 text-primary" />}
              emptyMessage="No hay brechas de conocimiento disponibles. Es posible que no se hayan cargado datos de análisis de colecciones."
              onReload={async () => {
                setIsLoading(true);
                try {
                  const analysesResponse = await apiClient.post('/api/get-saved-analyses', { all: true });
                  setAnalysisData(analysesResponse.data);
                  toast.success('Datos de análisis recargados.');
                } catch (error) {
                  toast.error('Error al recargar datos de análisis.');
                  console.error("Reload analyses error:", error);
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
              questions={analysisData
                .filter(a => !a.file_name.startsWith('Colección:'))
                .flatMap(a => a.result_payload.knowledge_gaps || [])
                .slice(0, 10)
              }
              icon={<BrainCircuit className="h-5 w-5 text-primary" />}
              emptyMessage="No hay preguntas para explorar disponibles. Es posible que no se hayan cargado datos de análisis de documentos individuales."
              onReload={async () => {
                setIsLoading(true);
                try {
                  const analysesResponse = await apiClient.post('/api/get-saved-analyses', { all: true });
                  setAnalysisData(analysesResponse.data);
                  toast.success('Datos de análisis recargados.');
                } catch (error) {
                  toast.error('Error al recargar datos de análisis.');
                  console.error("Reload analyses error:", error);
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
      </div>
      
      <WelcomeDialog isOpen={isWelcomeDialogOpen} onOpenChange={setIsWelcomeDialogOpen} />

      {/* El diálogo para mostrar los detalles */}
      <InsightDetailDialog 
        isOpen={!!viewingInsight} 
        onOpenChange={(open: boolean) => !open && setViewingInsight(null)}
        insight={viewingInsight}
      />
    </>
  );
}
