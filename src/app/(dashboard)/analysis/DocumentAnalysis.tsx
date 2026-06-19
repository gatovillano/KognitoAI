import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { DocumentAnalysisResult as SingleTextAnalysisType } from '@/lib/models';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  FileText,
  Brain,
  HelpCircle,
  Activity,
  Target,
  Zap,
  MessageSquare,
  AlertTriangle,
  Lightbulb,
} from 'lucide-react';
import { InteractiveTag } from '@/components/analysis/InteractiveTag';
import { SectionTTSButton } from './analysis-detail-dialog';
import { ActionableButton } from '@/components/analysis/ActionableButton';

interface DocumentAnalysisProps {
  analysis: SingleTextAnalysisType;
  docColors: any;
  handleThemeClick?: (theme: any) => void;
  handleConceptClick?: (concept: string) => void;
  openGapsSlider?: (gaps: any[], title: string) => void;
  openQuestionsSlider?: (questions: any[], title: string) => void;
  play: (text: string) => void;
  isLoading: boolean;
  isPlaying: boolean;
  activeText: string | null;
  documentTitle?: string;
}

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
  activeText,
  documentTitle,
}) => {
  if (!analysis) return null;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 mb-2">
        <FileText className={`w-6 h-6 ${docColors.icon}`} />
        <h3 className="text-2xl font-bold">{documentTitle || 'Análisis Detallado del Documento'}</h3>
      </div>

      <Tabs defaultValue="summary" className="w-full">
        <TabsList className="grid w-full grid-cols-6 mb-8">
          <TabsTrigger value="summary" className="gap-2">
            <FileText className="w-4 h-4" />
            <span className="hidden sm:inline">Resumen</span>
          </TabsTrigger>
          <TabsTrigger value="analysis" className="gap-2">
            <Activity className="w-4 h-4" />
            <span className="hidden sm:inline">Análisis</span>
          </TabsTrigger>
          <TabsTrigger value="themes" className="gap-2">
            <Target className="w-4 h-4" />
            <span className="hidden sm:inline">Temas</span>
          </TabsTrigger>
          <TabsTrigger value="concepts" className="gap-2">
            <Brain className="w-4 h-4" />
            <span className="hidden sm:inline">Conceptos</span>
          </TabsTrigger>
          <TabsTrigger value="gaps" className="gap-2">
            <AlertTriangle className="w-4 h-4" />
            <span className="hidden sm:inline">Brechas</span>
          </TabsTrigger>
          <TabsTrigger value="questions" className="gap-2">
            <HelpCircle className="w-4 h-4" />
            <span className="hidden sm:inline">Preguntas</span>
          </TabsTrigger>
        </TabsList>

        <TabsContent value="summary" className="space-y-4 animate-in fade-in-50 duration-500">
          {analysis.executive_summary && (
            <Card className={`${docColors.cardBg} border-none shadow-md`}>
              <CardHeader className="pb-2 flex flex-row items-center justify-between">
                <CardTitle className={`text-lg font-bold ${docColors.cardTitle}`}>Resumen Ejecutivo</CardTitle>
                <SectionTTSButton
                  text={analysis.executive_summary}
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

          {!analysis.executive_summary && (
            <div className="text-center py-12 text-muted-foreground">
              No hay un resumen ejecutivo disponible para este análisis.
            </div>
          )}
        </TabsContent>

        <TabsContent value="analysis" className="space-y-4 animate-in fade-in-50 duration-500">
          {analysis.general_analysis && (
            <Card className="border-none shadow-sm bg-muted/30">
              <CardHeader className="pb-2 flex flex-row items-center justify-between">
                <CardTitle className="text-md font-semibold flex items-center gap-2">
                  <Activity className="w-4 h-4 text-primary" />
                  Análisis General
                </CardTitle>
                <SectionTTSButton
                  text={analysis.general_analysis}
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
              <p className="text-sm italic text-foreground/80 leading-relaxed">{analysis.kai_synthesis}</p>
            </div>
          )}

          {Array.isArray(analysis.final_reflections) && analysis.final_reflections.length > 0 && (
            <Card className="bg-muted/50 border-dashed">
              <CardHeader>
                <CardTitle className="text-md font-bold flex items-center gap-2">
                  <Lightbulb className="w-4 h-4" />
                  Reflexiones Finales
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2 text-sm text-muted-foreground italic">
                  {analysis.final_reflections.map((reflection: any, index: number) => (
                    <li key={index}>
                      "{typeof reflection === 'string' ? reflection : (reflection.reflection || reflection.thought || JSON.stringify(reflection))}"
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}

          {!analysis.general_analysis && !analysis.kai_synthesis && (!analysis.final_reflections || analysis.final_reflections.length === 0) && (
            <div className="text-center py-12 text-muted-foreground">
              No hay contenido analítico extendido para este documento.
            </div>
          )}
        </TabsContent>

        <TabsContent value="themes" className="space-y-6 animate-in fade-in-50 duration-500">
          {Array.isArray(analysis.key_themes) && analysis.key_themes.length > 0 ? (
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
          ) : (
            <div className="text-center py-12 text-muted-foreground">
              No se identificaron temas clave en este análisis.
            </div>
          )}
        </TabsContent>

        <TabsContent value="concepts" className="space-y-6 animate-in fade-in-50 duration-500">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {Array.isArray(analysis.central_concepts) && analysis.central_concepts.length > 0 && (
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

            <div className="space-y-4">
              {Array.isArray(analysis.discipline) && analysis.discipline.length > 0 && (
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

          {(!analysis.central_concepts || analysis.central_concepts.length === 0) &&
            (!analysis.discipline || analysis.discipline.length === 0) &&
            !analysis.authorial_tone && (
              <div className="text-center py-12 text-muted-foreground">
                No hay conceptos o metadatos interpretativos para mostrar.
              </div>
            )}
        </TabsContent>

        <TabsContent value="gaps" className="space-y-6 animate-in fade-in-50 duration-500">
          {Array.isArray(analysis.knowledge_gaps) && analysis.knowledge_gaps.length > 0 && (
            <ActionableButton
              title="Brechas de Conocimiento"
              description="Identifica áreas donde falta información o se requiere más investigación."
              count={analysis.knowledge_gaps.length}
              variant="gap"
              onClick={() => openGapsSlider?.(analysis.knowledge_gaps || [], 'Brechas de Conocimiento')}
            />
          )}

          {Array.isArray(analysis.problematic_areas) && analysis.problematic_areas.length > 0 && (
            <div>
              <h4 className="text-lg font-bold mb-4 flex items-center gap-2 text-red-600">
                <AlertTriangle className="w-5 h-5" />
                Áreas Problemáticas
              </h4>
              <ul className="space-y-2">
                {analysis.problematic_areas.map((area: any, index: number) => (
                  <li key={index} className="flex gap-2 text-sm text-muted-foreground p-2 rounded bg-red-50 dark:bg-red-900/10 border border-red-100 dark:border-red-900/30">
                    <span className="font-bold text-red-500">•</span>
                    {typeof area === 'string' ? area : (area.issue || area.description || area.gap || JSON.stringify(area))}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {((!analysis.knowledge_gaps || analysis.knowledge_gaps.length === 0) &&
            (!analysis.problematic_areas || analysis.problematic_areas.length === 0)) && (
              <div className="text-center py-12 text-muted-foreground">
                No se registraron brechas ni áreas problemáticas destacables.
              </div>
            )}
        </TabsContent>

        <TabsContent value="questions" className="space-y-6 animate-in fade-in-50 duration-500">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {Array.isArray(analysis.exploration_questions) && analysis.exploration_questions.length > 0 && (
              <ActionableButton
                title="Preguntas de Exploración"
                description="Cuestionamientos clave para profundizar en el contenido."
                count={analysis.exploration_questions.length}
                variant="question"
                onClick={() => openQuestionsSlider?.(analysis.exploration_questions || [], 'Preguntas de Exploración')}
              />
            )}
          </div>

          {(!analysis.exploration_questions || analysis.exploration_questions.length === 0) && (
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
