import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { ProactiveInsightResult } from '@/lib/models';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Lightbulb, Zap, Link2, Info, MessageSquare, TrendingUp, AlertCircle } from 'lucide-react';

import { SectionTTSButton } from './analysis-detail-dialog';

interface ProactiveInsightAnalysisProps {
  analysis: ProactiveInsightResult;
  // TTS Props
  play: (text: string) => void;
  isLoading: boolean;
  isPlaying: boolean;
  activeText: string | null;
}

// Helper function to get Spanish labels for insight types
const getInsightTypeLabel = (type: string) => {
  switch (type) {
    case 'duplicidad': return 'Duplicidad';
    case 'sinergia': return 'Sinergia';
    case 'evolucion': return 'Evolución';
    case 'contradiccion': return 'Contradicción';
    default: return type;
  }
};

// Helper function to get color for confidence score
const getConfidenceColor = (score: number) => {
  if (score >= 0.8) return 'text-green-600 bg-green-50 border-green-200';
  if (score >= 0.6) return 'text-yellow-600 bg-yellow-50 border-yellow-200';
  return 'text-red-600 bg-red-50 border-red-200';
};

// Helper function to get confidence label
const getConfidenceLabel = (score: number) => {
  if (score >= 0.8) return 'Alta';
  if (score >= 0.6) return 'Media';
  return 'Baja';
};

