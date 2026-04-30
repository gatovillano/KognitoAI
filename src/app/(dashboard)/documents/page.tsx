'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import apiClient from '@/lib/api';
import { toast } from 'sonner';
import { 
  Plus, 
  FileText, 
  Trash2, 
  Edit3, 
  X, 
  Loader2, 
  Search, 
  FileBox, 
  Download, 
  Calendar,
  MoreVertical,
  MoreHorizontal,
  ChevronDown,
  ChevronRight,
  ArrowLeft,
  Briefcase,
  Layers,
  Info,
  Bot,
  Folder,
  Save,
  ExternalLink
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { 
  DropdownMenu, 
  DropdownMenuContent, 
  DropdownMenuItem, 
  DropdownMenuTrigger 
} from '@/components/ui/dropdown-menu';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface OnlyOfficeDoc {
  id: string;
  filename: string;
  extension: string;
  updated_at: string;
  created_at: string;
  workspace_id?: string | null;
  workspace_name?: string | null;
  workspace_color?: string | null;
  folder_id?: string | null;
}

interface OnlyOfficeFolder {
  id: string;
  name: string;
  parent_id: string | null;
  workspace_id: string | null;
  workspace_name?: string | null;
  workspace_color?: string | null;
  created_at: string;
}

interface Workspace {
  id: string;
  name: string;
  color?: string;
}

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<OnlyOfficeDoc[]>([]);
  const [folders, setFolders] = useState<OnlyOfficeFolder[]>([]);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [currentFolderId, setCurrentFolderId] = useState<string | null>(null);
  const [currentWorkspaceId, setCurrentWorkspaceId] = useState<string | null>(null);
  const [folderPath, setFolderPath] = useState<OnlyOfficeFolder[]>([]);
  
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [editingDoc, setEditingDoc] = useState<OnlyOfficeDoc | null>(null);
  const [isOpeningEditor, setIsOpeningEditor] = useState(false);
  
  const [isMoveDialogOpen, setIsMoveDialogOpen] = useState(false);
  const [itemToMove, setItemToMove] = useState<{id: string, name: string, type: 'doc' | 'folder'} | null>(null);
  const [isMoving, setIsMoving] = useState(false);
  const [selectedWorkspaceForMove, setSelectedWorkspaceForMove] = useState<string | null>(null);
  
  const [isCreateFolderOpen, setIsCreateFolderOpen] = useState(false);
  const [newFolderName, setNewFolderName] = useState('');
  const [draggingItem, setDraggingItem] = useState<{id: string, type: 'doc' | 'folder'} | null>(null);
  
  const [isCreateDocOpen, setIsCreateDocOpen] = useState(false);
  const [newDocType, setNewDocType] = useState<'word' | 'excel' | 'powerpoint'>('word');
  const [newDocName, setNewDocName] = useState('Nuevo documento');
  const [isCreatingDoc, setIsCreatingDoc] = useState(false);
  
  const searchParams = useSearchParams();
  const router = useRouter();
  const editorRef = useRef<any>(null);
  const [hasMounted, setHasMounted] = useState(false);

  useEffect(() => {
    setHasMounted(true);
  }, []);

  const fetchWorkspaces = async () => {
    try {
      const response = await apiClient.get('/api/workspaces');
      // The backend returns a PaginatedWorkspacesResponse object with a 'workspaces' array
      setWorkspaces(Array.isArray(response.data) ? response.data : response.data.workspaces || []);
    } catch (error) {
      console.error('Error fetching workspaces:', error);
      setWorkspaces([]);
    }
  };

  const fetchFolders = async () => {
    try {
      const params: any = {};
      params.parent_id = currentFolderId || "null";
      if (currentWorkspaceId) params.workspace_id = currentWorkspaceId;
      
      const response = await apiClient.get('/api/onlyoffice/folders', { params });
      setFolders(response.data);
    } catch (error) {
      console.error('Error fetching folders:', error);
    }
  };

  const fetchDocuments = async () => {
    setIsLoading(true);
    try {
      const params: any = {};
      params.folder_id = currentFolderId || "null";
      if (currentWorkspaceId) params.workspace_id = currentWorkspaceId;
      
      const response = await apiClient.get('/api/onlyoffice/list', { params });
      setDocuments(response.data);
    } catch (error) {
      console.error('Error fetching documents:', error);
      toast.error('Error al cargar la lista de documentos');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (hasMounted) {
      fetchWorkspaces();
    }
  }, [hasMounted]);

  useEffect(() => {
    if (hasMounted) {
      fetchFolders();
      fetchDocuments();
    }
  }, [currentFolderId, currentWorkspaceId, hasMounted]);

  useEffect(() => {
    if (!hasMounted) return;
    const openId = searchParams?.get('open');
    if (openId && documents.length > 0) {
      const doc = documents.find(d => d.id === openId);
      if (doc) {
        openEditor(doc);
        // Clear param to avoid reopening
        const newUrl = window.location.pathname;
        router.replace(newUrl);
      }
    }
  }, [searchParams, documents, hasMounted]);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files?.[0]) return;
    
    const file = e.target.files[0];
    const formData = new FormData();
    formData.append('file', file);
    if (currentWorkspaceId) formData.append('workspace_id', currentWorkspaceId);
    if (currentFolderId) formData.append('folder_id', currentFolderId);

    const toastId = toast.loading(`Subiendo ${file.name}...`);
    
    try {
      await apiClient.post('/api/onlyoffice/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      toast.success('Documento subido correctamente', { id: toastId });
      fetchDocuments();
    } catch (error: any) {
      const detail = error.response?.data?.detail || 'Error al subir el documento';
      toast.error(detail, { id: toastId });
    }
    
    // Reset input
    e.target.value = '';
  };

  const handleCreateFolder = async () => {
    if (!newFolderName.trim()) return;
    
    try {
      const formData = new FormData();
      formData.append('name', newFolderName);
      if (currentFolderId) formData.append('parent_id', currentFolderId);
      if (currentWorkspaceId) formData.append('workspace_id', currentWorkspaceId);
      
      await apiClient.post('/api/onlyoffice/folders', formData);
      toast.success('Carpeta creada');
      setIsCreateFolderOpen(false);
      setNewFolderName('');
      fetchFolders();
    } catch (error) {
      toast.error('Error al crear la carpeta');
    }
  };

  const handleCreateDocument = async () => {
    if (!newDocName.trim()) return;
    
    setIsCreatingDoc(true);
    try {
      const formData = new FormData();
      formData.append('type', newDocType);
      formData.append('name', newDocName);
      if (currentFolderId) formData.append('folder_id', currentFolderId);
      if (currentWorkspaceId) formData.append('workspace_id', currentWorkspaceId);
      
      const response = await apiClient.post('/api/onlyoffice/create', formData);
      toast.success('Documento creado correctamente');
      setIsCreateDocOpen(false);
      setNewDocName('Nuevo documento');
      fetchDocuments();
    } catch (error: any) {
      const detail = error.response?.data?.detail || 'Error al crear el documento';
      toast.error(detail);
    } finally {
      setIsCreatingDoc(false);
    }
  };

  const handleMoveToWorkspace = async () => {
    if (!itemToMove || !selectedWorkspaceForMove) return;
    
    setIsMoving(true);
    try {
      const formData = new FormData();
      const wsId = selectedWorkspaceForMove === "none" ? "null" : selectedWorkspaceForMove;
      formData.append('workspace_id', wsId);
      
      // When changing workspace, move to root of that workspace to guarantee visibility
      if (wsId !== "null") {
        if (itemToMove.type === 'doc') {
          formData.append('folder_id', 'null');
        } else {
          formData.append('parent_id', 'null');
        }
      }
      
      const endpoint = itemToMove.type === 'doc' 
        ? `/api/onlyoffice/${itemToMove.id}/meta` 
        : `/api/onlyoffice/folders/${itemToMove.id}/meta`;
      
      await apiClient.post(endpoint, formData);
      toast.success('Cambio realizado correctamente');
      
      setIsMoveDialogOpen(false);
      setItemToMove(null);
      
      // Delay refresh for DB consistency
      setTimeout(() => {
        fetchDocuments();
        fetchFolders();
      }, 500);
    } catch (error) {
      console.error('Error at handleMoveToWorkspace:', error);
      toast.error('Error al mover el ítem');
    } finally {
      setIsMoving(false);
    }
  };

  const handleDropToFolder = async (itemId: string, folderId: string, type: 'doc' | 'folder') => {
    if (type === 'folder' && itemId === folderId) return;
    
    // Find the target folder to inherit its workspace
    const targetFolder = folders.find(f => f.id === folderId);
    
    try {
      const formData = new FormData();
      if (type === 'doc') {
        formData.append('folder_id', folderId);
      } else {
        formData.append('parent_id', folderId);
      }
      
      // Also sync workspace if moving to a folder
      if (targetFolder?.workspace_id) {
        formData.append('workspace_id', targetFolder.workspace_id);
      }
      
      const endpoint = type === 'doc' 
        ? `/api/onlyoffice/${itemId}/meta` 
        : `/api/onlyoffice/folders/${itemId}/meta`;
        
      console.log(`Moving ${type} ${itemId} to folder ${folderId} via ${endpoint}`);
      await apiClient.post(endpoint, formData);
      toast.success(`${type === 'doc' ? 'Documento' : 'Carpeta'} movido correctamente`);
      
      // Delay re-fetch to allow DB consistency to propagate
      setTimeout(() => {
        fetchDocuments();
        fetchFolders();
      }, 500);
    } catch (error) {
      console.error('Error at handleDropToFolder:', error);
      toast.error('Error al mover el ítem');
    } finally {
      setDraggingItem(null);
    }
  };

  const handleDelete = async (id: string, filename: string) => {
    if (!confirm(`¿Estás seguro de que deseas eliminar "${filename}"?`)) return;
    
    try {
      await apiClient.delete(`/api/onlyoffice/${id}`);
      toast.success('Documento eliminado');
      setDocuments(prev => prev.filter(d => d.id !== id));
    } catch (error) {
      toast.error('Error al eliminar el documento');
    }
  };

  const handleDeleteFolder = async (id: string, folderName: string) => {
    if (!confirm(`¿Estás seguro de que deseas eliminar la carpeta "${folderName}" y todo su contenido?`)) return;
    
    try {
      await apiClient.delete(`/api/onlyoffice/folders/${id}`);
      toast.success('Carpeta eliminada');
      setFolders(prev => prev.filter(f => f.id !== id));
    } catch (error) {
      toast.error('Error al eliminar la carpeta');
    }
  };

  const openEditor = async (doc: OnlyOfficeDoc) => {
    setIsOpeningEditor(true);
    try {
      const response = await apiClient.get(`/api/onlyoffice/config/${doc.id}`);
      const { config, onlyoffice_url } = response.data;
      
      setEditingDoc(doc);
      
      // Load OnlyOffice script if not already present
      if (!(window as any).DocsAPI) {
        const script = document.createElement('script');
        script.src = `${onlyoffice_url}/web-apps/apps/api/documents/api.js`;
        script.id = 'onlyoffice-api-script';
        script.onload = () => initEditor(config);
        document.head.appendChild(script);
      } else {
        // Unload old editor if exists
        if (editorRef.current) {
          editorRef.current.destroyEditor();
        }
        // Short delay to ensure container is ready
        setTimeout(() => initEditor(config), 100);
      }
    } catch (error) {
      toast.error('Error al iniciar el editor');
      setIsOpeningEditor(false);
    }
  };

  const initEditor = (config: any) => {
    try {
      // @ts-ignore
      editorRef.current = new window.DocsAPI.DocEditor("onlyoffice-placeholder", config);
      setIsOpeningEditor(false);
    } catch (err) {
      console.error("Editor init failed", err);
      toast.error("Error al inicializar el editor de OnlyOffice");
      setIsOpeningEditor(false);
    }
  };

  const closeEditor = () => {
    if (editorRef.current) {
      editorRef.current.destroyEditor();
      editorRef.current = null;
    }
    setEditingDoc(null);
    fetchDocuments(); // Refresh to show updated time
  };

  const navigateToFolder = (folder: OnlyOfficeFolder | null) => {
    if (folder) {
      setCurrentFolderId(folder.id);
      setFolderPath(prev => [...prev, folder]);
    } else {
      setCurrentFolderId(null);
      setFolderPath([]);
    }
  };

  const navigateBack = () => {
    if (folderPath.length > 0) {
      const newPath = [...folderPath];
      newPath.pop();
      setFolderPath(newPath);
      setCurrentFolderId(newPath.length > 0 ? newPath[newPath.length - 1].id : null);
    }
  };

  const filteredDocs = documents.filter(doc => 
    doc.filename.toLowerCase().includes(searchQuery.toLowerCase())
  );
  
  const filteredFolders = folders.filter(f => 
    f.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const getIconColor = (ext: string) => {
    switch (ext.toLowerCase()) {
      case 'docx': case 'doc': case 'txt': return 'text-blue-500 bg-blue-500/10';
      case 'xlsx': case 'xls': case 'csv': return 'text-emerald-500 bg-emerald-500/10';
      case 'pptx': case 'ppt': return 'text-orange-500 bg-orange-500/10';
      default: return 'text-slate-500 bg-slate-500/10';
    }
  };

  if (!hasMounted) return null;

  if (editingDoc) {
    return (
      <div className="fixed inset-0 z-[100] bg-background flex flex-col animate-in fade-in duration-300">
        <header className="h-12 border-b flex items-center px-4 bg-background">
          <Button variant="ghost" size="sm" onClick={closeEditor} className="gap-2 text-muted-foreground hover:text-foreground hover:bg-muted">
            <ArrowLeft className="h-4 w-4" />
            <span className="font-medium">Volver</span>
          </Button>
        </header>
        <div id="onlyoffice-placeholder" className="flex-1 bg-muted/30">
          {isOpeningEditor && (
            <div className="h-full w-full flex flex-col items-center justify-center gap-4">
              <Loader2 className="h-10 w-10 text-primary animate-spin" />
              <p className="text-muted-foreground font-medium animate-pulse">Iniciando Editor OnlyOffice...</p>
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-8 max-w-7xl mx-auto space-y-8 h-full flex flex-col">
      {/* Hero Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="space-y-2">
          <div className="flex items-center gap-3">
            <div className="h-12 w-12 rounded-2xl bg-primary/10 flex items-center justify-center">
              <FileBox className="h-7 w-7 text-primary" />
            </div>
            <div className="flex items-center gap-2">
              <h1 className="text-3xl font-extrabold tracking-tight">OnlyOffice</h1>
              <Sheet>
                <SheetTrigger asChild>
                  <Button variant="ghost" size="icon" className="h-6 w-6 rounded-full hover:bg-primary/10 text-primary/60 hover:text-primary transition-all">
                    <Info className="h-4 w-4" />
                  </Button>
                </SheetTrigger>
                <SheetContent className="w-[400px] sm:w-[540px] overflow-y-auto">
                  <SheetHeader className="pb-6 border-b">
                    <SheetTitle className="text-2xl font-bold flex items-center gap-2">
                      <FileBox className="h-6 w-6 text-primary" />
                      Sobre OnlyOffice
                    </SheetTitle>
                    <SheetDescription>
                      Gestión avanzada de documentos y colaboración inteligente.
                    </SheetDescription>
                  </SheetHeader>
                  
                  <div className="py-6 space-y-8">
                    <section className="space-y-3">
                      <h3 className="text-sm font-bold uppercase tracking-wider text-primary">¿Qué es OnlyOffice en Kognito?</h3>
                      <p className="text-sm text-muted-foreground leading-relaxed">
                        Es tu suite de ofimática privada. Aquí puedes subir, organizar y editar documentos de Word, Excel y PowerPoint sin que tus datos salgan de tu servidor.
                      </p>
                    </section>

                    <section className="space-y-3">
                      <h3 className="text-sm font-bold uppercase tracking-wider text-primary">Interacción con el Agente</h3>
                      <div className="bg-primary/5 rounded-2xl p-4 border border-primary/10 space-y-3">
                        <p className="text-xs font-medium text-primary flex items-center gap-2">
                          <Bot className="h-4 w-4" /> El Agente puede ayudarte a:
                        </p>
                        <ul className="text-xs space-y-2 text-muted-foreground list-disc pl-4">
                          <li><strong>Listar carpetas</strong> para encontrar tus archivos por ti.</li>
                          <li><strong>Buscar documentos</strong> globalmente por nombre.</li>
                          <li><strong>Leer el contenido</strong> completo de archivos Word, Excel y PPT para resumirlos o responder preguntas basadas en sus datos.</li>
                        </ul>
                      </div>
                    </section>

                    <section className="space-y-3">
                      <h3 className="text-sm font-bold uppercase tracking-wider text-primary">Jerarquía y Workspaces</h3>
                      <p className="text-sm text-muted-foreground leading-relaxed">
                        Puedes asociar carpetas enteras a un <strong>Workspace</strong>. Al hacerlo, todos los documentos internos heredarán automáticamente ese proyecto, facilitando la colaboración con tu equipo.
                      </p>
                    </section>

                    <section className="space-y-3">
                      <h3 className="text-sm font-bold uppercase tracking-wider text-primary">Formatos compatibles</h3>
                      <div className="grid grid-cols-2 gap-2 text-[11px]">
                        <div className="flex items-center gap-2 p-2 rounded-lg bg-orange-500/5 text-orange-600 border border-orange-500/10">
                          <span className="font-bold">WORD</span> .docx, .doc, .txt
                        </div>
                        <div className="flex items-center gap-2 p-2 rounded-lg bg-emerald-500/5 text-emerald-600 border border-emerald-500/10">
                          <span className="font-bold">EXCEL</span> .xlsx, .xls, .csv
                        </div>
                        <div className="flex items-center gap-2 p-2 rounded-lg bg-blue-500/5 text-blue-600 border border-blue-500/10">
                          <span className="font-bold">PPT</span> .pptx, .ppt
                        </div>
                      </div>
                    </section>
                  </div>
                </SheetContent>
              </Sheet>
            </div>
          </div>
          <p className="text-muted-foreground ml-15 max-w-lg">
            Gestión documental inteligente y edición colaborativa integrada con OnlyOffice.
          </p>
        </div>
        
        <div className="flex flex-wrap md:flex-nowrap items-center justify-between gap-4">
          {/* 1. Buscar a la izquierda - Ancho fijo en desktop, flexible en mobile */}
          <div className="relative w-full md:w-96 group">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground group-focus-within:text-primary transition-all duration-300" />
            <Input 
              placeholder="Buscar documentos..." 
              className="pl-11 h-12 rounded-2xl bg-card/60 backdrop-blur-sm border-border/40 focus:border-primary/40 focus:ring-4 focus:ring-primary/5 transition-all text-sm font-medium"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          
          {/* 2. Filtro y Acciones a la derecha - Alineados horizontalmente */}
          <div className="flex items-center gap-3 w-full md:w-auto">
            <Select 
              value={currentWorkspaceId || "all"} 
              onValueChange={(val) => setCurrentWorkspaceId(val === "all" ? null : val)}
            >
              <SelectTrigger className="w-full md:w-56 h-12 rounded-2xl border-border/40 bg-card/60 hover:bg-muted/50 transition-all font-bold">
                <Briefcase className="h-4 w-4 mr-2 text-primary" />
                <SelectValue placeholder="Workspaces" />
              </SelectTrigger>
              <SelectContent className="rounded-2xl p-2 border-primary/10 shadow-2xl">
                <SelectItem value="all" className="rounded-xl font-medium">Todos los Proyectos</SelectItem>
                {workspaces.map(ws => (
                  <SelectItem key={ws.id} value={ws.id} className="rounded-xl font-medium">
                    <div className="flex items-center gap-2">
                      <div className="h-2 w-2 rounded-full" style={{ backgroundColor: ws.color || 'var(--primary)' }} />
                      {ws.name}
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" className="gap-2 h-12 px-6 rounded-2xl border-border/40 bg-card/60 hover:bg-muted/50 transition-all font-bold group shadow-sm">
                  <MoreHorizontal className="h-4 w-4 group-hover:scale-125 transition-transform duration-300" />
                  <span className="hidden sm:inline">Acciones</span>
                  <ChevronDown className="h-4 w-4 text-muted-foreground group-hover:text-foreground group-data-[state=open]:rotate-180 transition-all duration-300" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-64 rounded-2xl p-2 shadow-2xl border-primary/10 backdrop-blur-xl">
                <DropdownMenuItem onClick={() => setIsCreateFolderOpen(true)} className="gap-3 py-3 rounded-xl cursor-pointer">
                  <div className="p-2 rounded-lg bg-orange-500/10 text-orange-600">
                    <Folder className="h-4 w-4" />
                  </div>
                  <span className="font-bold text-orange-600">Nueva Carpeta</span>
                </DropdownMenuItem>
                <div className="h-px bg-border/40 my-2" />
                <DropdownMenuItem className="gap-3 py-3 rounded-xl p-0 h-auto cursor-pointer">
                  <label htmlFor="file-upload" className="flex items-center gap-3 w-full px-3 cursor-pointer">
                    <div className="p-2 rounded-lg bg-primary/10 text-primary">
                      <Plus className="h-4 w-4" />
                    </div>
                    <span className="font-bold text-primary">Subir Archivo</span>
                  </label>
                </DropdownMenuItem>
                <div className="h-px bg-border/40 my-2" />
                <DropdownMenuItem onClick={() => setIsCreateDocOpen(true)} className="gap-3 py-3 rounded-xl cursor-pointer">
                  <div className="p-2 rounded-lg bg-green-500/10 text-green-600">
                    <FileText className="h-4 w-4" />
                  </div>
                  <span className="font-bold text-green-600">Nuevo Documento</span>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>

            <input
              type="file"
              id="file-upload"
              className="hidden"
              onChange={handleUpload}
              accept=".docx,.xlsx,.pptx,.doc,.xls,.ppt,.txt,.csv"
            />
          </div>
        </div>
      </div>

      {/* Breadcrumbs / Navigation */}
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Button 
          variant="ghost" 
          size="sm" 
          onClick={() => navigateToFolder(null)} 
          className="h-8 gap-1.5 px-2 hover:bg-primary/10 transition-colors"
          onDragOver={(e: any) => {
            e.preventDefault();
            e.currentTarget.classList.add('bg-primary/20', 'scale-110');
          }}
          onDragLeave={(e: any) => {
            e.currentTarget.classList.remove('bg-primary/20', 'scale-110');
          }}
          onDrop={(e: any) => {
            e.preventDefault();
            e.currentTarget.classList.remove('bg-primary/20', 'scale-110');
            const itemId = e.dataTransfer.getData('itemId') || draggingItem?.id;
            const itemType = (e.dataTransfer.getData('itemType') as 'doc' | 'folder') || draggingItem?.type;
            if (itemId && itemType) handleDropToFolder(itemId, 'null', itemType);
          }}
        >
          <FileBox className="h-4 w-4" />
          Inicio
        </Button>
        {folderPath.map((folder, index) => (
          <React.Fragment key={folder.id}>
            <ChevronRight className="h-4 w-4" />
            <Button 
              variant="ghost" 
              size="sm" 
              onClick={() => {
                const newPath = folderPath.slice(0, index + 1);
                setFolderPath(newPath);
                setCurrentFolderId(folder.id);
              }}
              className="h-8 px-2"
            >
              {folder.name}
            </Button>
          </React.Fragment>
        ))}
      </div>

      {isLoading ? (
        <div className="flex-1 flex flex-col items-center justify-center gap-4 py-20">
          <Loader2 className="h-12 w-12 text-primary animate-spin" />
          <p className="text-muted-foreground font-medium animate-pulse">Cargando...</p>
        </div>
      ) : (filteredDocs.length > 0 || filteredFolders.length > 0) ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          <AnimatePresence mode="popLayout">
            {/* Folders first */}
            {filteredFolders.map((folder) => (
              <motion.div 
                key={folder.id}
                layout
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95 }}
                transition={{ duration: 0.3 }}
                draggable={true}
                onDragStart={(e: any) => {
                  e.stopPropagation();
                  const data = JSON.stringify({id: folder.id, type: 'folder'});
                  e.dataTransfer.effectAllowed = "move";
                  e.dataTransfer.setData('itemId', folder.id);
                  e.dataTransfer.setData('itemType', 'folder');
                  e.dataTransfer.setData('text/plain', folder.id);
                  setDraggingItem({id: folder.id, type: 'folder'});
                  e.currentTarget.classList.add('opacity-50', 'scale-95');
                }}
                onDragEnd={(e: any) => {
                  e.currentTarget.classList.remove('opacity-50', 'scale-95');
                  setDraggingItem(null);
                }}
                className="h-full"
              >
                <Card 
                  className="group relative h-full overflow-hidden bg-orange-500/5 backdrop-blur-sm border-orange-500/20 hover:border-orange-500/40 transition-all duration-300 hover:shadow-xl cursor-grab active:cursor-grabbing rounded-3xl p-5 border"
                  onClick={() => navigateToFolder(folder)}
                  onDragOver={(e: any) => {
                    e.preventDefault();
                    e.dataTransfer.dropEffect = "move";
                    e.currentTarget.classList.add('bg-orange-500/10', 'border-orange-500/60', 'scale-105');
                  }}
                  onDragEnter={(e: any) => {
                    e.preventDefault();
                    e.currentTarget.classList.add('bg-orange-500/10', 'border-orange-500/60', 'scale-105');
                  }}
                  onDragLeave={(e: any) => {
                    e.currentTarget.classList.remove('bg-orange-500/10', 'border-orange-500/60', 'scale-105');
                  }}
                  onDrop={(e: any) => {
                    e.preventDefault();
                    e.currentTarget.classList.remove('bg-orange-500/10', 'border-orange-500/60', 'scale-105');
                    const itemId = e.dataTransfer.getData('itemId') || e.dataTransfer.getData('text/plain') || draggingItem?.id;
                    const itemType = (e.dataTransfer.getData('itemType') as 'doc' | 'folder') || draggingItem?.type;
                    console.log('Dropped at Folder:', {itemId, itemType, targetFolderId: folder.id});
                    if (itemId && itemType) handleDropToFolder(itemId, folder.id, itemType);
                  }}
                >
                  <div className="flex items-start justify-between">
                    <div className="p-4 rounded-2xl bg-orange-500/10 text-orange-600 shadow-sm transition-transform group-hover:scale-110 duration-500">
                      <Folder className="h-8 w-8 fill-current" />
                    </div>
                    
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon" className="h-8 w-8 rounded-full hover:bg-muted" onClick={(e) => e.stopPropagation()}>
                          <MoreVertical className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end" className="w-48 rounded-xl shadow-xl">
                        <DropdownMenuItem onClick={(e) => { e.stopPropagation(); navigateToFolder(folder); }} className="gap-2 cursor-pointer">
                          <ExternalLink className="h-4 w-4" />
                          <span>Abrir</span>
                        </DropdownMenuItem>
                        <DropdownMenuItem 
                          onClick={(e) => { 
                            e.stopPropagation(); 
                            setItemToMove({id: folder.id, name: folder.name, type: 'folder'});
                            setSelectedWorkspaceForMove(folder.workspace_id || "none");
                            setIsMoveDialogOpen(true);
                          }} 
                          className="gap-2 cursor-pointer"
                        >
                          <Briefcase className="h-4 w-4" />
                          <span>Asociar Workspace</span>
                        </DropdownMenuItem>
                        <div className="h-px bg-border/40 my-1" />
                        <DropdownMenuItem 
                          onClick={(e) => { e.stopPropagation(); handleDeleteFolder(folder.id, folder.name); }} 
                          className="gap-2 cursor-pointer text-destructive focus:text-destructive focus:bg-destructive/10"
                        >
                          <Trash2 className="h-4 w-4" />
                          <span>Eliminar</span>
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                  <div className="mt-4 space-y-1">
                    <h3 className="font-bold text-lg leading-tight truncate group-hover:text-orange-600 transition-colors">
                      {folder.name}
                    </h3>
                    <p className="text-[10px] text-muted-foreground">Carpeta</p>
                    {folder.workspace_name && (
                      <div className="pt-2">
                        <div
                          className="inline-flex items-center gap-1.5 text-[10px] font-bold px-2 py-0.5 rounded-full border uppercase tracking-wider w-fit"
                          style={{
                            backgroundColor: folder.workspace_color ? `${folder.workspace_color}15` : '#f3f4f620',
                            borderColor: folder.workspace_color ? `${folder.workspace_color}40` : '#88888840',
                          }}
                        >
                          <span
                            className="h-1.5 w-1.5 rounded-full"
                            style={{ backgroundColor: folder.workspace_color || '#888888' }}
                          ></span>
                          <span style={{ color: folder.workspace_color || '#374151' }}>
                            {folder.workspace_name}
                          </span>
                        </div>
                      </div>
                    )}
                  </div>
                </Card>
              </motion.div>
            ))}

            {/* Documents */}
            {filteredDocs.map((doc) => (
              <motion.div 
                key={doc.id}
                layout
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95 }}
                transition={{ duration: 0.3 }}
                draggable={true}
                onDragStart={(e: any) => {
                  e.stopPropagation();
                  e.dataTransfer.effectAllowed = "move";
                  e.dataTransfer.setData('itemId', doc.id);
                  e.dataTransfer.setData('itemType', 'doc');
                  e.dataTransfer.setData('text/plain', doc.id);
                  setDraggingItem({id: doc.id, type: 'doc'});
                  e.currentTarget.classList.add('opacity-50', 'scale-95');
                }}
                onDragEnd={(e: any) => {
                  e.currentTarget.classList.remove('opacity-50', 'scale-95');
                  setDraggingItem(null);
                }}
                className="h-full"
              >
                <Card className="group relative h-full overflow-hidden bg-card/40 backdrop-blur-sm border-border/40 hover:border-primary/30 transition-all duration-300 hover:shadow-2xl hover:shadow-primary/5 rounded-3xl p-5 border cursor-grab active:cursor-grabbing">
                  <div className="flex flex-col gap-4">
                    <div className="flex items-start justify-between">
                      <div className={`p-4 rounded-2xl shadow-sm ${getIconColor(doc.extension)} transition-transform group-hover:scale-110 duration-500`}>
                        <FileText className="h-8 w-8" />
                      </div>
                      
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon" className="h-8 w-8 rounded-full hover:bg-muted">
                            <MoreVertical className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="w-48 rounded-xl border-border/40 shadow-xl">
                          <DropdownMenuItem onClick={() => openEditor(doc)} className="gap-2 cursor-pointer py-2 px-3">
                            <Edit3 className="h-4 w-4 text-primary" />
                            <span className="font-medium">Editar Ahora</span>
                          </DropdownMenuItem>
                          <DropdownMenuItem className="gap-2 cursor-pointer py-2 px-3">
                            <Download className="h-4 w-4" />
                            <span className="font-medium">Descargar</span>
                          </DropdownMenuItem>
                          <DropdownMenuItem 
                            onClick={() => {
                              setItemToMove({id: doc.id, name: doc.filename, type: 'doc'});
                              setSelectedWorkspaceForMove(doc.workspace_id || "none");
                              setIsMoveDialogOpen(true);
                            }} 
                            className="gap-2 cursor-pointer py-2 px-3"
                          >
                            <Briefcase className="h-4 w-4" />
                            <span className="font-medium">Asociar Workspace</span>
                          </DropdownMenuItem>
                          <div className="h-px bg-border/40 my-1" />
                          <DropdownMenuItem 
                            onClick={() => handleDelete(doc.id, doc.filename)} 
                            className="gap-2 cursor-pointer py-2 px-3 text-destructive focus:text-destructive focus:bg-destructive/10"
                          >
                            <Trash2 className="h-4 w-4" />
                            <span className="font-medium">Eliminar</span>
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>

                    <div className="space-y-1">
                      <h3 className="font-bold text-lg leading-tight truncate group-hover:text-primary transition-colors" title={doc.filename}>
                        {doc.filename}
                      </h3>
                      <div className="flex items-center gap-1.5 text-xs text-muted-foreground bg-muted/50 w-fit px-2 py-0.5 rounded-full">
                        <Calendar className="h-3 w-3" />
                        <span>Actualizado {new Date(doc.updated_at).toLocaleDateString()}</span>
                      </div>
                      
                      {doc.workspace_name && (
                        <div className="pt-2">
                          <div
                            className="inline-flex items-center gap-1.5 text-[10px] font-bold px-2 py-0.5 rounded-full border uppercase tracking-wider w-fit"
                            style={{
                              backgroundColor: doc.workspace_color ? `${doc.workspace_color}15` : '#f3f4f620',
                              borderColor: doc.workspace_color ? `${doc.workspace_color}40` : '#88888840',
                            }}
                          >
                            <span
                              className="h-1.5 w-1.5 rounded-full"
                              style={{ backgroundColor: doc.workspace_color || '#888888' }}
                            ></span>
                            <span style={{ color: doc.workspace_color || '#374151' }}>
                              {doc.workspace_name}
                            </span>
                          </div>
                        </div>
                      )}
                    </div>

                    <div className="pt-2">
                      <Button 
                        onClick={() => openEditor(doc)}
                        className="w-full bg-primary/5 text-primary hover:bg-primary hover:text-primary-foreground border border-primary/10 rounded-xl font-bold transition-all group-hover:shadow-md"
                      >
                        Abir Editor
                        <ChevronRight className="h-4 w-4 ml-1 transition-transform group-hover:translate-x-1" />
                      </Button>
                    </div>
                  </div>
                </Card>
              </motion.div>
          ))}
          </AnimatePresence>
        </div>
      ) : (
        <div className="flex-1 flex flex-col items-center justify-center p-12 text-center bg-card/20 backdrop-blur-sm rounded-[3rem] border border-dashed border-border/60 animate-in fade-in zoom-in duration-500">
          <div className="h-24 w-24 bg-muted/50 rounded-full flex items-center justify-center mb-6">
            <FileText className="h-12 w-12 text-muted-foreground/30" />
          </div>
          <h3 className="text-2xl font-bold text-foreground">Sin resultados</h3>
          <p className="text-muted-foreground mt-2 max-w-sm">
            {searchQuery 
              ? `No se encontró nada que coincida con "${searchQuery}"`
              : "Esta carpeta está vacía."}
          </p>
          {searchQuery && (
             <Button variant="link" onClick={() => setSearchQuery('')} className="mt-4 text-primary font-bold">
               Limpiar búsqueda
             </Button>
          )}
        </div>
      )}

      {/* Create Folder Dialog */}
      <Dialog open={isCreateFolderOpen} onOpenChange={setIsCreateFolderOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Nueva Carpeta</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <Input
              placeholder="Nombre de la carpeta"
              value={newFolderName}
              onChange={(e) => setNewFolderName(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleCreateFolder()}
              autoFocus
            />
          </div>
          <DialogFooter className="sm:justify-end">
            <Button variant="outline" onClick={() => setIsCreateFolderOpen(false)}>
              Cancelar
            </Button>
            <Button onClick={handleCreateFolder} disabled={!newFolderName.trim()}>
              Crear Carpeta
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Create Document Dialog */}
      <Dialog open={isCreateDocOpen} onOpenChange={setIsCreateDocOpen}>
        <DialogContent className="sm:max-w-md rounded-[2rem] border-primary/10 shadow-2xl">
          <DialogHeader>
            <DialogTitle className="text-2xl font-bold flex items-center gap-3">
              <div className="p-2 rounded-xl bg-green-500/10 text-green-600">
                <FileText className="h-6 w-6" />
              </div>
              Nuevo Documento
            </DialogTitle>
          </DialogHeader>
          <div className="py-6 space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Tipo de documento</label>
              <div className="grid grid-cols-3 gap-2">
                <button
                  type="button"
                  onClick={() => setNewDocType('word')}
                  className={`p-3 rounded-xl border-2 transition-all flex flex-col items-center gap-2 ${
                    newDocType === 'word' ? 'border-blue-500 bg-blue-500/10' : 'border-border hover:border-primary/30'
                  }`}
                >
                  <FileText className="h-6 w-6 text-blue-500" />
                  <span className="text-xs font-bold">Word</span>
                </button>
                <button
                  type="button"
                  onClick={() => setNewDocType('excel')}
                  className={`p-3 rounded-xl border-2 transition-all flex flex-col items-center gap-2 ${
                    newDocType === 'excel' ? 'border-emerald-500 bg-emerald-500/10' : 'border-border hover:border-primary/30'
                  }`}
                >
                  <FileText className="h-6 w-6 text-emerald-500" />
                  <span className="text-xs font-bold">Excel</span>
                </button>
                <button
                  type="button"
                  onClick={() => setNewDocType('powerpoint')}
                  className={`p-3 rounded-xl border-2 transition-all flex flex-col items-center gap-2 ${
                    newDocType === 'powerpoint' ? 'border-orange-500 bg-orange-500/10' : 'border-border hover:border-primary/30'
                  }`}
                >
                  <FileText className="h-6 w-6 text-orange-500" />
                  <span className="text-xs font-bold">PPT</span>
                </button>
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Nombre del archivo</label>
              <Input
                placeholder="Nombre del documento"
                value={newDocName}
                onChange={(e) => setNewDocName(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleCreateDocument()}
                autoFocus
              />
            </div>
          </div>
          <DialogFooter className="sm:justify-end gap-3">
            <Button variant="ghost" onClick={() => setIsCreateDocOpen(false)} className="rounded-xl h-12 px-6">
              Cancelar
            </Button>
            <Button 
              onClick={handleCreateDocument} 
              disabled={isCreatingDoc || !newDocName.trim()}
              className="rounded-xl h-12 px-8 bg-green-600 shadow-lg shadow-green-600/20 font-bold hover:bg-green-700"
            >
              {isCreatingDoc ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Plus className="h-4 w-4 mr-2" />}
              Crear Documento
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Move to Workspace Dialog */}
      <Dialog open={isMoveDialogOpen} onOpenChange={setIsMoveDialogOpen}>
        <DialogContent className="sm:max-w-md rounded-[2rem] border-primary/10 shadow-2xl">
          <DialogHeader>
            <DialogTitle className="text-2xl font-bold flex items-center gap-3">
              <div className="p-2 rounded-xl bg-primary/10 text-primary">
                <Briefcase className="h-6 w-6" />
              </div>
              Asociar a Workspace
            </DialogTitle>
          </DialogHeader>
          <div className="py-6 space-y-4">
            <p className="text-sm text-muted-foreground">
              Selecciona un espacio de trabajo para asociar <strong>{itemToMove?.name}</strong>. Esto ayudará a organizar mejor tus archivos.
            </p>
            <Select 
              value={selectedWorkspaceForMove || "none"} 
              onValueChange={setSelectedWorkspaceForMove}
            >
              <SelectTrigger className="w-full h-12 rounded-xl">
                <SelectValue placeholder="Seleccionar Workspace" />
              </SelectTrigger>
              <SelectContent className="rounded-xl shadow-xl">
                <SelectItem value="none">Ningún Workspace (Personal)</SelectItem>
                {workspaces.map(ws => (
                  <SelectItem key={ws.id} value={ws.id}>{ws.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <DialogFooter className="sm:justify-end gap-3">
            <Button variant="ghost" onClick={() => setIsMoveDialogOpen(false)} className="rounded-xl h-12 px-6">
              Cancelar
            </Button>
            <Button 
              onClick={handleMoveToWorkspace} 
              disabled={isMoving || !selectedWorkspaceForMove}
              className="rounded-xl h-12 px-8 bg-primary shadow-lg shadow-primary/20 font-bold"
            >
              {isMoving ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Save className="h-4 w-4 mr-2" />}
              Guardar Asociación
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
