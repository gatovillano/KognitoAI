'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { ScrollArea } from '@/components/ui/scroll-area';
import { BookOpen, Search, Lightbulb, Send } from 'lucide-react';

interface AnthropologicalProcessDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: (data: {
    theoreticalFramework: string;
    researchQuestion: string;
    hypothesis: string;
    datasetName: string;
    topic?: string;
    workspaceId?: string;
  }) => Promise<void>;
  defaultTopic?: string | null;
  workspaceId?: string | null;
}

export function AnthropologicalProcessDialog({
  isOpen,
  onOpenChange,
  onConfirm,
  defaultTopic,
  workspaceId,
}: AnthropologicalProcessDialogProps) {
  const [formData, setFormData] = useState({
    theoreticalFramework: '',
    researchQuestion: '',
    hypothesis: '',
    datasetName: '',
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async () => {
    if (!formData.theoreticalFramework || !formData.researchQuestion || !formData.hypothesis || !formData.datasetName) {
      return;
    }
    
    setIsSubmitting(true);
    try {
      await onConfirm({
        ...formData,
        topic: defaultTopic || undefined,
        workspaceId: workspaceId || undefined,
      });
      onOpenChange(false);
    } catch (error) {
      console.error('Error submitting anthropological process:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-xl">
            <BookOpen className="h-5 w-5 text-primary" />
            Procesamiento Antropológico de Grafos
          </DialogTitle>
          <DialogDescription>
            Configure los parámetros cualitativos para iniciar la codificación etnográfica y la extracción de categorías.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-6 py-4">
          <div className="grid gap-2">
            <Label htmlFor="datasetName" className="flex items-center gap-2">
              <Search className="h-3 w-3" /> Nombre del Dataset
            </Label>
            <Input
              id="datasetName"
              name="datasetName"
              placeholder="Ej: Entrevistas_SocioEconomicas_2024"
              value={formData.datasetName}
              onChange={handleInputChange}
            />
          </div>

          <div className="grid gap-4 p-4 rounded-lg bg-muted/50 border border-border">
            <div className="grid gap-2">
              <Label htmlFor="theoreticalFramework" className="flex items-center gap-2">
                <BookOpen className="h-3 w-3" /> Marco Teórico
              </Label>
              <Textarea
                id="theoreticalFramework"
                name="theoreticalFramework"
                placeholder="Describa las teorías, conceptos y autores que guiarán la codificación..."
                value={formData.theoreticalFramework}
                onChange={handleInputChange}
                className="min-h-[100px] resize-none"
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="researchQuestion" className="flex items-center gap-2">
                <Search className="h-3 w-3" /> Pregunta de Investigación
              </Label>
              <Input
                id="researchQuestion"
                name="researchQuestion"
                placeholder="¿Cuál es el fenómeno central que desea explorar?"
                value={formData.researchQuestion}
                onChange={handleInputChange}
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="hypothesis" className="flex items-center gap-2">
                <Lightbulb className="h-3 w-3" /> Hipótesis / Supuestos Iniciales
              </Label>
              <Textarea
                id="hypothesis"
                name="hypothesis"
                placeholder="Indique las intuiciones o patrones que espera encontrar en los datos..."
                value={formData.hypothesis}
                onChange={handleInputChange}
                className="min-h-[80px] resize-none"
              />
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancelar
          </Button>
          <Button 
            onClick={handleSubmit} 
            disabled={isSubmitting || !formData.theoreticalFramework || !formData.researchQuestion || !formData.hypothesis || !formData.datasetName}
            className="gap-2"
          >
            {isSubmitting ? (
              <span className="flex items-center gap-2">
                <span className="animate-spin h-3 w-3 border-2 border-white border-t-transparent rounded-full" />
                Procesando...
              </span>
            ) : (
              <>
                <Send className="h-4 w-4" />
                Iniciar Codificación
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
