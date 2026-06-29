'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { useRouter, useSearchParams } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { CommonChat } from '@/components/CommonChat';
import { Card } from '@/components/ui/card';
import apiClient from '@/lib/api';
import { toast } from 'sonner';
import { 
  Plus, 
  Upload,
  FileText, 
  Trash2, 
  Edit3, 
  X, 
  Loader2, 
  Search, 
  FileBox, 
  Download, 
  Calendar,
  Copy,
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
  ExternalLink,
  Share2,
  MessageSquare,
  Link2,
  UserPlus,
  FolderOutput
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
  DropdownMenuTrigger,
  DropdownMenuSeparator
} from '@/components/ui/dropdown-menu';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Checkbox } from '@/components/ui/checkbox';
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
  is_owner?: boolean;
}

interface ShareUserSuggestion {
  account_id: string;
  name?: string | null;
  username?: string | null;
  email?: string | null;
}

interface DocumentShareLink {
  id: string;
  scope: 'public' | 'private';
  can_edit: boolean;
  token?: string | null;
  share_url?: string | null;
  target_account_id?: string | null;
  target_email?: string | null;
  target_username?: string | null;
  target_name?: string | null;
  created_at?: string | null;
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
  const [isMoveItemDialogOpen, setIsMoveItemDialogOpen] = useState(false);
  const [itemToMove, setItemToMove] = useState<{id: string, name: string, type: 'doc' | 'folder'} | null>(null);
  const [isMoving, setIsMoving] = useState(false);
  const [selectedWorkspaceForMove, setSelectedWorkspaceForMove] = useState<string | null>(null);
  const [selectedTargetFolderForMove, setSelectedTargetFolderForMove] = useState<string>("null");
  const [allFolders, setAllFolders] = useState<OnlyOfficeFolder[]>([]);
  
  const [isRenameDialogOpen, setIsRenameDialogOpen] = useState(false);
  const [itemToRename, setItemToRename] = useState<{id: string, name: string, type: 'doc' | 'folder'} | null>(null);
  const [newName, setNewName] = useState('');
  const [isRenaming, setIsRenaming] = useState(false);
  
  const [isCreateFolderOpen, setIsCreateFolderOpen] = useState(false);
  const [newFolderName, setNewFolderName] = useState('');
  const [draggingItem, setDraggingItem] = useState<{id: string, type: 'doc' | 'folder'} | null>(null);
  
  const [isCreateDocOpen, setIsCreateDocOpen] = useState(false);
  const [newDocType, setNewDocType] = useState<'word' | 'excel' | 'powerpoint'>('word');
  const [newDocName, setNewDocName] = useState('Nuevo documento');
  const [isCreatingDoc, setIsCreatingDoc] = useState(false);

  const [isShareDialogOpen, setIsShareDialogOpen] = useState(false);
  const [shareTargetDoc, setShareTargetDoc] = useState<OnlyOfficeDoc | null>(null);
  const [shareLinks, setShareLinks] = useState<DocumentShareLink[]>([]);
  const [isLoadingShareLinks, setIsLoadingShareLinks] = useState(false);
  const [isCreatingShare, setIsCreatingShare] = useState(false);
  const [isPreparingDocChat, setIsPreparingDocChat] = useState(false);
  const [privateSearch, setPrivateSearch] = useState('');
  const [privateSuggestions, setPrivateSuggestions] = useState<ShareUserSuggestion[]>([]);
  const [selectedPrivateUser, setSelectedPrivateUser] = useState<ShareUserSuggestion | null>(null);
  const [shareCanEdit, setShareCanEdit] = useState(true);
  const [isChatSidebarOpen, setIsChatSidebarOpen] = useState(false);
  const [currentChatThreadId, setCurrentChatThreadId] = useState<string | null>(null);
  const [sidebarWidth, setSidebarWidth] = useState(450);
  const [isDraggingSidebar, setIsDraggingSidebar] = useState(false);
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [sortBy, setSortBy] = useState<'name' | 'date'>('name');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');
  const [selectedDocs, setSelectedDocs] = useState<string[]>([]);
  const [selectedFolders, setSelectedFolders] = useState<string[]>([]);
  const [lastSelected, setLastSelected] = useState<{id: string, type: 'doc' | 'folder'} | null>(null);
  const [bulkDeleteConfirmOpen, setBulkDeleteConfirmOpen] = useState(false);
  
  const searchParams = useSearchParams();
  const router = useRouter();
  const editorRef = useRef<any>(null);
  const [hasMounted, setHasMounted] = useState(false);

  useEffect(() => {
    setHasMounted(true);
  }, []);

