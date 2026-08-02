'use client';

import { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import {
  LayoutDashboard,
  RefreshCcw,
  Plus,
  BarChart3,
  Activity,
  FileText,
  Sparkles,
  AlertTriangle,
  TrendingUp,
  HelpCircle,
  Info,
  Loader2
} from 'lucide-react';
import { toast } from 'sonner';

import apiClient from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';
import { CommonChat } from '@/components/CommonChat';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '@/components/ui/sheet';
import { QuestionSlider } from '@/components/QuestionSlider';
import { KeyTopicSlider } from '@/components/KeyTopicSlider';
import { KeyTopicDetailDialog } from '@/components/KeyTopicDetailDialog';
import { DashboardInsightsResponse, KeyTopic } from '@/lib/models';

export default function DashboardPage() {
  const { user } = useAuth();
  const router = useRouter();

  // Dashboard Data States
  const [dashboardData, setDashboardData] = useState<DashboardInsightsResponse | null>(null);
  const [isLoadingDashboard, setIsLoadingDashboard] = useState(true);
  const [isInfoSheetOpen, setIsInfoSheetOpen] = useState(false);
  const [selectedKeyTopic, setSelectedKeyTopic] = useState<KeyTopic | null>(null);
  const [isKeyTopicDetailDialogOpen, setIsKeyTopicDetailDialogOpen] = useState(false);

  // Fetch Dashboard Data
  const fetchDashboardData = useCallback(async () => {
    if (!user?.account_id) return;

    setIsLoadingDashboard(true);
    try {
      const response = await apiClient.post<DashboardInsightsResponse>('/api/dashboard-insights', {});
      setDashboardData(response.data);
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
      // Silent error for dashboard data to not interrupt chat
    } finally {
      setIsLoadingDashboard(false);
    }
  }, [user?.account_id]);

  useEffect(() => {
    fetchDashboardData();
  }, [fetchDashboardData]);

  const handleRefreshDashboard = () => {
    fetchDashboardData();
    toast.success('Datos actualizados');
  };

  const systemStats = useMemo(() => {
    if (!dashboardData) return null;
    const totalProcessed = dashboardData.analysis_stats_by_type?.reduce((acc, stat) => acc + stat.completed + stat.failed, 0) || 0;
    const successRate = totalProcessed > 0 ? (dashboardData.analysis_stats_by_type?.reduce((acc, stat) => acc + stat.completed, 0) || 0) / totalProcessed * 100 : 0;
    return {
      totalProcessed,
      successRate: Math.round(successRate),
      activeInsights: dashboardData.total_proactive_insights || 0,
    };
  }, [dashboardData]);

  return (
    <div className="p-4 sm:p-8 max-w-7xl mx-auto overflow-x-hidden space-y-8 animate-in fade-in duration-500">
      {/* Header Section */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <h1 className="text-2xl sm:text-3xl font-bold flex items-center truncate">
            <LayoutDashboard className="mr-2 sm:mr-3 h-6 w-6 sm:h-8 sm:w-8 text-primary flex-shrink-0" />
            <span className="truncate">Escritorio</span>
          </h1>
          <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground flex-shrink-0" onClick={() => setIsInfoSheetOpen(true)}>
            <Info className="h-4 w-4" />
          </Button>
        </div>
        <div className="flex items-center gap-2 w-full sm:w-auto">
          <Button variant="outline" size="sm" onClick={handleRefreshDashboard} disabled={isLoadingDashboard} className="flex-1 sm:flex-none">
            <RefreshCcw className={`h-4 w-4 mr-2 ${isLoadingDashboard ? 'animate-spin' : ''}`} />
            Actualizar
          </Button>
        </div>
      </div>

      {/* Stats Section */}
      <AnimatePresence mode="wait">
        {isLoadingDashboard ? (
          <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
            {[1, 2, 3, 4].map((i) => (
              <Card key={i} className="h-24 animate-pulse bg-muted/50 border-none" />
            ))}
          </div>
        ) : dashboardData && systemStats ? (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4"
          >
            <Card className="relative overflow-hidden bg-gradient-to-br from-blue-500/5 to-purple-500/5">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Total de Análisis</CardTitle>
                <BarChart3 className="h-4 w-4 text-blue-500" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{dashboardData.total_analysis_tasks}</div>
                <p className="text-xs text-muted-foreground">{dashboardData.total_proactive_insights} insights proactivos</p>
              </CardContent>
            </Card>

            <Card className="relative overflow-hidden bg-gradient-to-br from-green-500/5 to-emerald-500/5">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Tasa de Éxito</CardTitle>
                <Activity className="h-4 w-4 text-green-500" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{systemStats.successRate}%</div>
                <p className="text-xs text-muted-foreground">Sistema operativo</p>
              </CardContent>
            </Card>

            <Card className="relative overflow-hidden bg-gradient-to-br from-orange-500/5 to-red-500/5">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Procesados</CardTitle>
                <FileText className="h-4 w-4 text-orange-500" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{systemStats.totalProcessed}</div>
                <p className="text-xs text-muted-foreground">Documentos y tareas</p>
              </CardContent>
            </Card>

            <Card className="relative overflow-hidden bg-gradient-to-br from-yellow-500/5 to-amber-500/5">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Insights Activos</CardTitle>
                <Sparkles className="h-4 w-4 text-yellow-500" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{systemStats.activeInsights}</div>
                <p className="text-xs text-muted-foreground">Generados por KAI</p>
              </CardContent>
            </Card>
          </motion.div>
        ) : null}
      </AnimatePresence>

      {/* Sliders Section */}
      {!isLoadingDashboard && dashboardData && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="grid gap-4 md:grid-cols-2 lg:grid-cols-3"
        >
          <QuestionSlider
            title="Brechas de Conocimiento"
            questions={dashboardData.emergent_knowledge_gaps || []}
            icon={<AlertTriangle className="h-5 w-5 text-amber-500" />}
            emptyMessage="No se detectaron brechas recientes."
            autoSlide={true}
          />

          <KeyTopicSlider
            title="Temas Clave"
            keyTopics={dashboardData.key_topics || []}
            icon={<TrendingUp className="h-5 w-5 text-blue-500" />}
            emptyMessage="No hay temas clave recientes."
            autoSlide={true}
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
          />
        </motion.div>
      )}

      {/* Chat Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="pt-8 h-[650px]"
      >
        <CommonChat />
      </motion.div>

      {/* Dialogs & Info */}
      <KeyTopicDetailDialog
        isOpen={isKeyTopicDetailDialogOpen}
        onOpenChange={setIsKeyTopicDetailDialogOpen}
        keyTopic={selectedKeyTopic}
      />

      <Sheet open={isInfoSheetOpen} onOpenChange={setIsInfoSheetOpen}>
        <SheetContent side="right" className="w-full sm:max-w-md">
          <SheetHeader>
            <SheetTitle>Escritorio de Kognito AI</SheetTitle>
            <SheetDescription>
              Tu centro de control inteligente para interactuar con tu conocimiento.
            </SheetDescription>
          </SheetHeader>
          <div className="py-6 space-y-4 text-sm">
            <p>Desde aquí puedes acceder rápidamente a los insights generados por la IA y comenzar nuevas conversaciones.</p>
            <div className="space-y-2">
              <h4 className="font-bold">Secciones:</h4>
              <ul className="list-disc pl-5 space-y-1 text-muted-foreground">
                <li><strong>Estadísticas:</strong> Resumen de la actividad de análisis.</li>
                <li><strong>Insights:</strong> Temas clave y brechas detectadas automáticamente.</li>
                <li><strong>Chat:</strong> Interfaz principal para consultas y análisis.</li>
              </ul>
            </div>
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
}
