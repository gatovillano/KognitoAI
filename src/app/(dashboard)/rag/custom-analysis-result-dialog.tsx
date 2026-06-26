'use client';

import { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { InlineMarkdownRenderer } from '@/components/InlineMarkdownRenderer';
import { 
  Sparkles, 
  FileText, 
  Download, 
  Copy, 
  Target, 
  CheckCircle,
  Calendar,
  User,
  Settings
} from 'lucide-react';
import { toast } from 'sonner';

interface CustomAnalysisResultDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  analysisResult: any;
}

export function CustomAnalysisResultDialog({ 
  isOpen, 
  onOpenChange, 
  analysisResult 
}: CustomAnalysisResultDialogProps) {
  const [copiedSection, setCopiedSection] = useState<string | null>(null);

  if (!analysisResult) {
    console.log("❌ CustomAnalysisResultDialog: No analysis result provided");
    return null;
  }

  console.log("✨ CustomAnalysisResultDialog - Analysis result:", analysisResult);

  const metadata = analysisResult.analysis_metadata || {};
  const customConfig = analysisResult.custom_config || {};
  const sections = analysisResult.sections || {};

  const copyToClipboard = async (text: string, sectionName: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedSection(sectionName);
      toast.success(`${sectionName} copiado al portapapeles`);
      setTimeout(() => setCopiedSection(null), 2000);
    } catch (error) {
      toast.error('Error al copiar al portapapeles');
    }
  };

  const copyFullAnalysis = async () => {
    try {
      const fullText = Object.entries(sections)
        .map(([key, value]) => `## ${key}\n\n${value}\n\n`)
        .join('');
      
      await navigator.clipboard.writeText(fullText);
      toast.success('Análisis completo copiado al portapapeles');
    } catch (error) {
      toast.error('Error al copiar el análisis completo');
    }
  };

  const getExtensionLabel = (extension: string) => {
    switch (extension) {
      case 'brief': return 'Breve';
      case 'standard': return 'Estándar';
      case 'detailed': return 'Detallado';
      default: return extension;
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-5xl max-h-[90vh]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-purple-500" />
            Análisis Personalizado
          </DialogTitle>
        </DialogHeader>

        <ScrollArea className="max-h-[75vh]">
          <div className="space-y-6 p-1">
            {/* Header con información del análisis */}
            <Card className="border-purple-200 bg-purple-50/50">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center gap-2 text-lg">
                    <Target className="h-5 w-5 text-purple-600" />
                    Configuración del Análisis
                  </CardTitle>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={copyFullAnalysis}
                      className="gap-1"
                    >
                      <Copy className="h-3 w-3" />
                      Copiar todo
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      className="gap-1"
                    >
                      <Download className="h-3 w-3" />
                      Exportar PDF
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <div className="text-sm font-medium text-purple-700 mb-1">Objetivo</div>
                    <div className="text-sm text-gray-700">{customConfig.objective || 'No especificado'}</div>
                  </div>
                  <div>
                    <div className="text-sm font-medium text-purple-700 mb-1">Extensión</div>
                    <Badge variant="secondary" className="text-xs">
                      {getExtensionLabel(customConfig.extension)}
                    </Badge>
                  </div>
                </div>
                
                {customConfig.expected_result && (
                  <div>
                    <div className="text-sm font-medium text-purple-700 mb-1">Resultado esperado</div>
                    <div className="text-sm text-gray-700">{customConfig.expected_result}</div>
                  </div>
                )}

                <div className="flex items-center gap-4 text-xs text-muted-foreground">
                  <div className="flex items-center gap-1">
                    <Calendar className="h-3 w-3" />
                    {metadata.created_at ? new Date(metadata.created_at).toLocaleString() : 'Fecha no disponible'}
                  </div>
                  <div className="flex items-center gap-1">
                    <Settings className="h-3 w-3" />
                    {metadata.tool_used || 'Herramienta no especificada'}
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Secciones del análisis */}
            <div className="space-y-4">
              {Object.entries(sections).map(([sectionName, content], index) => (
                <Card key={index} className="overflow-hidden">
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                      <CardTitle className="flex items-center gap-2 text-base">
                        <div className="h-6 w-6 rounded-full bg-purple-100 flex items-center justify-center">
                          <span className="text-xs font-medium text-purple-600">
                            {index + 1}
                          </span>
                        </div>
                        {sectionName}
                      </CardTitle>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => copyToClipboard(content as string, sectionName)}
                        className="gap-1 h-7 px-2"
                      >
                        {copiedSection === sectionName ? (
                          <CheckCircle className="h-3 w-3 text-green-500" />
                        ) : (
                          <Copy className="h-3 w-3" />
                        )}
                        <span className="text-xs">
                          {copiedSection === sectionName ? 'Copiado' : 'Copiar'}
                        </span>
                      </Button>
                    </div>
                  </CardHeader>
                  <CardContent className="pt-0">
                    <div className="prose prose-sm max-w-none">
                      <InlineMarkdownRenderer content={content as string} />
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>

            {/* Información técnica */}
            <Card className="border-gray-200 bg-gray-50/50">
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-sm">
                  <FileText className="h-4 w-4 text-gray-600" />
                  Información Técnica
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
                  <div>
                    <span className="font-medium text-gray-700">Documento analizado:</span>
                    <div className="text-gray-600 mt-1">{metadata.file_name || 'No especificado'}</div>
                  </div>
                  <div>
                    <span className="font-medium text-gray-700">Campos incluidos:</span>
                    <div className="text-gray-600 mt-1">
                      {customConfig.fields ? `${customConfig.fields.length} campos` : 'No especificado'}
                    </div>
                  </div>
                  <div>
                    <span className="font-medium text-gray-700">Tipo de análisis:</span>
                    <div className="text-gray-600 mt-1">{metadata.analysis_type || 'custom'}</div>
                  </div>
                </div>
                
                {customConfig.fields && customConfig.fields.length > 0 && (
                  <div className="mt-4">
                    <div className="text-xs font-medium text-gray-700 mb-2">Campos configurados:</div>
                    <div className="flex flex-wrap gap-1">
                      {customConfig.fields.map((field: any, index: number) => (
                        <Badge key={index} variant="outline" className="text-xs">
                          {field.name}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </ScrollArea>

        <div className="flex justify-end pt-4 border-t">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cerrar
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
