'use client';

import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { BarChart3, Brain, TrendingUp, Hash, Users, Target } from 'lucide-react';

interface SemanticTopicsAnalysisDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  analysisResult: any;
}

export function SemanticTopicsAnalysisDialog({ 
  isOpen, 
  onOpenChange, 
  analysisResult 
}: SemanticTopicsAnalysisDialogProps) {
  if (!analysisResult) {
    console.log("❌ SemanticTopicsAnalysisDialog: No analysis result provided");
    return null;
  }

  console.log("🔍 SemanticTopicsAnalysisDialog - Analysis result:", analysisResult);

  const groupedTopics = analysisResult.grouped_topics || [];
  const detailedClusters = analysisResult.detailed_clusters || [];
  const metadata = analysisResult.analysis_metadata || {};

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5 text-indigo-500" />
            Análisis Semántico de Temas
          </DialogTitle>
        </DialogHeader>
        
        <ScrollArea className="max-h-[70vh]">
          <div className="space-y-6 p-1">
            {/* Resumen del análisis */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Brain className="h-4 w-4" />
                  Resumen del Análisis
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-indigo-600">{metadata.total_topics || 0}</div>
                    <div className="text-sm text-muted-foreground">Temas Analizados</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-purple-600">{metadata.clusters_count || 0}</div>
                    <div className="text-sm text-muted-foreground">Grupos Formados</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-green-600">{groupedTopics.length}</div>
                    <div className="text-sm text-muted-foreground">Temas Principales</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-orange-600">
                      {metadata.max_terms_limit || 'Sin límite'}
                    </div>
                    <div className="text-sm text-muted-foreground">Límite de Términos</div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Temas agrupados principales */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <TrendingUp className="h-4 w-4" />
                  Temas Principales Agrupados
                </CardTitle>
                <CardDescription>
                  Los temas más relevantes organizados por frecuencia de aparición
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {groupedTopics.map((topic: any, index: number) => (
                    <div key={index} className="flex items-center justify-between p-3 border rounded-lg">
                      <div className="flex items-center gap-3">
                        <div className="h-8 w-8 rounded-full bg-indigo-100 flex items-center justify-center">
                          <span className="text-sm font-medium text-indigo-600">#{index + 1}</span>
                        </div>
                        <div>
                          <div className="font-medium">{topic.topic}</div>
                          {topic.description && (
                            <div className="text-sm text-muted-foreground">{topic.description}</div>
                          )}
                        </div>
                      </div>
                      <div className="text-right">
                        <Badge variant="secondary" className="mb-1">
                          {topic.mentions} menciones
                        </Badge>
                        {topic.topics && (
                          <div className="text-xs text-muted-foreground">
                            {topic.topics.length} términos
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Clusters detallados */}
            {detailedClusters.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Users className="h-4 w-4" />
                    Clusters Detallados
                  </CardTitle>
                  <CardDescription>
                    Información detallada de cada grupo semántico identificado
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {detailedClusters.map((cluster: any, index: number) => (
                      <div key={index} className="border rounded-lg p-4">
                        <div className="flex items-center justify-between mb-3">
                          <h4 className="font-medium flex items-center gap-2">
                            <Target className="h-4 w-4" />
                            {cluster.representative_term}
                          </h4>
                          <div className="flex gap-2">
                            <Badge variant="outline">
                              Cluster {cluster.cluster_id}
                            </Badge>
                            <Badge variant="secondary">
                              {cluster.total_mentions} menciones
                            </Badge>
                          </div>
                        </div>
                        
                        {cluster.description && (
                          <p className="text-sm text-muted-foreground mb-3">
                            {cluster.description}
                          </p>
                        )}
                        
                        <div className="space-y-2">
                          <div className="text-sm font-medium">Términos incluidos:</div>
                          <div className="flex flex-wrap gap-1">
                            {cluster.topics?.map((term: string, termIndex: number) => (
                              <Badge key={termIndex} variant="outline" className="text-xs">
                                {term}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Metadatos técnicos */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Hash className="h-4 w-4" />
                  Información Técnica
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="font-medium">Herramienta:</span> {metadata.tool_used || 'N/A'}
                  </div>
                  <div>
                    <span className="font-medium">Tipo de análisis:</span> {metadata.analysis_type || 'N/A'}
                  </div>
                  <div>
                    <span className="font-medium">Fecha de creación:</span>{' '}
                    {metadata.created_at ? new Date(metadata.created_at).toLocaleString() : 'N/A'}
                  </div>
                  <div>
                    <span className="font-medium">Total de clusters:</span> {metadata.clusters_count || 0}
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
}
