import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { Analysis, ThemeReference, GroupedTopic, DetailedCluster } from '@/lib/models';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ScrollText, Target, Brain, HelpCircle, AlertTriangle, Volume2, Loader2, Pause, Network, BarChart3, Info, Zap } from 'lucide-react';
import { InteractiveTag } from '@/components/analysis/InteractiveTag';
import { ActionableButton } from '@/components/analysis/ActionableButton';
import { SectionTTSButton } from './analysis-detail-dialog';

interface SemanticAnalysisProps {
  analysis: Analysis;
  semanticColors: any;
  handleThemeClick: (theme: ThemeReference) => void;
  handleConceptClick: (concept: string) => void;
  openGapsSlider: (gaps: any[], title: string) => void;
  openQuestionsSlider: (questions: any[], title: string) => void;
  play: (text: string) => void;
  isLoading: boolean;
  isPlaying: boolean;
  activeText: string | null;
}

const SemanticAnalysis: React.FC<SemanticAnalysisProps> = ({
  analysis,
  semanticColors,
  handleThemeClick,
  handleConceptClick,
  openGapsSlider,
  openQuestionsSlider,
  play,
  isLoading,
  isPlaying,
  activeText,
}) => {
  const semanticData = analysis.result || analysis.full_data || {};
  const textToRead = semanticData?.resumen_semantico || analysis.summary || "";

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-2 mb-2">
        <div className="flex items-center gap-2">
          <Network className={`w-6 h-6 ${semanticColors.icon}`} />
          <h3 className="text-2xl font-bold">Análisis Semántico Avanzado</h3>
        </div>
        <Button
          onClick={() => play(textToRead)}
          variant="outline"
          size="sm"
          className="gap-2"
          disabled={isLoading}
        >
          {isLoading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : isPlaying ? (
            <Pause className="h-4 w-4" />
          ) : (
            <Volume2 className="h-4 w-4" />
          )}
          {isLoading ? 'Cargando...' : isPlaying ? 'Pausar' : 'Escuchar'}
        </Button>
      </div>

      <Tabs defaultValue="summary" className="w-full">
        <TabsList className="grid w-full grid-cols-5 mb-8">
          <TabsTrigger value="summary" className="gap-2">
            <ScrollText className="w-4 h-4" />
            <span className="hidden sm:inline">Resumen</span>
          </TabsTrigger>
          <TabsTrigger value="topics" className="gap-2">
            <Target className="w-4 h-4" />
            <span className="hidden sm:inline">Temas</span>
          </TabsTrigger>
          <TabsTrigger value="concepts" className="gap-2">
            <Brain className="w-4 h-4" />
            <span className="hidden sm:inline">Conceptos</span>
          </TabsTrigger>
          <TabsTrigger value="insights" className="gap-2">
            <Zap className="w-4 h-4" />
            <span className="hidden sm:inline">Hallazgos</span>
          </TabsTrigger>
          <TabsTrigger value="metrics" className="gap-2">
            <BarChart3 className="w-4 h-4" />
            <span className="hidden sm:inline">Métricas</span>
          </TabsTrigger>
        </TabsList>

        {/* TAB: RESUMEN */}
        <TabsContent value="summary" className="space-y-4 animate-in fade-in-50 duration-500">
          {(semanticData?.resumen_semantico || analysis.summary) && (
            <Card className={`${semanticColors.cardBg} border-none shadow-md`}>
              <CardHeader className="pb-2">
                <CardTitle className={`text-lg font-bold ${semanticColors.cardTitle} flex items-center justify-between`}>
                  <span>Resumen Semántico</span>
                  <SectionTTSButton
                    text={semanticData?.resumen_semantico || analysis.summary || ""}
                    play={play}
                    isLoading={isLoading}
                    isPlaying={isPlaying}
                    activeText={activeText}
                  />
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="prose prose-sm max-w-none dark:prose-invert text-muted-foreground leading-relaxed">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{semanticData?.resumen_semantico || analysis.summary}</ReactMarkdown>
                </div>
              </CardContent>
            </Card>
          )}

          {semanticData?.kai_synthesis && (
            <div className="p-4 rounded-xl bg-gradient-to-br from-indigo-500/10 to-purple-500/10 border border-indigo-500/20">
              <h4 className="text-sm font-bold uppercase tracking-wider text-indigo-600 dark:text-indigo-400 mb-2 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Zap className="w-4 h-4" />
                  Síntesis de KAI
                </div>
                <SectionTTSButton
                  text={semanticData.kai_synthesis}
                  play={play}
                  isLoading={isLoading}
                  isPlaying={isPlaying}
                  activeText={activeText}
                />
              </h4>
              <p className="text-sm italic text-foreground/80 leading-relaxed">
                {semanticData.kai_synthesis}
              </p>
            </div>
          )}
        </TabsContent>

        {/* TAB: TEMAS Y CLUSTERS */}
        <TabsContent value="topics" className="space-y-6 animate-in fade-in-50 duration-500">
          {semanticData?.temas_transversales && semanticData.temas_transversales.length > 0 && (
            <div>
              <h4 className={`text-lg font-bold mb-4 flex items-center gap-2 ${semanticColors.icon}`}>
                <Target className="w-5 h-5" />
                Temas Transversales
              </h4>
              <div className="flex flex-wrap gap-2">
                {semanticData.temas_transversales.map((theme: ThemeReference, index: number) => (
                  <InteractiveTag
                    key={index}
                    type="theme"
                    label={theme.theme}
                    onClick={() => handleThemeClick(theme)}
                  />
                ))}
              </div>
            </div>
          )}

          {semanticData?.grouped_topics && semanticData.grouped_topics.length > 0 && (
            <div>
              <h4 className="text-md font-bold mb-4 flex items-center gap-2">
                <Network className="w-5 h-5 text-blue-500" />
                Tópicos Agrupados
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {semanticData.grouped_topics.map((topic: GroupedTopic, index: number) => (
                  <Card key={index} className="border-muted/60">
                    <CardHeader className="py-3 px-4 flex flex-row items-center justify-between space-y-0">
                      <CardTitle className="text-sm font-bold">{topic.topic}</CardTitle>
                      <Badge variant="secondary">{topic.mentions} menciones</Badge>
                    </CardHeader>
                    {topic.description && (
                      <CardContent className="py-2 px-4">
                        <p className="text-xs text-muted-foreground">{topic.description}</p>
                      </CardContent>
                    )}
                  </Card>
                ))}
              </div>
            </div>
          )}

          {semanticData?.detailed_clusters && semanticData.detailed_clusters.length > 0 && (
            <div>
              <h4 className="text-md font-bold mb-4 flex items-center gap-2">
                <BarChart3 className="w-5 h-5 text-emerald-500" />
                Clusters Detallados
              </h4>
              <div className="space-y-3">
                {semanticData.detailed_clusters.map((cluster: DetailedCluster, index: number) => (
                  <div key={index} className="p-4 rounded-lg border bg-card/50">
                    <div className="flex items-center justify-between mb-2">
                      <h5 className="font-bold text-foreground flex items-center gap-2">
                        <span className="w-6 h-6 rounded-full bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 flex items-center justify-center text-[10px]">
                          {cluster.cluster_id}
                        </span>
                        {cluster.representative_term}
                      </h5>
                      <span className="text-xs text-muted-foreground">{cluster.total_mentions} menciones totales</span>
                    </div>
                    <div className="text-sm text-muted-foreground mb-3">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {cluster.description}
                      </ReactMarkdown>
                    </div>
                    <div className="flex flex-wrap gap-1">
                      {cluster.topics.map((t, i) => (
                        <Badge key={i} variant="outline" className="text-[10px] py-0">{t}</Badge>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </TabsContent>

        {/* TAB: CONCEPTOS */}
        <TabsContent value="concepts" className="space-y-6 animate-in fade-in-50 duration-500">
          {semanticData?.conceptos_centrales && semanticData.conceptos_centrales.length > 0 && (
            <div>
              <h4 className={`text-lg font-bold mb-4 flex items-center gap-2 ${semanticColors.icon}`}>
                <Brain className="w-5 h-5" />
                Conceptos Centrales
              </h4>
              <div className="flex flex-wrap gap-2">
                {semanticData.conceptos_centrales.map((concept: string, index: number) => (
                  <InteractiveTag
                    key={index}
                    type="concept"
                    label={concept.split(':')[0]}
                    onClick={() => handleConceptClick(concept)}
                    className={semanticColors.tag}
                  />
                ))}
              </div>
            </div>
          )}

          {semanticData?.patrones_semanticos && (
            <div>
              <h4 className="text-md font-bold mb-4 flex items-center gap-2">
                <Network className="w-5 h-5 text-indigo-500" />
                Patrones Semánticos Detectados
              </h4>
              <div className="p-4 rounded-xl border bg-indigo-50/20 dark:bg-indigo-900/10">
                <pre className="text-xs text-muted-foreground whitespace-pre-wrap">
                  {JSON.stringify(semanticData.patrones_semanticos, null, 2)}
                </pre>
              </div>
            </div>
          )}
        </TabsContent>

        {/* TAB: HALLAZGOS */}
        <TabsContent value="insights" className="space-y-6 animate-in fade-in-50 duration-500">
          {semanticData?.brechas_conocimiento && semanticData.brechas_conocimiento.length > 0 && (
            <ActionableButton
              title="Brechas de Conocimiento"
              description="Identifica áreas donde el conocimiento es incompleto o requiere mayor investigación."
              count={semanticData.brechas_conocimiento.length}
              variant="gap"
              onClick={() => openGapsSlider?.(semanticData.brechas_conocimiento || [], "Brechas de Conocimiento Detectadas")}
            />
          )}

          {semanticData?.problematic_areas && semanticData.problematic_areas.length > 0 && (
            <div>
              <h4 className={`text-lg font-bold mb-4 flex items-center gap-2 ${semanticColors.icon}`}>
                <AlertTriangle className="w-5 h-5" />
                Áreas Problemáticas
              </h4>
              <div className="space-y-3">
                {semanticData.problematic_areas.map((area: any, index: number) => (
                  <div key={index} className="p-3 rounded-lg border border-red-100 dark:border-red-900/30 bg-red-50/30 dark:bg-red-900/10 flex gap-3 items-start">
                    <AlertTriangle className="w-4 h-4 text-red-500 mt-0.5" />
                    <div className="flex-1">
                      <p className="text-sm font-medium">{typeof area === 'string' ? area : (area.issue || area.description || area.gap || JSON.stringify(area))}</p>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 text-[10px]"
                      onClick={() => openQuestionsSlider([area], "Detalle de Área Problemática")}
                    >
                      Ver más
                    </Button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </TabsContent>

        {/* TAB: MÉTRICAS */}
        <TabsContent value="metrics" className="space-y-6 animate-in fade-in-50 duration-500">
          {semanticData?.clustering_metrics && (
            <div>
              <h4 className="text-lg font-bold mb-4 flex items-center gap-2">
                <BarChart3 className="w-5 h-5 text-primary" />
                Métricas de Clustering
              </h4>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="p-4 rounded-xl bg-muted/30 text-center">
                  <span className="text-xs font-bold text-muted-foreground block mb-1">K Óptimo</span>
                  <span className="text-xl font-black">{semanticData.clustering_metrics.optimal_k}</span>
                </div>
                <div className="p-4 rounded-xl bg-muted/30 text-center">
                  <span className="text-xs font-bold text-muted-foreground block mb-1">Silhouette</span>
                  <span className="text-xl font-black">{semanticData.clustering_metrics.silhouette_score?.toFixed(3)}</span>
                </div>
                <div className="p-4 rounded-xl bg-muted/30 text-center">
                  <span className="text-xs font-bold text-muted-foreground block mb-1">Inercia</span>
                  <span className="text-xl font-black">{Math.round(semanticData.clustering_metrics.inertia)}</span>
                </div>
                <div className="p-4 rounded-xl bg-muted/30 text-center">
                  <span className="text-xs font-bold text-muted-foreground block mb-1">Método</span>
                  <span className="text-sm font-bold uppercase">{semanticData.clustering_metrics.method || "K-Means"}</span>
                </div>
              </div>
            </div>
          )}

          {semanticData?.analysis_metadata && (
            <div>
              <h4 className="text-md font-bold mb-4 flex items-center gap-2">
                <Info className="w-5 h-5 text-slate-500" />
                Metadatos del Análisis
              </h4>
              <div className="p-4 rounded-xl border bg-card text-xs space-y-2">
                <div className="flex justify-between border-b pb-1">
                  <span className="text-muted-foreground">Herramienta:</span>
                  <span className="font-mono">{semanticData.analysis_metadata.tool_used}</span>
                </div>
                <div className="flex justify-between border-b pb-1">
                  <span className="text-muted-foreground">Tipo de Análisis:</span>
                  <span className="font-mono">{semanticData.analysis_metadata.analysis_type}</span>
                </div>
                <div className="flex justify-between border-b pb-1">
                  <span className="text-muted-foreground">Total Tópicos:</span>
                  <span className="font-mono">{semanticData.analysis_metadata.total_topics}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Fecha:</span>
                  <span className="font-mono">{semanticData.analysis_metadata.created_at}</span>
                </div>
              </div>
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default SemanticAnalysis;
