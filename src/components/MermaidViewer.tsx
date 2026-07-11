import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Maximize2, Activity } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface MermaidViewerProps {
  mermaidCode: string;
}

const MermaidViewer: React.FC<MermaidViewerProps> = ({ mermaidCode }) => {
  const [isOpen, setIsOpen] = useState(false);
  const mermaidContainerRef = useRef<HTMLDivElement>(null);
  const previewRef = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(1);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const startDragPos = useRef({ x: 0, y: 0 });

  const renderMermaid = useCallback(async (container: HTMLDivElement, id: string) => {
    if (container && mermaidCode) {
      try {
        // Asegurar que el contenedor sea visible y no se quede oculto de ejecuciones previas
        container.style.display = '';
        
        // Importar e inicializar dinámicamente mermaid
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
        
        // Renderizar usando el contenedor para evitar errores en Portales/Dialogs
        const { svg } = await mermaid.render(id, mermaidCode, container);
        container.innerHTML = svg;
        const svgElement = container.querySelector('svg');
        if (svgElement) {
          svgElement.style.width = '100%';
          svgElement.style.height = 'auto';
          svgElement.style.display = 'block';
        }
      } catch (error) {
        console.error("Error al renderizar Mermaid:", error);
        container.style.display = 'none';

        // Solo ocultamos el parentViewer si NO estamos dentro de un diálogo modal
        const isInsideDialog = container.closest('[role="dialog"]') !== null;
        if (!isInsideDialog) {
          const parentViewer = container.closest('.my-4.w-full') as HTMLElement;
          if (parentViewer) {
            parentViewer.style.display = 'none';
          }
        }
      }
    }
  }, [mermaidCode]);

  // Render para la previsualización inline
  useEffect(() => {
    if (previewRef.current) {
      renderMermaid(previewRef.current, `mermaid-preview-${Math.random().toString(36).substr(2, 9)}`);
    }
  }, [mermaidCode, renderMermaid]);

  // Render para el diálogo a pantalla completa
  useEffect(() => {
    if (isOpen) {
      const timer = setTimeout(() => {
        if (mermaidContainerRef.current) {
          renderMermaid(mermaidContainerRef.current, `mermaid-full-${Math.random().toString(36).substr(2, 9)}`);
        }
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [isOpen, renderMermaid]);

  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    setScale((prevScale) => {
      const newScale = prevScale * (1 - e.deltaY * 0.001);
      return Math.min(Math.max(0.1, newScale), 5);
    });
  }, []);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    setIsDragging(true);
    startDragPos.current = { x: e.clientX - position.x, y: e.clientY - position.y };
  }, [position]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!isDragging) return;
    setPosition({
      x: e.clientX - startDragPos.current.x,
      y: e.clientY - startDragPos.current.y,
    });
  }, [isDragging]);

  const handleMouseUp = useCallback(() => setIsDragging(false), []);

  return (
    <div className="my-4 w-full">
      <div className="relative group rounded-2xl border border-border/40 bg-card/50 backdrop-blur-sm overflow-hidden shadow-sm hover:shadow-md transition-all duration-300">
        <div className="flex items-center justify-between px-4 py-2 border-b border-border/10 bg-muted/30">
          <div className="flex items-center gap-2">
            <Activity className="h-3.5 w-3.5 text-primary" />
            <span className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">Diagrama de Flujo</span>
          </div>
          <Dialog open={isOpen} onOpenChange={setIsOpen}>
            <DialogTrigger asChild>
              <Button variant="ghost" size="sm" className="h-7 px-2 text-[10px] gap-1.5 uppercase font-bold tracking-wider hover:bg-primary/10">
                <Maximize2 className="h-3 w-3" />
                <span>Expandir</span>
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-[95vw] w-full h-[90vh] flex flex-col p-0 overflow-hidden bg-background/95 backdrop-blur-md border-border/40 sm:rounded-3xl">
              <DialogHeader className="p-6 border-b border-border/10">
                <DialogTitle className="text-xl font-bold tracking-tight">Diagrama Mermaid</DialogTitle>
                <DialogDescription className="text-sm text-muted-foreground italic">
                  Visualización interactiva. Usa la rueda del ratón para hacer zoom y arrastra para moverte.
                </DialogDescription>
              </DialogHeader>
              <div
                className="flex-1 overflow-hidden relative bg-muted/5 cursor-grab active:cursor-grabbing"
                onWheel={handleWheel}
                onMouseDown={handleMouseDown}
                onMouseMove={handleMouseMove}
                onMouseUp={handleMouseUp}
                onMouseLeave={handleMouseUp}
              >
                <div
                  ref={mermaidContainerRef}
                  className="absolute inset-0 p-8 flex items-center justify-center pointer-events-none"
                  style={{
                    transform: `translate(${position.x}px, ${position.y}px) scale(${scale})`,
                    transformOrigin: 'center center',
                    transition: isDragging ? 'none' : 'transform 0.1s ease-out'
                  }}
                />
              </div>
            </DialogContent>
          </Dialog>
        </div>

        <div
          ref={previewRef}
          className="p-6 min-h-[100px] flex items-center justify-center overflow-auto max-h-[400px]"
        />
      </div>
    </div>
  );
};

export default MermaidViewer;

