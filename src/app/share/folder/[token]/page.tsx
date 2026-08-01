'use client';

import React, { useEffect, useRef, useState } from 'react';
import { useParams } from 'next/navigation';
import { 
  Folder, 
  FileText, 
  FileSpreadsheet, 
  Presentation, 
  FileImage, 
  FileArchive, 
  FileCode, 
  FileVideo,
  FileAudio,
  File, 
  Download, 
  Eye, 
  Edit3, 
  Play,
  Music,
  ChevronRight, 
  Loader2, 
  Search, 
  X,
  LayoutGrid,
  List,
  ExternalLink
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';

interface SharedSubfolder {
  id: string;
  name: string;
  created_at?: string;
}

interface SharedDocument {
  id: string;
  filename: string;
  extension: string;
  created_at?: string;
  updated_at?: string;
}

interface BreadcrumbItem {
  id: string;
  name: string;
}

interface SharedFolderData {
  root_folder: { id: string; name: string };
  current_folder: { id: string; name: string; parent_id?: string | null };
  can_edit: boolean;
  breadcrumbs: BreadcrumbItem[];
  subfolders: SharedSubfolder[];
  documents: SharedDocument[];
}

interface OnlyOfficeConfigResponse {
  config: any;
  onlyoffice_url: string;
}

type MediaType = 'image' | 'video' | 'audio' | 'pdf' | 'office' | 'other';

declare global {
  interface Window {
    DocsAPI?: {
      DocEditor: new (placeholderId: string, config: any) => any;
    };
  }
}

export default function SharedFolderPage() {
  const params = useParams();
  const token = (params?.token as string) || '';

  const [currentSubfolderId, setCurrentSubfolderId] = useState<string | null>(null);
  const [folderData, setFolderData] = useState<SharedFolderData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');

  // States for OnlyOffice document viewer modal
  const [activeDoc, setActiveDoc] = useState<SharedDocument | null>(null);
  const [isLoadingDoc, setIsLoadingDoc] = useState(false);
  const [docError, setDocError] = useState<string | null>(null);
  const editorRef = useRef<any>(null);

  // State for direct Media preview (Image, Video, Audio, PDF)
  const [previewMediaDoc, setPreviewMediaDoc] = useState<{ doc: SharedDocument; mediaType: MediaType } | null>(null);

  const apiBase = process.env.NEXT_PUBLIC_API_URL || 'https://apibase.cuerpolibre.cl';

  const loadFolderContent = async (subId?: string | null) => {
    if (!token) return;
    setIsLoading(true);
    setError(null);

    try {
      let url = `${apiBase}/api/onlyoffice/share/folder/${token}`;
      if (subId) {
        url += `?subfolder_id=${subId}`;
      }

      const res = await fetch(url);
      if (!res.ok) {
        if (res.status === 404) {
          throw new Error('Carpeta compartida no encontrada o enlace expirado.');
        }
        throw new Error('Error al cargar la carpeta compartida.');
      }

      const data: SharedFolderData = await res.json();
      setFolderData(data);
    } catch (err: any) {
      console.error(err);
      setError(err.message || 'No se pudo abrir la carpeta compartida.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadFolderContent(currentSubfolderId);
  }, [token, currentSubfolderId]);

  const getMediaType = (ext: string): MediaType => {
    const lower = (ext || '').toLowerCase();
    if (['jpg', 'jpeg', 'png', 'gif', 'svg', 'webp'].includes(lower)) return 'image';
    if (['mp4', 'webm', 'mov', 'avi', 'mkv'].includes(lower)) return 'video';
    if (['mp3', 'wav', 'ogg', 'm4a', 'flac'].includes(lower)) return 'audio';
    if (['pdf'].includes(lower)) return 'pdf';
    if (['doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'csv', 'md'].includes(lower)) return 'office';
    return 'other';
  };

  const getFileIcon = (ext: string) => {
    const mediaType = getMediaType(ext);
    if (mediaType === 'image') return FileImage;
    if (mediaType === 'video') return FileVideo;
    if (mediaType === 'audio') return FileAudio;
    
    const lower = (ext || '').toLowerCase();
    if (['doc', 'docx', 'txt', 'rtf', 'odt', 'pdf'].includes(lower)) return FileText;
    if (['xls', 'xlsx', 'csv', 'ods'].includes(lower)) return FileSpreadsheet;
    if (['ppt', 'pptx', 'odp'].includes(lower)) return Presentation;
    if (['zip', 'tar', 'gz', 'rar', '7z'].includes(lower)) return FileArchive;
    if (['json', 'js', 'ts', 'html', 'css', 'py'].includes(lower)) return FileCode;
    return File;
  };

  const getIconColor = (ext: string) => {
    const mediaType = getMediaType(ext);
    if (mediaType === 'image') return 'text-purple-500';
    if (mediaType === 'video') return 'text-rose-500';
    if (mediaType === 'audio') return 'text-pink-500';
    
    const lower = (ext || '').toLowerCase();
    if (['doc', 'docx', 'txt', 'rtf', 'odt', 'pdf'].includes(lower)) return 'text-blue-500';
    if (['xls', 'xlsx', 'csv', 'ods'].includes(lower)) return 'text-emerald-500';
    if (['ppt', 'pptx', 'odp'].includes(lower)) return 'text-amber-500';
    if (['zip', 'tar', 'gz', 'rar', '7z'].includes(lower)) return 'text-orange-500';
    if (['json', 'js', 'ts', 'html', 'css', 'py'].includes(lower)) return 'text-cyan-500';
    return 'text-muted-foreground';
  };

  const handlePreview = (doc: SharedDocument) => {
    const mediaType = getMediaType(doc.extension);
    if (['image', 'video', 'audio', 'pdf'].includes(mediaType)) {
      setPreviewMediaDoc({ doc, mediaType });
    } else if (mediaType === 'office') {
      openDocumentEditor(doc);
    }
  };

  const openDocumentEditor = async (doc: SharedDocument) => {
    setActiveDoc(doc);
    setIsLoadingDoc(true);
    setDocError(null);

    try {
      const url = `${apiBase}/api/onlyoffice/share/folder/${token}/document/${doc.id}/config`;
      const response = await fetch(url);

      if (!response.ok) {
        throw new Error('No se pudo cargar el documento');
      }

      const data: OnlyOfficeConfigResponse = await response.json();

      const initEditor = () => {
        if (editorRef.current && typeof editorRef.current.destroyEditor === 'function') {
          editorRef.current.destroyEditor();
        }
        if (!window.DocsAPI?.DocEditor) {
          throw new Error('OnlyOffice API no disponible');
        }
        editorRef.current = new window.DocsAPI.DocEditor('shared-folder-doc-placeholder', data.config);
        setIsLoadingDoc(false);
      };

      if (!window.DocsAPI?.DocEditor) {
        const script = document.createElement('script');
        script.src = `${data.onlyoffice_url}/web-apps/apps/api/documents/api.js`;
        script.id = 'onlyoffice-api-script-folder-share';
        script.onload = () => initEditor();
        script.onerror = () => {
          setDocError('No se pudo cargar el visor de documentos');
          setIsLoadingDoc(false);
        };
        document.head.appendChild(script);
      } else {
        initEditor();
      }
    } catch (err: any) {
      console.error(err);
      setDocError(err.message || 'No se pudo abrir el documento');
      setIsLoadingDoc(false);
    }
  };

  const closeDocumentEditor = () => {
    if (editorRef.current && typeof editorRef.current.destroyEditor === 'function') {
      editorRef.current.destroyEditor();
    }
    setActiveDoc(null);
  };

  const downloadDocument = (docId: string) => {
    const downloadUrl = `${apiBase}/api/onlyoffice/share/folder/${token}/document/${docId}/download`;
    window.open(downloadUrl, '_blank');
  };

  const filteredSubfolders = (folderData?.subfolders || []).filter(sf => 
    sf.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const filteredDocuments = (folderData?.documents || []).filter(doc => 
    doc.filename.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const getDownloadUrl = (docId: string) => {
    return `${apiBase}/api/onlyoffice/share/folder/${token}/document/${docId}/download`;
  };

  return (
    <div className="min-h-screen w-full bg-background flex flex-col font-sans">
      {/* Top Header Navigation Bar */}
      <header className="border-b px-6 py-4 flex items-center justify-between bg-card/80 backdrop-blur sticky top-0 z-20">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-primary/10 rounded-2xl text-primary shadow-sm">
            <Folder className="h-6 w-6 fill-primary/20" />
          </div>
          <div>
            <h1 className="text-lg font-bold flex items-center gap-2">
              {folderData?.root_folder.name || 'Carpeta Compartida'}
              {folderData && (
                <Badge variant={folderData.can_edit ? "default" : "secondary"} className="text-xs rounded-full px-2.5">
                  {folderData.can_edit ? 'Acceso de edición' : 'Sólo lectura'}
                </Badge>
              )}
            </h1>
            <p className="text-xs text-muted-foreground">Carpeta compartida públicamente • KognitoAI</p>
          </div>
        </div>

        {/* View Mode Toggle Buttons */}
        <div className="flex items-center gap-2">
          <div className="bg-muted p-1 rounded-xl flex items-center border">
            <Button 
              variant={viewMode === 'grid' ? 'secondary' : 'ghost'} 
              size="sm" 
              className="h-7 w-7 p-0 rounded-lg"
              onClick={() => setViewMode('grid')}
              title="Vista en Cuadrícula"
            >
              <LayoutGrid className="h-4 w-4" />
            </Button>
            <Button 
              variant={viewMode === 'list' ? 'secondary' : 'ghost'} 
              size="sm" 
              className="h-7 w-7 p-0 rounded-lg"
              onClick={() => setViewMode('list')}
              title="Vista en Lista"
            >
              <List className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-6 flex flex-col gap-6">
        {isLoading ? (
          <div className="flex-1 flex flex-col items-center justify-center py-24 text-muted-foreground gap-4">
            <Loader2 className="h-10 w-10 animate-spin text-primary" />
            <p className="text-sm font-medium animate-pulse">Cargando contenido de la carpeta...</p>
          </div>
        ) : error ? (
          <div className="flex-1 flex flex-col items-center justify-center py-24 text-destructive gap-3 text-center">
            <div className="p-3 bg-destructive/10 rounded-2xl">
              <X className="h-8 w-8 text-destructive" />
            </div>
            <h2 className="text-lg font-bold">No se pudo acceder a la carpeta</h2>
            <p className="text-sm text-muted-foreground max-w-md">{error}</p>
          </div>
        ) : folderData && (
          <>
            {/* Breadcrumbs Navigation & Search Filter */}
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 bg-muted/20 p-3 rounded-2xl border border-border/50">
              <div className="flex items-center gap-1 text-sm flex-wrap">
                {folderData.breadcrumbs.map((crumb, idx) => {
                  const isLast = idx === folderData.breadcrumbs.length - 1;
                  return (
                    <div key={crumb.id} className="flex items-center gap-1">
                      {idx > 0 && <ChevronRight className="h-4 w-4 text-muted-foreground" />}
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setCurrentSubfolderId(crumb.id === folderData.root_folder.id ? null : crumb.id)}
                        className={`h-8 px-2 rounded-xl text-sm ${isLast ? 'text-foreground font-semibold bg-muted/50' : 'text-muted-foreground hover:text-foreground'}`}
                      >
                        {crumb.name}
                      </Button>
                    </div>
                  );
                })}
              </div>

              {/* Search Bar */}
              <div className="relative w-full sm:w-72">
                <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  type="text"
                  placeholder="Buscar en la carpeta..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9 h-9 text-sm rounded-xl bg-background border-border/60"
                />
              </div>
            </div>

            {/* Grid View Mode */}
            {viewMode === 'grid' ? (
              <div className="flex flex-col space-y-8 pb-12">
                {/* Subfolders Section */}
                {filteredSubfolders.length > 0 && (
                  <div className="space-y-4">
                    <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider pl-1">Carpetas</h2>
                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6 gap-4">
                      {filteredSubfolders.map((sf) => (
                        <Card 
                          key={`folder-${sf.id}`}
                          onClick={() => setCurrentSubfolderId(sf.id)}
                          className="group relative flex flex-col h-64 overflow-hidden transition-all duration-200 hover:bg-muted/60 cursor-pointer rounded-2xl border bg-card border-border/60 shadow-sm hover:shadow-md"
                        >
                          {/* Folder Top Preview Area */}
                          <div className="flex-1 flex items-center justify-center p-6 border-b border-border/40 bg-muted/30">
                            <div className="p-4 rounded-3xl bg-background shadow-sm text-amber-500 transition-transform group-hover:scale-110 duration-500">
                              <Folder className="h-14 w-14 fill-amber-500/20" />
                            </div>
                          </div>

                          {/* Folder Info Area */}
                          <div className="p-4 bg-card h-24 flex flex-col justify-center">
                            <div className="flex items-center gap-2 mb-1">
                              <Folder className="h-4 w-4 shrink-0 text-amber-500" />
                              <h3 className="font-medium text-sm leading-tight truncate text-foreground" title={sf.name}>
                                {sf.name}
                              </h3>
                            </div>
                            <div className="flex items-center justify-between mt-1">
                              <span className="text-[11px] text-muted-foreground flex items-center gap-1">
                                <Folder className="h-3 w-3" /> Carpeta
                              </span>
                              <ChevronRight className="h-4 w-4 text-muted-foreground group-hover:translate-x-1 transition-transform" />
                            </div>
                          </div>
                        </Card>
                      ))}
                    </div>
                  </div>
                )}

                {/* Documents / Files Section */}
                {filteredDocuments.length > 0 && (
                  <div className="space-y-4">
                    <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider pl-1">Archivos</h2>
                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6 gap-5">
                      {filteredDocuments.map((doc) => {
                        const mediaType = getMediaType(doc.extension);
                        const downloadUrl = getDownloadUrl(doc.id);

                        return (
                          <Card 
                            key={`doc-${doc.id}`}
                            onClick={() => handlePreview(doc)}
                            className="group relative flex flex-col h-64 overflow-hidden transition-all duration-200 cursor-pointer rounded-2xl border bg-card border-border/60 hover:bg-muted/20 shadow-sm hover:shadow-md"
                          >
                            {/* File Top Preview Area */}
                            <div className="flex-1 bg-muted/30 flex items-center justify-center border-b border-border/40 relative overflow-hidden">
                              {mediaType === 'image' ? (
                                // eslint-disable-next-line @next/next/no-img-element
                                <img 
                                  src={downloadUrl} 
                                  alt={doc.filename} 
                                  className="object-cover w-full h-full transition-transform group-hover:scale-105 duration-500"
                                  loading="lazy"
                                />
                              ) : mediaType === 'video' ? (
                                <div className="relative w-full h-full flex items-center justify-center bg-black/80">
                                  <video 
                                    src={downloadUrl} 
                                    className="object-cover w-full h-full opacity-70"
                                    muted 
                                  />
                                  <div className="absolute p-3 rounded-full bg-background/80 backdrop-blur shadow-lg group-hover:scale-110 transition-transform">
                                    <Play className="h-6 w-6 text-primary fill-current" />
                                  </div>
                                </div>
                              ) : (
                                <div className={`p-4 rounded-3xl bg-background shadow-sm ${getIconColor(doc.extension)} transition-transform group-hover:scale-110 duration-500`}>
                                  {React.createElement(getFileIcon(doc.extension), { className: "h-14 w-14" })}
                                </div>
                              )}
                            </div>

                            {/* File Info Area */}
                            <div className="p-4 bg-card h-24 flex flex-col justify-center">
                              <div className="flex items-center gap-2 mb-1">
                                {React.createElement(getFileIcon(doc.extension), { className: `h-4 w-4 shrink-0 ${getIconColor(doc.extension)}` })}
                                <h3 className="font-medium text-sm leading-tight truncate text-foreground" title={doc.filename}>
                                  {doc.filename}
                                </h3>
                              </div>
                              <div className="flex items-center justify-between mt-1">
                                <span className="text-[11px] text-muted-foreground uppercase font-mono bg-muted px-1.5 py-0.5 rounded">
                                  {doc.extension}
                                </span>
                                {doc.updated_at && (
                                  <span className="text-[10px] text-muted-foreground">
                                    {new Date(doc.updated_at).toLocaleDateString()}
                                  </span>
                                )}
                              </div>
                            </div>
                          </Card>
                        );
                      })}
                    </div>
                  </div>
                )}

                {filteredSubfolders.length === 0 && filteredDocuments.length === 0 && (
                  <div className="p-16 text-center border border-dashed rounded-3xl text-muted-foreground bg-muted/10 my-8">
                    <File className="h-12 w-12 mx-auto mb-3 opacity-40" />
                    <p className="text-base font-medium">Esta carpeta está vacía</p>
                  </div>
                )}
              </div>
            ) : (
              /* List View Mode */
              <div className="rounded-2xl border border-border/60 bg-card overflow-hidden shadow-sm">
                {/* List Header */}
                <div className="grid grid-cols-12 gap-4 px-4 py-3 bg-muted/40 text-xs font-semibold text-muted-foreground uppercase tracking-wider border-b">
                  <div className="col-span-7 md:col-span-6">Nombre</div>
                  <div className="col-span-3 hidden md:flex items-center">Tipo</div>
                  <div className="col-span-4 md:col-span-2 text-right">Acciones</div>
                </div>

                {/* Subfolders rows */}
                {filteredSubfolders.map((sf) => (
                  <div 
                    key={`sf-list-${sf.id}`}
                    onClick={() => setCurrentSubfolderId(sf.id)}
                    className="grid grid-cols-12 gap-4 px-4 py-3 items-center border-b border-border/40 hover:bg-muted/40 transition-colors cursor-pointer text-sm"
                  >
                    <div className="col-span-7 md:col-span-6 flex items-center gap-3 min-w-0">
                      <div className="p-2 bg-amber-500/10 text-amber-500 rounded-xl">
                        <Folder className="h-5 w-5 fill-amber-500/20" />
                      </div>
                      <span className="font-medium truncate">{sf.name}</span>
                    </div>
                    <div className="col-span-3 hidden md:flex items-center text-xs text-muted-foreground">
                      Carpeta
                    </div>
                    <div className="col-span-5 md:col-span-3 flex items-center justify-end gap-2">
                      <ChevronRight className="h-4 w-4 text-muted-foreground" />
                    </div>
                  </div>
                ))}

                {/* Documents rows */}
                {filteredDocuments.map((doc) => {
                  const mediaType = getMediaType(doc.extension);
                  return (
                    <div 
                      key={`doc-list-${doc.id}`}
                      onClick={() => handlePreview(doc)}
                      className="grid grid-cols-12 gap-4 px-4 py-3 items-center border-b border-border/40 hover:bg-muted/40 transition-colors cursor-pointer text-sm"
                    >
                      <div className="col-span-7 md:col-span-6 flex items-center gap-3 min-w-0">
                        <div className={`p-2 rounded-xl bg-muted ${getIconColor(doc.extension)}`}>
                          {React.createElement(getFileIcon(doc.extension), { className: "h-5 w-5" })}
                        </div>
                        <span className="font-medium truncate">{doc.filename}</span>
                      </div>
                      <div className="col-span-3 hidden md:flex items-center text-xs text-muted-foreground uppercase font-mono">
                        {doc.extension}
                      </div>
                      <div className="col-span-5 md:col-span-3 flex items-center justify-end gap-2" onClick={(e) => e.stopPropagation()}>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handlePreview(doc)}
                          className="h-8 px-2.5 text-xs rounded-xl"
                        >
                          {mediaType === 'video' ? (
                            <>
                              <Play className="h-3.5 w-3.5 mr-1 fill-current text-rose-500" /> Reproducir
                            </>
                          ) : mediaType === 'audio' ? (
                            <>
                              <Music className="h-3.5 w-3.5 mr-1 text-pink-500" /> Escuchar
                            </>
                          ) : (
                            <>
                              <Eye className="h-3.5 w-3.5 mr-1 text-primary" /> Ver
                            </>
                          )}
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => downloadDocument(doc.id)}
                          className="h-8 px-2.5 text-xs rounded-xl"
                        >
                          <Download className="h-3.5 w-3.5 mr-1" /> Descargar
                        </Button>
                      </div>
                    </div>
                  );
                })}

                {filteredSubfolders.length === 0 && filteredDocuments.length === 0 && (
                  <div className="p-12 text-center text-muted-foreground text-sm">
                    No hay elementos en esta carpeta
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </main>

      {/* Media Preview Modal for Videos, Images, Audio, and PDFs */}
      {previewMediaDoc && (
        <Dialog open={true} onOpenChange={() => setPreviewMediaDoc(null)}>
          <DialogContent className="max-w-4xl w-[90vw] p-0 flex flex-col overflow-hidden rounded-2xl border border-border/50 shadow-2xl">
            <DialogHeader className="p-4 border-b flex flex-row items-center justify-between space-y-0 bg-card">
              <DialogTitle className="text-sm font-medium flex items-center gap-2">
                {React.createElement(getFileIcon(previewMediaDoc.doc.extension), { className: `h-5 w-5 ${getIconColor(previewMediaDoc.doc.extension)}` })}
                <span className="truncate max-w-md">{previewMediaDoc.doc.filename}</span>
              </DialogTitle>
              <div className="flex items-center gap-2 pr-8">
                <Button variant="outline" size="sm" onClick={() => downloadDocument(previewMediaDoc.doc.id)} className="rounded-xl">
                  <Download className="h-3.5 w-3.5 mr-1.5" /> Descargar
                </Button>
              </div>
            </DialogHeader>

            <div className="p-6 bg-black/95 flex items-center justify-center min-h-[50vh] max-h-[80vh]">
              {previewMediaDoc.mediaType === 'image' && (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={getDownloadUrl(previewMediaDoc.doc.id)}
                  alt={previewMediaDoc.doc.filename}
                  className="max-h-[75vh] max-w-full object-contain rounded-xl shadow-2xl"
                />
              )}

              {previewMediaDoc.mediaType === 'video' && (
                <video
                  src={getDownloadUrl(previewMediaDoc.doc.id)}
                  controls
                  autoPlay
                  className="max-h-[75vh] max-w-full rounded-xl shadow-2xl"
                />
              )}

              {previewMediaDoc.mediaType === 'audio' && (
                <div className="p-10 text-center flex flex-col items-center gap-6 w-full max-w-md">
                  <div className="p-4 bg-primary/20 text-primary rounded-full animate-pulse">
                    <Music className="h-12 w-12" />
                  </div>
                  <p className="text-white text-sm font-medium">{previewMediaDoc.doc.filename}</p>
                  <audio
                    src={getDownloadUrl(previewMediaDoc.doc.id)}
                    controls
                    autoPlay
                    className="w-full"
                  />
                </div>
              )}

              {previewMediaDoc.mediaType === 'pdf' && (
                <iframe
                  src={getDownloadUrl(previewMediaDoc.doc.id)}
                  className="w-full h-[75vh] rounded-xl bg-white"
                />
              )}
            </div>
          </DialogContent>
        </Dialog>
      )}

      {/* Fullscreen Modal for OnlyOffice Document Viewer/Editor */}
      {activeDoc && (
        <Dialog open={true} onOpenChange={() => closeDocumentEditor()}>
          <DialogContent className="max-w-6xl w-[95vw] h-[90vh] p-0 flex flex-col overflow-hidden rounded-2xl">
            <DialogHeader className="p-4 border-b flex flex-row items-center justify-between space-y-0">
              <DialogTitle className="text-sm font-medium flex items-center gap-2">
                {React.createElement(getFileIcon(activeDoc.extension), { className: `h-5 w-5 ${getIconColor(activeDoc.extension)}` })}
                <span className="truncate max-w-md">{activeDoc.filename}</span>
              </DialogTitle>
              <div className="flex items-center gap-2 pr-8">
                <Button variant="outline" size="sm" onClick={() => downloadDocument(activeDoc.id)} className="rounded-xl">
                  <Download className="h-3.5 w-3.5 mr-1.5" /> Descargar
                </Button>
              </div>
            </DialogHeader>

            <div id="shared-folder-doc-placeholder" className="flex-1 bg-muted/20 relative">
              {isLoadingDoc && (
                <div className="absolute inset-0 flex items-center justify-center gap-3 text-muted-foreground bg-background/80 z-10">
                  <Loader2 className="h-6 w-6 animate-spin text-primary" />
                  <span>Cargando documento...</span>
                </div>
              )}
              {docError && (
                <div className="absolute inset-0 flex items-center justify-center text-sm text-destructive p-4 text-center">
                  {docError}
                </div>
              )}
            </div>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}