  useEffect(() => {
    if (!isDraggingSidebar) return;
    const handleMouseMove = (e: MouseEvent) => {
      const newWidth = document.body.clientWidth - e.clientX;
      if (newWidth > 300 && newWidth < Math.min(1000, document.body.clientWidth * 0.8)) {
        setSidebarWidth(newWidth);
      }
    };
    const handleMouseUp = () => setIsDraggingSidebar(false);

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
    document.body.style.userSelect = 'none';
    
    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.userSelect = '';
    };
  }, [isDraggingSidebar]);

  const fetchWorkspaces = async () => {
    try {
      const pageSize = 100;
      let skip = 0;
      let total = Infinity;
      const allWorkspaces: Workspace[] = [];

      while (skip < total) {
        const response = await apiClient.get('/api/workspaces', {
          params: { skip, limit: pageSize },
        });

        const payload = response.data;
        const pageItems: Workspace[] = Array.isArray(payload) ? payload : payload.workspaces || [];
        const payloadTotal = Array.isArray(payload) ? pageItems.length : Number(payload.total ?? pageItems.length);

        allWorkspaces.push(...pageItems);
        total = payloadTotal;

        if (pageItems.length < pageSize) {
          break;
        }

        skip += pageSize;
      }

      setWorkspaces(allWorkspaces);
    } catch (error) {
      console.error('Error fetching workspaces:', error);
      setWorkspaces([]);
    }
  };

  const fetchFolders = useCallback(async () => {
    try {
      const params: any = {};
      params.parent_id = currentFolderId || "null";
      if (currentWorkspaceId) params.workspace_id = currentWorkspaceId;
      
      const response = await apiClient.get('/api/onlyoffice/folders', { params });
      setFolders(response.data);
    } catch (error) {
      console.error('Error fetching folders:', error);
    }
  }, [currentFolderId, currentWorkspaceId]);

  const fetchAllFolders = async () => {
    try {
      const response = await apiClient.get('/api/onlyoffice/folders');
      setAllFolders(response.data);
    } catch (error) {
      console.error('Error fetching all folders:', error);
    }
  };

  const fetchDocuments = useCallback(async () => {
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
  }, [currentFolderId, currentWorkspaceId]);

  useEffect(() => {
    if (hasMounted) {
      fetchWorkspaces();
    }
  }, [hasMounted]);

  useEffect(() => {
    setSelectedDocs([]);
    setSelectedFolders([]);
    if (hasMounted) {
      fetchFolders();
      fetchDocuments();
    }
  }, [currentFolderId, currentWorkspaceId, hasMounted, fetchFolders, fetchDocuments]);

  const handleSelection = (id: string, type: 'doc' | 'folder', e?: React.MouseEvent | React.ChangeEvent) => {
    if (e && 'stopPropagation' in e) e.stopPropagation();
    
    const isShiftPressed = e && 'nativeEvent' in e && (e.nativeEvent as any).shiftKey;
    
    if (isShiftPressed && lastSelected) {
      const allItems = [
        ...filteredFolders.map(f => ({ id: f.id, type: 'folder' as const })),
        ...filteredDocs.map(d => ({ id: d.id, type: 'doc' as const }))
      ];
      
      const currentIndex = allItems.findIndex(item => item.id === id && item.type === type);
      const lastIndex = allItems.findIndex(item => item.id === lastSelected.id && item.type === lastSelected.type);
      
      if (currentIndex !== -1 && lastIndex !== -1) {
        const start = Math.min(currentIndex, lastIndex);
        const end = Math.max(currentIndex, lastIndex);
        const range = allItems.slice(start, end + 1);
        
        const newSelectedDocs = new Set(selectedDocs);
        const newSelectedFolders = new Set(selectedFolders);
        
        range.forEach(item => {
          if (item.type === 'doc') newSelectedDocs.add(item.id);
          else newSelectedFolders.add(item.id);
        });
        
        setSelectedDocs(Array.from(newSelectedDocs));
        setSelectedFolders(Array.from(newSelectedFolders));
        return;
      }
    }

    if (type === 'doc') {
      setSelectedDocs(prev => {
        const next = prev.includes(id) ? prev.filter(d => d !== id) : [...prev, id];
        if (next.includes(id)) setLastSelected({ id, type: 'doc' });
        return next;
      });
    } else {
      setSelectedFolders(prev => {
        const next = prev.includes(id) ? prev.filter(f => f !== id) : [...prev, id];
        if (next.includes(id)) setLastSelected({ id, type: 'folder' });
        return next;
      });
    }
  };

  const toggleDocSelection = (id: string, e?: React.MouseEvent | React.ChangeEvent) => handleSelection(id, 'doc', e);
  const toggleFolderSelection = (id: string, e?: React.MouseEvent | React.ChangeEvent) => handleSelection(id, 'folder', e);

  const selectAll = () => {
    setSelectedFolders(filteredFolders.map(f => f.id));
    setSelectedDocs(filteredDocs.map(d => d.id));
  };

  const deselectAll = () => {
    setSelectedFolders([]);
    setSelectedDocs([]);
  };

  const handleBulkDelete = async () => {
    const count = selectedDocs.length + selectedFolders.length;
    if (!count) return;
    
    try {
      if (selectedFolders.length > 0) {
        await Promise.all(selectedFolders.map(id => apiClient.delete(`/api/onlyoffice/folders/${id}`)));
      }
      if (selectedDocs.length > 0) {
        await Promise.all(selectedDocs.map(id => apiClient.delete(`/api/onlyoffice/${id}`)));
      }
      
      toast.success(`${count} elemento(s) eliminado(s) correctamente`);
      setSelectedDocs([]);
      setSelectedFolders([]);
      setBulkDeleteConfirmOpen(false);
      fetchFolders();
      fetchDocuments();
    } catch (error) {
      console.error('Error during bulk delete:', error);
      toast.error('Ocurrió un error al intentar eliminar algunos elementos.');
      setBulkDeleteConfirmOpen(false);
      fetchFolders();
      fetchDocuments();
    }
  };



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

  const handleRename = async () => {
    if (!itemToRename || !newName.trim()) return;
    
    setIsRenaming(true);
    try {
      const formData = new FormData();
      if (itemToRename.type === 'doc') {
        formData.append('filename', newName);
      } else {
        formData.append('name', newName);
      }
      
      const endpoint = itemToRename.type === 'doc' 
        ? `/api/onlyoffice/${itemToRename.id}/meta` 
        : `/api/onlyoffice/folders/${itemToRename.id}/meta`;
      
      await apiClient.post(endpoint, formData);
      toast.success('Nombre actualizado correctamente');
      setIsRenameDialogOpen(false);
      setItemToRename(null);
      
      setTimeout(() => {
        fetchDocuments();
        fetchFolders();
      }, 500);
    } catch (error) {
      toast.error('Error al renombrar');
    } finally {
      setIsRenaming(false);
    }
  };

  const handleMoveToWorkspace = async () => {
    if (!itemToMove || !selectedWorkspaceForMove) return;
    
    setIsMoving(true);
    try {
      const formData = new FormData();
      const wsId = selectedWorkspaceForMove === "none" ? "null" : selectedWorkspaceForMove;
      formData.append('workspace_id', wsId);
      
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

  const handleBulkMove = async () => {
    const itemsToMove = [
      ...selectedDocs.map(id => ({ id, type: 'doc' as const })),
      ...selectedFolders.map(id => ({ id, type: 'folder' as const }))
    ];
    if (itemsToMove.length === 0) return;
    
    setIsMoving(true);
    try {
      await Promise.all(itemsToMove.map(async (item) => {
        const formData = new FormData();
        if (item.type === 'doc') {
          formData.append('folder_id', selectedTargetFolderForMove === "null" ? "null" : selectedTargetFolderForMove);
        } else {
          formData.append('parent_id', selectedTargetFolderForMove === "null" ? "null" : selectedTargetFolderForMove);
        }
        
        const endpoint = item.type === 'doc' 
          ? `/api/onlyoffice/${item.id}/meta` 
          : `/api/onlyoffice/folders/${item.id}/meta`;
          
        await apiClient.post(endpoint, formData);
      }));

      toast.success('Elementos movidos correctamente');
      setIsMoveItemDialogOpen(false);
      setSelectedDocs([]);
      setSelectedFolders([]);
      fetchDocuments();
      fetchFolders();
    } catch (error) {
      console.error('Bulk move error:', error);
      toast.error('Error al mover elementos');
    } finally {
      setIsMoving(false);
    }
  };

  const handleDropToFolder = async (itemId: string, folderId: string, type: 'doc' | 'folder') => {
    const isDocSelected = type === 'doc' && selectedDocs.includes(itemId);
    const isFolderSelected = type === 'folder' && selectedFolders.includes(itemId);
    
    const itemsToMove: { id: string, type: 'doc' | 'folder' }[] = [];
    if (isDocSelected || isFolderSelected) {
      selectedDocs.forEach(id => itemsToMove.push({ id, type: 'doc' }));
      selectedFolders.forEach(id => itemsToMove.push({ id, type: 'folder' }));
    } else {
      itemsToMove.push({ id: itemId, type });
    }
    
    const targetFolder = folders.find(f => f.id === folderId);
    
    try {
      await Promise.all(itemsToMove.map(async (item) => {
        if (item.type === 'folder' && item.id === folderId) return;
        
        const formData = new FormData();
        if (item.type === 'doc') {
          formData.append('folder_id', folderId);
        } else {
          formData.append('parent_id', folderId);
        }
        
        if (targetFolder?.workspace_id) {
          formData.append('workspace_id', targetFolder.workspace_id);
        }
        
        const endpoint = item.type === 'doc' 
          ? `/api/onlyoffice/${item.id}/meta` 
          : `/api/onlyoffice/folders/${item.id}/meta`;
          
        await apiClient.post(endpoint, formData);
      }));

      toast.success(`${itemsToMove.length > 1 ? 'Ítems movidos' : (type === 'doc' ? 'Documento movido' : 'Carpeta movida')} correctamente`);
      
      setSelectedDocs([]);
      setSelectedFolders([]);

      setTimeout(() => {
        fetchDocuments();
        fetchFolders();
      }, 500);
    } catch (error) {
      console.error('Error at handleDropToFolder:', error);
      toast.error('Error al mover los ítems');
    } finally {
      setDraggingItem(null);
    }
  };

  const handleDuplicate = async (doc: OnlyOfficeDoc) => {
    try {
      const response = await apiClient.post(`/api/onlyoffice/${doc.id}/duplicate`);
      toast.success(`Documento "${doc.filename}" duplicado correctamente`);
      fetchDocuments();
    } catch (error) {
      toast.error('Error al duplicar el documento');
    }
  };

  const handleVectorize = async (doc: OnlyOfficeDoc) => {
    const toastId = toast.loading(`Vectorizando e indexando "${doc.filename}"...`);
    try {
      await apiClient.post(`/api/onlyoffice/${doc.id}/vectorize`);
      toast.success(`Documento "${doc.filename}" indexado correctamente para el RAG`, { id: toastId });
    } catch (error: any) {
      const errorMessage = error?.response?.data?.detail || 'Error al vectorizar el documento';
      toast.error(errorMessage, { id: toastId });
    }
  };

  const fetchDocumentShareLinks = async (docId: string) => {
    setIsLoadingShareLinks(true);
    try {
      const response = await apiClient.get(`/api/onlyoffice/${docId}/share-links`);
      setShareLinks(Array.isArray(response.data) ? response.data : []);
    } catch (error) {
      console.error('Error fetching document share links:', error);
      toast.error('No se pudieron cargar los enlaces de comparticion');
      setShareLinks([]);
    } finally {
      setIsLoadingShareLinks(false);
    }
  };

  const openShareDialog = async (doc: OnlyOfficeDoc) => {
    setShareTargetDoc(doc);
    setPrivateSearch('');
    setPrivateSuggestions([]);
    setSelectedPrivateUser(null);
    setShareCanEdit(true);
    setIsShareDialogOpen(true);
    await fetchDocumentShareLinks(doc.id);
  };

  const handleCreatePublicShare = async () => {
    if (!shareTargetDoc) return;
    setIsCreatingShare(true);
    try {
      const response = await apiClient.post(`/api/onlyoffice/${shareTargetDoc.id}/share-links`, {
        scope: 'public',
        can_edit: shareCanEdit,
      });
      const shareUrl = response.data?.share_url
        ? `${window.location.origin}${response.data.share_url}`
        : null;

      if (shareUrl) {
        await navigator.clipboard.writeText(shareUrl);
        toast.success('Enlace publico creado y copiado al portapapeles');
      } else {
        toast.success('Enlace publico creado');
      }
      await fetchDocumentShareLinks(shareTargetDoc.id);
    } catch (error) {
      console.error('Error creating public share:', error);
      toast.error('No se pudo crear el enlace publico');
    } finally {
      setIsCreatingShare(false);
    }
  };

  const handleCreatePrivateShare = async () => {
    if (!shareTargetDoc || !selectedPrivateUser?.account_id) return;
    setIsCreatingShare(true);
    try {
      await apiClient.post(`/api/onlyoffice/${shareTargetDoc.id}/share-links`, {
        scope: 'private',
        target_account_id: selectedPrivateUser.account_id,
        can_edit: shareCanEdit,
      });
      toast.success('Documento compartido con la cuenta seleccionada');
      setPrivateSearch('');
      setPrivateSuggestions([]);
      setSelectedPrivateUser(null);
      await fetchDocumentShareLinks(shareTargetDoc.id);
    } catch (error) {
      console.error('Error creating private share:', error);
      toast.error('No se pudo compartir el documento de forma privada');
    } finally {
      setIsCreatingShare(false);
    }
  };

  const handleDeleteShareLink = async (shareId: string) => {
    if (!shareTargetDoc) return;
    try {
      await apiClient.delete(`/api/onlyoffice/share-links/${shareId}`);
      toast.success('Comparticion eliminada');
      await fetchDocumentShareLinks(shareTargetDoc.id);
    } catch (error) {
      console.error('Error deleting share link:', error);
      toast.error('No se pudo eliminar la comparticion');
    }
  };

  const searchPrivateUsers = async (value: string) => {
    setPrivateSearch(value);
    setSelectedPrivateUser(null);

    if (value.trim().length < 2) {
      setPrivateSuggestions([]);
      return;
    }

    try {
      const response = await apiClient.get('/api/users/autocomplete', {
        params: { q: value.trim(), limit: 8 },
      });
      setPrivateSuggestions(Array.isArray(response.data) ? response.data : []);
    } catch (error) {
      console.error('Error searching users:', error);
      setPrivateSuggestions([]);
    }
  };

  const handleOpenDocumentChat = async (doc: OnlyOfficeDoc) => {
    if (isChatSidebarOpen && currentChatThreadId) {
      setIsChatSidebarOpen(false);
      return;
    }

    setIsPreparingDocChat(true);
    try {
      const response = await apiClient.get(`/api/onlyoffice/${doc.id}/chat-link`);
      const threadId = response.data?.thread_id;
      if (!threadId) {
        toast.error('No se pudo generar el enlace del chat del documento');
        return;
      }
      
      setCurrentChatThreadId(threadId);
      setIsChatSidebarOpen(true);
    } catch (error) {
      console.error('Error opening document chat:', error);
      toast.error('No se pudo abrir el chat del documento');
    } finally {
      setIsPreparingDocChat(false);
    }
  };

  const handleResetDocumentChat = async (doc: OnlyOfficeDoc) => {
    if (!confirm('¿Estás seguro de que deseas iniciar una nueva sesión de chat? Se creará un hilo limpio para este documento.')) return;
    
    setIsPreparingDocChat(true);
    try {
      const response = await apiClient.get(`/api/onlyoffice/${doc.id}/chat-link?force_new=true`);
      const threadId = response.data?.thread_id;
      if (!threadId) {
        toast.error('No se pudo reiniciar el chat');
        return;
      }
      
      setCurrentChatThreadId(threadId);
      setIsChatSidebarOpen(true);
      toast.success('Nueva sesión de chat iniciada');
    } catch (error) {
      console.error('Error resetting document chat:', error);
      toast.error('No se pudo reiniciar el chat');
    } finally {
      setIsPreparingDocChat(false);
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

  const initEditor = useCallback((config: any) => {
    try {
      // @ts-ignore
      editorRef.current = new window.DocsAPI.DocEditor("onlyoffice-placeholder", config);
      setIsOpeningEditor(false);
    } catch (err) {
      console.error("Editor init failed", err);
      toast.error("Error al inicializar el editor de OnlyOffice");
      setIsOpeningEditor(false);
    }
  }, []);

  const openEditor = useCallback(async (doc: OnlyOfficeDoc) => {
    setIsOpeningEditor(true);
    try {
      const response = await apiClient.get(`/api/onlyoffice/config/${doc.id}`);
      const { config, onlyoffice_url } = response.data;
      
      setEditingDoc(doc);
      
      if (!(window as any).DocsAPI) {
        const script = document.createElement('script');
        script.src = `${onlyoffice_url}/web-apps/apps/api/documents/api.js`;
        script.id = 'onlyoffice-api-script';
        script.onload = () => initEditor(config);
        document.head.appendChild(script);
      } else {
        if (editorRef.current) {
          editorRef.current.destroyEditor();
        }
        setTimeout(() => initEditor(config), 100);
      }
    } catch (error) {
      toast.error('Error al iniciar el editor');
      setIsOpeningEditor(false);
    }
  }, [initEditor]);

  useEffect(() => {
    if (!hasMounted) return;
    const openId = searchParams?.get('open');
    if (openId && documents.length > 0) {
      const doc = documents.find(d => d.id === openId);
      if (doc) {
        openEditor(doc);
        const newUrl = window.location.pathname;
        router.replace(newUrl);
      }
    }
  }, [searchParams, documents, hasMounted, openEditor, router]);

  const closeEditor = () => {
    if (editorRef.current) {
      editorRef.current.destroyEditor();
      editorRef.current = null;
    }
    setEditingDoc(null);
    setIsChatSidebarOpen(false);
    setCurrentChatThreadId(null);
    fetchDocuments();
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
  ).sort((a, b) => {
    if (sortBy === 'name') {
      return sortOrder === 'asc' ? a.filename.localeCompare(b.filename) : b.filename.localeCompare(a.filename);
    } else {
      return sortOrder === 'asc' ? new Date(a.updated_at).getTime() - new Date(b.updated_at).getTime() : new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
    }
  });
  
  const filteredFolders = folders.filter(f => 
    f.name.toLowerCase().includes(searchQuery.toLowerCase())
  ).sort((a, b) => {
    if (sortBy === 'name') {
      return sortOrder === 'asc' ? a.name.localeCompare(b.name) : b.name.localeCompare(a.name);
    } else {
      const aDate = a.created_at || 0;
      const bDate = b.created_at || 0;
      return sortOrder === 'asc' ? new Date(aDate).getTime() - new Date(bDate).getTime() : new Date(bDate).getTime() - new Date(aDate).getTime();
    }
  });

  const getIconColor = (ext: string) => {
    switch (ext.toLowerCase()) {
      case 'docx': case 'doc': case 'txt': return 'text-blue-500 bg-blue-500/10';
      case 'xlsx': case 'xls': case 'csv': return 'text-emerald-500 bg-emerald-500/10';
      case 'pptx': case 'ppt': return 'text-orange-500 bg-orange-500/10';
      case 'pdf': return 'text-rose-500 bg-rose-500/10';
      default: return 'text-slate-500 bg-slate-500/10';
    }
  };

  if (!hasMounted) return null;

  const editorOverlay = hasMounted && editingDoc
    ? createPortal(
        <div key="onlyoffice-editor-view" className="fixed inset-0 z-[200] bg-background flex flex-col animate-in fade-in duration-300">
          <header className="h-14 border-b flex items-center justify-between px-4 bg-background/95 backdrop-blur-sm gap-3">
            <div className="flex items-center gap-3 min-w-0">
              <Button
                variant="ghost"
                size="icon"
                onClick={closeEditor}
                className="rounded-xl text-muted-foreground hover:text-foreground hover:bg-muted"
                title="Volver"
              >
                <ArrowLeft className="h-4 w-4" />
              </Button>
              <p className="text-sm font-semibold truncate max-w-[42vw]" title={editingDoc.filename}>
                {editingDoc.filename}
              </p>
            </div>

            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                className="rounded-xl"
                onClick={() => openShareDialog(editingDoc)}
              >
                <Share2 className="h-4 w-4 mr-2" />
                Compartir
              </Button>
              
              {isChatSidebarOpen && (
                <Button
                  variant="outline"
                  size="sm"
                  className="rounded-xl border-dashed hover:border-primary hover:text-primary transition-colors"
                  onClick={() => handleResetDocumentChat(editingDoc)}
                  disabled={isPreparingDocChat}
                  title="Iniciar una nueva sesión de chat limpia"
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Nuevo Chat
                </Button>
              )}

              <Button
                size="sm"
                variant={isChatSidebarOpen ? "secondary" : "default"}
                className="rounded-xl"
                onClick={() => handleOpenDocumentChat(editingDoc)}
                disabled={isPreparingDocChat}
              >
                {isPreparingDocChat ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <MessageSquare className="h-4 w-4 mr-2" />
                )}
                {isChatSidebarOpen ? 'Cerrar Chat IA' : 'Chat IA'}
              </Button>
            </div>
          </header>
          <div className="flex-1 flex overflow-hidden relative">
            {isDraggingSidebar && (
              <div className="absolute inset-0 z-50 cursor-col-resize" />
            )}
            <div className="flex-1 relative bg-muted/30">
              <div id="onlyoffice-placeholder" className="absolute inset-0" />
              {isOpeningEditor && (
                <div className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-4 bg-background/80 backdrop-blur-sm">
                  <Loader2 className="h-10 w-10 text-primary animate-spin" />
                  <p className="text-muted-foreground font-medium animate-pulse">Iniciando Editor OnlyOffice...</p>
                </div>
              )}
            </div>
            {isChatSidebarOpen && currentChatThreadId && (
              <motion.div 
                initial={{ width: 0, opacity: 0 }}
                animate={{ width: sidebarWidth, opacity: 1 }}
                exit={{ width: 0, opacity: 0 }}
                transition={isDraggingSidebar ? { duration: 0 } : { type: "spring", damping: 20, stiffness: 150 }}
                className="border-l bg-background flex flex-col shadow-[-10px_0_15px_-3px_rgba(0,0,0,0.1)] z-10 relative"
              >
                <div 
                  className="absolute left-0 top-0 bottom-0 w-2 hover:bg-primary/30 cursor-col-resize z-20 transition-colors group"
                  onMouseDown={(e) => { e.preventDefault(); setIsDraggingSidebar(true); }}
                >
                  <div className={`absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-1 h-8 rounded-full transition-colors ${isDraggingSidebar ? 'bg-primary' : 'bg-border group-hover:bg-primary/50'}`} />
                </div>
                <CommonChat 
                  key={currentChatThreadId}
                  threadId={currentChatThreadId}
                  workspaceId={editingDoc?.workspace_id || undefined}
                />
              </motion.div>
            )}
          </div>
        </div>,
        document.body
      )
    : null;

  return (
    <>
    {editorOverlay}
    <div key="documents-main-container" className="p-4 sm:p-8 max-w-7xl mx-auto space-y-8 h-full flex flex-col">
      <div className="flex items-center justify-between mb-2">
        <div>
          <h1 className="text-3xl font-bold flex items-center">
            <FileBox className="mr-3 h-8 w-8 text-primary" />
            Documentos
            <Sheet>
              <SheetTrigger asChild>
                <Button variant="ghost" size="icon" className="ml-2 h-6 w-6 text-muted-foreground">
                  <Info className="h-4 w-4" />
                </Button>
              </SheetTrigger>
              <SheetContent className="w-[400px] sm:w-[540px] overflow-y-auto">
                <SheetHeader className="pb-6 border-b">
                  <SheetTitle className="text-2xl font-bold flex items-center gap-2">
                    <FileBox className="h-6 w-6 text-primary" />
                    Sobre Documentos
                  </SheetTitle>
                  <SheetDescription>
                    Gestión avanzada de documentos y colaboración inteligente.
                  </SheetDescription>
                </SheetHeader>
                
                <div className="py-6 space-y-8">
                  <section className="space-y-3">
                    <h3 className="text-sm font-bold uppercase tracking-wider text-primary">¿Qué es Documentos?</h3>
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
          </h1>
        </div>
        <div className="flex items-center gap-2">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm" className="h-8 px-2 md:px-4">
                <span className="hidden md:inline">Acciones</span> <MoreHorizontal className="md:ml-2 h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-[180px]">
              <DropdownMenuItem onClick={() => setIsCreateFolderOpen(true)}>
                <Folder className="mr-2 h-4 w-4" />
                Nueva Carpeta
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem className="p-0 h-auto">
                <label htmlFor="file-upload" className="flex items-center w-full px-2 py-1.5 cursor-pointer text-sm">
                  <Plus className="mr-2 h-4 w-4" />
                  Subir Archivo
                </label>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => setIsCreateDocOpen(true)}>
                <FileText className="mr-2 h-4 w-4" />
                Nuevo Documento
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
          <input
            type="file"
            id="file-upload"
            className="hidden"
            onChange={handleUpload}
            accept=".docx,.xlsx,.pptx,.doc,.xls,.ppt,.txt,.csv,.pdf"
          />
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-4">
        <div className="relative w-full md:flex-1 md:max-w-md group">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground group-focus-within:text-primary transition-all duration-300" />
          <Input 
            placeholder="Buscar documentos..." 
            className="pl-11 h-10 rounded-full bg-card/60 backdrop-blur-sm border-border/40 focus:border-primary/40 focus:ring-2 transition-all text-sm font-medium w-full"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
        <div className="flex items-center gap-3">
          <Select 
            value={currentWorkspaceId || "all"} 
            onValueChange={(val) => setCurrentWorkspaceId(val === "all" ? null : val)}
          >
            <SelectTrigger className="w-[180px] h-10 rounded-full border-border/40 bg-card/60">
              <SelectValue placeholder="Workspaces" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todos los Proyectos</SelectItem>
              {workspaces.map(ws => (
                <SelectItem key={ws.id} value={ws.id}>
                  <div className="flex items-center gap-2">
                    <div className="h-2 w-2 rounded-full" style={{ backgroundColor: ws.color || 'var(--primary)' }} />
                    {ws.name}
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <div className="flex items-center border border-border/40 bg-card/60 rounded-full overflow-hidden h-10">
            <button 
              onClick={() => setViewMode('grid')} 
              className={`px-3 h-full flex items-center justify-center transition-colors ${viewMode === 'grid' ? 'bg-primary/10 text-primary' : 'text-muted-foreground hover:bg-muted/50'}`}
              title="Vista de cuadrícula"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="7" height="7" x="3" y="3" rx="1"/><rect width="7" height="7" x="14" y="3" rx="1"/><rect width="7" height="7" x="14" y="14" rx="1"/><rect width="7" height="7" x="3" y="14" rx="1"/></svg>
            </button>
            <div className="w-px h-5 bg-border/40"></div>
            <button 
              onClick={() => setViewMode('list')} 
              className={`px-3 h-full flex items-center justify-center transition-colors ${viewMode === 'list' ? 'bg-primary/10 text-primary' : 'text-muted-foreground hover:bg-muted/50'}`}
              title="Vista de lista"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="8" x2="21" y1="6" y2="6"/><line x1="8" x2="21" y1="12" y2="12"/><line x1="8" x2="21" y1="18" y2="18"/><line x1="3" x2="3.01" y1="6" y2="6"/><line x1="3" x2="3.01" y1="12" y2="12"/><line x1="3" x2="3.01" y1="18" y2="18"/></svg>
            </button>
          </div>
        </div>
      </div>

      <div key="breadcrumbs-navigation" className="flex items-center gap-2 text-sm text-muted-foreground">
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

      <AnimatePresence>
        {(selectedDocs.length > 0 || selectedFolders.length > 0) && (
          <motion.div 
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="flex items-center gap-2 mb-4 p-2 bg-primary/5 rounded-2xl border border-primary/10 overflow-x-auto"
          >
            <div className="flex items-center gap-2 px-3 text-sm font-semibold text-primary/80 whitespace-nowrap">
              <Layers className="h-4 w-4" />
              {selectedDocs.length + selectedFolders.length} seleccionados
            </div>
            <Button variant="secondary" size="sm" onClick={() => { setItemToMove(null); setSelectedTargetFolderForMove("null"); setIsMoveItemDialogOpen(true); fetchAllFolders(); }} className="gap-2">
              <FolderOutput className="h-4 w-4" /> Mover
            </Button>
            <Button variant="destructive" size="sm" onClick={() => setBulkDeleteConfirmOpen(true)} className="gap-2 ml-auto">
              <Trash2 className="h-4 w-4" /> Eliminar
            </Button>
          </motion.div>
        )}
      </AnimatePresence>

      <div key="main-content-area" className="flex-1 flex flex-col">
        {isLoading ? (
          <div className="flex-1 flex flex-col items-center justify-center gap-4 py-20">
            <Loader2 className="h-12 w-12 text-primary animate-spin" />
            <p className="text-muted-foreground font-medium animate-pulse">Cargando...</p>
          </div>
        ) : (filteredDocs.length > 0 || filteredFolders.length > 0) ? (
          viewMode === 'grid' ? (
          <div className="flex flex-col space-y-8 pb-12">
            {filteredFolders.length > 0 && (
              <div className="space-y-4">
                <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider pl-1">Carpetas</h2>
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6 gap-4">
                  <AnimatePresence>
                  {filteredFolders.map((folder) => (
                    <motion.div 
                      key={`folder-${folder.id}`}
                      layout
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, scale: 0.95 }}
                      transition={{ duration: 0.2 }}
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
                    >
                      <Card 
                        className={`group relative flex flex-col h-64 overflow-hidden transition-all duration-200 hover:bg-muted/60 cursor-grab active:cursor-grabbing rounded-2xl border ${
                          selectedFolders.includes(folder.id) 
                            ? 'bg-primary/5 border-primary ring-1 ring-primary/50 shadow-md' 
                            : 'bg-card border-border/60 hover:bg-muted/20 shadow-sm hover:shadow-md'
                        }`}
                        onClick={(e) => {
                           const isMod = (e as any).shiftKey || (e as any).ctrlKey || (e as any).metaKey;
                           if (selectedDocs.length > 0 || selectedFolders.length > 0 || isMod) {
                             toggleFolderSelection(folder.id, e as any);
                           } else {
                             navigateToFolder(folder);
                           }
                        }}
                        onDragOver={(e: any) => {
                          e.preventDefault();
                          e.dataTransfer.dropEffect = "move";
                          e.currentTarget.classList.add('bg-primary/10', 'border-primary/60');
                        }}
                        onDragEnter={(e: any) => {
                          e.preventDefault();
                          e.currentTarget.classList.add('bg-primary/10', 'border-primary/60');
                        }}
                        onDragLeave={(e: any) => {
                          e.currentTarget.classList.remove('bg-primary/10', 'border-primary/60');
                        }}
                        onDrop={(e: any) => {
                          e.preventDefault();
                          e.currentTarget.classList.remove('bg-primary/10', 'border-primary/60');
                          const itemId = e.dataTransfer.getData('itemId') || e.dataTransfer.getData('text/plain') || draggingItem?.id;
                          const itemType = (e.dataTransfer.getData('itemType') as 'doc' | 'folder') || draggingItem?.type;
                          if (itemId && itemType) handleDropToFolder(itemId, folder.id, itemType);
                        }}
                      >
                        <div className={`absolute top-3 left-3 z-10 transition-opacity ${selectedFolders.includes(folder.id) ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'}`}>
                          <Checkbox 
                            checked={selectedFolders.includes(folder.id)}
                            onCheckedChange={() => toggleFolderSelection(folder.id)}
                            onClick={(e) => e.stopPropagation()}
                            className="w-4 h-4 rounded-sm"
                          />
                        </div>
                        
                        <div className="absolute top-2 right-2 z-10 opacity-0 group-hover:opacity-100 transition-opacity">
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button variant="secondary" size="icon" className="h-8 w-8 rounded-full shadow-sm bg-background/80 backdrop-blur" onClick={(e) => e.stopPropagation()}>
                                <MoreVertical className="h-4 w-4" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end" className="w-48 rounded-xl shadow-xl border-border/50">
                              <DropdownMenuItem onClick={(e) => { e.stopPropagation(); navigateToFolder(folder); }} className="gap-2 cursor-pointer focus:bg-muted">
                                <ExternalLink className="h-4 w-4" />
                                <span>Abrir</span>
                              </DropdownMenuItem>
                              <DropdownMenuItem 
                                onClick={(e) => { 
                                  e.stopPropagation(); 
                                  setItemToRename({id: folder.id, name: folder.name, type: 'folder'});
                                  setNewName(folder.name);
                                  setIsRenameDialogOpen(true);
                                }} 
                                className="gap-2 cursor-pointer focus:bg-muted"
                              >
                                <Edit3 className="h-4 w-4" />
                                <span>Renombrar</span>
                              </DropdownMenuItem>
                              <DropdownMenuItem 
                                onClick={(e) => { 
                                  e.stopPropagation(); 
                                  setItemToMove({id: folder.id, name: folder.name, type: 'folder'});
                                  setSelectedTargetFolderForMove("null");
                                  setIsMoveItemDialogOpen(true);
                                  fetchAllFolders();
                                }} 
                                className="gap-2 cursor-pointer focus:bg-muted"
                              >
                                <FolderOutput className="h-4 w-4" />
                                <span>Mover a...</span>
                              </DropdownMenuItem>
                              <DropdownMenuItem 
                                onClick={(e) => { 
                                  e.stopPropagation(); 
                                  setItemToMove({id: folder.id, name: folder.name, type: 'folder'});
                                  setSelectedWorkspaceForMove(folder.workspace_id || "none");
                                  setIsMoveDialogOpen(true);
                                }} 
                                className="gap-2 cursor-pointer focus:bg-muted"
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

                        {/* Folder Preview Area (Mock) */}
                        <div className="flex-1 bg-muted/30 flex items-center justify-center p-6 border-b border-border/40">
                          <div className="p-4 rounded-3xl bg-background shadow-sm text-foreground/70 transition-transform group-hover:scale-110 duration-500" style={{ color: folder.workspace_color || 'currentColor' }}>
                            <Folder className="h-14 w-14 fill-current opacity-80" />
                          </div>
                        </div>

                        {/* Folder Info Area */}
                        <div className="p-4 bg-card h-24 flex flex-col justify-center">
                          <div className="flex items-center gap-2 mb-1">
                            <Folder className="h-4 w-4 shrink-0" style={{ color: folder.workspace_color || 'currentColor' }} />
                            <h3 className="font-medium text-sm leading-tight truncate text-foreground" title={folder.name}>
                              {folder.name}
                            </h3>
                          </div>
                          
                          <div className="flex items-center justify-between mt-1">
                            <span className="text-[11px] text-muted-foreground flex items-center gap-1">
                              <Folder className="h-3 w-3" />
                              Carpeta
                            </span>
                            
                            {folder.workspace_name && (
                              <div
                                className="inline-flex items-center gap-1 text-[9px] font-bold px-1.5 py-0.5 rounded-full border uppercase tracking-wider"
                                style={{
                                  backgroundColor: folder.workspace_color ? `${folder.workspace_color}15` : '#f3f4f620',
                                  borderColor: folder.workspace_color ? `${folder.workspace_color}40` : '#88888840',
                                }}
                                title={folder.workspace_name}
                              >
                                <span
                                  className="h-1.5 w-1.5 rounded-full"
                                  style={{ backgroundColor: folder.workspace_color || '#888888' }}
                                ></span>
                                <span style={{ color: folder.workspace_color || '#374151' }} className="truncate max-w-[60px]">
                                  {folder.workspace_name}
                                </span>
                              </div>
                            )}
                          </div>
                        </div>
                      </Card>
                    </motion.div>
                  ))}
                  </AnimatePresence>
                </div>
              </div>
            )}

            {filteredDocs.length > 0 && (
              <div className="space-y-4">
                <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider pl-1">Archivos</h2>
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6 gap-5">
                  <AnimatePresence>
                  {filteredDocs.map((doc) => (
                    <motion.div 
                      key={`doc-${doc.id}`}
                      layout
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, scale: 0.95 }}
                      transition={{ duration: 0.2 }}
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
                      <Card 
                        className={`group relative flex flex-col h-64 overflow-hidden transition-all duration-200 cursor-pointer rounded-2xl border ${
                          selectedDocs.includes(doc.id)
                            ? 'bg-primary/5 border-primary ring-1 ring-primary/50 shadow-md'
                            : 'bg-card border-border/60 hover:bg-muted/20 shadow-sm hover:shadow-md'
                        }`}
                        onClick={(e) => {
                           const isMod = (e as any).shiftKey || (e as any).ctrlKey || (e as any).metaKey;
                           if (selectedDocs.length > 0 || selectedFolders.length > 0 || isMod) {
                             toggleDocSelection(doc.id, e as any);
                           } else {
                             openEditor(doc);
                           }
                        }}
                      >
                        <div className={`absolute top-3 left-3 z-10 transition-opacity ${selectedDocs.includes(doc.id) ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'}`}>
                          <Checkbox 
                            checked={selectedDocs.includes(doc.id)}
                            onCheckedChange={() => toggleDocSelection(doc.id)}
                            onClick={(e) => e.stopPropagation()}
                            className="w-4 h-4 rounded-sm"
                          />
                        </div>

                        <div className="absolute top-2 right-2 z-10 opacity-0 group-hover:opacity-100 transition-opacity">
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button variant="secondary" size="icon" className="h-8 w-8 rounded-full shadow-sm bg-background/80 backdrop-blur" onClick={(e) => e.stopPropagation()}>
                                <MoreVertical className="h-4 w-4" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end" className="w-48 rounded-xl border-border/40 shadow-xl">
                              <DropdownMenuItem onClick={() => openEditor(doc)} className="gap-2 cursor-pointer py-2 px-3">
                                <Edit3 className="h-4 w-4 text-primary" />
                                <span className="font-medium">Editar Ahora</span>
                              </DropdownMenuItem>
                              <DropdownMenuItem 
                                onClick={() => {
                                  setItemToRename({id: doc.id, name: doc.filename, type: 'doc'});
                                  setNewName(doc.filename);
                                  setIsRenameDialogOpen(true);
                                }} 
                                className="gap-2 cursor-pointer py-2 px-3"
                              >
                                <Edit3 className="h-4 w-4" />
                                <span className="font-medium">Renombrar</span>
                              </DropdownMenuItem>
                              <DropdownMenuItem className="gap-2 cursor-pointer py-2 px-3">
                                <Download className="h-4 w-4" />
                                <span className="font-medium">Descargar</span>
                              </DropdownMenuItem>
                               <DropdownMenuItem 
                                onClick={(e) => { 
                                  e.stopPropagation(); 
                                  setItemToMove({id: doc.id, name: doc.filename, type: 'doc'});
                                  setSelectedTargetFolderForMove("null");
                                  setIsMoveItemDialogOpen(true);
                                  fetchAllFolders();
                                }} 
                                className="gap-2 cursor-pointer py-2 px-3"
                              >
                                <FolderOutput className="h-4 w-4" />
                                <span className="font-medium">Mover a...</span>
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
                              <DropdownMenuItem 
                                onClick={() => handleDuplicate(doc)}
                                className="gap-2 cursor-pointer py-2 px-3"
                              >
                                <Copy className="h-4 w-4" />
                                <span className="font-medium">Duplicar Documento</span>
                              </DropdownMenuItem>
                              <DropdownMenuItem 
                                onClick={() => handleVectorize(doc)}
                                className="gap-2 cursor-pointer py-2 px-3"
                              >
                                <Layers className="h-4 w-4 text-emerald-500" />
                                <span className="font-medium text-emerald-500">Vectorizar (RAG)</span>
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

                        {/* File Preview Area (Mock) */}
                        <div className="flex-1 bg-muted/30 flex items-center justify-center p-6 border-b border-border/40">
                          <div className={`p-4 rounded-3xl bg-background shadow-sm ${getIconColor(doc.extension)} transition-transform group-hover:scale-110 duration-500`}>
                            <FileText className="h-14 w-14" />
                          </div>
                        </div>

                        {/* File Info Area */}
                        <div className="p-4 bg-card h-24 flex flex-col justify-center">
                          <div className="flex items-center gap-2 mb-1">
                            <FileText className={`h-4 w-4 shrink-0 ${getIconColor(doc.extension).split(' ')[0]}`} />
                            <h3 className="font-medium text-sm leading-tight truncate text-foreground" title={doc.filename}>
                              {doc.filename}
                            </h3>
                          </div>
                          
                          <div className="flex items-center justify-between mt-1">
                            <span className="text-[11px] text-muted-foreground flex items-center gap-1">
                              <Calendar className="h-3 w-3" />
                              {new Date(doc.updated_at).toLocaleDateString()}
                            </span>
                            
                            {doc.workspace_id && (
                              <div
                                className="inline-flex items-center gap-1 text-[9px] font-bold px-1.5 py-0.5 rounded-full border uppercase tracking-wider"
                                style={{
                                  backgroundColor: doc.workspace_color ? `${doc.workspace_color}15` : '#f3f4f620',
                                  borderColor: doc.workspace_color ? `${doc.workspace_color}40` : '#88888840',
                                }}
                                title={doc.workspace_name || 'Workspace'}
                              >
                                <span
                                  className="h-1.5 w-1.5 rounded-full"
                                  style={{ backgroundColor: doc.workspace_color || '#888888' }}
                                ></span>
                                <span style={{ color: doc.workspace_color || '#374151' }} className="truncate max-w-[60px]">
                                  {doc.workspace_name}
                                </span>
                              </div>
                            )}
                          </div>
                        </div>
                      </Card>
                    </motion.div>
                  ))}
                  </AnimatePresence>
                </div>
              </div>
            )}
          </div>
          ) : (
          <div className="flex flex-col gap-2">
            {/* List View Header */}
            <div className="grid grid-cols-12 gap-4 px-4 py-2 text-sm font-semibold text-muted-foreground border-b mb-2">
              <div 
                className="col-span-6 md:col-span-5 flex items-center gap-2 cursor-pointer hover:text-foreground transition-colors select-none" 
                onClick={() => { if (sortBy === 'name') setSortOrder(prev => prev === 'asc' ? 'desc' : 'asc'); else { setSortBy('name'); setSortOrder('asc'); } }}
              >
                Nombre <span className="text-xs">{sortBy === 'name' ? (sortOrder === 'asc' ? '↑' : '↓') : ''}</span>
              </div>
              <div className="col-span-3 hidden md:block">Workspace</div>
              <div 
                className="col-span-4 md:col-span-3 flex items-center justify-end gap-2 cursor-pointer hover:text-foreground transition-colors select-none"
                onClick={() => { if (sortBy === 'date') setSortOrder(prev => prev === 'asc' ? 'desc' : 'asc'); else { setSortBy('date'); setSortOrder('desc'); } }}
              >
                Actualizado <span className="text-xs">{sortBy === 'date' ? (sortOrder === 'asc' ? '↑' : '↓') : ''}</span>
              </div>
              <div className="col-span-2 md:col-span-1 text-right"></div>
            </div>
            
            <AnimatePresence>
              {filteredFolders.map((folder) => (
                <motion.div
                  key={`list-folder-${folder.id}`}
                  layout
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className={`grid grid-cols-12 gap-4 items-center px-4 py-2 rounded-xl cursor-pointer transition-colors border border-transparent ${
                    selectedFolders.includes(folder.id) ? 'bg-primary/10 border-primary/20 hover:bg-primary/20' : 'hover:bg-muted/50'
                  }`}
                  onClick={(e) => {
                     const isMod = (e as any).shiftKey || (e as any).ctrlKey || (e as any).metaKey;
                     if (selectedDocs.length > 0 || selectedFolders.length > 0 || isMod) {
                       toggleFolderSelection(folder.id, e as any);
                     } else {
                       navigateToFolder(folder);
                     }
                  }}
                >
                  <div className="col-span-6 md:col-span-5 flex items-center gap-3">
                    <Checkbox 
                      checked={selectedFolders.includes(folder.id)}
                      onCheckedChange={() => toggleFolderSelection(folder.id)}
                      onClick={(e) => e.stopPropagation()}
                      className="data-[state=checked]:bg-orange-600 data-[state=checked]:border-orange-600"
                    />
                    <div className="p-2 rounded-lg bg-orange-500/10 text-orange-600">
                      <Folder className="h-5 w-5 fill-current" />
                    </div>
                    <span className="font-bold truncate" title={folder.name}>{folder.name}</span>
                  </div>
                  <div className="col-span-3 hidden md:flex items-center">
                    {folder.workspace_name && (
                      <div className="flex items-center gap-2 text-sm">
                        <span className="h-2 w-2 rounded-full" style={{ backgroundColor: folder.workspace_color || '#888888' }}></span>
                        <span className="truncate">{folder.workspace_name}</span>
                      </div>
                    )}
                  </div>
                  <div className="col-span-4 md:col-span-3 text-right text-sm text-muted-foreground flex items-center justify-end">
                    -
                  </div>
                  <div className="col-span-2 md:col-span-1 flex justify-end">
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
                            setItemToRename({id: folder.id, name: folder.name, type: 'folder'});
                            setNewName(folder.name);
                            setIsRenameDialogOpen(true);
                          }} 
                          className="gap-2 cursor-pointer"
                        >
                          <Edit3 className="h-4 w-4" />
                          <span>Renombrar</span>
                        </DropdownMenuItem>
                        <DropdownMenuItem 
                          onClick={(e) => { 
                            e.stopPropagation(); 
                            setItemToMove({id: folder.id, name: folder.name, type: 'folder'});
                            setSelectedTargetFolderForMove("null");
                            setIsMoveItemDialogOpen(true);
                            fetchAllFolders();
                          }} 
                          className="gap-2 cursor-pointer"
                        >
                          <FolderOutput className="h-4 w-4" />
                          <span>Mover a...</span>
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
                </motion.div>
              ))}

              {filteredDocs.map((doc) => (
                <motion.div
                  key={`list-doc-${doc.id}`}
                  layout
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className={`grid grid-cols-12 gap-4 items-center px-4 py-2 rounded-xl cursor-pointer transition-colors border border-transparent ${
                    selectedDocs.includes(doc.id) ? 'bg-primary/10 border-primary/20 hover:bg-primary/20' : 'hover:bg-muted/50'
                  }`}
                  onClick={(e) => {
                     const isMod = (e as any).shiftKey || (e as any).ctrlKey || (e as any).metaKey;
                     if (selectedDocs.length > 0 || selectedFolders.length > 0 || isMod) {
                       toggleDocSelection(doc.id, e as any);
                     } else {
                       openEditor(doc);
                     }
                  }}
                >
                  <div className="col-span-6 md:col-span-5 flex items-center gap-3">
                    <Checkbox 
                      checked={selectedDocs.includes(doc.id)}
                      onCheckedChange={() => toggleDocSelection(doc.id)}
                      onClick={(e) => e.stopPropagation()}
                    />
                    <div className={`p-2 rounded-lg shadow-sm ${getIconColor(doc.extension)}`}>
                      <FileText className="h-5 w-5" />
                    </div>
                    <span className="font-bold truncate group-hover:text-primary transition-colors" title={doc.filename}>{doc.filename}</span>
                  </div>
                  <div className="col-span-3 hidden md:flex items-center">
                    {doc.workspace_name && (
                      <div className="flex items-center gap-2 text-sm">
                        <span className="h-2 w-2 rounded-full" style={{ backgroundColor: doc.workspace_color || '#888888' }}></span>
                        <span className="truncate">{doc.workspace_name}</span>
                      </div>
                    )}
                  </div>
                  <div className="col-span-4 md:col-span-3 text-right text-sm text-muted-foreground flex items-center justify-end gap-1.5">
                    {new Date(doc.updated_at).toLocaleDateString()}
                  </div>
                  <div className="col-span-2 md:col-span-1 flex justify-end">
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon" className="h-8 w-8 rounded-full hover:bg-muted" onClick={(e) => e.stopPropagation()}>
                          <MoreVertical className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end" className="w-48 rounded-xl border-border/40 shadow-xl">
                          <DropdownMenuItem onClick={(e) => { e.stopPropagation(); openEditor(doc); }} className="gap-2 cursor-pointer py-2 px-3">
                            <Edit3 className="h-4 w-4 text-primary" />
                            <span className="font-medium">Editar Ahora</span>
                          </DropdownMenuItem>
                          <DropdownMenuItem 
                            onClick={(e) => {
                              e.stopPropagation();
                              setItemToRename({id: doc.id, name: doc.filename, type: 'doc'});
                              setNewName(doc.filename);
                              setIsRenameDialogOpen(true);
                            }} 
                            className="gap-2 cursor-pointer py-2 px-3"
                          >
                            <Edit3 className="h-4 w-4" />
                            <span className="font-medium">Renombrar</span>
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={(e) => e.stopPropagation()} className="gap-2 cursor-pointer py-2 px-3">
                            <Download className="h-4 w-4" />
                            <span className="font-medium">Descargar</span>
                          </DropdownMenuItem>
                          <DropdownMenuItem 
                            onClick={(e) => { 
                              e.stopPropagation(); 
                              setItemToMove({id: doc.id, name: doc.filename, type: 'doc'});
                              setSelectedTargetFolderForMove("null");
                              setIsMoveItemDialogOpen(true);
                              fetchAllFolders();
                            }} 
                            className="gap-2 cursor-pointer py-2 px-3"
                          >
                            <FolderOutput className="h-4 w-4" />
                            <span className="font-medium">Mover a...</span>
                          </DropdownMenuItem>
                           <DropdownMenuItem 
                            onClick={(e) => {
                              e.stopPropagation();
                              setItemToMove({id: doc.id, name: doc.filename, type: 'doc'});
                              setSelectedWorkspaceForMove(doc.workspace_id || "none");
                              setIsMoveDialogOpen(true);
                            }} 
                            className="gap-2 cursor-pointer py-2 px-3"
                          >
                            <Briefcase className="h-4 w-4" />
                            <span className="font-medium">Asociar Workspace</span>
                          </DropdownMenuItem>
                          <DropdownMenuItem 
                            onClick={(e) => { e.stopPropagation(); handleDuplicate(doc); }}
                            className="gap-2 cursor-pointer py-2 px-3"
                          >
                            <Copy className="h-4 w-4" />
                            <span className="font-medium">Duplicar Documento</span>
                          </DropdownMenuItem>
                          <DropdownMenuItem 
                            onClick={(e) => { e.stopPropagation(); handleVectorize(doc); }}
                            className="gap-2 cursor-pointer py-2 px-3"
                          >
                            <Layers className="h-4 w-4 text-emerald-500" />
                            <span className="font-medium text-emerald-500">Vectorizar (RAG)</span>
                          </DropdownMenuItem>
                          <div className="h-px bg-border/40 my-1" />
                          <DropdownMenuItem 
                            onClick={(e) => { e.stopPropagation(); handleDelete(doc.id, doc.filename); }} 
                            className="gap-2 cursor-pointer py-2 px-3 text-destructive focus:text-destructive focus:bg-destructive/10"
                          >
                            <Trash2 className="h-4 w-4" />
                            <span className="font-medium">Eliminar</span>
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
          )
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
      </div>

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

      {/* Rename Dialog */}
      <Dialog open={isRenameDialogOpen} onOpenChange={setIsRenameDialogOpen}>
        <DialogContent className="sm:max-w-md rounded-[2rem] border-primary/10 shadow-2xl">
          <DialogHeader>
            <DialogTitle className="text-2xl font-bold flex items-center gap-3">
              <div className="p-2 rounded-xl bg-primary/10 text-primary">
                <Edit3 className="h-6 w-6" />
              </div>
              Renombrar {itemToRename?.type === 'doc' ? 'Archivo' : 'Carpeta'}
            </DialogTitle>
          </DialogHeader>
          <div className="py-6 space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Nuevo nombre</label>
              <Input
                placeholder="Nombre"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleRename()}
                autoFocus
              />
            </div>
          </div>
          <DialogFooter className="sm:justify-end gap-3">
            <Button variant="ghost" onClick={() => setIsRenameDialogOpen(false)} className="rounded-xl h-12 px-6">
              Cancelar
            </Button>
            <Button 
              onClick={handleRename} 
              disabled={isRenaming || !newName.trim()}
              className="rounded-xl h-12 px-8 bg-primary shadow-lg shadow-primary/20 font-bold"
            >
              {isRenaming ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Save className="h-4 w-4 mr-2" />}
              Guardar Cambios
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Move Item to Folder Dialog */}
      <Dialog open={isMoveItemDialogOpen} onOpenChange={setIsMoveItemDialogOpen}>
        <DialogContent className="sm:max-w-md rounded-[2rem] border-primary/10 shadow-2xl">
          <DialogHeader>
            <DialogTitle className="text-2xl font-bold flex items-center gap-3">
              <div className="p-2 rounded-xl bg-primary/10 text-primary">
                <FolderOutput className="h-6 w-6" />
              </div>
              Mover
            </DialogTitle>
          </DialogHeader>
          <div className="py-6 space-y-4">
            <p className="text-sm text-muted-foreground">
              Selecciona la carpeta de destino para <strong>{itemToMove?.name || (selectedDocs.length + selectedFolders.length + " ítems seleccionados")}</strong>.
            </p>
            <Select 
              value={selectedTargetFolderForMove || "null"} 
              onValueChange={setSelectedTargetFolderForMove}
            >
              <SelectTrigger className="w-full h-12 rounded-xl border-primary/20">
                <SelectValue placeholder="Carpeta destino" />
              </SelectTrigger>
              <SelectContent className="max-h-[300px]">
                <SelectItem value="null">
                  <div className="flex items-center gap-2 font-bold">
                    <FileBox className="h-4 w-4" />
                    Inicio (Raíz)
                  </div>
                </SelectItem>
                {allFolders.map(f => (
                  <SelectItem key={f.id} value={f.id}>
                    <div className="flex items-center gap-2">
                      <Folder className="h-4 w-4 text-orange-500" />
                      {f.name}
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <DialogFooter className="sm:justify-end gap-3">
            <Button variant="ghost" onClick={() => setIsMoveItemDialogOpen(false)} className="rounded-xl h-12 px-6">
              Cancelar
            </Button>
            <Button 
              onClick={() => {
                if (itemToMove) {
                  handleDropToFolder(itemToMove.id, selectedTargetFolderForMove, itemToMove.type);
                } else if (selectedDocs.length > 0 || selectedFolders.length > 0) {
                  const firstDocId = selectedDocs[0];
                  const firstFolderId = selectedFolders[0];
                  if (firstDocId) {
                    handleDropToFolder(firstDocId, selectedTargetFolderForMove, 'doc');
                  } else if (firstFolderId) {
                    handleDropToFolder(firstFolderId, selectedTargetFolderForMove, 'folder');
                  }
                }
                setIsMoveItemDialogOpen(false);
              }} 
              disabled={isMoving}
              className="rounded-xl h-12 px-8 bg-primary shadow-lg shadow-primary/20 font-bold"
            >
              {isMoving ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <FolderOutput className="h-4 w-4 mr-2" />}
              Mover
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

      <Dialog open={isShareDialogOpen} onOpenChange={setIsShareDialogOpen}>
        <DialogContent className="sm:max-w-2xl rounded-[2rem] border-primary/10 shadow-2xl">
          <DialogHeader>
            <DialogTitle className="text-2xl font-bold flex items-center gap-3">
              <div className="p-2 rounded-xl bg-primary/10 text-primary">
                <Share2 className="h-6 w-6" />
              </div>
              Compartir Documento
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-6 py-2">
            <div className="rounded-2xl border p-4 space-y-3">
              <p className="text-sm font-semibold">Enlace publico</p>
              <p className="text-xs text-muted-foreground">
                Crea un enlace para abrir el documento sin seleccionar una cuenta especifica.
              </p>
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="public-can-edit"
                  checked={shareCanEdit}
                  onCheckedChange={(checked) => setShareCanEdit(checked === true)}
                />
                <label htmlFor="public-can-edit" className="text-xs cursor-pointer">
                  Permitir edicion (desactivar para solo vista)
                </label>
              </div>
              <Button onClick={handleCreatePublicShare} disabled={isCreatingShare} className="rounded-xl">
                {isCreatingShare ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Link2 className="h-4 w-4 mr-2" />}
                Crear Enlace Publico
              </Button>
            </div>

            <div className="rounded-2xl border p-4 space-y-3">
              <p className="text-sm font-semibold">Comparticion privada</p>
              <p className="text-xs text-muted-foreground">
                Invita una cuenta de KognitoAI por nombre, usuario o email.
              </p>
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="private-can-edit"
                  checked={shareCanEdit}
                  onCheckedChange={(checked) => setShareCanEdit(checked === true)}
                />
                <label htmlFor="private-can-edit" className="text-xs cursor-pointer">
                  Permitir edicion (desactivar para solo vista)
                </label>
              </div>
              <Input
                placeholder="Escribe nombre, usuario o email"
                value={privateSearch}
                onChange={(e) => searchPrivateUsers(e.target.value)}
              />

              {privateSuggestions.length > 0 && (
                <div className="max-h-40 overflow-auto rounded-xl border">
                  {privateSuggestions.map((candidate) => {
                    const label = candidate.name || candidate.username || candidate.email || 'Cuenta';
                    const meta = [candidate.username ? `@${candidate.username}` : null, candidate.email]
                      .filter(Boolean)
                      .join(' • ');
                    return (
                      <button
                        key={candidate.account_id}
                        type="button"
                        onClick={() => setSelectedPrivateUser(candidate)}
                        className={`w-full text-left px-3 py-2 text-sm hover:bg-muted transition-colors ${selectedPrivateUser?.account_id === candidate.account_id ? 'bg-primary/10' : ''}`}
                      >
                        <div className="font-medium">{label}</div>
                        {meta && <div className="text-xs text-muted-foreground">{meta}</div>}
                      </button>
                    );
                  })}
                </div>
              )}

              <Button
                onClick={handleCreatePrivateShare}
                disabled={isCreatingShare || !selectedPrivateUser}
                className="rounded-xl"
              >
                {isCreatingShare ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <UserPlus className="h-4 w-4 mr-2" />}
                Compartir con Cuenta
              </Button>
            </div>

            <div className="rounded-2xl border p-4 space-y-3">
              <p className="text-sm font-semibold">Accesos actuales</p>
              {isLoadingShareLinks ? (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Cargando accesos...
                </div>
              ) : shareLinks.length === 0 ? (
                <p className="text-sm text-muted-foreground">No hay accesos compartidos todavia.</p>
              ) : (
                <div className="space-y-2 max-h-56 overflow-auto">
                  {shareLinks.map((link) => {
                    const privateLabel = link.target_name || link.target_username || link.target_email || 'Cuenta privada';
                    const shareUrl = link.share_url ? `${window.location.origin}${link.share_url}` : null;
                    return (
                      <div key={link.id} className="rounded-xl border p-3 flex items-center justify-between gap-3">
                        <div className="min-w-0">
                          <p className="text-sm font-medium truncate">
                            {link.scope === 'public' ? 'Enlace publico' : `Privado: ${privateLabel}`}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {link.can_edit ? 'Con edicion' : 'Solo lectura'}
                          </p>
                          {shareUrl && (
                            <p className="text-xs text-muted-foreground truncate">{shareUrl}</p>
                          )}
                        </div>
                        <div className="flex items-center gap-2">
                          {shareUrl && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={async () => {
                                await navigator.clipboard.writeText(shareUrl);
                                toast.success('Enlace copiado');
                              }}
                            >
                              Copiar
                            </Button>
                          )}
                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-destructive"
                            onClick={() => handleDeleteShareLink(link.id)}
                          >
                            Quitar
                          </Button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setIsShareDialogOpen(false)}>
              Cerrar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Bulk Delete Confirm Dialog */}
      <Dialog open={bulkDeleteConfirmOpen} onOpenChange={setBulkDeleteConfirmOpen}>
        <DialogContent className="sm:max-w-md rounded-[2rem] border-destructive/10 shadow-2xl">
          <DialogHeader>
            <DialogTitle className="text-2xl font-bold flex items-center gap-3 text-destructive">
              <div className="p-2 rounded-xl bg-destructive/10 text-destructive">
                <Trash2 className="h-6 w-6" />
              </div>
              Eliminar Elementos
            </DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <p className="text-sm text-muted-foreground">
              ¿Estás seguro de que deseas eliminar los {selectedDocs.length + selectedFolders.length} elementos seleccionados? Esta acción no se puede deshacer.
            </p>
          </div>
          <DialogFooter className="sm:justify-end gap-3">
            <Button variant="outline" onClick={() => setBulkDeleteConfirmOpen(false)} className="rounded-xl h-12 px-6">
              Cancelar
            </Button>
            <Button 
              variant="destructive" 
              onClick={handleBulkDelete} 
              className="rounded-xl h-12 px-8 shadow-lg shadow-destructive/20 font-bold"
            >
              Sí, eliminar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
    </>
  );
}
