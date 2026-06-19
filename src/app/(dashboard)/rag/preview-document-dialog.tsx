// En: src/app/(dashboard)/rag/preview-document-dialog.tsx
'use client';

import { Children, Fragment, cloneElement, isValidElement, type ComponentPropsWithoutRef, type MutableRefObject, type ReactNode, useEffect, useMemo, useState, useRef } from 'react';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import ReactMarkdown from 'react-markdown';
import type { Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import apiClient from '@/lib/api';
import type { Document } from './columns'; // Importamos el tipo

interface PreviewDocumentDialogProps {
  document: Document | null;
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
}

type HighlightCounter = { current: number };

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function normalizePhysicalDocumentId(value: unknown): string | null {
  if (typeof value !== 'string') {
    return null;
  }

  const normalizedValue = value.trim();

  if (!normalizedValue) {
    return null;
  }

  if (['none', 'null', 'undefined'].includes(normalizedValue.toLowerCase())) {
    return null;
  }

  return UUID_PATTERN.test(normalizedValue) ? normalizedValue : null;
}

function highlightTextNodes(
  node: ReactNode,
  targetText: string | undefined,
  highlightRef: MutableRefObject<HTMLElement | null>,
  counter: HighlightCounter
): ReactNode {
  if (!targetText) {
    return node;
  }

  if (typeof node === 'string') {
    const parts = node.split(targetText);

    if (parts.length === 1) {
      return node;
    }

    return parts.flatMap((part, index) => {
      if (index === parts.length - 1) {
        return part;
      }

      counter.current += 1;
      const shouldAttachRef = counter.current === 1;

      return [
        part,
        <mark
          key={`highlight-${counter.current}-${index}`}
          ref={shouldAttachRef ? highlightRef : undefined}
          className="rounded border border-yellow-400/50 bg-yellow-200 px-1 text-foreground dark:bg-yellow-900/50"
        >
          {targetText}
        </mark>,
      ];
    });
  }

  if (Array.isArray(node)) {
    return node.map((child, index) => (
      <Fragment key={`highlight-fragment-${index}`}>
        {highlightTextNodes(child, targetText, highlightRef, counter)}
      </Fragment>
    ));
  }

  if (isValidElement(node)) {
    const childProps = node.props as { children?: ReactNode };

    if (!childProps.children) {
      return node;
    }

    return cloneElement(node as any, {
      ...childProps,
      children: Children.map(childProps.children, child => highlightTextNodes(child, targetText, highlightRef, counter)),
    });
  }

  return node;
}

function createHighlightedTag(
  tagName: any,
  targetText: string | undefined,
  highlightRef: MutableRefObject<HTMLElement | null>,
  counter: HighlightCounter
) {
  return function HighlightedTag({ children, ...props }: any) {
    const TagName = tagName;

    return (
      <TagName {...props}>
        {highlightTextNodes(children, targetText, highlightRef, counter)}
      </TagName>
    );
  };
}

function normalizeDocumentContent(value: unknown): string {
  if (typeof value === 'string') {
    return value;
  }

  if (value == null) {
    return '';
  }

  if (Array.isArray(value)) {
    return value
      .map(item => normalizeDocumentContent(item))
      .filter(Boolean)
      .join('\n\n');
  }

  if (typeof value === 'object') {
    const contentValue = (value as { content?: unknown }).content;
    const textValue = (value as { text?: unknown }).text;

    if (typeof contentValue === 'string') {
      return contentValue;
    }

    if (typeof textValue === 'string') {
      return textValue;
    }

    try {
      return JSON.stringify(value, null, 2);
    } catch {
      return String(value);
    }
  }

  return String(value);
}

export function PreviewDocumentDialog({ document, isOpen, onOpenChange, highlightText }: PreviewDocumentDialogProps & { highlightText?: string }) {
  const [content, setContent] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [pdfPreviewUrl, setPdfPreviewUrl] = useState<string | null>(null);
  const highlightRef = useRef<HTMLElement>(null);

  const markdownComponents = useMemo<Components>(() => {
    const counter = { current: 0 };

    return {
      p: createHighlightedTag('p', highlightText, highlightRef, counter),
      h1: createHighlightedTag('h1', highlightText, highlightRef, counter),
      h2: createHighlightedTag('h2', highlightText, highlightRef, counter),
      h3: createHighlightedTag('h3', highlightText, highlightRef, counter),
      h4: createHighlightedTag('h4', highlightText, highlightRef, counter),
      h5: createHighlightedTag('h5', highlightText, highlightRef, counter),
      h6: createHighlightedTag('h6', highlightText, highlightRef, counter),
      ul: createHighlightedTag('ul', highlightText, highlightRef, counter),
      ol: createHighlightedTag('ol', highlightText, highlightRef, counter),
      li: createHighlightedTag('li', highlightText, highlightRef, counter),
      blockquote: createHighlightedTag('blockquote', highlightText, highlightRef, counter),
      a: createHighlightedTag('a', highlightText, highlightRef, counter),
      strong: createHighlightedTag('strong', highlightText, highlightRef, counter),
      em: createHighlightedTag('em', highlightText, highlightRef, counter),
      del: createHighlightedTag('del', highlightText, highlightRef, counter),
      code: createHighlightedTag('code', highlightText, highlightRef, counter),
      pre: createHighlightedTag('pre', highlightText, highlightRef, counter),
      table: createHighlightedTag('table', highlightText, highlightRef, counter),
      thead: createHighlightedTag('thead', highlightText, highlightRef, counter),
      tbody: createHighlightedTag('tbody', highlightText, highlightRef, counter),
      tr: createHighlightedTag('tr', highlightText, highlightRef, counter),
      th: createHighlightedTag('th', highlightText, highlightRef, counter),
      td: createHighlightedTag('td', highlightText, highlightRef, counter),
    };
  }, [highlightText]);

  const renderedContent = useMemo(() => {
    if (!content) {
      return null;
    }

    return (
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
        {content}
      </ReactMarkdown>
    );
  }, [content, markdownComponents]);

  const isPdf = document?.file_name?.toLowerCase().endsWith('.pdf');
  const physicalDocumentId = normalizePhysicalDocumentId(document?.physical_document_id);
  const hasPhysicalFile = Boolean(physicalDocumentId);
  const showNativePdfViewer = isPdf && hasPhysicalFile;

  useEffect(() => {
    if (!isOpen || !document) {
      setContent('');
      setPdfPreviewUrl(null);
      setIsLoading(false);
      return;
    }

    let cancelled = false;
    let objectUrlToRevoke: string | null = null;

    const loadTextPreview = async () => {
      const response = await apiClient.get(`/api/documents/get-document-content?file_name=${encodeURIComponent(document.file_name)}`);
      if (!cancelled) {
        setContent(normalizeDocumentContent(response.data?.content));
      }
    };

    const fetchPreview = async () => {
      setIsLoading(true);
      setContent('');
      setPdfPreviewUrl(null);

      try {
        if (showNativePdfViewer && physicalDocumentId) {
          const response = await apiClient.get(`/api/onlyoffice/download/${physicalDocumentId}?inline=true`, {
            responseType: 'blob',
          });

          if (cancelled) {
            return;
          }

          const blob = response.data instanceof Blob
            ? response.data
            : new Blob([response.data], { type: 'application/pdf' });
          const contentTypeHeader = typeof response.headers?.['content-type'] === 'string'
            ? response.headers['content-type']
            : '';
          const isPdfResponse = contentTypeHeader.includes('application/pdf') || blob.type === 'application/pdf';

          if (blob.size > 0 && isPdfResponse) {
            objectUrlToRevoke = URL.createObjectURL(blob);
            setPdfPreviewUrl(objectUrlToRevoke);
            return;
          }

          console.warn('PreviewDocumentDialog: PDF inline preview unavailable.', {
            documentId: physicalDocumentId,
            blobSize: blob.size,
            contentTypeHeader,
            blobType: blob.type,
          });
          setContent('No se pudo cargar el PDF original.');
          return;
        }

        if (isPdf) {
          setContent('No se encontró el PDF original para este documento.');
          return;
        }

        await loadTextPreview();
      } catch (error) {
        if (!cancelled) {
          if (showNativePdfViewer) {
            setContent('No se pudo cargar el PDF original.');
          } else {
            setContent('No se pudo cargar el contenido de este documento.');
          }
          console.error(error);
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    };

    fetchPreview();

    return () => {
      cancelled = true;
      if (objectUrlToRevoke) {
        URL.revokeObjectURL(objectUrlToRevoke);
      }
    };
  }, [isOpen, document, isPdf, showNativePdfViewer, physicalDocumentId]);

  // Efecto para hacer scroll al texto resaltado una vez que el contenido se ha cargado y renderizado
  useEffect(() => {
    if (!isLoading && content && highlightText && highlightRef.current) {
      // Pequeño timeout para asegurar que el DOM se ha actualizado
      setTimeout(() => {
        highlightRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }, 100);
    }
  }, [isLoading, content, highlightText]);

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl w-full h-[90vh] sm:h-[80vh] flex flex-col p-4 sm:p-6">
        <DialogHeader>
          <DialogTitle className="truncate text-lg sm:text-xl">
            Previsualizando: {document?.title || document?.file_name}
          </DialogTitle>
          <DialogDescription className="sr-only">
            Vista previa del documento seleccionado.
          </DialogDescription>
        </DialogHeader>
        <div className="flex-grow overflow-hidden">
          {showNativePdfViewer ? (
            isLoading ? (
              <div className="flex items-center justify-center h-full">
                <p className="text-muted-foreground">Cargando PDF...</p>
              </div>
            ) : pdfPreviewUrl ? (
              <div className="h-full w-full">
                <iframe
                  src={pdfPreviewUrl}
                  className="w-full h-full border-0 rounded-md"
                  title={`PDF Viewer - ${document?.title || document?.file_name || ''}`}
                />
              </div>
            ) : (
              <ScrollArea className="h-full pr-4">
                <div className="prose prose-sm max-w-none whitespace-pre-wrap break-words p-2 dark:prose-invert">
                  {content || 'No se pudo cargar la previsualización del PDF.'}
                </div>
              </ScrollArea>
            )
          ) : (
            <ScrollArea className="h-full pr-4">
              {isLoading ? (
                <div className="flex items-center justify-center h-full">
                  <p className="text-muted-foreground">Cargando contenido...</p>
                </div>
              ) : (
                <div className="prose prose-sm max-w-none whitespace-pre-wrap break-words p-2 dark:prose-invert">
                  {renderedContent}
                </div>
              )}
            </ScrollArea>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
