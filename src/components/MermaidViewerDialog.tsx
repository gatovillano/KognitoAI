'use client';

import React, { useCallback, useEffect, useRef } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

interface MermaidViewerDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  mermaidCode: string;
  title?: string;
  description?: string;
}

export function MermaidViewerDialog({
  isOpen,
  onOpenChange,
  mermaidCode,
  title = 'Diagrama Mermaid',
  description = 'Visualización interactiva del diagrama.',
}: MermaidViewerDialogProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  const renderMermaid = useCallback(async (container: HTMLDivElement, id: string) => {
    if (!container || !mermaidCode) return;

    try {
      const mermaidModule = await import('mermaid');
      const mermaid = mermaidModule.default;
      mermaid.initialize({
        startOnLoad: false,
        theme: 'dark',
        securityLevel: 'loose',
        fontFamily: 'inherit',
        themeVariables: {
          fontFamily: 'inherit',
        },
        flowchart: {
          htmlLabels: true,
          useMaxWidth: true,
          padding: 18,
        },
        themeCSS: `
          g.edgeLabel foreignObject,
          g.edgeLabel foreignobject,
          g.label foreignObject,
          g.label foreignobject,
          div.label,
          .nodeLabel {
            overflow: visible !important;
          }
        `
      });
      
      const { svg } = await mermaid.render(id, mermaidCode);
      container.innerHTML = svg;

      const svgElement = container.querySelector('svg');
      if (svgElement) {
        svgElement.style.width = '100%';
        svgElement.style.height = 'auto';
        svgElement.style.display = 'block';
      }
    } catch (error) {
      container.innerHTML = '<div class="text-sm text-muted-foreground">No se pudo renderizar el diagrama Mermaid.</div>';
      console.error('Error rendering Mermaid dialog:', error);
    }
  }, [mermaidCode]);

  useEffect(() => {
    if (isOpen && containerRef.current) {
      renderMermaid(containerRef.current, `mermaid-dialog-${Math.random().toString(36).slice(2, 10)}`);
    }
  }, [isOpen, renderMermaid]);

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-[95vw] w-full h-[90vh] flex flex-col p-0 overflow-hidden bg-background/95 backdrop-blur-md border-border/40 sm:rounded-3xl">
        <DialogHeader className="p-6 border-b border-border/10">
          <DialogTitle className="text-xl font-bold tracking-tight">{title}</DialogTitle>
          <DialogDescription className="text-sm text-muted-foreground italic">
            {description}
          </DialogDescription>
        </DialogHeader>
        <div className="flex-1 overflow-auto bg-muted/5 p-6">
          <div ref={containerRef} className="min-h-[200px] flex items-center justify-center" />
        </div>
      </DialogContent>
    </Dialog>
  );
}
