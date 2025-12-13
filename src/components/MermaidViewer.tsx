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

interface MermaidViewerProps {
  mermaidCode: string;
  trigger?: React.ReactNode; // Elemento que activará el diálogo
}

const MermaidViewer: React.FC<MermaidViewerProps> = ({ mermaidCode, trigger }) => {
  const [isOpen, setIsOpen] = useState(false);
  const mermaidContainerRef = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(1);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const startDragPos = useRef({ x: 0, y: 0 });

  const renderMermaid = useCallback(async () => {
    if (mermaidContainerRef.current && mermaidCode && isOpen) {
      mermaidContainerRef.current.innerHTML = ''; // Limpiar contenido previo
      try {
        const { svg } = await mermaid.render('mermaid-diagram', mermaidCode);
        mermaidContainerRef.current.innerHTML = svg;
      } catch (error) {
        console.error('Error rendering mermaid diagram:', error);
        mermaidContainerRef.current.innerHTML = `
          <div class="p-4 border border-red-200 rounded bg-red-50 dark:bg-red-900/10 dark:border-red-800 w-full h-full overflow-auto">
            <p class="text-red-600 dark:text-red-400 text-sm font-medium mb-2">Error al renderizar diagrama:</p>
            <pre class="text-xs p-2 bg-gray-100 dark:bg-gray-800 rounded text-gray-700 dark:text-gray-300 whitespace-pre-wrap font-mono">${mermaidCode}</pre>
          </div>
        `;
      }
    }
  }, [mermaidCode, isOpen]);

  useEffect(() => {
    if (isOpen) {
      renderMermaid();
    }
  }, [isOpen, renderMermaid]);

  const handleWheel = useCallback((e: WheelEvent) => {
    e.preventDefault();
    setScale((prevScale) => {
      const newScale = prevScale * (1 - e.deltaY * 0.001);
      return Math.min(Math.max(0.1, newScale), 5); // Limitar zoom entre 0.1 y 5
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

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  const handleMouseLeave = useCallback(() => {
    setIsDragging(false);
  }, []);

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      {trigger && <DialogTrigger asChild>{trigger}</DialogTrigger>}
      <DialogContent className="max-w-screen-xl h-[90vh] flex flex-col p-0">
        <DialogHeader className="p-4 border-b">
          <DialogTitle>Diagrama Mermaid</DialogTitle>
          <DialogDescription>
            Visualización interactiva del diagrama Mermaid. Usa la rueda del ratón para hacer zoom y arrastra para moverte.
          </DialogDescription>
        </DialogHeader>
        <div
          className="flex-1 overflow-hidden relative bg-gray-50 dark:bg-gray-900"
          onWheel={handleWheel as any}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseLeave}
        >
          <div
            ref={mermaidContainerRef}
            className="absolute top-0 left-0 flex items-center justify-center"
            style={{
              transform: `translate(${position.x}px, ${position.y}px) scale(${scale})`,
              transformOrigin: '0 0',
              cursor: isDragging ? 'grabbing' : 'grab',
              width: '100%',
              height: '100%',
            }}
          >
            {/* El diagrama Mermaid se renderizará aquí */}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default MermaidViewer;
