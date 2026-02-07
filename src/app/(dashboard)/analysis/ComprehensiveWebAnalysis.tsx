import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { ComprehensiveWebAnalysisResult, Analysis } from '@/lib/models';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Globe, Zap, HelpCircle, Info, FileText } from 'lucide-react';

import { SectionTTSButton } from './analysis-detail-dialog';

interface ComprehensiveWebAnalysisProps {
  analysis: ComprehensiveWebAnalysisResult;
  parentAnalysis?: Analysis;
  // TTS Props
  play: (text: string) => void;
  isLoading: boolean;
  isPlaying: boolean;
  activeText: string | null;
}

const ComprehensiveWebAnalysis: React.FC<ComprehensiveWebAnalysisProps> = ({
  analysis,
  parentAnalysis,
  play,
  isLoading,
  isPlaying,
  activeText
}) => {
  if (!analysis) return null;

  const webColors = {
    cardBg: 'bg-sky-50/50 border-sky-100 dark:bg-sky-900/10 dark:border-sky-900/50',
    cardTitle: 'text-sky-900 dark:text-sky-100',
    icon: 'text-sky-600',
  };

  const hasInsights = parentAnalysis?.insights && parentAnalysis.insights.length > 0;
  const hasQuestions = parentAnalysis?.questions && parentAnalysis.questions.length > 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 mb-2">
        <Globe className={`w-6 h-6 ${webColors.icon}`} />
        <h3 className="text-2xl font-bold">Análisis Web Exhaustivo</h3>
      </div>

      <Tabs defaultValue="report" className="w-full">
        <TabsList className={`grid w-full ${hasInsights || hasQuestions ? 'grid-cols-3' : 'grid-cols-1'} mb-8`}>
          <TabsTrigger value="report" className="gap-2">
            <FileText className="w-4 h-4" />
            <span className="hidden sm:inline">Reporte Completo</span>
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

        {/* TAB: REPORTE */}
        <TabsContent value="report" className="space-y-4 animate-in fade-in-50 duration-500">
          <Card className={`${webColors.cardBg} border-none shadow-md`}>
            <CardHeader className="pb-2 flex flex-row items-center justify-between">
              <CardTitle className={`text-lg font-bold ${webColors.cardTitle} flex items-center gap-2`}>
                <Globe className="w-5 h-5" />
                Resultados de la Investigación Web
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
            <div className="mt-6 p-5 rounded-xl bg-gradient-to-br from-sky-500/10 to-blue-500/10 border border-sky-500/20 shadow-inner relative group">
              <div className="absolute top-4 right-4 opacity-0 group-hover:opacity-100 transition-opacity">
                <SectionTTSButton
                  text={parentAnalysis.summary}
                  play={play}
                  isLoading={isLoading}
                  isPlaying={isPlaying}
                  activeText={activeText}
                />
              </div>
              <h4 className="text-sm font-bold uppercase tracking-wider text-sky-600 dark:text-sky-400 mb-2 flex items-center gap-2">
                <Info className="w-4 h-4" />
                Síntesis Ejecutiva
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
                <div key={i} className="p-4 rounded-xl border bg-card shadow-sm border-l-4 border-l-sky-500">
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
                  <HelpCircle className="w-5 h-5 text-sky-500 mt-0.5" />
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

export default ComprehensiveWebAnalysis;
