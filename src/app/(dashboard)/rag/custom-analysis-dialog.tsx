'use client';

import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Checkbox } from '@/components/ui/checkbox';
import { Plus, X, Target, FileText, Sparkles, Settings, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import apiClient from '@/lib/api';

interface CustomAnalysisDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  document: any;
  topic: string;
  onAnalysisStart?: () => void;
}

interface CustomField {
  id: string;
  name: string;
  description: string;
}

export function CustomAnalysisDialog({
  isOpen,
  onOpenChange,
  document,
  topic,
  onAnalysisStart
}: CustomAnalysisDialogProps) {
  const [objective, setObjective] = useState('');
  const [expectedResult, setExpectedResult] = useState('');
  const [extension, setExtension] = useState<string>('');
  const [customFields, setCustomFields] = useState<CustomField[]>([]);
  const [newFieldName, setNewFieldName] = useState('');
  const [newFieldDescription, setNewFieldDescription] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // Estados para documentos de la colección
  const [documents, setDocuments] = useState<any[]>([]);
  const [selectedDocument, setSelectedDocument] = useState<string>('');
  const [isLoadingDocuments, setIsLoadingDocuments] = useState(false);
  const [analyzeFullCollection, setAnalyzeFullCollection] = useState(false);

  const predefinedFields = [
    { name: 'Resumen Ejecutivo', description: 'Síntesis concisa del contenido principal' },
    { name: 'Conceptos Clave', description: 'Términos y conceptos más importantes' },
    { name: 'Conclusiones', description: 'Puntos de cierre y reflexiones finales' },
    { name: 'Recomendaciones', description: 'Sugerencias y próximos pasos' }
  ];

  const extensionOptions = [
    { value: 'brief', label: 'Breve', description: '1-2 páginas, puntos esenciales' },
    { value: 'standard', label: 'Estándar', description: '3-5 páginas, análisis completo' },
    { value: 'detailed', label: 'Detallado', description: '5+ páginas, análisis exhaustivo' }
  ];

  // Cargar documentos de la colección cuando se abre el diálogo
  useEffect(() => {
    if (isOpen && topic) {
      loadDocuments();
    }
  }, [isOpen, topic]);

  const loadDocuments = async () => {
    setIsLoadingDocuments(true);
    try {
      const response = await apiClient.post('/api/list-documents', { topic });
      setDocuments(response.data || []);

      // Si hay un documento preseleccionado, establecerlo
      if (document?.file_name) {
        setSelectedDocument(document.file_name);
      }
    } catch (error) {
      console.error('Error loading documents:', error);
      toast.error('Error al cargar los documentos de la colección');
    } finally {
      setIsLoadingDocuments(false);
    }
  };

  const addCustomField = () => {
    if (!newFieldName.trim()) {
      toast.error('El nombre del campo es requerido');
      return;
    }

    const newField: CustomField = {
      id: Date.now().toString(),
      name: newFieldName.trim(),
      description: newFieldDescription.trim() || 'Campo personalizado'
    };

    setCustomFields([...customFields, newField]);
    setNewFieldName('');
    setNewFieldDescription('');
  };

  const removeCustomField = (id: string) => {
    setCustomFields(customFields.filter(field => field.id !== id));
  };

  const handleSubmit = async () => {
    if (!objective.trim()) {
      toast.error('El objetivo del análisis es requerido');
      return;
    }

    if (!analyzeFullCollection && !selectedDocument) {
      toast.error('Selecciona un documento para analizar o elige analizar la colección completa');
      return;
    }

    if (!extension) {
      toast.error('Selecciona la extensión del análisis');
      return;
    }

    setIsLoading(true);

    try {
      const allFields = [
        ...predefinedFields,
        ...customFields
      ];

      const requestData: any = {
        objective,
        expected_result: expectedResult,
        extension,
        fields: allFields,
        analyze_full_collection: analyzeFullCollection
      };

      if (analyzeFullCollection) {
        requestData.topic = topic;
      } else {
        requestData.file_name = selectedDocument;
      }

      const response = await apiClient.post('/api/start-custom-analysis', requestData);

      const analysisType = analyzeFullCollection ? 'de la colección completa' : `del documento "${selectedDocument}"`;
      toast.success(`Análisis personalizado ${analysisType} iniciado correctamente`);
      onAnalysisStart?.();
      onOpenChange(false);

      // Reset form
      setObjective('');
      setExpectedResult('');
      setExtension('');
      setSelectedDocument('');
      setCustomFields([]);
      setAnalyzeFullCollection(false);
    } catch (error: any) {
      console.error('Error starting custom analysis:', error);
      toast.error(error.response?.data?.detail || 'Error al iniciar el análisis personalizado');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-purple-500" />
            Análisis Personalizado
          </DialogTitle>
          <DialogDescription>
            Configura un análisis a medida para obtener exactamente la información que necesitas
          </DialogDescription>
        </DialogHeader>

        <ScrollArea className="max-h-[70vh]">
          <div className="space-y-6 p-1">
            {/* Documento seleccionado */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-sm">
                  <FileText className="h-4 w-4" />
                  Contenido a analizar
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {/* Opción de colección completa */}
                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="analyze-full-collection"
                      checked={analyzeFullCollection}
                      onCheckedChange={(checked) => {
                        setAnalyzeFullCollection(checked as boolean);
                        if (checked) {
                          setSelectedDocument('');
                        }
                      }}
                    />
                    <Label htmlFor="analyze-full-collection" className="text-sm font-medium">
                      Analizar colección completa ({documents.length} documentos)
                    </Label>
                  </div>

                  {/* Descripción de la opción seleccionada */}
                  {analyzeFullCollection ? (
                    <div className="p-3 bg-gray-50 border border-gray-200 rounded-lg">
                      <div className="text-sm text-gray-700">
                        <strong>Análisis de colección completa:</strong> Se analizarán todos los documentos de la colección
                        para identificar patrones, conexiones y temas transversales entre ellos.
                      </div>
                    </div>
                  ) : (
                    <div className="text-xs text-muted-foreground">
                      Selecciona un documento específico para análisis individual
                    </div>
                  )}

                  {/* Selector de documento individual */}
                  {!analyzeFullCollection && (
                    <div className="space-y-2">
                      <Label htmlFor="document-select">Selecciona un documento específico *</Label>
                      <Select value={selectedDocument} onValueChange={setSelectedDocument} disabled={isLoadingDocuments}>
                        <SelectTrigger id="document-select">
                          <SelectValue placeholder={
                            isLoadingDocuments
                              ? "Cargando documentos..."
                              : "Selecciona un documento"
                          } />
                        </SelectTrigger>
                        <SelectContent>
                          {isLoadingDocuments ? (
                            <SelectItem value="__loading__" disabled>
                              <div className="flex items-center gap-2">
                                <Loader2 className="h-3 w-3 animate-spin" />
                                Cargando documentos...
                              </div>
                            </SelectItem>
                          ) : documents.length > 0 ? (
                            documents.map((doc) => (
                              <SelectItem key={doc.file_name} value={doc.file_name}>
                                <div className="flex flex-col">
                                  <span className="font-medium">{doc.file_name}</span>
                                  {doc.title && (
                                    <span className="text-xs text-muted-foreground">{doc.title}</span>
                                  )}
                                </div>
                              </SelectItem>
                            ))
                          ) : (
                            <SelectItem value="__no_documents__" disabled>
                              No hay documentos en esta colección
                            </SelectItem>
                          )}
                        </SelectContent>
                  </Select>
                  {selectedDocument && (
                    <div className="text-xs text-muted-foreground">
                      Documento seleccionado: <span className="font-medium">{selectedDocument}</span>
                    </div>
                  )}
                </div>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Configuración del análisis */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Target className="h-4 w-4" />
                  Configuración del Análisis
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="objective">Objetivo del análisis *</Label>
                  <Textarea
                    id="objective"
                    placeholder="Describe qué quieres lograr con este análisis..."
                    value={objective}
                    onChange={(e) => setObjective(e.target.value)}
                    rows={3}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="expected-result">Resultado esperado</Label>
                  <Textarea
                    id="expected-result"
                    placeholder="Describe el tipo de resultado que esperas obtener..."
                    value={expectedResult}
                    onChange={(e) => setExpectedResult(e.target.value)}
                    rows={2}
                  />
                </div>

                <div className="space-y-2">
                  <Label>Extensión del análisis *</Label>
                  <Select value={extension} onValueChange={setExtension}>
                    <SelectTrigger>
                      <SelectValue placeholder="Selecciona la extensión" />
                    </SelectTrigger>
                    <SelectContent>
                      {extensionOptions.map((option) => (
                        <SelectItem key={option.value} value={option.value}>
                          <div>
                            <div className="font-medium">{option.label}</div>
                            <div className="text-xs text-muted-foreground">{option.description}</div>
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </CardContent>
            </Card>

            {/* Campos del análisis */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Settings className="h-4 w-4" />
                  Campos del Análisis
                </CardTitle>
                <CardDescription>
                  Campos que se incluirán en el análisis final
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Campos predefinidos */}
                <div>
                  <h4 className="text-sm font-medium mb-3">Campos predefinidos</h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {predefinedFields.map((field, index) => (
                      <div key={index} className="flex items-center gap-2 p-2 border rounded-lg">
                        <Badge variant="secondary" className="text-xs">
                          {field.name}
                        </Badge>
                        <span className="text-xs text-muted-foreground">{field.description}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <Separator />

                {/* Campos personalizados */}
                <div>
                  <h4 className="text-sm font-medium mb-3">Campos personalizados</h4>
                  
                  {customFields.length > 0 && (
                    <div className="space-y-2 mb-4">
                      {customFields.map((field) => (
                        <div key={field.id} className="flex items-center gap-2 p-2 border rounded-lg">
                          <Badge variant="outline" className="text-xs">
                            {field.name}
                          </Badge>
                          <span className="text-xs text-muted-foreground flex-1">{field.description}</span>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => removeCustomField(field.id)}
                            className="h-6 w-6 p-0"
                          >
                            <X className="h-3 w-3" />
                          </Button>
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="space-y-3 p-3 border rounded-lg bg-muted/50">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      <div className="space-y-1">
                        <Label htmlFor="field-name" className="text-xs">Nombre del campo</Label>
                        <Input
                          id="field-name"
                          placeholder="ej. Metodología"
                          value={newFieldName}
                          onChange={(e) => setNewFieldName(e.target.value)}
                          className="h-8"
                        />
                      </div>
                      <div className="space-y-1">
                        <Label htmlFor="field-description" className="text-xs">Descripción</Label>
                        <Input
                          id="field-description"
                          placeholder="ej. Métodos utilizados en el estudio"
                          value={newFieldDescription}
                          onChange={(e) => setNewFieldDescription(e.target.value)}
                          className="h-8"
                        />
                      </div>
                    </div>
                    <Button
                      onClick={addCustomField}
                      variant="outline"
                      size="sm"
                      className="w-full h-8"
                    >
                      <Plus className="h-3 w-3 mr-1" />
                      Agregar campo
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </ScrollArea>

        <div className="flex justify-end gap-2 pt-4 border-t">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancelar
          </Button>
          <Button onClick={handleSubmit} disabled={isLoading}>
            {isLoading ? 'Iniciando...' : 'Iniciar Análisis'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
