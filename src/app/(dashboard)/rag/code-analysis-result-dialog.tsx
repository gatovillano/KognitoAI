'use client';

import { useMemo } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { InlineMarkdownRenderer } from '@/components/InlineMarkdownRenderer';
import { Code, FileText, Settings, AlertTriangle, Lightbulb, GitBranch } from 'lucide-react';
import apiClient from '@/lib/api';
import { toast } from 'sonner';
import { useTextToSpeech } from '@/hooks/useTextToSpeech';

interface CodeAnalysisItem {
  component?: string;
  pattern?: string;
  library?: string;
  issue?: string;
  recommendation?: string;
  description: string;
  rationale?: string;
  application?: string;
  implementation?: string;
}

interface CodeAnalysisResultDialogProps {
  repoName: string | null;
  analysis: any;
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CodeAnalysisResultDialog({ repoName, analysis, isOpen, onOpenChange }: CodeAnalysisResultDialogProps) {
  if (!analysis) return null;

  console.log("Code Analysis object:", analysis);

  // Helper function to ensure array and handle different data structures
  const ensureCodeArray = (value: any): CodeAnalysisItem[] => {
    if (!value) return [];
    if (Array.isArray(value)) return value;
    return [];
  };

  const codeStructure = ensureCodeArray(analysis.code_structure);
  const designPatterns = ensureCodeArray(analysis.design_patterns);
  const dependencies = ensureCodeArray(analysis.dependencies);
  const potentialIssues = ensureCodeArray(analysis.potential_issues);
  const recommendations = ensureCodeArray(analysis.recommendations);
  const executiveSummary = analysis.executive_summary || 'No se proporcionó un resumen ejecutivo.';
  const formattedResult = analysis.formatted_result || '';
  const metadata = analysis.analysis_metadata || {};

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-5xl w-full max-h-[90vh] rounded-3xl backdrop-blur-xl bg-card/95 border-0 shadow-2xl flex flex-col p-0">
        <DialogHeader className="p-6 pb-4 border-b">
          <DialogTitle className="flex items-center gap-2 text-2xl font-bold text-foreground">
            <Code className="h-6 w-6" />
            Análisis de Código - {repoName || 'Repositorio'}
          </DialogTitle>
          <DialogDescription className="text-muted-foreground">
            {metadata.total_files && metadata.total_chunks ?
              `Análisis de ${metadata.total_files} archivos en ${metadata.total_chunks} partes` :
              'Análisis completo del repositorio'
            }
          </DialogDescription>
        </DialogHeader>
        <Tabs defaultValue="overview" className="flex-1 flex flex-col min-h-0">
          <TabsList className="grid w-full grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6 bg-transparent border-b border-border/50 mb-4 px-6">
            <TabsTrigger value="overview">Resumen</TabsTrigger>
            <TabsTrigger value="structure">Estructura</TabsTrigger>
            <TabsTrigger value="patterns">Patrones</TabsTrigger>
            <TabsTrigger value="dependencies">Dependencias</TabsTrigger>
            <TabsTrigger value="issues">Problemas</TabsTrigger>
            <TabsTrigger value="recommendations">Recomendaciones</TabsTrigger>
          </TabsList>
          <div className="flex-1 overflow-y-auto">
            <div className="p-6 space-y-6">
              <TabsContent value="overview" className="mt-0 space-y-4">
                <Card className="border-none shadow-none bg-transparent p-0">
                  <CardHeader className="px-0 pt-0 pb-2">
                    <CardTitle className="flex items-center gap-2 text-lg font-semibold text-foreground">
                      <FileText className="h-5 w-5" />
                      Resumen Ejecutivo
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-0">
                    <p className="text-sm text-muted-foreground whitespace-pre-wrap leading-relaxed p-3 bg-muted rounded-md border border-border/50">{executiveSummary}</p>
                  </CardContent>
                </Card>
                {formattedResult && (
                  <Card className="border-none shadow-none bg-transparent p-0">
                    <CardHeader className="px-0 pt-0 pb-2">
                      <CardTitle className="text-lg font-semibold text-foreground">Análisis Detallado</CardTitle>
                    </CardHeader>
                    <CardContent className="p-0">
                      <div className="prose prose-sm dark:prose-invert max-w-none p-3 bg-muted rounded-md border border-border/50">
                        <InlineMarkdownRenderer content={formattedResult} />
                      </div>
                    </CardContent>
                  </Card>
                )}
              </TabsContent>
              <TabsContent value="structure" className="mt-0 space-y-4">
                <Card className="border-none shadow-none bg-transparent p-0">
                  <CardHeader className="px-0 pt-0 pb-2">
                    <CardTitle className="flex items-center gap-2 text-lg font-semibold text-foreground">
                      <GitBranch className="h-5 w-5" />
                      Estructura del Código ({codeStructure.length} componentes)
                    </CardTitle>
                    <CardDescription className="text-muted-foreground">
                      Componentes principales identificados en el código
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="p-0">
                    {codeStructure.length > 0 ? (
                      <div className="space-y-3">
                        {codeStructure.map((item, i) => (
                          <div key={i} className="border-l-4 border-blue-500 pl-4 p-3 bg-muted rounded-md border border-border/50">
                            <h4 className="font-medium text-foreground">{item.component}</h4>
                            <p className="text-sm text-muted-foreground">{item.description}</p>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-sm text-muted-foreground">No se encontraron componentes de estructura.</p>
                    )}
                  </CardContent>
                </Card>
              </TabsContent>
              <TabsContent value="patterns" className="mt-0 space-y-4">
                <Card className="border-none shadow-none bg-transparent p-0">
                  <CardHeader className="px-0 pt-0 pb-2">
                    <CardTitle className="flex items-center gap-2 text-lg font-semibold text-foreground">
                      <Settings className="h-5 w-5" />
                      Patrones de Diseño ({designPatterns.length} patrones)
                    </CardTitle>
                    <CardDescription className="text-muted-foreground">
                      Patrones de diseño identificados en el código
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="p-0">
                    {designPatterns.length > 0 ? (
                      <div className="space-y-3">
                        {designPatterns.map((item, i) => (
                          <div key={i} className="border-l-4 border-green-500 pl-4 p-3 bg-muted rounded-md border border-border/50">
                            <h4 className="font-medium text-foreground">{item.pattern}</h4>
                            <p className="text-sm text-muted-foreground">{item.description}</p>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-sm text-muted-foreground">No se encontraron patrones de diseño específicos.</p>
                    )}
                  </CardContent>
                </Card>
              </TabsContent>
              <TabsContent value="dependencies" className="mt-0 space-y-4">
                <Card className="border-none shadow-none bg-transparent p-0">
                  <CardHeader className="px-0 pt-0 pb-2">
                    <CardTitle className="text-lg font-semibold text-foreground">Dependencias ({dependencies.length} bibliotecas)</CardTitle>
                    <CardDescription className="text-muted-foreground">
                      Bibliotecas y frameworks utilizados
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="p-0">
                    {dependencies.length > 0 ? (
                      <div className="grid gap-3">
                        {dependencies.map((item, i) => (
                          <div key={i} className="flex flex-col sm:flex-row items-start sm:items-center gap-2 sm:gap-3 p-3 border rounded-lg border-border/50">
                            <Badge variant="secondary">{item.library}</Badge>
                            <p className="text-sm text-muted-foreground flex-1">{item.description}</p>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-sm text-muted-foreground">No se identificaron dependencias específicas.</p>
                    )}
                  </CardContent>
                </Card>
              </TabsContent>
              <TabsContent value="issues" className="mt-0 space-y-4">
                <Card className="border-none shadow-none bg-transparent p-0">
                  <CardHeader className="px-0 pt-0 pb-2">
                    <CardTitle className="flex items-center gap-2 text-lg font-semibold text-foreground">
                      <AlertTriangle className="h-5 w-5 text-orange-500" />
                      Problemas Potenciales ({potentialIssues.length} problemas)
                    </CardTitle>
                    <CardDescription className="text-muted-foreground">
                      Posibles problemas de código, seguridad o arquitectura
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="p-0">
                    {potentialIssues.length > 0 ? (
                      <div className="space-y-3">
                        {potentialIssues.map((item, i) => (
                          <div key={i} className="border-l-4 border-orange-500 pl-4 p-3 bg-orange-50 dark:bg-orange-950/20 rounded-r-lg border border-border/50">
                            <h4 className="font-medium text-orange-800 dark:text-orange-200">{item.issue}</h4>
                            <p className="text-sm text-orange-700 dark:text-orange-300">{item.description}</p>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-sm text-muted-foreground">No se identificaron problemas potenciales.</p>
                    )}
                  </CardContent>
                </Card>
              </TabsContent>
              <TabsContent value="recommendations" className="mt-0 space-y-4">
                <Card className="border-none shadow-none bg-transparent p-0">
                  <CardHeader className="px-0 pt-0 pb-2">
                    <CardTitle className="flex items-center gap-2 text-lg font-semibold text-foreground">
                      <Lightbulb className="h-5 w-5 text-blue-500" />
                      Recomendaciones ({recommendations.length} sugerencias)
                    </CardTitle>
                    <CardDescription className="text-muted-foreground">
                      Sugerencias para mejorar el código
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="p-0">
                    {recommendations.length > 0 ? (
                      <div className="space-y-4">
                        {recommendations.map((item, i) => (
                          <div key={i} className="border rounded-lg p-4 space-y-2 border-border/50">
                            <h4 className="font-medium text-blue-800 dark:text-blue-200">{item.recommendation}</h4>
                            {item.rationale && (
                              <p className="text-sm text-muted-foreground"><strong>Justificación:</strong> {item.rationale}</p>
                            )}
                            {item.application && (
                              <p className="text-sm text-muted-foreground"><strong>Aplicación:</strong> {item.application}</p>
                            )}
                            {item.implementation && (
                              <p className="text-sm text-muted-foreground"><strong>Implementación:</strong> {item.implementation}</p>
                            )}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-sm text-muted-foreground">No se generaron recomendaciones específicas.</p>
                    )}
                  </CardContent>
                </Card>
              </TabsContent>
            </div>
          </div>
        </Tabs>
        <DialogFooter className="p-6 pt-4 border-t gap-2">
          <Button
            variant="destructive"
            onClick={async () => {
              try {
                await apiClient.post('/api/delete-analysis', { task_id: analysis.id });
                toast.success('Análisis eliminado correctamente');
                onOpenChange(false);
              } catch (error) {
                toast.error('Error al eliminar el análisis');
                console.error(error);
              }
            }}
          >
            Eliminar Análisis
          </Button>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
          >
            Cerrar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
