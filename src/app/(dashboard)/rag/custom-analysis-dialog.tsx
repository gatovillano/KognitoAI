// src/app/(dashboard)/rag/custom-analysis-dialog.tsx
'use client';

import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { PlusCircle, XCircle, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import apiClient from '@/lib/api';

interface CustomAnalysisDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  topic: string; // La colección actual
  onAnalysisStart: (taskId: string) => void; // Para notificar el inicio del análisis
  documentFileName?: string; // Opcional: si el análisis es para un documento específico
}

export function CustomAnalysisDialog({ isOpen, onOpenChange, topic, onAnalysisStart, documentFileName }: CustomAnalysisDialogProps) {
  const [objective, setObjective] = useState('');
  const [expectedResult, setExpectedResult] = useState('');
  const [extension, setExtension] = useState('standard'); // 'brief', 'standard', 'detailed'
  const [fields, setFields] = useState([{ name: '', description: '' }]);
  const [isLoading, setIsLoading] = useState(false);

  // Resetear el formulario cuando se abre el diálogo
  useEffect(() => {
    if (isOpen) {
      setObjective('');
      setExpectedResult('');
      setExtension('standard');
      setFields([{ name: '', description: '' }]);
      setIsLoading(false);
    }
  }, [isOpen]);

  const handleAddField = () => {
    setFields([...fields, { name: '', description: '' }]);
  };

  const handleRemoveField = (index: number) => {
    const newFields = fields.filter((_, i) => i !== index);
    setFields(newFields);
  };

  const handleFieldChange = (index: number, key: 'name' | 'description', value: string) => {
    const newFields = [...fields];
    newFields[index] = { ...newFields[index], [key]: value };
    setFields(newFields);
  };

  const handleSubmit = async () => {
    if (!objective.trim() || fields.some(f => !f.name.trim() || !f.description.trim())) {
      toast.error('Por favor, completa el objetivo y todos los campos requeridos.');
      return;
    }

    setIsLoading(true);
    try {
      const payload = {
        file_name: documentFileName || `Colección: ${topic}`, // Usar el nombre del documento o la colección
        objective,
        expected_result: expectedResult || undefined,
        extension,
        fields: fields.filter(f => f.name.trim() && f.description.trim()), // Asegurarse de enviar solo campos válidos
      };

      const response = await apiClient.post('/api/start-custom-analysis', payload);
      onAnalysisStart(response.data.task_id);
      toast.success('Análisis personalizado iniciado con éxito.');
      onOpenChange(false); // Cerrar el diálogo
    } catch (error) {
      toast.error('Error al iniciar el análisis personalizado.');
      console.error('Error starting custom analysis:', error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl w-full max-h-[95vh] sm:max-h-[90vh] p-4 sm:p-6">
        <DialogHeader>
          <DialogTitle className="text-lg sm:text-xl">Configurar Análisis Personalizado</DialogTitle>
          <DialogDescription>
            Define el objetivo, la extensión y los campos específicos para tu análisis.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-2">
          <div>
            <Label htmlFor="objective">Objetivo del Análisis <span className="text-red-500">*</span></Label>
            <Textarea
              id="objective"
              placeholder="Ej: Identificar las principales vulnerabilidades de seguridad en el código."
              value={objective}
              onChange={(e) => setObjective(e.target.value)}
              rows={3}
            />
          </div>

          <div>
            <Label htmlFor="expectedResult">Resultado Esperado (Opcional)</Label>
            <Textarea
              id="expectedResult"
              placeholder="Ej: Un listado de vulnerabilidades con su severidad y recomendaciones de mitigación."
              value={expectedResult}
              onChange={(e) => setExpectedResult(e.target.value)}
              rows={2}
            />
          </div>

          <div>
            <Label htmlFor="extension">Extensión del Análisis</Label>
            <Select value={extension} onValueChange={setExtension}>
              <SelectTrigger id="extension">
                <SelectValue placeholder="Selecciona la extensión" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="brief">Breve (Máx. 2 páginas)</SelectItem>
                <SelectItem value="standard">Estándar (3-5 páginas)</SelectItem>
                <SelectItem value="detailed">Detallado (Mín. 5 páginas)</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-3">
            <Label>Campos Requeridos en el Análisis <span className="text-red-500">*</span></Label>
            {fields.map((field, index) => (
              <div key={index} className="flex flex-col sm:flex-row sm:items-end gap-2">
                <div className="grid gap-1 flex-1">
                  <Label htmlFor={`fieldName-${index}`} className="sr-only">Nombre del Campo</Label>
                  <Input
                    id={`fieldName-${index}`}
                    placeholder="Nombre del Campo (Ej: Vulnerabilidades)"
                    value={field.name}
                    onChange={(e) => handleFieldChange(index, 'name', e.target.value)}
                  />
                </div>
                <div className="grid gap-1 flex-1">
                  <Label htmlFor={`fieldDescription-${index}`} className="sr-only">Descripción del Campo</Label>
                  <Input
                    id={`fieldDescription-${index}`}
                    placeholder="Descripción (Ej: Listado de vulnerabilidades encontradas)"
                    value={field.description}
                    onChange={(e) => handleFieldChange(index, 'description', e.target.value)}
                  />
                </div>
                {fields.length > 1 && (
                  <Button variant="ghost" size="icon" onClick={() => handleRemoveField(index)}>
                    <XCircle className="h-5 w-5 text-red-500" />
                  </Button>
                )}
              </div>
            ))}
            <Button variant="outline" onClick={handleAddField} className="gap-2">
              <PlusCircle className="h-4 w-4" />
              Añadir Campo
            </Button>
          </div>
        </div>
        <DialogFooter className="flex flex-col-reverse sm:flex-row sm:justify-end gap-2 mt-4">
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isLoading} className="w-full sm:w-auto">
            Cancelar
          </Button>
          <Button onClick={handleSubmit} disabled={isLoading} className="w-full sm:w-auto">
            {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Iniciar Análisis
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
