import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { ScopedRagAnalysisResult, Analysis } from '@/lib/models';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Search, Zap, HelpCircle, Info, FileText } from 'lucide-react';

import { SectionTTSButton } from './analysis-detail-dialog';

interface ScopedRagAnalysisProps {
  analysis: ScopedRagAnalysisResult;
  parentAnalysis?: Analysis;
  // TTS Props
  play: (text: string) => void;
  isLoading: boolean;
  isPlaying: boolean;
  activeText: string | null;
}

const ScopedRagAnalysis: React.FC<ScopedRagAnalysisProps> = ({
  analysis,
  parentAnalysis,
  play,
  isLoading,
  isPlaying,
  activeText
}) => {
  if (!analysis) return null;

  const ragColors = {
    cardBg: 'bg-rose-50/50 border-rose-100 dark:bg-rose-900/10 dark:border-rose-900/50',
    cardTitle: 'text-rose-900 dark:text-rose-100',
    icon: 'text-rose-600',
  };

  const hasInsights = parentAnalysis?.insights && parentAnalysis.insights.length > 0;
  const hasQuestions = parentAnalysis?.questions && parentAnalysis.questions.length > 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 mb-2">
        <Search className={`w-6 h-6 ${ragColors.icon}`} />
        <h3 className="text-2xl font-bold">Análisis RAG Enfocado</h3>
      </div>

      <Tabs defaultValue="report" className="w-full">
        <TabsList className={`grid w-full ${hasInsights || hasQuestions ? 'grid-cols-3' : 'grid-cols-1'} mb-8`}>
          <TabsTrigger value="report" className="gap-2">
            <FileText className="w-4 h-4" />
            <span className="hidden sm:inline">Análisis</span>
          </TabsTrigger>
          {(hasInsights || hasQuestions) && (
            <>
              <TabsTrigger value="insights" className="gap-2" disabled={!hasInsights}>
                <Zap className="w-4 h-4" />
                <span className="hidden sm:inline">Insights</span>
              </TabsTrigger>
              <TabsTrigger value="questions" className="gap-2" disabled={!hasQuestions}>
                <HelpCircle className="w-4 h-4" />
                <span className="hidden sm:inline">Preguntas</span>
              </TabsTrigger>
            </>
          )}
        </TabsList>

        {/* TAB: ANÁLISIS */}
        <TabsContent value="report" className="space-y-4 animate-in fade-in-50 duration-500">
          <Card className={`${ragColors.cardBg} border-none shadow-md`}>
            <CardHeader className="pb-2 flex flex-row items-center justify-between">
              <CardTitle className={`text-lg font-bold ${ragColors.cardTitle} flex items-center gap-2`}>
                <Search className="w-5 h-5" />
                Resultado de la Búsqueda Semántica
              </CardTitle>
              <SectionTTSButton
                text={analysis}
                play={play}
                isLoading={isLoading}
                isPlaying={isPlaying}
                activeText={activeText}
              />
            </CardHeader>
            <CardContent>
              <div className="prose prose-sm max-w-none dark:prose-invert text-muted-foreground leading-relaxed">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{analysis}</ReactMarkdown>
              </div>
            </CardContent>
          </Card>

          {parentAnalysis?.summary && (
            <div className="mt-6 p-5 rounded-xl bg-gradient-to-br from-rose-500/10 to-red-500/10 border border-rose-500/20 shadow-inner relative group">
              <div className="absolute top-4 right-4 opacity-0 group-hover:opacity-100 transition-opacity">
                <SectionTTSButton
                  text={parentAnalysis.summary}
                  play={play}
                  isLoading={isLoading}
                  isPlaying={isPlaying}
                  activeText={activeText}
                />
              </div>
              <h4 className="text-sm font-bold uppercase tracking-wider text-rose-600 dark:text-rose-400 mb-2 flex items-center gap-2">
                <Info className="w-4 h-4" />
                Resumen de KAI
              </h4>
              <p className="text-sm italic text-foreground/90 leading-relaxed">
                {parentAnalysis.summary}
              </p>
            </div>
          )}
        </TabsContent>

        {/* TAB: INSIGHTS */}
        {hasInsights && (
          <TabsContent value="insights" className="space-y-4 animate-in fade-in-50 duration-500">
            <div className="grid grid-cols-1 gap-3">
              {parentAnalysis.insights?.map((insight, i) => (
                <div key={i} className="p-4 rounded-xl border bg-card shadow-sm border-l-4 border-l-rose-500">
                  <p className="text-sm font-medium">{typeof insight === 'string' ? insight : insight.summary}</p>
                </div>
              ))}
            </div>
          </TabsContent>
        )}

        {/* TAB: PREGUNTAS */}
        {hasQuestions && (
          <TabsContent value="questions" className="space-y-4 animate-in fade-in-50 duration-500">
            <div className="grid grid-cols-1 gap-3">
              {parentAnalysis.questions?.map((q, i) => (
                <div key={i} className="p-4 rounded-xl border bg-card shadow-sm flex gap-3 items-start">
                  <HelpCircle className="w-5 h-5 text-rose-500 mt-0.5" />
                  <p className="text-sm italic">{typeof q === 'string' ? q : q.issue}</p>
                </div>
              ))}
            </div>
          </TabsContent>
        )}
      </Tabs>
    </div>
  );
};

export default ScopedRagAnalysis;
