// src/app/(dashboard)/analysis/deep-research-detail-dialog.tsx

import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { FileText, Target, ExternalLink, Lightbulb, Search, MessageSquare } from 'lucide-react';
import { Analysis, DeepResearchAnalysisResult } from '@/lib/models'; // Import DeepResearchAnalysisResult
import { ContextualChat } from '@/components/ContextualChat';

interface DeepResearchDetailDialogProps {
  analysis: Analysis;
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
}

export function DeepResearchDetailDialog({ analysis, isOpen, onOpenChange }: DeepResearchDetailDialogProps) {
  const [isChatOpen, setIsChatOpen] = useState(false);
  const deepResearchResult = analysis.result as DeepResearchAnalysisResult;

  if (!deepResearchResult || !deepResearchResult.final_report) {
    return (
      <Dialog open={isOpen} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto rounded-3xl backdrop-blur-2xl bg-card/95 border-border/50 shadow-2xl">
          <DialogHeader className="p-4">
            <DialogTitle className="text-3xl font-black tracking-tight leading-tight">
              Error al cargar la Investigación Profunda
            </DialogTitle>
            <DialogDescription className="text-base">
              No se encontraron datos válidos para la investigación profunda.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="p-4 border-t border-border/10">
            <Button onClick={() => onOpenChange(false)} variant="ghost" className="rounded-xl">
              Cerrar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    );
  }

  const report = {
    summary: deepResearchResult.final_report,
    findings: analysis.summary ? [analysis.summary] : [], // Usar analysis.summary como hallazgo principal si existe
    sources: deepResearchResult.sources || [],
    recommendations: deepResearchResult.recommendations || [],
  };

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent
        className="max-w-3xl max-h-[90vh] overflow-y-auto rounded-3xl backdrop-blur-2xl bg-card/95 border-border/50 shadow-2xl"
        onPointerDownOutside={(e) => {
          const target = e.target as HTMLElement;
          if (target.closest('.contextual-chat-container')) {
            e.preventDefault();
          }
        }}
        onInteractOutside={(e) => {
          const target = e.target as HTMLElement;
          if (target.closest('.contextual-chat-container')) {
            e.preventDefault();
          }
        }}
        onFocusOutside={(e) => {
          const target = e.target as HTMLElement;
          if (target.closest('.contextual-chat-container')) {
            e.preventDefault();
          }
        }}
      >
        <DialogHeader className="p-4">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-2">
                <Badge variant="secondary" className="rounded-full px-3 text-[10px] font-bold tracking-widest uppercase">Investigación Profunda</Badge>
              </div>
              <DialogTitle className="text-3xl font-black tracking-tight leading-tight">
                {analysis.title || "Informe de Investigación Profunda"}
              </DialogTitle>
              <DialogDescription className="text-base">
                Resultados detallados de la investigación profunda asistida por IA.
              </DialogDescription>
            </div>
            <div className="flex-shrink-0">
              <Button variant="ghost" size="icon" onClick={() => setIsChatOpen(true)} className="text-muted-foreground hover:text-primary hover:bg-primary/10" title="Chatear con esta investigación">
                <MessageSquare className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </DialogHeader>
        
        <div className="py-2">
          <Tabs defaultValue="summary" className="w-full">
            <TabsList className="grid w-full grid-cols-4 h-12 bg-muted/50 rounded-xl p-1">
              <TabsTrigger value="summary" className="gap-2"><FileText className="h-4 w-4" />Resumen</TabsTrigger>
              <TabsTrigger value="findings" className="gap-2"><Target className="h-4 w-4" />Hallazgos</TabsTrigger>
              <TabsTrigger value="sources" className="gap-2"><ExternalLink className="h-4 w-4" />Fuentes</TabsTrigger>
              <TabsTrigger value="recommendations" className="gap-2"><Lightbulb className="h-4 w-4" />Acciones</TabsTrigger>
            </TabsList>
            
            <div className="mt-6">
              <TabsContent value="summary">
                <Card className="border-0 shadow-none bg-transparent">
                  <CardContent className="p-0">
                    <p className="text-lg leading-relaxed whitespace-pre-wrap">
                      {report.summary || "No hay resumen disponible."}
                    </p>
                  </CardContent>
                </Card>
              </TabsContent>
              
              <TabsContent value="findings">
                <div className="space-y-4">
                  {report.findings?.map((finding: string, index: number) => (
                    <div key={index} className="p-4 rounded-xl bg-card border border-border/50 flex gap-4">
                      <span className="flex-shrink-0 w-6 h-6 rounded-full bg-primary/10 text-primary flex items-center justify-center text-xs font-bold">
                        {index + 1}
                      </span>
                      <p className="text-sm leading-relaxed whitespace-pre-wrap">{finding}</p>
                    </div>
                  )) || <p className="text-muted-foreground text-center py-8">No hay hallazgos disponibles.</p>}
                </div>
              </TabsContent>
              
              <TabsContent value="sources">
                <div className="space-y-3">
                  {report.sources?.map((source: any, index: number) => (
                    <a 
                      key={index} 
                      href={source.url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="flex items-center justify-between p-4 rounded-xl bg-card border border-border/50 hover:bg-accent/50 transition-all"
                    >
                      <span className="text-sm font-medium truncate max-w-[250px]">{source.title || source.url}</span>
                      <Badge variant="secondary">{source.type || "Web"}</Badge>
                    </a>
                  )) || <p className="text-muted-foreground text-center py-8">No hay fuentes disponibles.</p>}
                </div>
              </TabsContent>
              
              <TabsContent value="recommendations">
                <div className="space-y-4">
                  {report.recommendations?.map((rec: string, index: number) => (
                    <div key={index} className="p-4 rounded-xl bg-green-500/5 border border-green-500/20 flex gap-4">
                      <Lightbulb className="h-5 w-5 text-green-600 flex-shrink-0" />
                      <p className="text-sm text-green-800 dark:text-green-300 leading-relaxed whitespace-pre-wrap">{rec}</p>
                    </div>
                  )) || <p className="text-muted-foreground text-center py-8">No hay recomendaciones disponibles.</p>}
                </div>
              </TabsContent>
            </div>
          </Tabs>
        </div>
        
        <DialogFooter className="p-4 border-t border-border/10">
          <Button
            onClick={() => onOpenChange(false)}
            variant="ghost"
            className="rounded-xl"
          >
            Cerrar
          </Button>
        </DialogFooter>

        {/* Chat Contextual para la Investigación Profunda - Movido dentro de DialogContent */}
        <ContextualChat
          isOpen={isChatOpen}
          onClose={() => setIsChatOpen(false)}
          context={{
            type: 'analysis',
            id: analysis.id,
            snapshot: analysis
          }}
          title={analysis.title || "Investigación Profunda"}
        />
      </DialogContent>
    </Dialog>
  );
}