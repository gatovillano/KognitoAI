import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { CodeAnalysisResultFrontend } from '@/lib/models';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Code, Layout, GitBranch, AlertTriangle, Zap, Info, Box, Puzzle, CircleCheck, Sparkles, ShieldCheck, Gauge, Hammer, FileText } from 'lucide-react';

interface CodeAnalysisProps {
  analysis: CodeAnalysisResultFrontend;
  codeColors: any;
}

const CodeAnalysis: React.FC<CodeAnalysisProps> = ({
  analysis,
  codeColors,
}) => {
  if (!analysis) return null;

  // Determinar qué pestañas mostrar basadas en si hay datos
  const hasStructure = Array.isArray(analysis.code_structure) && analysis.code_structure.length > 0;
  const hasPatterns = Array.isArray(analysis.design_patterns) && analysis.design_patterns.length > 0;
  const hasSecurity = Array.isArray(analysis.security_analysis) && analysis.security_analysis.length > 0;
  const hasPerformance = Array.isArray(analysis.performance_analysis) && analysis.performance_analysis.length > 0;
  const hasRefactoring = Array.isArray(analysis.refactoring_opportunities) && analysis.refactoring_opportunities.length > 0;
  const hasDocs = Array.isArray(analysis.documentation_health) && analysis.documentation_health.length > 0;
  const hasDeps = Array.isArray(analysis.dependencies) && analysis.dependencies.length > 0;
  const hasIssues = Array.isArray(analysis.potential_issues) && analysis.potential_issues.length > 0;
  const hasRecommendations = Array.isArray(analysis.recommendations) && analysis.recommendations.length > 0;

  return (
    <div className="space-y-6 w-full max-w-full overflow-x-hidden">
      <div className="flex items-center gap-2 mb-2">
        <Code className={`w-6 h-6 ${codeColors.icon}`} />
        <h3 className="text-2xl font-bold">Análisis Técnico de Código</h3>
      </div>

      <Tabs defaultValue="summary" className="w-full">
        <div className="overflow-x-auto pb-2 mb-6 scrollbar-hide">
          <TabsList className="flex w-max min-w-full lg:w-full lg:grid lg:grid-cols-9 gap-1">
            <TabsTrigger value="summary" className="gap-2 px-3">
              <Info className="w-4 h-4" />
              <span className="text-xs lg:text-sm">Resumen</span>
            </TabsTrigger>
            {(hasStructure || hasPatterns) && (
              <TabsTrigger value="architecture" className="gap-2 px-3">
                <Layout className="w-4 h-4" />
                <span className="text-xs lg:text-sm">Arquitectura</span>
              </TabsTrigger>
            )}
            {hasSecurity && (
              <TabsTrigger value="security" className="gap-2 px-3">
                <ShieldCheck className="w-4 h-4" />
                <span className="text-xs lg:text-sm">Seguridad</span>
              </TabsTrigger>
            )}
            {hasPerformance && (
              <TabsTrigger value="performance" className="gap-2 px-3">
                <Gauge className="w-4 h-4" />
                <span className="text-xs lg:text-sm">Rendimiento</span>
              </TabsTrigger>
            )}
            {hasRefactoring && (
              <TabsTrigger value="refactoring" className="gap-2 px-3">
                <Hammer className="w-4 h-4" />
                <span className="text-xs lg:text-sm">Refactor</span>
              </TabsTrigger>
            )}
            {hasDocs && (
              <TabsTrigger value="docs" className="gap-2 px-3">
                <FileText className="w-4 h-4" />
                <span className="text-xs lg:text-sm">Docs</span>
              </TabsTrigger>
            )}
            {hasDeps && (
              <TabsTrigger value="dependencies" className="gap-2 px-3">
                <Box className="w-4 h-4" />
                <span className="text-xs lg:text-sm">Dependencias</span>
              </TabsTrigger>
            )}
            {hasIssues && (
              <TabsTrigger value="issues" className="gap-2 px-3">
                <AlertTriangle className="w-4 h-4" />
                <span className="text-xs lg:text-sm">Problemas</span>
              </TabsTrigger>
            )}
            {hasRecommendations && (
              <TabsTrigger value="recommendations" className="gap-2 px-3">
                <Zap className="w-4 h-4" />
                <span className="text-xs lg:text-sm">Mejoras</span>
              </TabsTrigger>
            )}
          </TabsList>
        </div>

        {/* TAB: RESUMEN */}
        <TabsContent value="summary" className="space-y-4 animate-in fade-in-50 duration-500 w-full min-w-0">
          {analysis.executive_summary ? (
            <Card className={`${codeColors.cardBg} border-none shadow-md overflow-hidden`}>
              <CardHeader className="pb-2">
                <CardTitle className={`text-lg font-bold ${codeColors.cardTitle}`}>Resumen Ejecutivo</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="prose prose-sm max-w-none dark:prose-invert text-muted-foreground leading-relaxed break-words [word-break:break-word] overflow-hidden">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{analysis.executive_summary}</ReactMarkdown>
                </div>
              </CardContent>
            </Card>
          ) : (
            <div className="text-center py-12 text-muted-foreground">
              <Info className="w-12 h-12 mx-auto mb-4 opacity-20" />
              <p>No hay un resumen ejecutivo disponible para este análisis.</p>
            </div>
          )}
        </TabsContent>

        {/* TAB: ARQUITECTURA */}
        <TabsContent value="architecture" className="space-y-6 animate-in fade-in-50 duration-500 w-full min-w-0">
          {hasStructure && (
            <div>
              <h4 className={`text-lg font-bold mb-4 flex items-center gap-2 ${codeColors.icon}`}>
                <Layout className="w-5 h-5" />
                Estructura de Componentes
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {analysis.code_structure?.map((item, index) => (
                  <Card key={index} className="border-muted/60 hover:shadow-md transition-all min-w-0 overflow-hidden">
                    <CardHeader className="py-3 px-4 bg-muted/20">
                      <CardTitle className="text-sm font-bold flex items-center gap-2">
                        <GitBranch className="w-3 h-3 text-primary flex-shrink-0" />
                        <span className="truncate block" title={item.component}>{item.component}</span>
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="py-3 px-4">
                      <p className="text-xs text-muted-foreground break-words">{item.description}</p>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          )}

          {hasStructure && hasPatterns && <Separator />}

          {hasPatterns && (
            <div>
              <h4 className="text-lg font-bold mb-4 flex items-center gap-2">
                <Puzzle className="w-5 h-5 text-purple-500" />
                Patrones de Diseño
              </h4>
              <div className="space-y-3">
                {analysis.design_patterns?.map((item, index) => (
                  <div key={index} className="p-4 rounded-xl border bg-card shadow-sm break-words overflow-hidden">
                    <h5 className="font-bold text-foreground mb-1 break-all">{item.pattern}</h5>
                    <p className="text-sm text-muted-foreground">{item.description}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </TabsContent>

        {/* TAB: SEGURIDAD */}
        <TabsContent value="security" className="space-y-6 animate-in fade-in-50 duration-500 w-full min-w-0">
          {hasSecurity && (
            <div>
              <h4 className="text-lg font-bold mb-4 flex items-center gap-2 text-orange-600">
                <ShieldCheck className="w-5 h-5" />
                Análisis de Seguridad
              </h4>
              <div className="space-y-3">
                {analysis.security_analysis?.map((item, index) => (
                  <Card key={index} className={`border-l-4 ${
                    item.severity === 'Critical' || item.severity === 'High' ? 'border-l-red-500 bg-red-50/10' : 'border-l-orange-500 bg-orange-50/10'
                  } overflow-hidden`}>
                    <CardHeader className="py-3 px-4 flex flex-row items-center justify-between">
                      <CardTitle className="text-sm font-bold">{item.vulnerability}</CardTitle>
                      <Badge variant={item.severity === 'Critical' || item.severity === 'High' ? 'destructive' : 'outline'}>
                        {item.severity}
                      </Badge>
                    </CardHeader>
                    <CardContent className="py-3 px-4">
                      <p className="text-xs text-muted-foreground">{item.description}</p>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          )}
        </TabsContent>

        {/* TAB: RENDIMIENTO */}
        <TabsContent value="performance" className="space-y-6 animate-in fade-in-50 duration-500 w-full min-w-0">
          {hasPerformance && (
            <div>
              <h4 className="text-lg font-bold mb-4 flex items-center gap-2 text-blue-500">
                <Gauge className="w-5 h-5" />
                Rendimiento y Eficiencia
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {analysis.performance_analysis?.map((item, index) => (
                  <Card key={index} className="border-muted/60">
                    <CardHeader className="py-3 px-4 bg-blue-50/30 dark:bg-blue-900/10">
                      <div className="flex items-center justify-between">
                        <Badge variant="secondary" className="text-[10px] uppercase">{item.area}</Badge>
                      </div>
                      <CardTitle className="text-sm font-bold mt-2">{item.issue}</CardTitle>
                    </CardHeader>
                    <CardContent className="py-3 px-4">
                      <p className="text-xs text-muted-foreground mb-2"><strong>Sugerencia:</strong> {item.suggestion}</p>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          )}
        </TabsContent>

        {/* TAB: REFACTOR */}
        <TabsContent value="refactoring" className="space-y-6 animate-in fade-in-50 duration-500 w-full min-w-0">
          {hasRefactoring && (
            <div>
              <h4 className="text-lg font-bold mb-4 flex items-center gap-2 text-indigo-500">
                <Hammer className="w-5 h-5" />
                Oportunidades de Refactorización
              </h4>
              <div className="space-y-3">
                {analysis.refactoring_opportunities?.map((item, index) => (
                  <Card key={index} className="border-muted/60">
                    <CardHeader className="py-3 px-4">
                      <CardTitle className="text-sm font-bold text-indigo-600 dark:text-indigo-400">{item.concept}</CardTitle>
                    </CardHeader>
                    <CardContent className="py-3 px-4 space-y-2">
                      <p className="text-xs text-muted-foreground">{item.description}</p>
                      <div className="flex items-center gap-2 mt-2">
                        <CircleCheck className="w-3 h-3 text-green-500" />
                        <span className="text-[10px] font-bold uppercase text-muted-foreground">Beneficio: {item.benefit}</span>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          )}
        </TabsContent>

        {/* TAB: DOCS */}
        <TabsContent value="docs" className="space-y-6 animate-in fade-in-50 duration-500 w-full min-w-0">
          {hasDocs && (
            <div>
              <h4 className="text-lg font-bold mb-4 flex items-center gap-2 text-teal-600">
                <FileText className="w-5 h-5" />
                Salud de la Documentación
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {analysis.documentation_health?.map((item, index) => (
                  <Card key={index} className="border-muted/60">
                    <CardHeader className="py-3 px-4 flex flex-row items-center justify-between space-y-0">
                      <CardTitle className="text-sm font-bold">{item.item}</CardTitle>
                      <Badge variant={item.status === 'Good' ? 'secondary' : 'outline'} className={item.status === 'Good' ? 'bg-green-500/10 text-green-600 border-none' : ''}>
                        {item.status}
                      </Badge>
                    </CardHeader>
                    <CardContent className="py-3 px-4">
                      <p className="text-xs text-muted-foreground">{item.recommendation}</p>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          )}
        </TabsContent>

        {/* TAB: DEPENDENCIAS */}
        <TabsContent value="dependencies" className="space-y-6 animate-in fade-in-50 duration-500 w-full min-w-0">
          {hasDeps ? (
            <div>
              <h4 className="text-lg font-bold mb-4 flex items-center gap-2 text-blue-600">
                <Box className="w-5 h-5" />
                Librerías y Dependencias
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {analysis.dependencies?.map((item, index) => (
                  <div key={index} className="p-3 rounded-lg border bg-blue-50/30 dark:bg-blue-900/10 flex flex-col gap-1 min-w-0 overflow-hidden">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-bold text-sm text-blue-700 dark:text-blue-300 truncate" title={item.library}>{item.library}</span>
                      <Badge variant="outline" className="text-[10px] flex-shrink-0">Dep</Badge>
                    </div>
                    <p className="text-xs text-muted-foreground break-words">{item.description}</p>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="text-center py-12 text-muted-foreground">
              <Box className="w-12 h-12 mx-auto mb-4 opacity-20" />
              <p>No se identificaron dependencias externas relevantes.</p>
            </div>
          )}
        </TabsContent>

        {/* TAB: PROBLEMAS */}
        <TabsContent value="issues" className="space-y-6 animate-in fade-in-50 duration-500 w-full min-w-0">
          {hasIssues ? (
            <div>
              <h4 className="text-lg font-bold mb-4 flex items-center gap-2 text-red-600">
                <AlertTriangle className="w-5 h-5" />
                Problemas Potenciales Detectados
              </h4>
              <div className="space-y-3">
                {analysis.potential_issues?.map((item, index) => (
                  <Card key={index} className="border-l-4 border-l-red-500 bg-red-50/20 overflow-hidden min-w-0">
                    <CardContent className="pt-4">
                      <h5 className="font-bold text-red-900 dark:text-red-100 break-words whitespace-normal">{item.issue}</h5>
                      <div className="prose prose-sm max-w-none dark:prose-invert text-muted-foreground mt-1 leading-relaxed break-words whitespace-normal overflow-hidden">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{item.description}</ReactMarkdown>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          ) : (
            <div className="text-center py-12 text-muted-foreground">
              <CircleCheck className="w-12 h-12 mx-auto mb-4 text-green-500 opacity-50" />
              <p>No se detectaron problemas potenciales en el código.</p>
            </div>
          )}
        </TabsContent>

        {/* TAB: MEJORAS */}
        <TabsContent value="recommendations" className="space-y-6 animate-in fade-in-50 duration-500 w-full min-w-0">
          {hasRecommendations ? (
            <div>
              <h4 className="text-lg font-bold mb-4 flex items-center gap-2 text-green-600">
                <Zap className="w-5 h-5" />
                Recomendaciones de Mejora
              </h4>
              <div className="space-y-4">
                {analysis.recommendations?.map((item, index) => (
                  <div key={index} className="p-4 rounded-xl border bg-green-50/30 dark:bg-green-900/10 space-y-3 overflow-hidden">
                    <div className="flex items-center gap-2">
                      <div className="w-6 h-6 rounded-full bg-green-500 text-white flex items-center justify-center text-xs font-bold flex-shrink-0">
                        {index + 1}
                      </div>
                      <h5 className="font-bold text-foreground break-words whitespace-normal">{item.recommendation}</h5>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm w-full min-w-0">
                      <div className="min-w-0 overflow-hidden">
                        <span className="text-xs font-bold text-muted-foreground uppercase block mb-1">Razón</span>
                        <div className="prose prose-sm max-w-none dark:prose-invert text-muted-foreground leading-relaxed break-words whitespace-normal overflow-hidden">
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>{item.rationale}</ReactMarkdown>
                        </div>
                      </div>
                      <div className="min-w-0 overflow-hidden">
                        <span className="text-xs font-bold text-muted-foreground uppercase block mb-1">Aplicación</span>
                        <div className="prose prose-sm max-w-none dark:prose-invert text-muted-foreground leading-relaxed break-words whitespace-normal overflow-hidden">
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>{item.application}</ReactMarkdown>
                        </div>
                      </div>
                    </div>
                    {item.implementation && (
                      <div className="pt-2">
                        <span className="text-xs font-bold text-muted-foreground uppercase block mb-1">Implementación</span>
                        <pre className="text-xs bg-muted p-3 rounded-lg border whitespace-pre-wrap break-words font-mono leading-relaxed">
                          {item.implementation}
                        </pre>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="text-center py-12 text-muted-foreground">
              <Sparkles className="w-12 h-12 mx-auto mb-4 text-yellow-500 opacity-50" />
              <p>El código sigue las mejores prácticas identificadas.</p>
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default CodeAnalysis;
