import React from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { FileText, Sparkles, X, CheckCircle2, ListTodo, Tag } from 'lucide-react';
import { cn } from '@/lib/utils';

interface DocumentSummaryData {
  summary: string;
  key_points: string[];
  topics: string[];
  document_type: string;
  confidence?: number;
}

interface DocumentSummaryDialogProps {
  isOpen: boolean;
  onClose: () => void;
  documentTitle: string;
  summaryData: DocumentSummaryData | null;
  isLoading?: boolean;
}

export const DocumentSummaryDialog: React.FC<DocumentSummaryDialogProps> = ({
  isOpen,
  onClose,
  documentTitle,
  summaryData,
  isLoading = false,
}) => {
  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-2xl max-h-[90vh]">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <Sparkles className="w-6 h-6 text-blue-600" />
            <DialogTitle>Resumen del Documento</DialogTitle>
          </div>
          <DialogDescription className="flex items-center gap-2 text-sm">
            <FileText className="w-4 h-4" />
            {documentTitle}
          </DialogDescription>
        </DialogHeader>

        <ScrollArea className="max-h-[60vh] pr-4">
          {isLoading ? (
            <div className="flex flex-col items-center justify-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mb-4"></div>
              <p className="text-muted-foreground">Generando resumen...</p>
            </div>
          ) : summaryData ? (
            <div className="space-y-6">
              {/* Resumen Ejecutivo */}
              <Card className="border-blue-100 bg-blue-50/30 dark:border-blue-900 dark:bg-blue-950/10">
                <CardHeader className="pb-3">
                  <CardTitle className="text-base font-semibold flex items-center gap-2 text-blue-900 dark:text-blue-100">
                    <Sparkles className="w-4 h-4" />
                    Resumen Ejecutivo
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm leading-relaxed text-foreground/90">
                    {summaryData.summary}
                  </p>
                </CardContent>
              </Card>

              {/* Puntos Clave */}
              {summaryData.key_points && summaryData.key_points.length > 0 && (
                <Card className="border-border/50">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-base font-semibold flex items-center gap-2">
                      <ListTodo className="w-4 h-4 text-primary" />
                      Puntos Clave
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="space-y-2">
                      {summaryData.key_points.map((point, idx) => (
                        <li key={idx} className="flex items-start gap-2 text-sm">
                          <CheckCircle2 className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
                          <span className="text-foreground/90">{point}</span>
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              )}

              {/* Temas */}
              {summaryData.topics && summaryData.topics.length > 0 && (
                <Card className="border-border/50">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-base font-semibold flex items-center gap-2">
                      <Tag className="w-4 h-4 text-purple-600" />
                      Temas Principales
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="flex flex-wrap gap-2">
                      {summaryData.topics.map((topic, idx) => (
                        <Badge key={idx} variant="secondary" className="text-sm">
                          {topic}
                        </Badge>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Metadatos */}
              <div className="flex items-center justify-between text-xs text-muted-foreground pt-2 border-t">
                <div className="flex items-center gap-4">
                  <span>
                    <strong>Tipo:</strong> {summaryData.document_type}
                  </span>
                  {summaryData.confidence !== undefined && (
                    <span>
                      <strong>Confianza:</strong> {Math.round(summaryData.confidence * 100)}%
                    </span>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-12 text-muted-foreground">
              <FileText className="w-12 h-12 mx-auto mb-4 opacity-20" />
              <p>No hay resumen disponible</p>
            </div>
          )}
        </ScrollArea>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            <X className="w-4 h-4 mr-2" />
            Cerrar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
