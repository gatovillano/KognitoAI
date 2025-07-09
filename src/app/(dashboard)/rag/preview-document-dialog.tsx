// En: src/app/(dashboard)/rag/preview-document-dialog.tsx
'use client';

import { useEffect, useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { InlineMarkdownRenderer } from '@/components/InlineMarkdownRenderer'; // Importamos el componente de Markdown
import apiClient from '@/lib/api';
import type { Document } from './columns'; // Importamos el tipo

interface PreviewDocumentDialogProps {
  document: Document | null;
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
}

export function PreviewDocumentDialog({ document, isOpen, onOpenChange }: PreviewDocumentDialogProps) {
  const [content, setContent] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (isOpen && document) {
      const fetchContent = async () => {
        setIsLoading(true);
        setContent('');
        try {
          const response = await apiClient.post('/api/get-document-content', {
            file_name: document.file_name,
          });
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

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="truncate">
            Previsualizando: {document?.title || document?.file_name}
          </DialogTitle>
        </DialogHeader>
        <div className="flex-grow overflow-hidden">
            <ScrollArea className="h-full pr-4">
                {isLoading ? (
                    <p>Cargando contenido...</p>
                ) : (
                    <InlineMarkdownRenderer content={content} />
                )}
            </ScrollArea>
        </div>
      </DialogContent>
    </Dialog>
  );
}
