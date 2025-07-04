// En: src/app/(dashboard)/dashboard/page.tsx

'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Bar, BarChart, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import apiClient from '@/lib/api';
import { toast } from 'sonner';
import { Badge } from '@/components/ui/badge';
import { InsightDetailDialog } from '@/components/InsightDetailDialog'; // Importamos el nuevo diálogo
import { HelpCircle, Bot, Library, FileText, FolderKanban, Notebook, Calendar, Search, ScanSearch, BrainCircuit } from 'lucide-react';
import Link from 'next/link';

// Tipos para los datos que esperamos de la API
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
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [viewingInsight, setViewingInsight] = useState<Insight | null>(null);

  const [analysisData, setAnalysisData] = useState<AnalysisData[]>([]);

  useEffect(() => {
    const fetchInsights = async () => {
      setIsLoading(true);
      try {
        const [insightsResponse, analysesResponse] = await Promise.all([
          apiClient.post('/api/dashboard-insights', { all: false }), // Pedir solo los insights para el dashboard
          apiClient.post('/api/get-saved-analyses', { all: true })
        ]);
        setData(insightsResponse.data);
        setAnalysisData(analysesResponse.data);
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
        return <Bot className="h-5 w-5 text-cyan-600" />;
      case 'connection':
        return <Library className="h-5 w-5 text-cyan-600" />;
      case 'project':
        return <FolderKanban className="h-5 w-5 text-cyan-600" />;
      default:
        return <FileText className="h-5 w-5 text-cyan-600" />;
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
      <div className="p-6 space-y-6">
        <div>
          <h1 className="text-3xl font-bold">Dashboard de Insights</h1>
          <p className="text-muted-foreground">Kognito está encontrando patrones y conexiones en tu conocimiento.</p>
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          {/* Gráfico de Temas Principales */}
          <Card className="rounded-3xl backdrop-blur-xl bg-card/80 border-0 shadow-xl">
            <CardHeader>
              <CardTitle>Temas Principales</CardTitle>
              <CardDescription className="space-y-1">
                <span>Tópicos más frecuentes en tu base de conocimiento.</span>
                <div className="text-xs text-muted-foreground/70 bg-muted/20 px-2 py-1 rounded-full inline-block mt-2">
                  💡 Nota: Actualmente no agrupados por similitud semántica
                </div>
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-6">
              <div className="flex justify-end mb-4 space-x-2">
                <input
                  type="number"
                  min="1"
                  defaultValue="20"
                  className="px-3 py-2 w-24 border-0 bg-muted/30 rounded-2xl text-sm focus:ring-2 focus:ring-primary/20 focus:bg-muted/50 transition-all"
                  id="maxTermsInput"
                  placeholder="Max términos"
                />
                <button 
                  className="px-4 py-2 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700 text-white rounded-2xl font-medium shadow-lg hover:shadow-xl transition-all duration-200 flex items-center gap-2"
                  onClick={async () => {
                    setIsLoading(true);
                    try {
                      // Get the max terms value from input
                      const maxTermsInput = document.getElementById('maxTermsInput') as HTMLInputElement;
                      const maxTerms = maxTermsInput.value ? parseInt(maxTermsInput.value) : undefined;
                      // Trigger semantic analysis process with optional max_terms parameter
                      const formData = new FormData();
                      if (maxTerms && maxTerms > 0) {
                        formData.append('max_terms', maxTerms.toString());
                      }
                      const triggerResponse = await apiClient.post('/api/update-semantic-topics', formData);
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
                      <stop offset="0%" stopColor="#06b6d4" />
                      <stop offset="100%" stopColor="#2563eb" />
                    </linearGradient>
                  </defs>
                  <XAxis type="number" hide />
                  <YAxis dataKey="topic" type="category" stroke="hsl(var(--foreground))" fontSize={16} tickLine={false} axisLine={false} width={200} interval={0} tick={{ dy: 15 }} />
                  <Tooltip 
                    cursor={{ fill: 'hsl(var(--muted))' }} 
                    contentStyle={{ 
                      backgroundColor: 'hsl(var(--background))', 
                      border: '1px solid hsl(var(--border))', 
                      borderRadius: '12px',
                      boxShadow: '0 10px 25px rgba(0,0,0,0.1)'
                    }} 
                  />
                  <Bar dataKey="mentions" fill="url(#barGradient)" radius={[0, 8, 8, 0]} barSize={40} />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* Tarjeta de Ayuda */}
          <Card className="rounded-3xl backdrop-blur-xl bg-card/80 border-0 shadow-xl">
              <CardHeader>
                  <CardTitle className="flex items-center gap-2"><HelpCircle />Ayuda y Capacidades</CardTitle>
                  <CardDescription>Descubre qué puedes pedirle a Kognito en el chat o desde la interfaz.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4 text-sm overflow-y-auto h-[350px] pr-2">
                   <div>
                      <p className="font-semibold flex items-center gap-2"><Notebook className="h-4 w-4" /> Gestión de Notas</p>
                      <p className="text-muted-foreground pl-6">"Crea una nota sobre...", "muéstrame mis notas de trabajo", "edita la nota sobre la reunión".</p>
                  </div>
                   <div>
                      <p className="font-semibold flex items-center gap-2"><Calendar className="h-4 w-4" /> Agenda</p>
                      <p className="text-muted-foreground pl-6">"Agenda una reunión para mañana a las 3pm", "¿qué tengo para hoy?".</p>
                  </div>
                   <div>
                      <p className="font-semibold flex items-center gap-2"><Search className="h-4 w-4" /> Búsqueda Web</p>
                      <p className="text-muted-foreground pl-6">"Busca las últimas noticias sobre IA generativa", "¿cuál es la capital de Mongolia?".</p>
                  </div>
                   <div>
                      <p className="font-semibold flex items-center gap-2"><ScanSearch className="h-4 w-4" /> Análisis de Conocimiento</p>
                      <p className="text-muted-foreground pl-6">Activa esta herramienta en el chat para analizar profundamente tu base de conocimientos personal y obtener respuestas basadas en tus documentos y notas.</p>
                  </div>
                   <div>
                      <p className="font-semibold flex items-center gap-2"><BrainCircuit className="h-4 w-4" /> Búsqueda y Análisis</p>
                      <p className="text-muted-foreground pl-6">Utiliza esta herramienta en el chat para realizar investigaciones exhaustivas que combinan búsquedas en la web con tu base de conocimientos personal, proporcionando un análisis completo y detallado.</p>
                  </div>
              </CardContent>
          </Card>
        </div>

        {/* Galería de Tarjetas de Insights */}
        <div>
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-2xl font-bold">Descubrimientos Proactivos</h2>
            <Link href="/dashboard/insights" className="text-sm font-medium text-cyan-600 hover:text-cyan-500 transition-colors">
              Ver todo
            </Link>
          </div>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {data.proactive_insights.slice(0, 6).map(insight => ( // Limitar a 6 en el dashboard
              <Card key={insight.id} className="rounded-3xl backdrop-blur-xl bg-card/80 border-0 shadow-xl hover:shadow-2xl transition-all duration-200 cursor-pointer hover:scale-105" onClick={() => setViewingInsight(insight)}>
                <CardHeader>
                  <div className="flex items-center gap-2">
                     {getInsightIcon(insight.type)}
                     <CardTitle className="text-base">{insight.type.charAt(0).toUpperCase() + insight.type.slice(1)}</CardTitle>
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground line-clamp-3 mb-3">{insight.summary}</p>
                  <div className="text-xs space-y-1">
                    <p className="font-semibold">Ítems Relacionados:</p>
                    {insight.related_items.slice(0, 2).map((item, idx) => (
                      <p key={idx} className="flex items-center gap-1.5 text-muted-foreground truncate">
                        <FileText className="h-3 w-3" />
                        {item.title || item.reference}
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
        <div>
          <h2 className="text-2xl font-bold mb-4">Preguntas de Análisis</h2>
          <div className="grid gap-4 md:grid-cols-2">
            <Card className="rounded-3xl backdrop-blur-xl bg-card/80 border-0 shadow-xl">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <HelpCircle className="h-5 w-5 text-cyan-600" />
                  Brechas de Conocimiento (Colecciones)
                </CardTitle>
              </CardHeader>
              <CardContent>
                {analysisData.filter(a => a.file_name.startsWith('Colección:')).length > 0 ? (
                  <ul className="list-disc list-inside space-y-2 text-sm text-muted-foreground">
                    {analysisData.filter(a => a.file_name.startsWith('Colección:')).flatMap(a => a.result_payload.brechas_conocimiento || []).slice(0, 5).map((gap, idx) => (
                      <li key={idx}>{gap}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-muted-foreground">No hay brechas de conocimiento disponibles.</p>
                )}
              </CardContent>
            </Card>
            <Card className="rounded-3xl backdrop-blur-xl bg-card/80 border-0 shadow-xl">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <HelpCircle className="h-5 w-5 text-cyan-600" />
                  Preguntas para Explorar (Documentos)
                </CardTitle>
              </CardHeader>
              <CardContent>
                {analysisData.filter(a => !a.file_name.startsWith('Colección:')).length > 0 ? (
                  <ul className="list-disc list-inside space-y-2 text-sm text-muted-foreground">
                    {analysisData.filter(a => !a.file_name.startsWith('Colección:')).flatMap(a => a.result_payload.preguntas_para_explorar || []).slice(0, 5).map((question, idx) => (
                      <li key={idx}>{question}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-muted-foreground">No hay preguntas para explorar disponibles.</p>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
      
      {/* El diálogo para mostrar los detalles */}
      <InsightDetailDialog 
        isOpen={!!viewingInsight} 
        onOpenChange={(open: boolean) => !open && setViewingInsight(null)}
        insight={viewingInsight}
      />
    </>
  );
}
