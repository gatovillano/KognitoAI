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
import { EmptyChat } from '@/components/EmptyChat';
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

  // Chat States
  const [chatInput, setChatInput] = useState('');
  const [isResponding, setIsResponding] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isKnowledgeAnalysisActive, setIsKnowledgeAnalysisActive] = useState(false);
  const [isWebSearchActive, setIsWebSearchActive] = useState(false);
  const [isComprehensiveAnalysisActive, setIsComprehensiveAnalysisActive] = useState(false);
  const [isUploadingFile, setIsUploadingFile] = useState(false);
  const [isProcessingAudio, setIsProcessingAudio] = useState(false);
  const [isDeepResearchActive, setIsDeepResearchActive] = useState(false);
  const [workspaceId, setWorkspaceId] = useState<string | undefined>(undefined);
  const [selectedContext, setSelectedContext] = useState<any[]>([]);

  // Dashboard Data States
  const [dashboardData, setDashboardData] = useState<DashboardInsightsResponse | null>(null);
  const [isLoadingDashboard, setIsLoadingDashboard] = useState(true);
  const [isInfoSheetOpen, setIsInfoSheetOpen] = useState(false);
  const [selectedKeyTopic, setSelectedKeyTopic] = useState<KeyTopic | null>(null);
  const [isKeyTopicDetailDialogOpen, setIsKeyTopicDetailDialogOpen] = useState(false);

  const textAreaRef = useRef<HTMLTextAreaElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioStreamRef = useRef<MediaStream | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

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

  // Chat Handlers
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioStreamRef.current = stream;
      mediaRecorderRef.current = new MediaRecorder(stream);
      audioChunksRef.current = [];

      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0) audioChunksRef.current.push(event.data);
      };

      mediaRecorderRef.current.onstop = async () => {
        await new Promise(resolve => window.setTimeout(resolve, 0));
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });

        if (audioBlob.size <= 110) {
          toast.error('La grabación quedó incompleta. Intenta de nuevo.');
          setIsRecording(false);
          audioStreamRef.current?.getTracks().forEach(track => track.stop());
          audioStreamRef.current = null;
          return;
        }

        const formData = new FormData();
        formData.append('file', audioBlob, 'recording.webm');

        try {
          const response = await apiClient.post('/api/transcribe-audio', formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
          });
          setChatInput(response.data.transcription);
          toast.success('Transcripción completada');
        } catch (error) {
          toast.error('Error al transcribir audio');
        } finally {
          setIsRecording(false);
          audioStreamRef.current?.getTracks().forEach(track => track.stop());
          audioStreamRef.current = null;
        }
      };

      mediaRecorderRef.current.start(500);
      setIsRecording(true);
    } catch (error) {
      toast.error('Error al acceder al micrófono');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current?.state === 'recording') {
      mediaRecorderRef.current.requestData();
      mediaRecorderRef.current.stop();
    }
  };

  const handleChatSubmit = async (e?: React.FormEvent, messageTextFromInput?: string) => {
    if (e) e.preventDefault();
    const messageToProcess = messageTextFromInput || chatInput;
    if (!messageToProcess.trim()) return;

    setIsResponding(true);
    try {
      const threadResponse = await apiClient.post('/api/threads', {});
      const newThread = threadResponse.data;

      const initialMessage = messageToProcess;
      const initialRagContext = selectedContext.length > 0 ? JSON.stringify(selectedContext) : '';

      const newSearchParams = new URLSearchParams();
      if (initialMessage) {
        newSearchParams.set('initialMessage', initialMessage);
      }
      if (initialRagContext) {
        newSearchParams.set('initialRagContext', initialRagContext);
      }

      router.push(`/chat/${newThread.id}?${newSearchParams.toString()}`);
    } catch (error) {
      console.error('Error al iniciar el chat:', error);
      toast.error('Error al iniciar el chat');
      setIsResponding(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files?.length || isUploadingFile) return;

    setIsUploadingFile(true);
    try {
      const threadResponse = await apiClient.post('/api/threads', {});
      const newThread = threadResponse.data;
      const formData = new FormData();

      Array.from(e.target.files).forEach(file => formData.append('files', file));
      formData.append('topic', 'General');

      await apiClient.post('/api/documents/upload-document', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      toast.success('Archivos subidos con éxito');
      router.push(`/chat/${newThread.id}`);
    } catch (error) {
      toast.error('Error al subir archivos');
    } finally {
      setIsUploadingFile(false);
    }
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
        className="pt-8"
      >
        <EmptyChat
          onSendMessage={handleChatSubmit}
          newMessage={chatInput}
          setNewMessage={setChatInput}
          isResponding={isResponding}
          isRecording={isRecording}
          isProcessingAudio={isProcessingAudio}
          isUploadingFile={isUploadingFile}
          isKnowledgeAnalysisActive={isKnowledgeAnalysisActive}
          isWebSearchActive={isWebSearchActive}
          isComprehensiveAnalysisActive={isComprehensiveAnalysisActive}
          isDeepResearchActive={isDeepResearchActive}
          onKeyDown={() => {}}
          onToggleKnowledgeAnalysis={() => setIsKnowledgeAnalysisActive(!isKnowledgeAnalysisActive)}
          onToggleWebSearch={() => setIsWebSearchActive(!isWebSearchActive)}
          onToggleComprehensiveAnalysis={() => setIsComprehensiveAnalysisActive(!isComprehensiveAnalysisActive)}
          onToggleDeepResearch={() => setIsDeepResearchActive(!isDeepResearchActive)}
          onStartRecording={startRecording}
          onStopRecording={stopRecording}
          onFileUpload={handleFileUpload}
          onRemoveContextItem={() => { }}
          onPaste={() => { }}
          isUploadingImages={false}
          uploadedImagePreviews={[]}
          onRemoveImage={() => { }}
          onImageUpload={() => { }}
          workspaceId={workspaceId}
          selectedContext={selectedContext}
          onContextSelected={setSelectedContext}
          isVectorizingFile={false}
        />
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
