import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { NoteAnalysisResult } from '@/lib/models';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { FileText, Target, Brain, Zap, Lightbulb, Info, ArrowRight } from 'lucide-react';
import { InteractiveTag } from '@/components/analysis/InteractiveTag';

import { SectionTTSButton } from './analysis-detail-dialog';

interface NoteAnalysisProps {
  analysis: NoteAnalysisResult;
  noteColors: any;
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

const NoteAnalysis: React.FC<NoteAnalysisProps> = ({
  analysis,
  noteColors,
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
        <FileText className={`w-6 h-6 ${noteColors.icon}`} />
        <h3 className="text-2xl font-bold">Análisis Individual de Nota</h3>
      </div>

      <Tabs defaultValue="summary" className="w-full">
        <TabsList className="grid w-full grid-cols-3 mb-8">
          <TabsTrigger value="summary" className="gap-2">
            <Info className="w-4 h-4" />
            <span className="hidden sm:inline">Resumen</span>
          </TabsTrigger>
          <TabsTrigger value="themes" className="gap-2">
            <Brain className="w-4 h-4" />
            <span className="hidden sm:inline">Temas</span>
          </TabsTrigger>
          <TabsTrigger value="action" className="gap-2">
            <Zap className="w-4 h-4" />
            <span className="hidden sm:inline">Acción</span>
          </TabsTrigger>
        </TabsList>

        {/* TAB: RESUMEN */}
        <TabsContent value="summary" className="space-y-4 animate-in fade-in-50 duration-500">
          {analysis.executive_summary && (
            <Card className={`${noteColors.cardBg} border-none shadow-md`}>
              <CardHeader className="pb-2">
                <CardTitle className={`text-lg font-bold ${noteColors.cardTitle}`}>Resumen de la Nota</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="prose prose-sm max-w-none dark:prose-invert text-muted-foreground leading-relaxed">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{analysis.executive_summary}</ReactMarkdown>
                </div>
              </CardContent>
            </Card>
          )}

          {analysis.kai_insight && (
            <div className="mt-6 p-5 rounded-xl bg-gradient-to-br from-blue-500/10 to-indigo-500/10 border border-blue-500/20 shadow-inner relative group">
              <div className="absolute top-4 right-4 opacity-0 group-hover:opacity-100 transition-opacity">
                <SectionTTSButton
                  text={analysis.kai_insight}
                  play={play}
                  isLoading={isLoading}
                  isPlaying={isPlaying}
                  activeText={activeText}
                />
              </div>
              <h4 className="text-sm font-bold uppercase tracking-wider text-blue-600 dark:text-blue-400 mb-2 flex items-center gap-2">
                <Lightbulb className="w-4 h-4" />
                Insight Maestro de KAI
              </h4>
              <div className="prose prose-sm max-w-none dark:prose-invert text-foreground/90 italic leading-relaxed">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{analysis.kai_insight}</ReactMarkdown>
              </div>
            </div>
          )}
        </TabsContent>

        {/* TAB: TEMAS Y CONCEPTOS */}
        <TabsContent value="themes" className="space-y-6 animate-in fade-in-50 duration-500">
          {analysis.key_themes && analysis.key_themes.length > 0 && (
            <div>
              <h4 className={`text-lg font-bold mb-4 flex items-center gap-2 ${noteColors.icon}`}>
                <Target className="w-5 h-5" />
                Temas Clave
              </h4>
              <div className="flex flex-wrap gap-2">
                {analysis.key_themes.map((theme, index) => (
                  <InteractiveTag
                    key={index}
                    type="theme"
                    label={theme}
                    onClick={() => handleThemeClick?.({ theme, related_quotes: [] })}
                  />
                ))}
              </div>
            </div>
          )}

          <Separator />

          {analysis.related_concepts && analysis.related_concepts.length > 0 && (
            <div>
              <h4 className="text-lg font-bold mb-4 flex items-center gap-2 text-purple-600">
                <Brain className="w-5 h-5" />
                Conceptos Relacionados
              </h4>
              <div className="flex flex-wrap gap-2">
                {analysis.related_concepts.map((concept, index) => (
                  <InteractiveTag
                    key={index}
                    type="concept"
                    label={concept}
                    onClick={() => handleConceptClick?.(concept)}
                  />
                ))}
              </div>
            </div>
          )}
        </TabsContent>

        {/* TAB: ACCIÓN E IMPLICACIONES */}
        <TabsContent value="action" className="space-y-6 animate-in fade-in-50 duration-500">
          {analysis.potential_implications && analysis.potential_implications.length > 0 && (
            <div>
              <h4 className="text-lg font-bold mb-4 flex items-center gap-2 text-amber-600">
                <Info className="w-5 h-5" />
                Implicaciones Potenciales
              </h4>
              <div className="space-y-3">
                {analysis.potential_implications.map((imp: any, index: number) => (
                  <div key={index} className="p-4 rounded-xl border bg-amber-50/30 dark:bg-amber-900/10 flex gap-3 items-start">
                    <div className="mt-1"><ArrowRight className="w-4 h-4 text-amber-500" /></div>
                    <p className="text-sm text-foreground leading-relaxed">{typeof imp === 'string' ? imp : (imp.implication || imp.description || JSON.stringify(imp))}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          <Separator />

          {analysis.action_suggestions && analysis.action_suggestions.length > 0 && (
            <ActionableButton
              title="Sugerencias de Acción"
              description="Pasos recomendados para desarrollar o aplicar las ideas de la nota."
              count={analysis.action_suggestions.length}
              variant="question"
              onClick={() => openSimpleListDialog?.(
                analysis.action_suggestions || [],
                "Sugerencias de Acción",
                "Pasos recomendados para desarrollar o aplicar las ideas de la nota.",
                <Zap className="w-6 h-6 text-emerald-600" />,
                "bg-emerald-100 dark:bg-emerald-900/30"
              )}
            />
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default NoteAnalysis;
