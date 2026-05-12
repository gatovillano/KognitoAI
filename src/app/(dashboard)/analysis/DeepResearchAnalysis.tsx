import React, { useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { DeepResearchAnalysisResult, Analysis } from '@/lib/models';
import { Zap, Link2, FileText, AlertTriangle, LayoutDashboard } from 'lucide-react';
import { SectionTTSButton } from './analysis-detail-dialog';
import { MarkdownRenderer } from '@/components/MarkdownRenderer';
import { Source, ContentPart, SourceButton } from '@/components/SourceButton';
import { SourcesTab } from '@/components/SourcesTab';
import { processMessageWithCitations, collectSourcesFromMessage, getSourceIdentityKey } from '@/lib/chatUtils';

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
  const { citationSources, additionalSources } = useMemo(() => {
    if (!analysis) {
      return { citationSources: [], additionalSources: [] };
    }

    // Las fuentes pueden venir de analysis.sources directamente.
    // Soportamos tanto objetos Source normalizados (con type) como dicts crudos del grafo (sin type).
    let rawSources: any[] = [];

    if (Array.isArray(analysis.sources) && analysis.sources.length > 0) {
      rawSources = analysis.sources;
    } else if ((analysis as any).full_data && Array.isArray(((analysis as any).full_data).sources)) {
      rawSources = ((analysis as any).full_data).sources;
    } else {
      console.log('[DeepResearch] No se encontraron fuentes en analysis.sources ni en full_data.sources');
      return { citationSources: [], additionalSources: [] };
    }

    // Normalizar: asegurar estructura completa y IDs únicos para evitar colisiones en deduplicación
    const normalizedSources = rawSources.map((s: any, index) => {
      // Fallback de ID robusto
      const stableId = s.id || s.document_id || s.metadata?.document_id || `source-${index}`;
      
      return {
        ...s,
        id: stableId,
        type: s.type || s.metadata?.type || 'web',
        snippet: s.snippet || s.content || s.page_content || s.metadata?.snippet || '',
        url: s.url || s.metadata?.document_id || s.link || '',
        title: s.title || s.name || s.metadata?.title || 'Fuente de investigación',
        is_cited: s.is_cited !== undefined ? s.is_cited : true // Asumimos que si está en la lista de fuentes es porque se citó o se usó
      };
    });

    console.log('[DeepResearch] === DEBUG FUENTES ===');
    console.log('[DeepResearch] Raw sources count:', rawSources.length);
    console.log('[DeepResearch] Normalized sources:', normalizedSources);

    // Usar collectSourcesFromMessage para deduplicar
    const result = collectSourcesFromMessage(normalizedSources as any[]);
    console.log('[DeepResearch] Fuentes finales tras deduplicación:', result.additionalSources);
    console.log('[DeepResearch] ==========================');
    return result;
  }, [analysis]);


  const reportContent = useMemo(() => {
    if (!analysis) return '';
    if (analysis.final_report) return analysis.final_report;
    if (analysis.summary) return analysis.summary;
    return '';
  }, [analysis]);

  const { contentParts, citedSources, resolvedSources } = useMemo(() => {
    return processMessageWithCitations(reportContent, citationSources);
  }, [reportContent, citationSources]);

  const displaySources = resolvedSources.length > 0 ? resolvedSources : additionalSources;
  const citationNumberBySource = useMemo(() => {
    return new Map(displaySources.map((source, index) => [getSourceIdentityKey(source), index + 1]));
  }, [displaySources]);

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
    cardBg: 'bg-card border-border/40 dark:bg-card/40 dark:border-border/20',
    cardTitle: 'text-foreground',
    icon: 'text-primary',
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 mb-2">
        <div className="p-2 rounded-xl bg-primary/10">
          <FileText className={`w-6 h-6 ${gapColors.icon}`} />
        </div>
        <div>
          <h3 className="text-2xl font-black tracking-tight">Investigación Profunda</h3>
          <p className="text-xs text-muted-foreground uppercase tracking-widest font-bold">Análisis Detallado Basado en Evidencia</p>
        </div>
      </div>

      <Tabs defaultValue="report" className="w-full">
        <TabsList className="grid w-full grid-cols-3 mb-8 h-14 bg-muted/40 p-1.5 rounded-2xl border border-border/50 backdrop-blur-md">
          <TabsTrigger value="report" className="gap-2.5 rounded-xl data-[state=active]:bg-background data-[state=active]:shadow-lg data-[state=active]:text-primary transition-all duration-300">
            <FileText className="w-4.5 h-4.5" />
            <span className="font-bold">Informe Detallado</span>
          </TabsTrigger>
          <TabsTrigger value="schema" className="gap-2.5 rounded-xl data-[state=active]:bg-background data-[state=active]:shadow-lg data-[state=active]:text-primary transition-all duration-300">
            <LayoutDashboard className="w-4.5 h-4.5" />
            <span className="font-bold">Esquema Visual</span>
          </TabsTrigger>
          <TabsTrigger value="sources" className="gap-2.5 rounded-xl data-[state=active]:bg-background data-[state=active]:shadow-lg data-[state=active]:text-primary transition-all duration-300">
            <Link2 className="w-4.5 h-4.5" />
            <span className="font-bold">Fuentes</span>
            {displaySources.length > 0 && (
              <Badge variant="secondary" className="ml-1 px-1.5 h-5 min-w-5 flex items-center justify-center rounded-full text-[10px] bg-primary/10 text-primary border-none text-xs">
                {displaySources.length}
              </Badge>
            )}
          </TabsTrigger>
        </TabsList>

        {/* TAB: REPORTE */}
        <TabsContent value="report" className="space-y-4 animate-in fade-in-50 slide-in-from-left-4 duration-500">
          {reportContent ? (
            <Card className={`${gapColors.cardBg} border shadow-2xl shadow-primary/5 rounded-[2.5rem] overflow-hidden`}>
              <CardHeader className="pb-4 flex flex-row items-center justify-between bg-muted/20 border-b border-border/10 px-8 py-6">
                <div className="flex items-center gap-3">
                  <div className="h-3 w-3 rounded-full bg-primary shadow-[0_0_10px_rgba(var(--primary),0.5)] animate-pulse" />
                  <CardTitle className={`text-sm font-black uppercase tracking-[0.2em] ${gapColors.cardTitle}`}>Análisis Ejecutivo</CardTitle>
                </div>
                <SectionTTSButton
                  text={reportContent}
                  play={play}
                  isLoading={isLoading}
                  isPlaying={isPlaying}
                  activeText={activeText}
                />
              </CardHeader>
              <CardContent className="p-8 sm:p-10">
                <div className="text-foreground leading-relaxed prose prose-slate dark:prose-invert max-w-none">
                  <MarkdownRenderer contentParts={contentParts} fontSize="text-sm sm:text-base lg:text-lg" />
                </div>

                {/* Sección de Fuentes al final del reporte */}
                {citedSources.length > 0 && (
                  <div className="mt-12 pt-8 border-t border-border/10">
                    <div className="flex items-center gap-2 mb-6">
                      <div className="p-1.5 rounded-lg bg-primary/10">
                        <Link2 className="h-4 w-4 text-primary" />
                      </div>
                      <span className="text-[10px] font-black text-muted-foreground uppercase tracking-widest">Referencias de Investigación</span>
                    </div>
                    <div className="flex flex-wrap gap-3">
                      {citedSources.map((source, idx) => (
                        <SourceButton
                          key={idx}
                          source={source}
                          citationNumber={citationNumberBySource.get(getSourceIdentityKey(source)) || idx + 1}
                        />
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          ) : (
            <div className="flex flex-col items-center justify-center p-12 border-2 border-dashed border-muted rounded-3xl bg-muted/10">
              <div className="bg-background p-4 rounded-full shadow-sm mb-4">
                <FileText className="w-10 h-10 text-muted-foreground opacity-20" />
              </div>
              <p className="text-muted-foreground font-bold">No hay contenido de informe disponible</p>
              <p className="text-xs text-muted-foreground mt-1">El análisis está vacío o no generó un reporte final.</p>
            </div>
          )}

          {/* @ts-ignore */}
          {analysis.kai_synthesis && (
            <div className="mt-8 p-6 rounded-3xl bg-gradient-to-br from-primary/5 via-fuchsia-500/5 to-purple-500/5 border border-primary/20 shadow-xl relative overflow-hidden group">
              <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                <Zap className="w-12 h-12 text-primary" />
              </div>
              <h4 className="text-sm font-black uppercase tracking-widest text-primary mb-3 flex items-center gap-2">
                <Zap className="w-4 h-4" />
                Perspectiva de Inteligencia (KAI)
              </h4>
              <p className="text-sm sm:text-base italic text-foreground/80 leading-relaxed relative z-10">
                {/* @ts-ignore */}
                {analysis.kai_synthesis}
              </p>
            </div>
          )}
        </TabsContent>

        {/* TAB: ESQUEMA */}
        <TabsContent value="schema" className="space-y-4 animate-in fade-in-50 slide-in-from-bottom-6 duration-700">
          {analysis.visual_schema ? (
            <div className="relative group">
              {/* Fondo decorativo de 'Lienzo' */}
              <div className="absolute inset-0 bg-[radial-gradient(#e5e7eb_1px,transparent_1px)] [background-size:20px_20px] opacity-[0.15] pointer-events-none rounded-[3rem]" />

              <div className="rounded-[3rem] overflow-hidden border border-border/40 shadow-2xl bg-card/80 backdrop-blur-sm min-h-[500px] flex flex-col relative z-10">
                <div className="bg-muted/30 border-b border-border/10 px-8 py-4 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <LayoutDashboard className="w-4 h-4 text-primary" />
                    <span className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">Lienzo Esquema Visual</span>
                  </div>
                  <div className="flex gap-1">
                    <div className="w-2 h-2 rounded-full bg-red-400/20" />
                    <div className="w-2 h-2 rounded-full bg-amber-400/20" />
                    <div className="w-2 h-2 rounded-full bg-green-400/20" />
                  </div>
                </div>

                <div
                  className="visual-schema-content p-8 sm:p-12 overflow-auto max-h-[75vh] custom-scrollbar selection:bg-primary/20"
                  dangerouslySetInnerHTML={{ __html: analysis.visual_schema }}
                />
              </div>

              <style jsx global>{`
                .visual-schema-content {
                  font-family: 'Inter', system-ui, -apple-system, sans-serif;
                  color: inherit;
                  line-height: 1.6;
                }
                .visual-schema-content img {
                  max-width: 100%;
                  height: auto;
                  border-radius: 1.5rem;
                  box-shadow: 0 10px 30px -10px rgba(0,0,0,0.1);
                  margin: 2rem auto;
                  display: block;
                }
                .visual-schema-content table {
                  width: 100%;
                  border-collapse: separate;
                  border-spacing: 0;
                  margin: 2rem 0;
                  border: 1px solid rgba(128, 128, 128, 0.1);
                  border-radius: 1rem;
                  overflow: hidden;
                  background: rgba(var(--card), 0.5);
                }
                .visual-schema-content th {
                  background: rgba(var(--primary), 0.05);
                  font-weight: 800;
                  text-transform: uppercase;
                  font-size: 0.75rem;
                  letter-spacing: 0.05em;
                  padding: 1rem;
                  border-bottom: 2px solid rgba(var(--primary), 0.1);
                  text-align: left;
                }
                .visual-schema-content td {
                  padding: 1rem;
                  border-bottom: 1px solid rgba(128, 128, 128, 0.05);
                  font-size: 0.875rem;
                }
                .visual-schema-content tr:last-child td {
                  border-bottom: none;
                }
                .visual-schema-content h1, .visual-schema-content h2, .visual-schema-content h3 {
                  font-weight: 900;
                  letter-spacing: -0.02em;
                  margin-top: 2.5rem;
                  margin-bottom: 1rem;
                  color: hsl(var(--foreground));
                }
                .visual-schema-content h1 { font-size: 2rem; border-left: 4px solid hsl(var(--primary)); padding-left: 1rem; }
                .visual-schema-content h2 { font-size: 1.5rem; }
                .visual-schema-content h3 { font-size: 1.25rem; }
                
                .visual-schema-content p {
                  margin-bottom: 1.25rem;
                  opacity: 0.9;
                }
                
                .visual-schema-content ul, .visual-schema-content ol {
                  margin-bottom: 1.5rem;
                  padding-left: 1.5rem;
                }
                .visual-schema-content li {
                  margin-bottom: 0.5rem;
                }
                
                /* Estilo de lienzo técnico */
                .custom-scrollbar::-webkit-scrollbar {
                  width: 6px;
                  height: 6px;
                }
                .custom-scrollbar::-webkit-scrollbar-track {
                  background: transparent;
                }
                .custom-scrollbar::-webkit-scrollbar-thumb {
                  background: hsl(var(--primary) / 0.1);
                  border-radius: 10px;
                }
                .custom-scrollbar::-webkit-scrollbar-thumb:hover {
                  background: hsl(var(--primary) / 0.3);
                }
              `}</style>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center p-12 border-2 border-dashed border-muted rounded-3xl bg-muted/10">
              <div className="bg-background p-4 rounded-full shadow-sm mb-4">
                <LayoutDashboard className="w-10 h-10 text-muted-foreground opacity-20" />
              </div>
              <p className="text-muted-foreground font-bold">No hay esquema visual disponible</p>
              <p className="text-xs text-muted-foreground mt-1">Este análisis no incluye una representación gráfica.</p>
            </div>
          )}
        </TabsContent>

        {/* TAB: FUENTES */}
        <TabsContent value="sources" className="space-y-6 animate-in fade-in-50 duration-500">
          <SourcesTab sources={displaySources} />
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default DeepResearchAnalysis;