const ProactiveInsightAnalysis: React.FC<ProactiveInsightAnalysisProps> = ({
  analysis,
  play,
  isLoading,
  isPlaying,
  activeText
}) => {
  if (!analysis) return null;

  const insightColors = {
    cardBg: 'bg-yellow-50/50 border-yellow-100 dark:bg-yellow-900/10 dark:border-yellow-900/50',
    cardTitle: 'text-yellow-900 dark:text-yellow-100',
    icon: 'text-yellow-600',
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 mb-2">
        <Lightbulb className={`w-6 h-6 ${insightColors.icon}`} />
        <h3 className="text-2xl font-bold">Insight Proactivo de KAI</h3>
      </div>

      {/* Summary Header with Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <Card className="bg-gradient-to-br from-blue-50 to-indigo-50 border-blue-200">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-100 rounded-lg">
                <TrendingUp className="w-4 h-4 text-blue-600" />
              </div>
              <div>
                <p className="text-xs font-medium text-blue-600 uppercase tracking-wide">Tipo de Insight</p>
                <p className="text-lg font-bold text-blue-900">{getInsightTypeLabel(analysis.type)}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-green-50 to-emerald-50 border-green-200">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-green-100 rounded-lg">
                <AlertCircle className="w-4 h-4 text-green-600" />
              </div>
              <div>
                <p className="text-xs font-medium text-green-600 uppercase tracking-wide">Confianza</p>
                <div className="flex items-center gap-2">
                  <p className="text-lg font-bold text-green-900">
                    {Math.round(analysis.confidence_score * 100)}%
                  </p>
                  <Badge variant="outline" className={`text-xs ${getConfidenceColor(analysis.confidence_score)}`}>
                    {getConfidenceLabel(analysis.confidence_score)}
                  </Badge>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-purple-50 to-violet-50 border-purple-200">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-purple-100 rounded-lg">
                <Link2 className="w-4 h-4 text-purple-600" />
              </div>
              <div>
                <p className="text-xs font-medium text-purple-600 uppercase tracking-wide">Elementos Relacionados</p>
                <p className="text-lg font-bold text-purple-900">
                  {Array.isArray(analysis.related_items) ? analysis.related_items.length : 0}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="insight" className="w-full">
        <TabsList className="grid w-full grid-cols-3 mb-8">
          <TabsTrigger value="insight" className="gap-2">
            <Info className="w-4 h-4" />
            <span className="hidden sm:inline">Insight</span>
          </TabsTrigger>
          <TabsTrigger value="action" className="gap-2">
            <Zap className="w-4 h-4" />
            <span className="hidden sm:inline">Acción</span>
          </TabsTrigger>
          <TabsTrigger value="related" className="gap-2">
            <Link2 className="w-4 h-4" />
            <span className="hidden sm:inline">Relacionados</span>
          </TabsTrigger>
        </TabsList>

        {/* TAB: INSIGHT */}
        <TabsContent value="insight" className="space-y-4 animate-in fade-in-50 duration-500">
          <Card className={`${insightColors.cardBg} border-none shadow-md`}>
            <CardHeader className="pb-2 flex flex-row items-center justify-between">
              <CardTitle className={`text-lg font-bold ${insightColors.cardTitle} flex items-center gap-2`}>
                <Badge variant="outline" className="bg-yellow-100 dark:bg-yellow-900/30 border-yellow-200 text-yellow-700 dark:text-yellow-300">
                  {getInsightTypeLabel(analysis.type)}
                </Badge>
                <span>Análisis de Situación</span>
              </CardTitle>
              <SectionTTSButton
                text={analysis.insight_message}
                play={play}
                isLoading={isLoading}
                isPlaying={isPlaying}
                activeText={activeText}
              />
            </CardHeader>
            <CardContent>
              <div className="text-sm text-foreground leading-relaxed">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{analysis.insight_message}</ReactMarkdown>
              </div>
            </CardContent>
          </Card>

          {analysis.kai_synthesis && (
            <div className="mt-6 p-5 rounded-xl bg-gradient-to-br from-yellow-500/10 to-orange-500/10 border border-yellow-500/20 shadow-inner relative group">
              <div className="absolute top-4 right-4 opacity-0 group-hover:opacity-100 transition-opacity">
                <SectionTTSButton
                  text={analysis.kai_synthesis}
                  play={play}
                  isLoading={isLoading}
                  isPlaying={isPlaying}
                  activeText={activeText}
                />
              </div>
              <h4 className="text-sm font-bold uppercase tracking-wider text-yellow-600 dark:text-yellow-400 mb-2 flex items-center gap-2">
                <Zap className="w-4 h-4" />
                Síntesis de KAI
              </h4>
              <p className="text-sm italic text-foreground/90 leading-relaxed">
                {analysis.kai_synthesis}
              </p>
            </div>
          )}
        </TabsContent>

        {/* TAB: ACCIÓN */}
        <TabsContent value="action" className="space-y-6 animate-in fade-in-50 duration-500">
          {analysis.action_suggestion ? (
            <div>
              <h4 className={`text-lg font-bold mb-4 flex items-center gap-2 ${insightColors.icon}`}>
                <Zap className="w-5 h-5" />
                Sugerencia de Acción Inmediata
              </h4>
              <Card className="border-l-4 border-l-yellow-500 bg-yellow-50/20">
                <CardContent className="pt-6">
                  <p className="text-sm font-medium text-foreground leading-relaxed">
                    {analysis.action_suggestion}
                  </p>
                </CardContent>
              </Card>
            </div>
          ) : (
            <div className="text-center py-12 text-muted-foreground">
              <Zap className="w-12 h-12 mx-auto mb-4 opacity-20" />
              <p>No hay acciones sugeridas para este insight en este momento.</p>
            </div>
          )}
        </TabsContent>

        {/* TAB: RELACIONADOS */}
        <TabsContent value="related" className="space-y-6 animate-in fade-in-50 duration-500">
          {Array.isArray(analysis.related_items) && analysis.related_items.length > 0 ? (
            <div>
              <h4 className="text-lg font-bold mb-4 flex items-center gap-2 text-slate-600">
                <Link2 className="w-5 h-5" />
                Elementos del Exocerebro Conectados
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {Array.isArray(analysis.related_items) && analysis.related_items.length > 0 ? (
                  analysis.related_items.map((item, index) => (
                    <div key={index} className="p-4 rounded-xl border bg-card shadow-sm hover:shadow-md transition-shadow">
                      <h5 className="font-bold text-sm mb-2 flex items-center gap-2">
                        <MessageSquare className="w-3 h-3 text-primary" />
                        {item.title || item.name || item.id || `Elemento ${index + 1}`}
                      </h5>
                      <p className="text-xs text-muted-foreground line-clamp-3 leading-relaxed">
                        {item.content || item.description || item.summary || 'Sin descripción disponible'}
                      </p>
                      {item.type && (
                        <Badge variant="secondary" className="mt-2 text-xs">
                          {item.type}
                        </Badge>
                      )}
                    </div>
                  ))
                ) : (
                  <div className="col-span-2 text-center py-8 text-muted-foreground">
                    <MessageSquare className="w-8 h-8 mx-auto mb-2 opacity-20" />
                    <p>No hay elementos relacionados disponibles</p>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="text-center py-12 text-muted-foreground">
              <Link2 className="w-12 h-12 mx-auto mb-4 opacity-20" />
              <p>No se encontraron elementos relacionados directamente.</p>
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default ProactiveInsightAnalysis;
