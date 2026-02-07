import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import mermaid from 'mermaid';
import { Maximize2, Activity } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface MermaidViewerProps {
  mermaidCode: string;
}

// Inicializar mermaid fuera del componente
if (typeof window !== 'undefined') {
  mermaid.initialize({
    startOnLoad: true,
    theme: 'dark',
    securityLevel: 'loose',
    fontFamily: 'Inter, system-ui, sans-serif',
  });
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
        const { svg } = await mermaid.render(id, mermaidCode);
        container.innerHTML = svg;
        const svgElement = container.querySelector('svg');
        if (svgElement) {
          svgElement.style.width = '100%';
          svgElement.style.height = 'auto';
          svgElement.style.display = 'block';
        }
      } catch (error) {
        console.error('Error rendering mermaid diagram:', error);
        container.innerHTML = `
          <div class="p-4 border border-red-200 rounded bg-red-50 dark:bg-red-900/10 dark:border-red-800 w-full h-full overflow-auto text-red-600 dark:text-red-400">
            <p class="text-sm font-medium mb-2">Error al renderizar diagrama:</p>
            <pre class="text-xs p-2 bg-gray-100 dark:bg-gray-800 rounded whitespace-pre-wrap font-mono">${mermaidCode}</pre>
          </div>
        `;
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
    if (isOpen && mermaidContainerRef.current) {
      renderMermaid(mermaidContainerRef.current, `mermaid-full-${Math.random().toString(36).substr(2, 9)}`);
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

