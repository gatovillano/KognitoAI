'use client';

import React, { useState } from 'react';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Shield, Zap, RefreshCcw, FileText, Layout, Activity, Check } from 'lucide-react';
import { cn } from '@/lib/utils';

interface StartCodeAnalysisDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: (analysisType: string) => void;
  title?: string;
  isRepo?: boolean;
}

const analysisTypes = [
  {
    id: 'all',
    title: 'Análisis Completo',
    description: 'Análisis exhaustivo de estructura, patrones, seguridad y rendimiento.',
    icon: <Activity className="h-5 w-5" />,
    color: 'text-blue-500',
    bg: 'bg-blue-500/10'
  },
  {
    id: 'security',
    title: 'Seguridad',
    description: 'Identificación de vulnerabilidades, secretos expuestos y riesgos de seguridad.',
    icon: <Shield className="h-5 w-5" />,
    color: 'text-red-500',
    bg: 'bg-red-500/10'
  },
  {
    id: 'performance',
    title: 'Rendimiento',
    description: 'Optimización de algoritmos, uso de recursos y cuellos de botella.',
    icon: <Zap className="h-5 w-5" />,
    color: 'text-yellow-500',
    bg: 'bg-yellow-500/10'
  },
  {
    id: 'refactoring',
    title: 'Refactorización',
    description: 'Oportunidades para mejorar la calidad, legibilidad y mantenibilidad del código.',
    icon: <RefreshCcw className="h-5 w-5" />,
    color: 'text-purple-500',
    bg: 'bg-purple-500/10'
  },
  {
    id: 'documentation',
    title: 'Documentación',
    description: 'Evaluación de la cobertura de comentarios, docstrings y legibilidad.',
    icon: <FileText className="h-5 w-5" />,
    color: 'text-green-500',
    bg: 'bg-green-500/10'
  },
  {
    id: 'structure',
    title: 'Arquitectura',
    description: 'Análisis de la estructura de carpetas, componentes y dependencias.',
    icon: <Layout className="h-5 w-5" />,
    color: 'text-cyan-500',
    bg: 'bg-cyan-500/10'
  }
];

export const StartCodeAnalysisDialog: React.FC<StartCodeAnalysisDialogProps> = ({
  isOpen,
  onOpenChange,
  onConfirm,
  title = "Seleccionar Tipo de Análisis",
  isRepo = false
}) => {
  const [selectedType, setSelectedType] = useState('all');

  const handleConfirm = () => {
    onConfirm(selectedType);
    onOpenChange(false);
  };

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[550px] rounded-2xl bg-card/95 backdrop-blur-xl border shadow-2xl">
        <DialogHeader>
          <DialogTitle className="text-2xl font-bold flex items-center gap-2">
            {title}
          </DialogTitle>
          <DialogDescription>
            Elige el enfoque del análisis para {isRepo ? 'este repositorio' : 'este archivo'}.
          </DialogDescription>
        </DialogHeader>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 py-4">
          {analysisTypes.map((type) => (
            <div
              key={type.id}
              onClick={() => setSelectedType(type.id)}
              className={cn(
                "relative flex flex-col p-4 rounded-xl border-2 transition-all cursor-pointer hover:border-primary/50",
                selectedType === type.id 
                  ? "border-primary bg-primary/5 shadow-md" 
                  : "border-transparent bg-muted/30"
              )}
            >
              {selectedType === type.id && (
                <div className="absolute top-2 right-2 h-5 w-5 rounded-full bg-primary flex items-center justify-center">
                  <Check className="h-3 w-3 text-primary-foreground" />
                </div>
              )}
              <div className={cn("w-10 h-10 rounded-lg flex items-center justify-center mb-3", type.bg, type.color)}>
                {type.icon}
              </div>
              <h4 className="font-bold text-sm mb-1">{type.title}</h4>
              <p className="text-xs text-muted-foreground leading-relaxed">
                {type.description}
              </p>
            </div>
          ))}
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button variant="outline" onClick={() => onOpenChange(false)} className="rounded-xl">
            Cancelar
          </Button>
          <Button onClick={handleConfirm} className="rounded-xl px-8">
            Iniciar Análisis
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
