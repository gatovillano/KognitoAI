'use client';

import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Code, FileText, Settings, AlertTriangle, Lightbulb, GitBranch } from 'lucide-react';
import apiClient from '@/lib/api';
import { toast } from 'sonner';

interface CodeAnalysisItem {
  component?: string;
  pattern?: string;
  library?: string;
  issue?: string;
  recommendation?: string;
  name?: string;
  context?: string;
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
  if (!analysis) {
    console.log("❌ CodeAnalysisResultDialog: No analysis data provided");
    return null;
  }

  console.log("💻 CodeAnalysisResultDialog - Analysis object:", analysis);
  console.log("💻 CodeAnalysisResultDialog - Repo name:", repoName);

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
  const metadata = analysis.analysis_metadata || {};

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-5xl max-h-[90vh]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Code className="h-5 w-5" />
            Análisis de Código - {repoName || 'Repositorio'}
          </DialogTitle>
          <DialogDescription>
            {metadata.total_files && metadata.total_chunks ? 
              `Análisis de ${metadata.total_files} archivos en ${metadata.total_chunks} partes` :
              'Análisis completo del repositorio'
            }
          </DialogDescription>
        </DialogHeader>
        
        <Tabs defaultValue="overview" className="w-full">
          <TabsList className="grid w-full grid-cols-6">
            <TabsTrigger value="overview">Resumen</TabsTrigger>
            <TabsTrigger value="structure">Estructura</TabsTrigger>
            <TabsTrigger value="patterns">Patrones</TabsTrigger>
            <TabsTrigger value="dependencies">Dependencias</TabsTrigger>
            <TabsTrigger value="issues">Problemas</TabsTrigger>
            <TabsTrigger value="recommendations">Recomendaciones</TabsTrigger>
          </TabsList>
          
          <ScrollArea className="h-[60vh] mt-4">
            <TabsContent value="overview" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <FileText className="h-4 w-4" />
                    Resumen Ejecutivo
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm whitespace-pre-wrap">{executiveSummary}</p>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="structure" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <GitBranch className="h-4 w-4" />
                    Estructura del Código ({codeStructure.length} componentes)
                  </CardTitle>
                  <CardDescription>
                    Componentes principales identificados en el código
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {codeStructure.length > 0 ? (
                    <div className="space-y-3">
                      {codeStructure.map((item, i) => {
                        const title = item.component || (item as any).name || 'Sin título';
                        return (
                          <div key={i} className="border-l-4 border-blue-500 pl-4">
                            <h4 className="font-medium">{title}</h4>
                            <p className="text-sm text-muted-foreground">{item.description}</p>
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground">No se encontraron componentes de estructura.</p>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="patterns" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Settings className="h-4 w-4" />
                    Patrones de Diseño ({designPatterns.length} patrones)
                  </CardTitle>
                  <CardDescription>
                    Patrones de diseño identificados en el código
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {designPatterns.length > 0 ? (
                    <div className="space-y-3">
                      {designPatterns.map((item, i) => (
                        <div key={i} className="border-l-4 border-green-500 pl-4">
                          <h4 className="font-medium">{item.pattern}</h4>
                          <p className="text-sm text-muted-foreground">{item.description || item.context || ''}</p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground">No se encontraron patrones de diseño específicos.</p>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="dependencies" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>Dependencias ({dependencies.length} bibliotecas)</CardTitle>
                  <CardDescription>
                    Bibliotecas y frameworks utilizados
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {dependencies.length > 0 ? (
                    <div className="grid gap-3">
                      {dependencies.map((item, i) => (
                        <div key={i} className="flex items-start gap-3 p-3 border rounded-lg">
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

            <TabsContent value="issues" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4 text-orange-500" />
                    Problemas Potenciales ({potentialIssues.length} problemas)
                  </CardTitle>
                  <CardDescription>
                    Posibles problemas de código, seguridad o arquitectura
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {potentialIssues.length > 0 ? (
                    <div className="space-y-3">
                      {potentialIssues.map((item, i) => (
                        <div key={i} className="border-l-4 border-orange-500 pl-4 p-3 bg-orange-50 dark:bg-orange-950/20 rounded-r-lg">
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

            <TabsContent value="recommendations" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Lightbulb className="h-4 w-4 text-blue-500" />
                    Recomendaciones ({recommendations.length} sugerencias)
                  </CardTitle>
                  <CardDescription>
                    Sugerencias para mejorar el código
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {recommendations.length > 0 ? (
                    <div className="space-y-4">
                      {recommendations.map((item, i) => (
                        <div key={i} className="border rounded-lg p-4 space-y-2">
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
          </ScrollArea>
        </Tabs>

        <div className="flex justify-between mt-4">
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
        </div>
      </DialogContent>
    </Dialog>
  );
}
