// En: src/app/(dashboard)/dashboard/page.tsx

'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Bar, BarChart, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import apiClient from '@/lib/api';
import { toast } from 'sonner';
import { InsightDetailDialog } from '@/components/InsightDetailDialog';
import { HelpCircle, Bot, Library, FileText, FolderKanban, Search, BrainCircuit, Sparkles, ArrowLeft } from 'lucide-react';
import Link from 'next/link';
import { InlineMarkdownRenderer } from '@/components/InlineMarkdownRenderer';
import { QuestionSlider } from '@/components/QuestionSlider';
import { CustomChartTooltip } from '@/components/CustomChartTooltip';
import { DashboardHelpCarousel } from '@/components/DashboardHelpCarousel';
import dynamic from 'next/dynamic';

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
  related_items: any[]; // Made required to match InsightDetailDialog component
  action_suggestion?: string;
  synthetic_name?: string; // Nuevo campo para el nombre sintético
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
  const [analysisData, setAnalysisData] = useState<AnalysisData[]>([]);
  const [isWelcomeDialogOpen, setIsWelcomeDialogOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [conversations, setConversations] = useState<Conversation[]>([]);

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(e.target.value);
  };

  useEffect(() => {
    const fetchInsights = async () => {
      setIsLoading(true);
      try {
        const [insightsResponse, analysesResponse, conversationsResponse] = await Promise.all([
          apiClient.post('/api/dashboard-insights', { all: false }),
          apiClient.post('/api/get-saved-analyses', { all: true }),
          apiClient.get('/api/threads') // Nueva llamada para obtener conversaciones
        ]);

        // Transform insights data to ensure related_items is always an array
        const transformedData = {
          ...insightsResponse.data,
          proactive_insights: (insightsResponse.data.proactive_insights || []).map((insight: any) => ({
            ...insight,
            related_items: insight.related_items || []
          }))
        };

        setData(transformedData);
        setAnalysisData(analysesResponse.data);
        setConversations(conversationsResponse.data); // Guardar las conversaciones

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

  if (!data || (data.key_topics.length === 0 && data.proactive_insights.length === 0 && conversations.length === 0)) {
    return (
      <div className="p-6 text-center">
        <p className="text-muted-foreground">No hay datos disponibles en este momento.</p>
      </div>
    );
  }

  return (
    <>
      <div className="p-4 sm:p-8 max-w-7xl mx-auto overflow-x-hidden">
        {/* Header moderno */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <div className="h-12 w-12 rounded-xl bg-primary/10 flex items-center justify-center">
              <Bot className="h-6 w-6 text-primary" />
            </div>
            <div>
              <h1 className="text-3xl font-bold">Dashboard de Insights</h1>
              <p className="text-muted-foreground">Kognito está encontrando patrones y conexiones en tu conocimiento de forma inteligente.</p>
            </div>
          </div>
          <Link href="/dashboard" className="inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 border border-input bg-background hover:bg-accent hover:text-accent-foreground h-10 px-4 py-2">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Volver al Dashboard
          </Link>
        </div>

        <div className="mb-8">
          <div className="relative">
            <svg className="absolute left-4 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <Input
              type="text"
              placeholder="Buscar en el dashboard..."
              value={searchTerm}
              onChange={handleSearchChange}
              className="pl-12 h-12 rounded-full bg-card border-0 shadow-sm focus:ring-2 focus:ring-primary/20"
            />
          </div>
        </div>

        {/* Gráfico de Temas Principales - Ahora ocupa el ancho completo */}
        <div className="mb-8 px-2">
          <div className="mb-6">
            <div>
              <h2 className="text-2xl font-semibold flex items-center">
                <Library className="mr-3 h-6 w-6 text-primary" />
                Temas Principales
              </h2>
              <p className="text-muted-foreground mt-1">Tópicos más frecuentes en tu base de conocimiento.</p>
            </div>
          </div>
          <Card className="modern-card border-0 shadow-medium hover:shadow-strong transition-all duration-300 h-full">
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
                          const dataResponse = await apiClient.post('/api/dashboard-insights', { all: false });
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
        </div>

        {/* El grid existente ahora contendrá la tarjeta de Ayuda y Capacidades y el nuevo panel de Conversaciones */}
        <div className="grid gap-8 lg:grid-cols-2 px-2">
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

          {/* Nuevo Panel de Últimas Conversaciones */}
          <Card className="modern-card border-0 shadow-medium hover:shadow-strong transition-all duration-300 h-full">
            <CardHeader className="pb-4">
              <CardTitle className="text-2xl font-bold flex items-center gap-3 mb-2">
                <div className="w-3 h-3 rounded-full bg-primary"></div>
                <Bot className="h-6 w-6 text-primary" />
                Últimas Conversaciones
              </CardTitle>
              <CardDescription className="text-lg">Tus interacciones más recientes con Kognito.</CardDescription>
            </CardHeader>
            <CardContent className="pt-0">
              {conversations.length > 0 ? (
                <div className="space-y-4">
                  {conversations.slice(0, 5).map(conv => (
                    <Link href={`/chat/${conv.id}`} key={conv.id} className="block p-3 rounded-lg bg-muted/40 hover:bg-muted/60 transition-colors duration-200">
                      <p className="font-medium text-foreground line-clamp-1">{conv.title || 'Conversación sin título'}</p>
                      <p className="text-sm text-muted-foreground">ID: {conv.id.substring(0, 8)}...</p>
                    </Link>
                  ))}
                </div>
              ) : (
                <p className="text-center text-muted-foreground py-4">No hay conversaciones recientes.</p>
              )}
              {conversations.length > 5 && (
                <div className="flex justify-end mt-4">
                  <Link href="/chat" className="typography-body-small font-medium text-primary hover:text-primary/80 transition-colors">
                    Ver todas
                  </Link>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Galería de Tarjetas de Insights */}
        <div className="spacing-section mt-16">
          <div className="mb-6">
            <div>
              <h2 className="text-2xl font-semibold flex items-center">
                <Sparkles className="mr-3 h-6 w-6 text-primary" />
                Descubrimientos Proactivos
              </h2>
              <p className="text-muted-foreground mt-1">Insights generados automáticamente por Kognito.</p>
            </div>
          </div>
          <div className="flex justify-end items-center spacing-component mb-10">
            <Link href="/dashboard/insights" className="typography-body-small font-medium text-primary hover:text-primary/80 transition-colors">
              Ver todo
            </Link>
          </div>
          <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3 px-2">
            {(data.proactive_insights || []).slice(0, 6).map(insight => ( // Limitar a 6 en el dashboard
              <Card key={insight.id} className="modern-card border-0 shadow-medium hover:shadow-strong transition-all duration-300 cursor-pointer hover:scale-105 group" onClick={() => setViewingInsight(insight)}>
                <CardHeader className="pb-3">
                  <div className="flex items-center gap-3">
                     <div className="w-1.5 h-1.5 rounded-full bg-primary"></div>
                     {getInsightIcon(insight.type)}
                     <CardTitle className="text-lg font-semibold group-hover:text-primary transition-colors">
                       {(insight.type || '').charAt(0).toUpperCase() + (insight.type || '').slice(1)}
                     </CardTitle>
                  </div>
                </CardHeader>
                <CardContent className="pt-0">
                  <p className="text-sm text-muted-foreground line-clamp-3 mb-4 leading-relaxed">{insight.summary}</p>
                  <div className="text-xs space-y-2">
                    <p className="font-semibold text-foreground">Ítems Relacionados:</p>
                    {(() => {
                      // Handle different possible structures of related_items
                      let items: any = insight.related_items || [];

                      // If related_items is an object with an 'items' property, use that
                      if (typeof items === 'object' && !Array.isArray(items) && (items as any).items) {
                        items = (items as any).items;
                      }

                      // Ensure we have an array
                      if (!Array.isArray(items)) {
                        items = [];
                      }

                      return items.slice(0, 2).map((item: any, idx: number) => (
                        <p key={idx} className="flex items-center gap-2 text-muted-foreground truncate">
                          <FileText className="h-3 w-3 text-primary/60" />
                          <span className="truncate">{item.title || item.reference || 'Sin título'}</span>
                        </p>
                      ));
                    })()}
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
          <div className="mb-6">
            <div>
              <h2 className="text-2xl font-semibold flex items-center">
                <Search className="mr-3 h-6 w-6 text-primary" />
                Preguntas de Análisis
              </h2>
              <p className="text-muted-foreground mt-1">Preguntas generadas a partir de tus datos para explorar.</p>
            </div>
          </div>
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
      <InsightDetailDialog isOpen={!!viewingInsight} onOpenChange={(open: boolean) => !open && setViewingInsight(null)} 
      insight={viewingInsight} />
    </>
  );
}

