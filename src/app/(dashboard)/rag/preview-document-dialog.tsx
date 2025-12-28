// En: src/app/(dashboard)/rag/preview-document-dialog.tsx
'use client';

import { useEffect, useState, useRef } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import apiClient from '@/lib/api';
import type { Document } from './columns'; // Importamos el tipo

interface PreviewDocumentDialogProps {
  document: Document | null;
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
}

export function PreviewDocumentDialog({ document, isOpen, onOpenChange, highlightText }: PreviewDocumentDialogProps & { highlightText?: string }) {
  const [content, setContent] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const highlightRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (isOpen && document) {
      const fetchContent = async () => {
        setIsLoading(true);
        setContent('');
        try {
          const response = await apiClient.get(`/api/documents/get-document-content?file_name=${encodeURIComponent(document.file_name)}`);
          setContent(response.data.content);
        } catch (error) {
          setContent('No se pudo cargar el contenido de este documento.');
          console.error(error);
        } finally {
          setIsLoading(false);
        }
      };
      fetchContent();
    }
  }, [isOpen, document]);

  // Efecto para hacer scroll al texto resaltado una vez que el contenido se ha cargado y renderizado
  useEffect(() => {
    if (!isLoading && content && highlightText && highlightRef.current) {
      // Pequeño timeout para asegurar que el DOM se ha actualizado
      setTimeout(() => {
        highlightRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }, 100);
    }
  }, [isLoading, content, highlightText]);

  const renderContent = () => {
    if (!content) return null;
    if (!highlightText) return content;

    // Normalizamos para buscar ignorando espacios extra si es necesario, 
    // pero por ahora probamos búsqueda directa para mantener el formato.
    const index = content.indexOf(highlightText);

    if (index === -1) {
      // Intento de búsqueda más flexible si la exacta falla (por diferencias de saltos de línea, etc)
      // Esto es básico, se podría mejorar con lógica difusa si fuera necesario.
      return content;
    }

    const before = content.substring(0, index);
    const match = content.substring(index, index + highlightText.length);
    const after = content.substring(index + highlightText.length);

    return (
      <>
        {before}
        <mark
          ref={highlightRef}
          className="bg-yellow-200 dark:bg-yellow-900/50 text-foreground px-1 rounded border border-yellow-400/50 animate-pulse"
        >
          {match}
        </mark>
        {after}
      </>
    );
  };

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl w-full h-[90vh] sm:h-[80vh] flex flex-col p-4 sm:p-6">
        <DialogHeader>
          <DialogTitle className="truncate text-lg sm:text-xl">
            Previsualizando: {document?.title || document?.file_name}
          </DialogTitle>
        </DialogHeader>
        <div className="flex-grow overflow-hidden">
          <ScrollArea className="h-full pr-4">
            {isLoading ? (
              <div className="flex items-center justify-center h-full">
                <p className="text-muted-foreground">Cargando contenido...</p>
              </div>
            ) : (
              <pre className="text-sm whitespace-pre-wrap font-sans p-2">
                {renderContent()}
              </pre>
            )}
          </ScrollArea>
        </div>
      </DialogContent>
    </Dialog>
  );
}