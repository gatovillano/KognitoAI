import React, { useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { DeepResearchAnalysisResult } from '@/lib/models';
import { Zap, Link2, FileText, AlertTriangle } from 'lucide-react';
import { SectionTTSButton } from './analysis-detail-dialog';
import { MarkdownRenderer } from '@/components/MarkdownRenderer';
import { Source, ContentPart, SourceButton } from '@/components/SourceButton';
import { SourcesTab } from '@/components/SourcesTab';

interface DeepResearchAnalysisProps {
  analysis: DeepResearchAnalysisResult;
  // TTS Props
  play: (text: string) => void;
  isLoading: boolean;
  isPlaying: boolean;
  activeText: string | null;
}

const DeepResearchAnalysis: React.FC<DeepResearchAnalysisProps> = ({
  analysis,
  play,
  isLoading,
  isPlaying,
  activeText
}) => {
  // Hooks must be called at the top level, before any early returns.
  const sources: Source[] = useMemo(() => {
    if (!analysis || !Array.isArray(analysis.sources)) {
      console.log('[DeepResearch] No analysis or sources found');
      return [];
    }
    console.log('[DeepResearch] Processing sources:', analysis.sources);
    return analysis.sources.map(s => ({
      id: s.id,
      title: s.title,
      url: s.url,
      snippet: s.snippet || 'Sin descripción disponible',
      type: (s.type as Source['type']) || 'web',
      metadata: {},
      name: s.title
    }));
  }, [analysis]);

  const reportContent = useMemo(() => {
    if (!analysis) return '';
    if (analysis.final_report) return analysis.final_report;
    return '';
  }, [analysis]);

  const { contentParts } = useMemo(() => {
    const processMessageWithCitations = (text: string, allSources: Source[]): { contentParts: ContentPart[] } => {
      if (!allSources || allSources.length === 0) {
        console.log('[DeepResearch] No sources available for citation processing');
        return { contentParts: [{ type: 'text', content: text }] };
      }

      console.log('[DeepResearch] Processing citations in text. Available sources:', allSources.length);
      const contentParts: ContentPart[] = [];
      let lastIndex = 0;
      const citationRegex = /\[(\d+)\]/g;
      let match: RegExpExecArray | null;
      let citationsFound = 0;

      while ((match = citationRegex.exec(text)) !== null) {
        const citationNumber = parseInt(match[1], 10);
        const fullMatch = match[0];
        const index = match.index!;
        const source = allSources.find(s => s.id == citationNumber);

        if (source) {
          citationsFound++;
          console.log(`[DeepResearch] Found citation [${citationNumber}] with source:`, source.title);
          if (index > lastIndex) {
            contentParts.push({ type: 'text', content: text.substring(lastIndex, index) });
          }
          contentParts.push({ type: 'citation', source: source, citationNumber: citationNumber });
          lastIndex = index + fullMatch.length;
        } else {
          console.warn(`[DeepResearch] Citation [${citationNumber}] not found in sources`);
        }
      }

      console.log(`[DeepResearch] Total citations found and processed: ${citationsFound}`);
      if (lastIndex < text.length) {
        contentParts.push({ type: 'text', content: text.substring(lastIndex) });
      }
      return { contentParts };
    };

    return processMessageWithCitations(reportContent, sources);
  }, [reportContent, sources]);

  if (!analysis) {
    return (
      <div className="flex flex-col items-center justify-center p-8 border border-dashed border-destructive/50 rounded-lg bg-destructive/5">
        <AlertTriangle className="w-10 h-10 text-destructive mb-2" />
        <p className="text-destructive font-medium">Error: No se pudieron cargar los datos del análisis.</p>
        <p className="text-xs text-muted-foreground">El objeto de análisis está vacío o indefinido.</p>
      </div>
    );
  }

  const gapColors = {
    cardBg: 'bg-fuchsia-50/50 border-fuchsia-100 dark:bg-fuchsia-900/10 dark:border-fuchsia-900/50',
    cardTitle: 'text-fuchsia-900 dark:text-fuchsia-100',
    icon: 'text-fuchsia-600',
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 mb-2">
        <FileText className={`w-6 h-6 ${gapColors.icon}`} />
        <h3 className="text-2xl font-bold">Investigación Profunda de Brechas</h3>
      </div>

      <Tabs defaultValue="report" className="w-full">
        <TabsList className="grid w-full grid-cols-2 mb-8">
          <TabsTrigger value="report" className="gap-2">
            <FileText className="w-4 h-4" />
            <span className="hidden sm:inline">Reporte</span>
          </TabsTrigger>
          <TabsTrigger value="sources" className="gap-2">
            <Link2 className="w-4 h-4" />
            <span className="hidden sm:inline">Fuentes</span>
          </TabsTrigger>
        </TabsList>

        {/* TAB: REPORTE */}
        <TabsContent value="report" className="space-y-4 animate-in fade-in-50 duration-500">
          {reportContent ? (
            <Card className={`${gapColors.cardBg} border-none shadow-md`}>
              <CardHeader className="pb-2 flex flex-row items-center justify-between">
                <CardTitle className={`text-lg font-bold ${gapColors.cardTitle}`}>Informe Detallado</CardTitle>
                <SectionTTSButton
                  text={reportContent}
                  play={play}
                  isLoading={isLoading}
                  isPlaying={isPlaying}
                  activeText={activeText}
                />
              </CardHeader>
              <CardContent>
                <div className="text-sm text-foreground leading-relaxed">
                  <MarkdownRenderer contentParts={contentParts} fontSize="text-sm" />
                </div>

                {/* Sección de Fuentes al final del reporte */}
                {Array.isArray(sources) && sources.length > 0 && (
                  <div className="mt-6 pt-4 border-t border-border/10">
                    <div className="flex items-center gap-2 mb-3">
                      <Link2 className="h-3 w-3 text-primary" />
                      <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">Fuentes y Referencias</span>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {sources.map((source, idx) => (
                        <SourceButton key={idx} source={source} citationNumber={source.id as number} />
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          ) : (
            <div className="flex flex-col items-center justify-center p-8 border-2 border-dashed border-muted rounded-xl bg-muted/30">
              <FileText className="w-10 h-10 text-muted-foreground mb-3 opacity-50" />
              <p className="text-muted-foreground font-medium">No hay contenido de informe disponible.</p>
              <p className="text-xs text-muted-foreground mt-1">Es posible que el análisis no haya generado un reporte final.</p>
            </div>
          )}

          {/* @ts-ignore: kai_synthesis might exist on runtime object even if not in type definition yet */}
          {analysis.kai_synthesis && (
            <div className="mt-6 p-5 rounded-xl bg-gradient-to-br from-fuchsia-500/10 to-purple-500/10 border border-fuchsia-500/20 shadow-inner">
              <h4 className="text-sm font-bold uppercase tracking-wider text-fuchsia-600 dark:text-fuchsia-400 mb-2 flex items-center gap-2">
                <Zap className="w-4 h-4" />
                Síntesis de KAI
              </h4>
              <p className="text-sm italic text-foreground/90 leading-relaxed">
                {/* @ts-ignore */}
                {analysis.kai_synthesis}
              </p>
            </div>
          )}
        </TabsContent>

        {/* TAB: FUENTES */}
        <TabsContent value="sources" className="space-y-6 animate-in fade-in-50 duration-500">
          <SourcesTab sources={sources} />
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default DeepResearchAnalysis;
