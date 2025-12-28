import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { DocumentAnalysisResult as SingleTextAnalysisType } from '@/lib/models';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { FileText, List, Brain, HelpCircle, Activity, Layout, Users, Target, Zap, MessageSquare } from 'lucide-react';
import { InteractiveTag } from '@/components/analysis/InteractiveTag';

import { SectionTTSButton } from './analysis-detail-dialog';

interface DocumentAnalysisProps {
  analysis: SingleTextAnalysisType;
  docColors: any;
  handleThemeClick?: (theme: any) => void;
  handleConceptClick?: (concept: string) => void;
  openGapsSlider?: (gaps: any[], title: string) => void;
  openQuestionsSlider?: (questions: any[], title: string) => void;
  // TTS Props
  play: (text: string) => void;
  isLoading: boolean;
  isPlaying: boolean;
  activeText: string | null;
}

import { ActionableButton } from '@/components/analysis/ActionableButton';

const DocumentAnalysis: React.FC<DocumentAnalysisProps> = ({
  analysis,
  docColors,
  handleThemeClick,
  handleConceptClick,
  openGapsSlider,
  openQuestionsSlider,
  play,
  isLoading,
  isPlaying,
  activeText
}) => {
  if (!analysis) return null;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 mb-2">
        <FileText className={`w-6 h-6 ${docColors.icon}`} />
        <h3 className="text-2xl font-bold">Análisis Detallado del Documento</h3>
      </div>

      <Tabs defaultValue="summary" className="w-full">
        <TabsList className="grid w-full grid-cols-5 mb-8">
          <TabsTrigger value="summary" className="gap-2">
            <Layout className="w-4 h-4" />
            <span className="hidden sm:inline">Resumen</span>
          </TabsTrigger>
          <TabsTrigger value="themes" className="gap-2">
            <Target className="w-4 h-4" />
            <span className="hidden sm:inline">Temas</span>
          </TabsTrigger>
          <TabsTrigger value="structure" className="gap-2">
            <List className="w-4 h-4" />
            <span className="hidden sm:inline">Estructura</span>
          </TabsTrigger>
          <TabsTrigger value="insights" className="gap-2">
            <Brain className="w-4 h-4" />
            <span className="hidden sm:inline">Hallazgos</span>
          </TabsTrigger>
          <TabsTrigger value="questions" className="gap-2">
            <HelpCircle className="w-4 h-4" />
            <span className="hidden sm:inline">Preguntas</span>
          </TabsTrigger>
        </TabsList>

        {/* TAB: RESUMEN */}
        <TabsContent value="summary" className="space-y-4 animate-in fade-in-50 duration-500">
          {analysis.executive_summary && (
            <Card className={`${docColors.cardBg} border-none shadow-md`}>
              <CardHeader className="pb-2 flex flex-row items-center justify-between">
                <CardTitle className={`text-lg font-bold ${docColors.cardTitle}`}>Resumen Ejecutivo</CardTitle>
                <SectionTTSButton
                  text={analysis.executive_summary || ""}
                  play={play}
                  isLoading={isLoading}
                  isPlaying={isPlaying}
                  activeText={activeText}
                />
              </CardHeader>
              <CardContent>
                <div className="prose prose-sm max-w-none dark:prose-invert text-muted-foreground leading-relaxed">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{analysis.executive_summary}</ReactMarkdown>
                </div>
              </CardContent>
            </Card>
          )}

          {analysis.general_analysis && (
            <Card className="border-none shadow-sm bg-muted/30">
              <CardHeader className="pb-2 flex flex-row items-center justify-between">
                <CardTitle className="text-md font-semibold flex items-center gap-2">
                  <Activity className="w-4 h-4 text-primary" />
                  Análisis General
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
                <div className="prose prose-sm max-w-none dark:prose-invert text-muted-foreground">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{analysis.general_analysis}</ReactMarkdown>
                </div>
              </CardContent>
            </Card>
          )}

          {analysis.kai_synthesis && (
            <div className="mt-6 p-4 rounded-xl bg-gradient-to-br from-primary/10 to-secondary/10 border border-primary/20 relative group">
              <div className="absolute top-4 right-4 opacity-0 group-hover:opacity-100 transition-opacity">
                <SectionTTSButton
                  text={analysis.kai_synthesis}
                  play={play}
                  isLoading={isLoading}
                  isPlaying={isPlaying}
                  activeText={activeText}
                />
              </div>
              <h4 className="text-sm font-bold uppercase tracking-wider text-primary mb-2 flex items-center gap-2">
                <Zap className="w-4 h-4" />
                Síntesis de KAI
              </h4>
              <p className="text-sm italic text-foreground/80 leading-relaxed">
                {analysis.kai_synthesis}
              </p>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
            {analysis.sentiment_analysis && (
              <div className="p-3 rounded-lg bg-background border shadow-sm">
                <span className="text-xs font-semibold text-muted-foreground block mb-1">Sentimiento Predominante</span>
                <div className="flex items-center justify-between">
                  <Badge variant="secondary" className="capitalize">{analysis.sentiment_analysis.overall_sentiment}</Badge>
                  <span className="text-sm font-bold">{(analysis.sentiment_analysis.score * 100).toFixed(0)}%</span>
                </div>
              </div>
            )}
            {analysis.relevance_score !== undefined && (
              <div className="p-3 rounded-lg bg-background border shadow-sm">
                <span className="text-xs font-semibold text-muted-foreground block mb-1">Puntuación de Relevancia</span>
                <div className="flex items-center gap-2">
                  <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary"
                      style={{ width: `${analysis.relevance_score * 10}%` }}
                    />
                  </div>
                  <span className="text-sm font-bold">{analysis.relevance_score}/10</span>
                </div>
              </div>
            )}
          </div>
        </TabsContent>

        {/* TAB: TEMAS Y CONCEPTOS */}
        <TabsContent value="themes" className="space-y-6 animate-in fade-in-50 duration-500">
          {analysis.key_themes && analysis.key_themes.length > 0 && (
            <div>
              <h4 className={`text-lg font-bold mb-4 flex items-center gap-2 ${docColors.icon}`}>
                <Target className="w-5 h-5" />
                Temas Clave Identificados
              </h4>
              <div className="flex flex-wrap gap-2">
                {analysis.key_themes.map((theme, index) => (
                  <InteractiveTag
                    key={index}
                    type="theme"
                    label={theme.theme}
                    onClick={() => handleThemeClick?.(theme)}
                  />
                ))}
              </div>
            </div>
          )}

          <Separator />

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {analysis.central_concepts && analysis.central_concepts.length > 0 && (
              <div>
                <h4 className="text-md font-bold mb-3 flex items-center gap-2">
                  <Brain className="w-4 h-4 text-purple-500" />
                  Conceptos Centrales
                </h4>
                <div className="flex flex-wrap gap-2">
                  {analysis.central_concepts.map((concept, index) => (
                    <InteractiveTag
                      key={index}
                      type="concept"
                      label={concept.split(':')[0]}
                      onClick={() => handleConceptClick?.(concept)}
                      className={docColors.tag}
                    />
                  ))}
                </div>
              </div>
            )}

            {analysis.keywords && analysis.keywords.length > 0 && (
              <div>
                <h4 className="text-md font-bold mb-3 flex items-center gap-2">
                  <List className="w-4 h-4 text-blue-500" />
                  Palabras Clave
                </h4>
                <div className="flex flex-wrap gap-2">
                  {analysis.keywords.map((keyword, index) => (
                    <Badge key={index} variant="secondary">
                      {keyword}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </div>
        </TabsContent>

        {/* TAB: ESTRUCTURA Y ENTIDADES */}
        <TabsContent value="structure" className="space-y-6 animate-in fade-in-50 duration-500">
          {analysis.document_structure && analysis.document_structure.length > 0 && (
            <div>
              <h4 className="text-lg font-bold mb-4 flex items-center gap-2">
                <Layout className="w-5 h-5 text-indigo-500" />
                Estructura del Documento
              </h4>
              <div className="relative border-l-2 border-muted ml-3 pl-6 space-y-6">
                {analysis.document_structure.map((section, index) => (
                  <div key={index} className="relative">
                    <div className="absolute -left-[31px] top-1 w-4 h-4 rounded-full bg-indigo-500 border-4 border-background" />
                    <h5 className="font-bold text-foreground">{section.section}</h5>
                    <p className="text-sm text-muted-foreground mt-1">{section.summary}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          <Separator />

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {analysis.key_entities && analysis.key_entities.length > 0 && (
              <div>
                <h4 className="text-md font-bold mb-3 flex items-center gap-2">
                  <Users className="w-4 h-4 text-orange-500" />
                  Entidades Relevantes
                </h4>
                <div className="space-y-2">
                  {analysis.key_entities.map((entity, index) => (
                    <div key={index} className="flex items-center justify-between p-2 rounded bg-muted/50 text-sm">
                      <span className="font-medium">{entity.entity}</span>
                      <Badge variant="outline" className="text-[10px] uppercase">{entity.type}</Badge>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="space-y-4">
              {analysis.discipline && analysis.discipline.length > 0 && (
                <div>
                  <h4 className="text-md font-bold mb-2">Disciplina / Ámbito</h4>
                  <div className="flex flex-wrap gap-2">
                    {analysis.discipline.map((d, i) => (
                      <Badge key={i} variant="outline">{d}</Badge>
                    ))}
                  </div>
                </div>
              )}
              {analysis.authorial_tone && (
                <div>
                  <h4 className="text-md font-bold mb-2">Tono del Autor</h4>
                  <p className="text-sm text-muted-foreground bg-muted/30 p-2 rounded border italic">
                    {analysis.authorial_tone}
                  </p>
                </div>
              )}
            </div>
          </div>
        </TabsContent>

        {/* TAB: HALLAZGOS Y ACCIÓN */}
        <TabsContent value="insights" className="space-y-6 animate-in fade-in-50 duration-500">
          {analysis.knowledge_gaps && analysis.knowledge_gaps.length > 0 && (
            <ActionableButton
              title="Brechas de Conocimiento"
              description="Identifica áreas donde falta información o se requiere más investigación."
              count={analysis.knowledge_gaps.length}
              variant="gap"
              onClick={() => openGapsSlider?.(analysis.knowledge_gaps || [], "Brechas de Conocimiento")}
            />
          )}

          {analysis.problematic_areas && analysis.problematic_areas.length > 0 && (
            <div>
              <h4 className="text-lg font-bold mb-4 flex items-center gap-2 text-red-600">
                <Activity className="w-5 h-5" />
                Áreas Problemáticas
              </h4>
              <ul className="space-y-2">
                {analysis.problematic_areas.map((area, index) => (
                  <li key={index} className="flex gap-2 text-sm text-muted-foreground p-2 rounded bg-red-50 dark:bg-red-900/10 border border-red-100 dark:border-red-900/30">
                    <span className="font-bold text-red-500">•</span>
                    {area}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {analysis.action_items && analysis.action_items.length > 0 && (
            <div>
              <h4 className="text-lg font-bold mb-4 flex items-center gap-2 text-green-600">
                <Zap className="w-5 h-5" />
                Acciones Recomendadas
              </h4>
              <div className="space-y-2">
                {analysis.action_items.map((item, index) => (
                  <div key={index} className="flex items-center gap-3 p-3 rounded-lg border bg-green-50/30 dark:bg-green-900/10">
                    <div className="w-6 h-6 rounded-full bg-green-500 text-white flex items-center justify-center text-xs font-bold">
                      {index + 1}
                    </div>
                    <p className="text-sm font-medium">{item}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {analysis.final_reflections && analysis.final_reflections.length > 0 && (
            <Card className="bg-muted/50 border-dashed">
              <CardHeader>
                <CardTitle className="text-md font-bold flex items-center gap-2">
                  <MessageSquare className="w-4 h-4" />
                  Reflexiones Finales
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2 text-sm text-muted-foreground italic">
                  {analysis.final_reflections.map((reflection, index) => (
                    <li key={index}>"{reflection}"</li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* TAB: PREGUNTAS */}
        <TabsContent value="questions" className="space-y-6 animate-in fade-in-50 duration-500">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {analysis.exploration_questions && analysis.exploration_questions.length > 0 && (
              <ActionableButton
                title="Preguntas de Exploración"
                description="Cuestionamientos clave para profundizar en el contenido."
                count={analysis.exploration_questions.length}
                variant="question"
                onClick={() => openQuestionsSlider?.(analysis.exploration_questions || [], "Preguntas de Exploración")}
              />
            )}

            {analysis.generated_questions && analysis.generated_questions.length > 0 && (
              <ActionableButton
                title="Preguntas Generadas"
                description="Preguntas automáticas basadas en el contexto del documento."
                count={analysis.generated_questions.length}
                variant="question"
                onClick={() => openQuestionsSlider?.(analysis.generated_questions || [], "Preguntas Generadas")}
              />
            )}
          </div>

          {((!analysis.exploration_questions || analysis.exploration_questions.length === 0) &&
            (!analysis.generated_questions || analysis.generated_questions.length === 0)) && (
              <div className="text-center py-12 text-muted-foreground">
                <HelpCircle className="w-12 h-12 mx-auto mb-4 opacity-20" />
                <p>No se generaron preguntas específicas para este documento.</p>
              </div>
            )}
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default DocumentAnalysis;

