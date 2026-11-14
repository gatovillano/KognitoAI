'use client';

import { useParams } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';
import { Loader2, Download, FileText, FileSpreadsheet, Presentation, FileImage, FileVideo, FileAudio, File } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

interface OnlyOfficeConfigResponse {
  config: any;
  onlyoffice_url: string;
  document?: {
    id: string;
    filename: string;
    extension: string;
    can_edit: boolean;
  };
}

declare global {
  interface Window {
    DocsAPI?: {
      DocEditor: new (placeholderId: string, config: any) => any;
    };
  }
}

type MediaType = 'image' | 'video' | 'audio' | 'pdf' | 'office' | 'other';

export default function SharedOnlyOfficeDocumentPage() {
  const params = useParams();
  const token = (params?.token as string) || '';
  const editorRef = useRef<any>(null);

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [docInfo, setDocInfo] = useState<{ id: string; filename: string; extension: string; can_edit: boolean } | null>(null);
  const [mediaType, setMediaType] = useState<MediaType>('office');

  const apiBase = process.env.NEXT_PUBLIC_API_URL || '';

  const getMediaType = (ext: string): MediaType => {
    const lower = (ext || '').toLowerCase();
    if (['jpg', 'jpeg', 'png', 'gif', 'svg', 'webp'].includes(lower)) return 'image';
    if (['mp4', 'webm', 'mov', 'avi', 'mkv'].includes(lower)) return 'video';
    if (['mp3', 'wav', 'ogg', 'm4a', 'flac'].includes(lower)) return 'audio';
    if (['pdf'].includes(lower)) return 'pdf';
    if (['doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'csv', 'md', 'rtf', 'odt', 'ods', 'odp'].includes(lower)) return 'office';
    return 'other';
  };

  const getFileIcon = (ext: string) => {
    const type = getMediaType(ext);
    if (type === 'image') return FileImage;
    if (type === 'video') return FileVideo;
    if (type === 'audio') return FileAudio;
    const lower = (ext || '').toLowerCase();
    if (['xls', 'xlsx', 'csv', 'ods'].includes(lower)) return FileSpreadsheet;
    if (['ppt', 'pptx', 'odp'].includes(lower)) return Presentation;
    if (['doc', 'docx', 'txt', 'rtf', 'odt', 'pdf', 'md'].includes(lower)) return FileText;
    return File;
  };

  useEffect(() => {
    const loadSharedEditor = async () => {
      if (!token) return;

      try {
        const response = await fetch(`${apiBase}/api/onlyoffice/share/${token}/config`);

        if (!response.ok) {
          if (response.status === 404) {
            throw new Error('El documento compartido no existe o el enlace ha caducado');
          }
          throw new Error('No se pudo cargar el documento compartido');
        }

        const data: OnlyOfficeConfigResponse = await response.json();
        if (data.document) {
          setDocInfo(data.document);
          const detectedType = getMediaType(data.document.extension);
          setMediaType(detectedType);
        }

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
            // Si el script de OnlyOffice falla y es PDF o medio, permitir previsualización directa
            setIsLoading(false);
          };
          document.head.appendChild(script);
        } else {
          initEditor();
        }
      } catch (err: any) {
        console.error(err);
        setError(err.message || 'No se pudo abrir el documento compartido');
        setIsLoading(false);
      }
    };

    loadSharedEditor();

    return () => {
      if (editorRef.current && typeof editorRef.current.destroyEditor === 'function') {
        editorRef.current.destroyEditor();
      }
    };
  }, [token, apiBase]);

  const downloadUrl = `${apiBase}/api/onlyoffice/share/document/${token}/download`;

  const handleDownload = () => {
    window.open(downloadUrl, '_blank');
  };

  const IconComponent = getFileIcon(docInfo?.extension || '');

  return (
    <div className="h-screen w-screen bg-background flex flex-col font-sans">
      <header className="h-14 border-b px-6 flex items-center justify-between bg-card/80 backdrop-blur z-20">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary/10 rounded-xl text-primary">
            <IconComponent className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-sm font-semibold truncate max-w-md">
              {docInfo?.filename || 'Documento Compartido'}
            </h1>
            <p className="text-xs text-muted-foreground">Documento público • Sin inicio de sesión requerido</p>
          </div>
          {docInfo && (
            <Badge variant={docInfo.can_edit ? "default" : "secondary"} className="text-xs rounded-full ml-2">
              {docInfo.can_edit ? 'Edición pública' : 'Solo lectura'}
            </Badge>
          )}
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleDownload} className="rounded-xl">
            <Download className="h-4 w-4 mr-1.5" />
            Descargar
          </Button>
        </div>
      </header>

      <div className="flex-1 bg-muted/20 relative flex flex-col overflow-hidden">
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center gap-3 text-muted-foreground bg-background/80 z-10">
            <Loader2 className="h-6 w-6 animate-spin text-primary" />
            <span className="text-sm font-medium">Cargando documento...</span>
          </div>
        )}

        {error && (
          <div className="h-full w-full flex flex-col items-center justify-center text-sm text-destructive p-4 gap-4">
            <p className="font-semibold">{error}</p>
            <Button variant="outline" size="sm" onClick={handleDownload} className="rounded-xl">
              <Download className="h-4 w-4 mr-1.5" /> Descargar archivo directamente
            </Button>
          </div>
        )}

        {/* Media Fallbacks for non-Office types when appropriate */}
        {mediaType === 'image' && !error && (
          <div className="flex-1 flex items-center justify-center p-6 overflow-auto">
            <img src={`${downloadUrl}?inline=true`} alt={docInfo?.filename} className="max-h-[85vh] max-w-full rounded-xl shadow-lg object-contain" />
          </div>
        )}

        {mediaType === 'video' && !error && (
          <div className="flex-1 flex items-center justify-center p-6">
            <video src={downloadUrl} controls autoPlay className="max-h-[85vh] max-w-full rounded-xl shadow-lg" />
          </div>
        )}

        {mediaType === 'audio' && !error && (
          <div className="flex-1 flex flex-col items-center justify-center p-6 gap-4">
            <div className="p-4 bg-primary/20 text-primary rounded-full">
              <FileAudio className="h-12 w-12" />
            </div>
            <p className="text-sm font-medium">{docInfo?.filename}</p>
            <audio src={downloadUrl} controls autoPlay className="w-full max-w-md" />
          </div>
        )}

        {/* OnlyOffice Placeholder container */}
        <div
          id="shared-onlyoffice-placeholder"
          className={`flex-1 w-full h-full ${['image', 'video', 'audio'].includes(mediaType) ? 'hidden' : 'block'}`}
        />
      </div>
    </div>
  );
}
