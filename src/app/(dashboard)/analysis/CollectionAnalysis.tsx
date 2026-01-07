import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Button } from '@/components/ui/button';
import { CollectionAnalysis as CollectionAnalysisType, CollectionConnection } from '@/lib/models';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { LibraryBig, Link as LinkIcon, Target, Brain, HelpCircle, AlertTriangle, Zap, MessageSquare, Info, BarChart3, Activity } from 'lucide-react';
import { InteractiveTag } from '@/components/analysis/InteractiveTag';

interface CollectionAnalysisProps {
  analysis: CollectionAnalysisType;
  colColors: any;
  openGapsSlider: (gaps: any[], title: string) => void;
  openQuestionsSlider?: (questions: any[], title: string) => void;
  handleThemeClick?: (theme: any) => void;
  handleConceptClick?: (concept: string) => void;
  play: (text: string) => void;
  isLoading: boolean;
  isPlaying: boolean;
  activeText: string | null;
}

import { ActionableButton } from '@/components/analysis/ActionableButton';
import { SectionTTSButton } from './analysis-detail-dialog';

const CollectionAnalysis: React.FC<CollectionAnalysisProps> = ({
  analysis,
  colColors,
  openGapsSlider,
  openQuestionsSlider,
  handleThemeClick,
  handleConceptClick,
  play,
  isLoading,
  isPlaying,
  activeText,
}) => {
  if (!analysis) return null;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 mb-2">
        <LibraryBig className={`w-6 h-6 ${colColors.icon}`} />
        <h3 className="text-2xl font-bold">Análisis de Colección - KAI Exocerebro</h3>
      </div>

      <Tabs defaultValue="summary" className="w-full">
        <TabsList className="grid w-full grid-cols-6 mb-8">
          <TabsTrigger value="summary" className="gap-2">
            <Info className="w-4 h-4" />
            <span className="hidden sm:inline">Resumen</span>
          </TabsTrigger>
          <TabsTrigger value="general" className="gap-2">
            <Activity className="w-4 h-4" />
            <span className="hidden sm:inline">Análisis General</span>
          </TabsTrigger>
          <TabsTrigger value="themes" className="gap-2">
            <Target className="w-4 h-4" />
            <span className="hidden sm:inline">Temas</span>
          </TabsTrigger>
          <TabsTrigger value="connections" className="gap-2">
            <LinkIcon className="w-4 h-4" />
            <span className="hidden sm:inline">Conexiones</span>
          </TabsTrigger>
          <TabsTrigger value="insights" className="gap-2">
            <Zap className="w-4 h-4" />
            <span className="hidden sm:inline">Hallazgos</span>
          </TabsTrigger>
          <TabsTrigger value="meta" className="gap-2">
            <BarChart3 className="w-4 h-4" />
            <span className="hidden sm:inline">Meta</span>
          </TabsTrigger>
        </TabsList>

        {/* TAB: RESUMEN */}
        <TabsContent value="summary" className="space-y-4 animate-in fade-in-50 duration-500">
          {analysis.collection_summary && (
            <Card className={`${colColors.cardBg} border-none shadow-md`}>
              <CardHeader className="pb-2">
                <CardTitle className={`text-lg font-bold ${colColors.cardTitle} flex items-center justify-between`}>
                  Resumen de la Colección
                  <SectionTTSButton
                    text={analysis.collection_summary || ""}
                    play={play}
                    isLoading={isLoading}
                    isPlaying={isPlaying}
                    activeText={activeText}
                  />
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="prose prose-sm max-w-none dark:prose-invert text-muted-foreground leading-relaxed">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{analysis.collection_summary}</ReactMarkdown>
                </div>
              </CardContent>
            </Card>
          )}

          {analysis.kai_synthesis && (
            <div className="mt-6 p-5 rounded-xl bg-gradient-to-br from-primary/10 to-emerald-500/10 border border-emerald-500/20 shadow-inner">
              <h4 className="text-sm font-bold uppercase tracking-wider text-emerald-600 dark:text-emerald-400 mb-2 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Zap className="w-4 h-4" />
                  Síntesis Maestra de KAI
                </div>
                <SectionTTSButton
                  text={analysis.kai_synthesis || ""}
                  play={play}
                  isLoading={isLoading}
                  isPlaying={isPlaying}
                  activeText={activeText}
                />
              </h4>
              <div className="text-sm italic text-foreground/90 leading-relaxed">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{analysis.kai_synthesis}</ReactMarkdown>
              </div>
            </div>
          )}

          {analysis.collection_insights && analysis.collection_insights.length > 0 && (
            <div className="grid grid-cols-1 gap-3 mt-4">
              <h4 className="text-sm font-bold text-muted-foreground uppercase tracking-tight">Insights de Colección</h4>
              {analysis.collection_insights.map((insight, i) => (
                <div key={i} className="p-3 rounded-lg bg-muted/40 border-l-4 border-l-primary flex gap-3 items-start">
                  <div className="mt-1"><Zap className="w-3 h-3 text-primary" /></div>
                  <p className="text-sm">{insight}</p>
                </div>
              ))}
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
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{analysis.general_analysis}</ReactMarkdown>
                </div>
              </CardContent>
            </Card>
          ) : (
            <div className="text-center py-12 text-muted-foreground">
              <Activity className="w-12 h-12 mx-auto mb-4 opacity-20" />
              <p>No hay análisis general disponible para esta colección.</p>
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

        {/* TAB: TEMAS Y CONCEPTOS */}
        <TabsContent value="themes" className="space-y-6 animate-in fade-in-50 duration-500">
          {analysis.cross_cutting_themes && analysis.cross_cutting_themes.length > 0 && (
            <div>
              <h4 className={`text-lg font-bold mb-4 flex items-center gap-2 ${colColors.icon}`}>
                <Target className="w-5 h-5" />
                Temas Transversales
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

          <div>
            {analysis.central_concepts && analysis.central_concepts.length > 0 && (
              <div className="mb-6"> {/* Added margin-bottom for spacing */}
                <h4 className="text-md font-bold mb-3 flex items-center gap-2">
                  <Brain className="w-4 h-4 text-purple-500" />
                  Conceptos Centrales
                </h4>
                <div className="flex flex-wrap gap-2">
                  {analysis.central_concepts.map((concept, index) => (
                    <InteractiveTag
                      key={index}
                      type="concept"
                      label={concept.split(':')[0].replace(/\*\*/g, '')}
                      onClick={() => handleConceptClick?.(concept)}
                      className={colColors.tag}
                    />
                  ))}
                </div>
              </div>
            )}

            {analysis.concept_relationships && analysis.concept_relationships.length > 0 && (
              <div>
                <h4 className="text-md font-bold mb-3 flex items-center gap-2">
                  <LinkIcon className="w-4 h-4 text-blue-500" />
                  Relaciones Conceptuales
                </h4>
                <div className="space-y-3">
                  {analysis.concept_relationships.map((rel: any, index: number) => (
                    <div key={index} className="text-sm text-muted-foreground flex gap-2 items-start p-3 rounded-lg bg-muted/30 border border-muted/50">
                      <div className="mt-1"><LinkIcon className="w-3 h-3 text-blue-500" /></div>
                      <div className="prose prose-sm dark:prose-invert max-w-none">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{typeof rel === 'string' ? rel : (rel.relationship || rel.description || JSON.stringify(rel))}</ReactMarkdown>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </TabsContent>

        {/* TAB: CONEXIONES */}
        <TabsContent value="connections" className="space-y-6 animate-in fade-in-50 duration-500">
          {analysis.identified_connections && analysis.identified_connections.length > 0 ? (
            <div>
              <h4 className="text-lg font-bold mb-4 flex items-center gap-2 text-indigo-600">
                <LinkIcon className="w-5 h-5" />
                Conexiones entre Documentos
              </h4>
              <div className="space-y-4">
                {analysis.identified_connections.map((connection: CollectionConnection, index: number) => (
                  <div key={index} className="p-4 rounded-xl border bg-card shadow-sm hover:shadow-md transition-shadow border-l-4 border-l-indigo-500">
                    <div className="flex flex-wrap gap-2 mb-3">
                      {connection.document_titles.map((title, tIdx) => (
                        <Badge key={tIdx} variant="outline" className="text-[10px] bg-indigo-50 dark:bg-indigo-900/20">
                          {title}
                        </Badge>
                      ))}
                    </div>
                    <p className="text-sm text-foreground font-medium leading-relaxed">
                      {connection.insight}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="text-center py-12 text-muted-foreground">
              <LinkIcon className="w-12 h-12 mx-auto mb-4 opacity-20" />
              <p>No se identificaron conexiones explícitas entre los documentos.</p>
            </div>
          )}
        </TabsContent>

        {/* TAB: HALLAZGOS Y CRÍTICA */}
        <TabsContent value="insights" className="space-y-6 animate-in fade-in-50 duration-500">
          {analysis.emergent_knowledge_gaps && analysis.emergent_knowledge_gaps.length > 0 && (
            <ActionableButton
              title="Brechas de Conocimiento Emergentes"
              description="Identifica áreas donde falta información en la colección analizada."
              count={analysis.emergent_knowledge_gaps.length}
              variant="gap"
              onClick={() => openGapsSlider?.(analysis.emergent_knowledge_gaps || [], "Brechas de Conocimiento Emergentes")}
            />
          )}

          {analysis.problematic_areas && analysis.problematic_areas.length > 0 && (
            <div>
              <h4 className="text-lg font-bold mb-4 flex items-center gap-2 text-red-600">
                <AlertTriangle className="w-5 h-5" />
                Áreas Problemáticas o Conflictivas
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {analysis.problematic_areas.map((area: any, index: number) => (
                  <div key={index} className="p-3 rounded-lg border border-red-100 dark:border-red-900/30 bg-red-50/30 dark:bg-red-900/10 text-sm flex gap-2">
                    <span className="text-red-500 font-bold">!</span>
                    {typeof area === 'string' ? area : (area.issue || area.description || JSON.stringify(area))}
                  </div>
                ))}
              </div>
            </div>
          )}

          {analysis.final_reflections && analysis.final_reflections.length > 0 && (
            <Card className="border-dashed bg-muted/30">
              <CardHeader className="pb-2">
                <CardTitle className="text-md font-bold flex items-center gap-2">
                  <MessageSquare className="w-4 h-4 text-primary" />
                  Reflexiones Finales
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {analysis.final_reflections.map((reflection: any, index: number) => (
                    <p key={index} className="text-sm text-muted-foreground italic border-l-2 border-primary/20 pl-3">
                      "{typeof reflection === 'string' ? reflection : (reflection.reflection || reflection.thought || JSON.stringify(reflection))}"
                    </p>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* TAB: META Y METODOLOGÍA */}
        <TabsContent value="meta" className="space-y-6 animate-in fade-in-50 duration-500">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {analysis.methodological_notes && analysis.methodological_notes.length > 0 && (
              <div>
                <h4 className="text-lg font-bold mb-4 flex items-center gap-2 text-slate-600">
                  <Info className="w-5 h-5" />
                  Notas Metodológicas
                </h4>
                <ul className="space-y-2">
                  {analysis.methodological_notes.map((note: any, i: number) => (
                    <li key={i} className="text-sm text-muted-foreground bg-slate-50 dark:bg-slate-900/20 p-3 rounded-lg border">
                      {typeof note === 'string' ? note : (note.note || note.description || JSON.stringify(note))}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {analysis.exploration_questions && analysis.exploration_questions.length > 0 && (
              <ActionableButton
                title="Preguntas de Exploración"
                description="Cuestionamientos clave para profundizar en la colección."
                count={analysis.exploration_questions.length}
                variant="question"
                onClick={() => openQuestionsSlider?.(analysis.exploration_questions || [], "Preguntas de Exploración")}
              />
            )}
          </div>

          {analysis.patrones_semanticos && (
            <div className="mt-8 p-6 rounded-2xl bg-card border shadow-sm">
              <h4 className="text-md font-bold mb-4 flex items-center gap-2">
                <BarChart3 className="w-5 h-5 text-primary" />
                Métricas del Análisis Semántico
              </h4>
              <div className="grid grid-cols-3 gap-4">
                <div className="text-center p-4 rounded-xl bg-muted/30">
                  <span className="text-2xl font-black text-primary block">{analysis.patrones_semanticos.total_documentos || 0}</span>
                  <span className="text-[10px] uppercase font-bold text-muted-foreground">Documentos</span>
                </div>
                <div className="text-center p-4 rounded-xl bg-muted/30">
                  <span className="text-2xl font-black text-primary block">{analysis.patrones_semanticos.total_chunks_analizados || 0}</span>
                  <span className="text-[10px] uppercase font-bold text-muted-foreground">Fragmentos</span>
                </div>
                <div className="text-center p-4 rounded-xl bg-muted/30">
                  <span className="text-2xl font-black text-primary block">{analysis.patrones_semanticos.temas_identificados || 0}</span>
                  <span className="text-[10px] uppercase font-bold text-muted-foreground">Temas</span>
                </div>
              </div>
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default CollectionAnalysis;
