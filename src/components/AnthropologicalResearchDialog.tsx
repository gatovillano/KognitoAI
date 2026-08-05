'use client';

import React, { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { SelectedContextItem } from '@/types/context';
import ContextSelectorDialog from '@/components/ContextSelectorDialog';
import { BookOpen, HelpCircle, Lightbulb, FileText, CheckCircle2, Microscope } from 'lucide-react';
import { toast } from 'sonner';

interface AnthropologicalResearchParams {
  theoreticalFrameworkItems: SelectedContextItem[];
  ethnographicMaterialItems: SelectedContextItem[];
  researchQuestion: string;
  hypothesis: string;
  deepenTheoreticalFramework: boolean;
}

interface AnthropologicalResearchDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onStartResearch: (params: AnthropologicalResearchParams) => void;
  workspaceId?: string;
}

export const AnthropologicalResearchDialog: React.FC<AnthropologicalResearchDialogProps> = ({
  isOpen,
  onClose,
  onStartResearch,
  workspaceId,
}) => {
  const [theoreticalFrameworkItems, setTheoreticalFrameworkItems] = useState<SelectedContextItem[]>([]);
  const [ethnographicMaterialItems, setEthnographicMaterialItems] = useState<SelectedContextItem[]>([]);
  const [researchQuestion, setResearchQuestion] = useState<string>('');
  const [hypothesis, setHypothesis] = useState<string>('');
  const [deepenTheoreticalFramework, setDeepenTheoreticalFramework] = useState<boolean>(false);
  const [isContextSelectorOpen, setIsContextSelectorOpen] = useState<boolean>(false);
  const [isEthnoSelectorOpen, setIsEthnoSelectorOpen] = useState<boolean>(false);

  const handleStart = () => {
    if (theoreticalFrameworkItems.length === 0) {
      toast.error('Por favor, selecciona al menos un archivo o nota como Marco Teórico.');
      return;
    }

    onStartResearch({
      theoreticalFrameworkItems,
      ethnographicMaterialItems,
      researchQuestion,
      hypothesis,
      deepenTheoreticalFramework,
    });
    onClose();
  };

  return (
    <>
      <Dialog open={isOpen} onOpenChange={onClose}>
        <DialogContent className="sm:max-w-[650px] max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-xl font-bold text-primary">
              <BookOpen className="h-6 w-6 text-indigo-500" />
              Configurar Investigación Antropológica
            </DialogTitle>
            <DialogDescription>
              Configura el marco teórico de referencia, pregunta de investigación e hipótesis para el procesamiento etnográfico exhaustivo (codificación 1:N: 1 Código atómico agrupa Múltiples Citas).
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-6 py-4">
            {/* Sección Marco Teórico */}
            <div className="space-y-3 rounded-lg border p-4 bg-muted/30">
              <div className="flex items-center justify-between">
                <div>
                  <Label className="text-base font-semibold flex items-center gap-2">
                    <FileText className="h-4 w-4 text-indigo-500" />
                    Marco Teórico (Archivos de Contexto)
                  </Label>
                  <p className="text-xs text-muted-foreground">
                    Selecciona los documentos o notas que servirán como lente analítico.
                  </p>
                </div>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setIsContextSelectorOpen(true)}
                  className="gap-2"
                >
                  <BookOpen className="h-4 w-4" />
                  {theoreticalFrameworkItems.length > 0 ? 'Modificar Contexto' : 'Seleccionar Archivos'}
                </Button>
              </div>

              {theoreticalFrameworkItems.length > 0 ? (
                <div className="mt-2 space-y-1">
                  <div className="flex items-center gap-2 text-xs font-medium text-emerald-600 dark:text-emerald-400">
                    <CheckCircle2 className="h-4 w-4" />
                    {theoreticalFrameworkItems.length} ítem(s) cargado(s) como Marco Teórico
                  </div>
                  <ul className="text-xs text-muted-foreground list-disc pl-5 max-h-24 overflow-y-auto">
                    {theoreticalFrameworkItems.map((item, idx) => (
                      <li key={`${item.type}-${item.id}-${idx}`}>
                        <span className="font-medium text-foreground">{item.name || item.title}</span> ({item.type})
                      </li>
                    ))}
                  </ul>
                </div>
              ) : (
                <p className="text-xs text-amber-600 dark:text-amber-400 font-medium italic">
                  * No se ha seleccionado ningún archivo de marco teórico aún.
                </p>
              )}
            </div>

            {/* Sección Material Etnográfico */}
            <div className="space-y-3 rounded-lg border p-4 bg-muted/30">
              <div className="flex items-center justify-between">
                <div>
                  <Label className="text-base font-semibold flex items-center gap-2">
                    <Microscope className="h-4 w-4 text-emerald-500" />
                    Material Etnográfico (Corpus)
                  </Label>
                  <p className="text-xs text-muted-foreground">
                    Entrevistas, diarios de campo, textos u otro corpus a analizar cualitativamente.
                  </p>
                </div>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setIsEthnoSelectorOpen(true)}
                  className="gap-2"
                >
                  <Microscope className="h-4 w-4" />
                  {ethnographicMaterialItems.length > 0 ? 'Modificar Corpus' : 'Seleccionar Archivos'}
                </Button>
              </div>

              {ethnographicMaterialItems.length > 0 ? (
                <div className="mt-2 space-y-1">
                  <div className="flex items-center gap-2 text-xs font-medium text-emerald-600 dark:text-emerald-400">
                    <CheckCircle2 className="h-4 w-4" />
                    {ethnographicMaterialItems.length} ítem(s) cargado(s) como corpus
                  </div>
                  <ul className="text-xs text-muted-foreground list-disc pl-5 max-h-24 overflow-y-auto">
                    {ethnographicMaterialItems.map((item, idx) => (
                      <li key={`${item.type}-${item.id}-${idx}`}>
                        <span className="font-medium text-foreground">{item.name || item.title}</span> ({item.type})
                      </li>
                    ))}
                  </ul>
                </div>
              ) : (
                <p className="text-xs text-muted-foreground/60 italic">
                  Opcional: sin corpus seleccionado, el agente investigará en fuentes externas.
                </p>
              )}
            </div>

            {/* Toggle Profundizar Marco Teórico */}
            <div className="flex items-center justify-between rounded-lg border p-4">
              <div className="space-y-0.5 pr-4">
                <Label htmlFor="deepen-switch" className="text-sm font-semibold cursor-pointer">
                  Profundizar Marco Teórico durante la investigación
                </Label>
                <p className="text-xs text-muted-foreground">
                  Si se activa, el agente investigará y ampliará los conceptos clave del marco teórico preliminar antes de la codificación.
                </p>
              </div>
              <Switch
                id="deepen-switch"
                checked={deepenTheoreticalFramework}
                onCheckedChange={setDeepenTheoreticalFramework}
              />
            </div>

            {/* Pregunta de Investigación */}
            <div className="space-y-2">
              <Label htmlFor="research-question" className="text-sm font-semibold flex items-center gap-2">
                <HelpCircle className="h-4 w-4 text-blue-500" />
                Pregunta de Investigación (Opcional)
              </Label>
              <Input
                id="research-question"
                placeholder="Ej: ¿Cómo articulan los actores locales la noción de soberanía alimentaria?"
                value={researchQuestion}
                onChange={(e) => setResearchQuestion(e.target.value)}
              />
            </div>

            {/* Hipótesis */}
            <div className="space-y-2">
              <Label htmlFor="hypothesis" className="text-sm font-semibold flex items-center gap-2">
                <Lightbulb className="h-4 w-4 text-amber-500" />
                Hipótesis de Trabajo (Opcional)
              </Label>
              <Textarea
                id="hypothesis"
                rows={3}
                placeholder="Ej: Las prácticas comunitarias resignifican el discurso oficial integrando saberes ancestrales frente a las presiones del mercado."
                value={hypothesis}
                onChange={(e) => setHypothesis(e.target.value)}
              />
            </div>
          </div>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button type="button" variant="ghost" onClick={onClose}>
              Cancelar
            </Button>
            <Button type="button" onClick={handleStart} className="bg-indigo-600 hover:bg-indigo-700 text-white">
              Iniciar Investigación Antropológica
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Selector de Contexto para el Marco Teórico */}
      <ContextSelectorDialog
        isOpen={isContextSelectorOpen}
        onClose={() => setIsContextSelectorOpen(false)}
        onSelectContext={(selectedItems) => {
          setTheoreticalFrameworkItems(selectedItems);
          setIsContextSelectorOpen(false);
        }}
        onSelectNote={() => {}}
        currentContext={theoreticalFrameworkItems}
        workspaceId={workspaceId}
      />

      {/* Selector de Contexto para Material Etnográfico */}
      <ContextSelectorDialog
        isOpen={isEthnoSelectorOpen}
        onClose={() => setIsEthnoSelectorOpen(false)}
        onSelectContext={(selectedItems) => {
          setEthnographicMaterialItems(selectedItems);
          setIsEthnoSelectorOpen(false);
        }}
        onSelectNote={() => {}}
        currentContext={ethnographicMaterialItems}
        workspaceId={workspaceId}
      />
    </>
  );
};

export default AnthropologicalResearchDialog;
