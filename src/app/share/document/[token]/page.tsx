'use client';

import { useParams } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';
import { Loader2 } from 'lucide-react';

interface OnlyOfficeConfigResponse {
  config: any;
  onlyoffice_url: string;
}

declare global {
  interface Window {
    DocsAPI?: {
      DocEditor: new (placeholderId: string, config: any) => any;
    };
  }
}

export default function SharedOnlyOfficeDocumentPage() {
  const params = useParams();
  const token = (params?.token as string) || '';
  const editorRef = useRef<any>(null);

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadSharedEditor = async () => {
      if (!token) return;

      try {
        const apiBase = process.env.NEXT_PUBLIC_API_URL || 'https://apibase.cuerpolibre.cl';
        const response = await fetch(`${apiBase}/api/onlyoffice/share/${token}/config`);

        if (!response.ok) {
          throw new Error('No se pudo cargar el documento compartido');
        }

        const data: OnlyOfficeConfigResponse = await response.json();

        const initEditor = () => {
          if (editorRef.current && typeof editorRef.current.destroyEditor === 'function') {
            editorRef.current.destroyEditor();
          }
          if (!window.DocsAPI?.DocEditor) {
            throw new Error('OnlyOffice API no disponible');
          }
          editorRef.current = new window.DocsAPI.DocEditor('shared-onlyoffice-placeholder', data.config);
          setIsLoading(false);
        };

        if (!window.DocsAPI?.DocEditor) {
          const script = document.createElement('script');
          script.src = `${data.onlyoffice_url}/web-apps/apps/api/documents/api.js`;
          script.id = 'onlyoffice-api-script-shared';
          script.onload = () => initEditor();
          script.onerror = () => {
            setError('No se pudo cargar el script de OnlyOffice');
            setIsLoading(false);
          };
          document.head.appendChild(script);
        } else {
          initEditor();
        }
      } catch (err) {
        console.error(err);
        setError('No se pudo abrir el documento compartido');
        setIsLoading(false);
      }
    };

    loadSharedEditor();

    return () => {
      if (editorRef.current && typeof editorRef.current.destroyEditor === 'function') {
        editorRef.current.destroyEditor();
      }
    };
  }, [token]);

  return (
    <div className="h-screen w-screen bg-background flex flex-col">
      <header className="h-12 border-b px-4 flex items-center">
        <p className="text-sm font-medium">Documento compartido</p>
      </header>
      <div id="shared-onlyoffice-placeholder" className="flex-1 bg-muted/20">
        {isLoading && (
          <div className="h-full w-full flex items-center justify-center gap-3 text-muted-foreground">
            <Loader2 className="h-5 w-5 animate-spin" />
            <span>Cargando editor...</span>
          </div>
        )}
        {error && (
          <div className="h-full w-full flex items-center justify-center text-sm text-destructive">
            {error}
          </div>
        )}
      </div>
    </div>
  );
}
