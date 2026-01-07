import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { NoteCollectionAnalysisResult } from '@/lib/models';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { LibraryBig, Target, Zap, TrendingUp, HelpCircle, Info, MessageSquare, Activity } from 'lucide-react';
import { InteractiveTag } from '@/components/analysis/InteractiveTag';

import { SectionTTSButton } from './analysis-detail-dialog';

interface NoteCollectionAnalysisProps {
  analysis: NoteCollectionAnalysisResult;
  noteCollectionColors: any;
  handleThemeClick?: (theme: any) => void;
  handleConceptClick?: (concept: string) => void;
  openGapsSlider?: (gaps: any[], title: string) => void;
  openQuestionsSlider?: (questions: any[], title: string) => void;
  openSimpleListDialog?: (items: string[], title: string, description: string, icon: React.ReactNode, colorClass: string) => void;
  // TTS Props
  play: (text: string) => void;
  isLoading: boolean;
  isPlaying: boolean;
  activeText: string | null;
}

import { ActionableButton } from '@/components/analysis/ActionableButton';

const NoteCollectionAnalysis: React.FC<NoteCollectionAnalysisProps> = ({
  analysis,
  noteCollectionColors,
  handleThemeClick,
  handleConceptClick,
  openGapsSlider,
  openQuestionsSlider,
  openSimpleListDialog,
  play,
  isLoading,
  isPlaying,
  activeText
}) => {
  if (!analysis) return null;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 mb-2">
        <LibraryBig className={`w-6 h-6 ${noteCollectionColors.icon}`} />
        <h3 className="text-2xl font-bold">Análisis de Colección de Notas</h3>
      </div>

      <Tabs defaultValue="summary" className="w-full">
        <TabsList className="grid w-full grid-cols-4 mb-8">
          <TabsTrigger value="summary" className="gap-2">
            <Info className="w-4 h-4" />
            <span className="hidden sm:inline">Resumen</span>
          </TabsTrigger>
          <TabsTrigger value="general" className="gap-2">
            <Activity className="w-4 h-4" />
            <span className="hidden sm:inline">Análisis General</span>
          </TabsTrigger>
          <TabsTrigger value="insights" className="gap-2">
            <Zap className="w-4 h-4" />
            <span className="hidden sm:inline">Temas e Insights</span>
          </TabsTrigger>
          <TabsTrigger value="strategy" className="gap-2">
            <TrendingUp className="w-4 h-4" />
            <span className="hidden sm:inline">Estrategia</span>
          </TabsTrigger>
        </TabsList>

        {/* TAB: RESUMEN */}
        <TabsContent value="summary" className="space-y-4 animate-in fade-in-50 duration-500">
          {analysis.collection_summary && (
            <Card className={`${noteCollectionColors.cardBg} border-none shadow-md`}>
              <CardHeader className="pb-2 flex flex-row items-center justify-between">
                <CardTitle className={`text-lg font-bold ${noteCollectionColors.cardTitle}`}>Resumen de la Colección</CardTitle>
                <SectionTTSButton
                  text={analysis.collection_summary || ""}
                  play={play}
                  isLoading={isLoading}
                  isPlaying={isPlaying}
                  activeText={activeText}
                />
              </CardHeader>
              <CardContent>
                <div className="prose prose-sm max-w-none dark:prose-invert text-muted-foreground leading-relaxed">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {typeof analysis.collection_summary === 'string'
                      ? analysis.collection_summary
                      : (analysis.collection_summary as any)?.summary || JSON.stringify(analysis.collection_summary)}
                  </ReactMarkdown>
                </div>
              </CardContent>
            </Card>
          )}

          {analysis.kai_synthesis && (
            <div className="mt-6 p-5 rounded-xl bg-gradient-to-br from-amber-500/10 to-orange-500/10 border border-amber-500/20 relative group">
              <div className="absolute top-4 right-4 opacity-0 group-hover:opacity-100 transition-opacity">
                <SectionTTSButton
                  text={analysis.kai_synthesis}
                  play={play}
                  isLoading={isLoading}
                  isPlaying={isPlaying}
                  activeText={activeText}
                />
              </div>
              <h4 className="text-sm font-bold uppercase tracking-wider text-amber-600 dark:text-amber-400 mb-2 flex items-center gap-2">
                <Zap className="w-4 h-4" />
                Síntesis de KAI
              </h4>
              <div className="text-sm italic text-foreground/90 leading-relaxed">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{String(analysis.kai_synthesis)}</ReactMarkdown>
              </div>
            </div>
          )}

        </TabsContent>

        {/* TAB: ANÁLISIS GENERAL */}
        <TabsContent value="general" className="space-y-4 animate-in fade-in-50 duration-500">
          {analysis.general_analysis ? (
            <Card className="border-none shadow-sm bg-muted/30">
              <CardHeader className="pb-2 flex flex-row items-center justify-between">
                <CardTitle className="text-md font-semibold flex items-center gap-2">
                  <Activity className="w-4 h-4 text-primary" />
                  Análisis General Extenso
                </CardTitle>
                <SectionTTSButton
                  text={analysis.general_analysis || ""}
                  play={play}
                  isLoading={isLoading}
                  isPlaying={isPlaying}
                  activeText={activeText}
                />
              </CardHeader>
              <CardContent>
                <div className="prose prose-sm max-w-none dark:prose-invert text-muted-foreground leading-relaxed">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {typeof analysis.general_analysis === 'string'
                      ? analysis.general_analysis
                      : (analysis.general_analysis as any)?.analysis || JSON.stringify(analysis.general_analysis)}
                  </ReactMarkdown>
                </div>
              </CardContent>
            </Card>
          ) : (
            <div className="text-center py-12 text-muted-foreground">
              <Activity className="w-12 h-12 mx-auto mb-4 opacity-20" />
              <p>No hay análisis general disponible para esta colección de notas.</p>
            </div>
          )}

          {analysis.authorial_tone && (
            <div className="mt-4">
              <h4 className="text-md font-bold mb-2 flex items-center gap-2">
                <MessageSquare className="w-4 h-4 text-slate-500" />
                Tono Predominante
              </h4>
              <p className="text-sm text-muted-foreground bg-muted/30 p-3 rounded-lg border italic">
                {analysis.authorial_tone}
              </p>
            </div>
          )}
        </TabsContent>

        {/* TAB: TEMAS E INSIGHTS */}
        <TabsContent value="insights" className="space-y-6 animate-in fade-in-50 duration-500">
          {analysis.cross_cutting_themes && analysis.cross_cutting_themes.length > 0 && (
            <div>
              <h4 className={`text-lg font-bold mb-4 flex items-center gap-2 ${noteCollectionColors.icon}`}>
                <Target className="w-5 h-5" />
                Temas Transversales Identificados
              </h4>
              <div className="flex flex-wrap gap-2">
                {analysis.cross_cutting_themes.map((theme, index) => (
                  <InteractiveTag
                    key={index}
                    type="theme"
                    label={typeof theme === 'string' ? theme : theme.theme}
                    onClick={() => handleThemeClick?.(typeof theme === 'string' ? { theme, related_quotes: [] } : theme)}
                  />
                ))}
              </div>
            </div>
          )}

          <Separator />

          {analysis.synthesized_insights && analysis.synthesized_insights.length > 0 && (
            <div>
              <h4 className="text-lg font-bold mb-4 flex items-center gap-2 text-primary">
                <MessageSquare className="w-5 h-5" />
                Insights Sintetizados
              </h4>
              <div className="grid grid-cols-1 gap-3">
                {analysis.synthesized_insights.map((insight: any, index: number) => (
                  <div key={index} className="p-4 rounded-xl border bg-card shadow-sm hover:shadow-md transition-shadow border-l-4 border-l-primary">
                    <p className="text-sm text-foreground leading-relaxed">
                      {typeof insight === 'string' ? insight : (insight.insight || insight.description || JSON.stringify(insight))}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </TabsContent>

        {/* TAB: ESTRATEGIA Y BRECHAS */}
        <TabsContent value="strategy" className="space-y-6 animate-in fade-in-50 duration-500">
          {analysis.strategic_recommendations && analysis.strategic_recommendations.length > 0 && (
            <ActionableButton
              title="Recomendaciones Estratégicas"
              description="Pasos clave para capitalizar los hallazgos de la colección de notas."
              count={analysis.strategic_recommendations.length}
              variant="question"
              onClick={() => openSimpleListDialog?.(
                analysis.strategic_recommendations || [],
                "Recomendaciones Estratégicas",
                "Pasos clave para capitalizar los hallazgos de la colección de notas.",
                <TrendingUp className="w-6 h-6 text-emerald-600" />,
                "bg-emerald-100 dark:bg-emerald-900/30"
              )}
            />
          )}

          <Separator />

          {analysis.knowledge_gaps && analysis.knowledge_gaps.length > 0 && (
            <ActionableButton
              title="Brechas de Conocimiento"
              description="Áreas donde se requiere profundizar o conectar más información."
              count={analysis.knowledge_gaps.length}
              variant="gap"
              onClick={() => openSimpleListDialog?.(
                analysis.knowledge_gaps || [],
                "Brechas de Conocimiento",
                "Áreas donde se requiere profundizar o conectar más información.",
                <HelpCircle className="w-6 h-6 text-amber-600" />,
                "bg-amber-100 dark:bg-amber-900/30"
              )}
            />
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default NoteCollectionAnalysis;
