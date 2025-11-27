import { useState, useEffect } from 'react';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Network, Lightbulb } from "lucide-react";

interface DatasetNameDialogProps {
    isOpen: boolean;
    onOpenChange: (open: boolean) => void;
    onConfirm: (datasetName: string, mode: 'hybrid' | 'conceptual') => void;
    defaultTopic?: string | null;
    workspaceId?: string;
}

export function DatasetNameDialog({
    isOpen,
    onOpenChange,
    onConfirm,
    defaultTopic,
    workspaceId
}: DatasetNameDialogProps) {
    const [datasetName, setDatasetName] = useState("");
    const [mode, setMode] = useState<'hybrid' | 'conceptual'>('hybrid');
    const [selectionType, setSelectionType] = useState<'auto' | 'custom'>('auto');

    useEffect(() => {
        if (isOpen) {
            // Calculate auto name
            // Clean topic name to be safe for dataset names
            const cleanTopic = defaultTopic ? defaultTopic.replace(/[^a-zA-Z0-9_-]/g, '_').toLowerCase() : null;

            const autoName = cleanTopic
                ? `topic_${cleanTopic}`
                : (workspaceId ? `workspace_${workspaceId}_all` : 'global_context');

            setDatasetName(autoName);
            setSelectionType('auto');
        }
    }, [isOpen, defaultTopic, workspaceId]);

    const handleConfirm = () => {
        onConfirm(datasetName, mode);
        onOpenChange(false);
    };

    return (
        <Dialog open={isOpen} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[500px]">
                <DialogHeader>
                    <DialogTitle>Procesar Grafo de Conocimiento</DialogTitle>
                    <DialogDescription>
                        Configura cómo se procesarán tus documentos para generar el grafo.
                    </DialogDescription>
                </DialogHeader>

                <div className="grid gap-6 py-4">
                    {/* Mode Selection */}
                    <div className="space-y-3">
                        <Label className="text-base font-medium">Modo de Procesamiento</Label>
                        <RadioGroup value={mode} onValueChange={(v) => setMode(v as any)} className="grid grid-cols-1 gap-3">

                            <div className={`flex items-start space-x-3 space-y-0 rounded-md border p-3 hover:bg-accent hover:text-accent-foreground cursor-pointer ${mode === 'hybrid' ? 'border-primary bg-primary/5' : ''}`} onClick={() => setMode('hybrid')}>
                                <RadioGroupItem value="hybrid" id="hybrid" className="mt-1" />
                                <div className="grid gap-1.5 leading-none">
                                    <Label htmlFor="hybrid" className="font-semibold cursor-pointer flex items-center gap-2">
                                        <Network className="h-4 w-4 text-primary" />
                                        Modo Estándar (Híbrido)
                                        <span className="inline-flex items-center rounded-full border border-transparent bg-primary/10 px-2 py-0.5 text-xs font-semibold text-primary transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2">
                                            Recomendado
                                        </span>
                                    </Label>
                                    <p className="text-sm text-muted-foreground">
                                        Extrae entidades (personas, orgs), conceptos y relaciones semánticas ricas. Ideal para navegación y búsqueda general.
                                    </p>
                                </div>
                            </div>

                            <div className={`flex items-start space-x-3 space-y-0 rounded-md border p-3 hover:bg-accent hover:text-accent-foreground cursor-pointer ${mode === 'conceptual' ? 'border-primary bg-primary/5' : ''}`} onClick={() => setMode('conceptual')}>
                                <RadioGroupItem value="conceptual" id="conceptual" className="mt-1" />
                                <div className="grid gap-1.5 leading-none">
                                    <Label htmlFor="conceptual" className="font-semibold cursor-pointer flex items-center gap-2">
                                        <Lightbulb className="h-4 w-4 text-amber-500" />
                                        Modo Conceptual (Experimental)
                                    </Label>
                                    <p className="text-sm text-muted-foreground">
                                        Enfocado en extraer citas textuales, perfiles de ideas y detectar tendencias temporales.
                                    </p>
                                </div>
                            </div>

                        </RadioGroup>
                    </div>

                    {/* Dataset Name */}
                    <div className="space-y-3">
                        <Label className="text-base font-medium">Nombre del Dataset</Label>
                        <RadioGroup value={selectionType} onValueChange={(v: any) => setSelectionType(v)} className="space-y-2">
                            <div className="flex items-center space-x-2">
                                <RadioGroupItem value="auto" id="auto" />
                                <Label htmlFor="auto" className="cursor-pointer">
                                    Automático: <span className="font-mono text-xs bg-muted px-1 py-0.5 rounded">{defaultTopic ? `topic_${defaultTopic.replace(/[^a-zA-Z0-9_-]/g, '_').toLowerCase()}` : (workspaceId ? `workspace_${workspaceId}_all` : 'global_context')}</span>
                                </Label>
                            </div>
                            <div className="flex items-center space-x-2">
                                <RadioGroupItem value="custom" id="custom" />
                                <Label htmlFor="custom" className="cursor-pointer">Personalizado</Label>
                            </div>
                        </RadioGroup>

                        {selectionType === 'custom' && (
                            <Input
                                value={datasetName}
                                onChange={(e) => setDatasetName(e.target.value)}
                                placeholder="Ej: mi_proyecto_v1"
                                className="mt-2"
                            />
                        )}
                    </div>
                </div>

                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)}>Cancelar</Button>
                    <Button onClick={handleConfirm}>Iniciar Procesamiento</Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
