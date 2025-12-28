import React, { useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { DeepResearchAnalysisResult } from '@/lib/models';
import { Zap, Link2, FileText, AlertTriangle } from 'lucide-react';
import { SectionTTSButton } from './analysis-detail-dialog';
import { MarkdownRenderer } from '@/components/MarkdownRenderer';
import { Source, ContentPart } from '@/components/SourceButton';

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

  // Convertir las fuentes del análisis al tipo Source esperado por MarkdownRenderer
  const sources: Source[] = useMemo(() => {
    if (!analysis.sources) return [];
    return analysis.sources.map(s => ({
      id: s.id,
      title: s.title,
      url: s.url,
      snippet: s.snippet,
      type: (s.type as Source['type']) || 'web', // Default to web if type is missing or incompatible
      metadata: {},
      name: s.title
    }));
  }, [analysis.sources]);

  const processMessageWithCitations = (text: string, allSources: Source[]): { contentParts: ContentPart[] } => {
    if (!allSources || allSources.length === 0) {
      return { contentParts: [{ type: 'text', content: text }] };
    }

    const contentParts: ContentPart[] = [];
    let lastIndex = 0;

    // Expresión regular para buscar citas como [1], [2], etc.
    const citationRegex = /\[(\d+)\]/g;
    let match: RegExpExecArray | null;

    while ((match = citationRegex.exec(text)) !== null) {
      const citationNumber = parseInt(match[1], 10);
      const fullMatch = match[0];
      const index = match.index!;

      const source = allSources.find(s => s.id == citationNumber);

      if (source) {
        // Añadir el texto antes de la cita
        if (index > lastIndex) {
          contentParts.push({ type: 'text', content: text.substring(lastIndex, index) });
        }

        // Añadir la cita como un componente
        contentParts.push({ type: 'citation', source: source, citationNumber: citationNumber });
        lastIndex = index + fullMatch.length;
      }
    }

    // Añadir cualquier texto restante después de la última cita
    if (lastIndex < text.length) {
      contentParts.push({ type: 'text', content: text.substring(lastIndex) });
    }

    return { contentParts };
  };

  // Determine the report content, handling backward compatibility where content might be in 'findings'
  const reportContent = useMemo(() => {
    if (analysis.final_report) return analysis.final_report;
    if (analysis.findings && Array.isArray(analysis.findings) && analysis.findings.length > 0) {
      return analysis.findings.join('\n\n');
    }
    return '';
  }, [analysis]);

  const { contentParts } = useMemo(() =>
    processMessageWithCitations(reportContent, sources),
    [reportContent, sources]);

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
          {sources.length > 0 ? (
            <div>
              <h4 className="text-lg font-bold mb-4 flex items-center gap-2 text-slate-600">
                <Link2 className="w-5 h-5" />
                Bibliografía y Referencias
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {sources.map((source, index) => (
                  <a
                    key={index}
                    href={source.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="group p-3 rounded-lg border bg-card hover:bg-accent transition-all flex flex-col gap-1 overflow-hidden"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] font-bold text-muted-foreground uppercase">Fuente #{source.id}</span>
                      <Link2 className="w-3 h-3 text-muted-foreground group-hover:text-primary transition-colors" />
                    </div>
                    <p className="font-bold text-sm truncate group-hover:text-primary transition-colors">{source.title || source.url}</p>
                    <p className="text-[10px] text-muted-foreground truncate">{source.url}</p>
                  </a>
                ))}
              </div>
            </div>
          ) : (
            <div className="text-center py-12 text-muted-foreground">
              <Link2 className="w-12 h-12 mx-auto mb-4 opacity-20" />
              <p>No se registraron fuentes externas para esta investigación.</p>
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default DeepResearchAnalysis;
