'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Input } from '@/components/ui/input';
import { Checkbox } from '@/components/ui/checkbox';
import { Loader2, FileText, Github, Image as ImageIcon } from 'lucide-react';
import { toast } from 'sonner';
import apiClient from '@/lib/api';
import { AlbumResponse, PhotoResponse } from '@/types/gallery';
import { SelectedContextItem } from '@/types/context';
import NextImage from 'next/image';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { ChevronRight, Folder, File as FileIcon } from 'lucide-react';

interface Note {
  id: number;
  title?: string;
  content: string;
  category?: string;
  created_at: string;
  updated_at: string;
  workspace_id?: string;
  workspace_name?: string;
  workspace_color?: string;
}

interface ContextSelectorDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectContext: (selectedItems: SelectedContextItem[]) => void;
  onSelectNote: (note: Note) => void;
  currentContext: SelectedContextItem[];
  workspaceId?: string;
  initialTab?: 'context' | 'notes' | 'onlyoffice' | 'github' | 'galleries';
}

interface OnlyOfficeDocument {
  id: string;
  filename: string;
}

const ContextSelectorDialog: React.FC<ContextSelectorDialogProps> = ({
  isOpen,
  onClose,
  onSelectContext,
  onSelectNote,
  currentContext,
  workspaceId,
  initialTab = 'context',
}) => {
  const [selectedDocuments, setSelectedDocuments] = useState<SelectedContextItem[]>(currentContext || []);
  const [collections, setCollections] = useState<{ topic: string; items: SelectedContextItem[] }[]>([]);
  const [expandedTopics, setExpandedTopics] = useState<Record<string, boolean>>({});
  const [isLoadingContext, setIsLoadingContext] = useState(false);

  // Estado para notas
  const [notes, setNotes] = useState<Note[]>([]);
  const [loadingNotes, setLoadingNotes] = useState<boolean>(false);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [activeTab, setActiveTab] = useState<'context' | 'notes' | 'onlyoffice' | 'github' | 'galleries'>(initialTab as any);

  // Estado para OnlyOffice
  const [onlyOfficeDocuments, setOnlyOfficeDocuments] = useState<OnlyOfficeDocument[]>([]);
  const [isLoadingOnlyOffice, setIsLoadingOnlyOffice] = useState(false);

  // Estado para GitHub
  const [githubRepos, setGithubRepos] = useState<any[]>([]);
  const [isLoadingGithub, setIsLoadingGithub] = useState(false);
  const [githubUrl, setGithubUrl] = useState('');

  // Estado para Galerías y Fotos
  const [albums, setAlbums] = useState<AlbumResponse[]>([]);
  const [isLoadingGalleries, setIsLoadingGalleries] = useState(false);
  const [expandedAlbums, setExpandedAlbums] = useState<Record<string, boolean>>({});

  const fetchDocuments = useCallback(async () => {
    setIsLoadingContext(true);
    try {
      const apiParams: { workspace_id?: string | null } = {};
      if (workspaceId) {
        apiParams.workspace_id = workspaceId;
      }
      
      const [collectionsRes, documentsRes] = await Promise.all([
        apiClient.get('/api/collections', { params: { ...apiParams } }),
        apiClient.get('/api/documents/list-documents', { params: { ...apiParams } }),
      ]);

      const fetchedCollections = collectionsRes.data.map((col: any) => ({
        id: col.id,
        type: 'collection',
        name: col.name,
        title: col.name,
        topic: col.name,
      }));

      const fetchedDocuments = documentsRes.data.map((doc: any) => ({
        id: doc.document_id,
        type: 'document',
        name: doc.title || doc.file_name,
        title: doc.title || doc.file_name,
        topic: doc.topic,
        file_name: doc.file_name,
      }));

      const groupedItems: { [key: string]: { id: string; topic: string; items: SelectedContextItem[] } } = {};
      let groupIdCounter = 0;

      fetchedCollections.forEach((col: SelectedContextItem) => {
        const topicKey = col.topic || 'Sin categoría';
        if (!groupedItems[topicKey]) {
          groupedItems[topicKey] = { id: `group-${groupIdCounter++}`, topic: topicKey, items: [] };
        }
        groupedItems[topicKey].items.push(col);
      });

      fetchedDocuments.forEach((doc: SelectedContextItem) => {
        const topicKey = doc.topic || 'Sin categoría';
        if (!groupedItems[topicKey]) {
          groupedItems[topicKey] = { id: `group-${groupIdCounter++}`, topic: topicKey, items: [] };
        }
        groupedItems[topicKey].items.push(doc);
      });
      
      setCollections(Object.values(groupedItems));
    } catch (error) {
      toast.error('Error al cargar los documentos y colecciones');
      console.error(error);
    } finally {
      setIsLoadingContext(false);
    }
  }, [workspaceId]);

  const fetchOnlyOfficeDocuments = useCallback(async () => {
    setIsLoadingOnlyOffice(true);
    try {
      const params: { workspace_id?: string } = {};
      if (workspaceId) {
        params.workspace_id = workspaceId;
      }

      const response = await apiClient.get('/api/onlyoffice/list', { params });
      const docs: OnlyOfficeDocument[] = (response.data || []).map((doc: any) => ({
        id: String(doc.id),
        filename: doc.filename || 'Documento sin nombre',
      }));
      setOnlyOfficeDocuments(docs);
    } catch (error) {
      console.error('Error fetching OnlyOffice documents:', error);
      toast.error('Error al cargar documentos de OnlyOffice.');
    } finally {
      setIsLoadingOnlyOffice(false);
    }
  }, [workspaceId]);

  const fetchGithubRepositories = useCallback(async () => {
    setIsLoadingGithub(true);
    try {
      const response = await apiClient.post('/api/github/list-github-repositories', {});
      setGithubRepos(response.data || []);
    } catch (error) {
      console.error('Error fetching GitHub repositories:', error);
      toast.error('Error al cargar repositorios de GitHub.');
    } finally {
      setIsLoadingGithub(false);
    }
  }, []);

  const fetchGalleries = useCallback(async () => {
    setIsLoadingGalleries(true);
    try {
      const params: Record<string, any> = {};
      if (workspaceId) {
        params.workspace_id = workspaceId;
      }
      const response = await apiClient.get<AlbumResponse[]>('/api/galleries/albums', { params });
      setAlbums(response.data || []);
    } catch (error) {
      console.error('Error fetching galleries:', error);
      toast.error('Error al cargar galerías y fotos.');
    } finally {
      setIsLoadingGalleries(false);
    }
  }, [workspaceId]);

  const toggleAlbumExpansion = async (albumId: string) => {
    setExpandedAlbums(prev => ({ ...prev, [albumId]: !prev[albumId] }));
    const targetAlbum = albums.find(a => a.id === albumId);
    if (targetAlbum && (!targetAlbum.photos || targetAlbum.photos.length === 0)) {
      try {
        const res = await apiClient.get<AlbumResponse>(`/api/galleries/albums/${albumId}`);
        if (res.data) {
          setAlbums(prev => prev.map(a => a.id === albumId ? { ...a, photos: res.data.photos || [] } : a));
        }
      } catch (error) {
        console.error('Error fetching album photos:', error);
      }
    }
  };

  const handleSelectPhoto = (album: AlbumResponse, photo: PhotoResponse) => {
    const photoId = photo.id;
    setSelectedDocuments(prev => {
      const isSelected = prev.some(d => d.id === photoId && d.type === 'image');
      if (isSelected) {
        return prev.filter(d => !(d.id === photoId && d.type === 'image'));
      } else {
        const fileName = photo.file_path.split('/').pop() || photo.id;
        const photoItem: SelectedContextItem = {
          id: photoId,
          type: 'image',
          name: `[Foto] ${album.name} - ${fileName}`,
          title: fileName,
          topic: album.name,
          file_name: photo.file_path,
          content: `${process.env.NEXT_PUBLIC_API_URL || ''}/media/${photo.file_path}`
        };
        return [...prev, photoItem];
      }
    });
  };

  const handleSelectAlbumGroup = async (album: AlbumResponse) => {
    let currentPhotos = album.photos || [];
    if (currentPhotos.length === 0) {
      try {
        const res = await apiClient.get<AlbumResponse>(`/api/galleries/albums/${album.id}`);
        if (res.data && res.data.photos) {
          currentPhotos = res.data.photos;
          setAlbums(prev => prev.map(a => a.id === album.id ? { ...a, photos: currentPhotos } : a));
        }
      } catch (error) {
        console.error('Error fetching album photos for group selection:', error);
        return;
      }
    }

    if (currentPhotos.length === 0) return;

    setSelectedDocuments(prev => {
      const allSelected = currentPhotos.every(p => prev.some(d => d.id === p.id && d.type === 'image'));
      if (allSelected) {
        return prev.filter(selected => !currentPhotos.some(p => p.id === selected.id && selected.type === 'image'));
      } else {
        const newSelected = [...prev];
        currentPhotos.forEach(photo => {
          if (!newSelected.some(d => d.id === photo.id && d.type === 'image')) {
            const fileName = photo.file_path.split('/').pop() || photo.id;
            const photoItem: SelectedContextItem = {
              id: photo.id,
              type: 'image',
              name: `[Foto] ${album.name} - ${fileName}`,
              title: fileName,
              topic: album.name,
              file_name: photo.file_path,
              content: `${process.env.NEXT_PUBLIC_API_URL || ''}/media/${photo.file_path}`
            };
            newSelected.push(photoItem);
          }
        });
        return newSelected;
      }
    });
  };

  const fetchNotes = useCallback(async () => {
    setLoadingNotes(true);
    try {
      const response = await fetch('/api/notes/list-notes', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('authToken')}`,
        },
        body: JSON.stringify({
          search_term: searchTerm,
          workspace_id: workspaceId,
          skip: 0,
          limit: 100,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setNotes(data.notes);
    } catch (error) {
      console.error('Error fetching notes:', error);
      toast.error('Error al cargar las notas.');
    } finally {
      setLoadingNotes(false);
    }
  }, [searchTerm, workspaceId]);

  useEffect(() => {
    if (isOpen) {
      setSelectedDocuments(currentContext || []);
      setActiveTab(initialTab as any);
      fetchDocuments();
      fetchNotes();
      fetchOnlyOfficeDocuments();
      fetchGithubRepositories();
      fetchGalleries();
    }
  }, [isOpen, initialTab, currentContext, fetchDocuments, fetchNotes, fetchOnlyOfficeDocuments, fetchGithubRepositories, fetchGalleries]);

  const toggleTopicExpansion = (topic: string) => {
    setExpandedTopics(prev => ({ ...prev, [topic]: !prev[topic] }));
  };

  const handleSelectItem = (item: SelectedContextItem) => {
    setSelectedDocuments(prev => {
      const isSelected = prev.some(d => d.id === item.id && d.type === item.type);
      if (isSelected) {
        return prev.filter(d => !(d.id === item.id && d.type === item.type));
      } else {
        return [...prev, item];
      }
    });
  };

  const handleSelectGroup = (group: { topic: string; items: SelectedContextItem[] }) => {
    setSelectedDocuments(prev => {
      const allItemsInGroupSelected = group.items.every(item => isItemSelected(item));
      if (allItemsInGroupSelected) {
        return prev.filter(selected => !group.items.some(item => item.id === selected.id && item.type === selected.type));
      } else {
        const newSelected = [...prev];
        group.items.forEach(item => {
          if (!isItemSelected(item)) {
            newSelected.push(item);
          }
        });
        return newSelected;
      }
    });
  };

  const handleSelectGithubRepo = async (repo: any) => {
    const isSelected = selectedDocuments.some(d => d.id === repo.url && d.type === 'repository');
    
    if (isSelected) {
      setSelectedDocuments(prev => prev.filter(d => !(d.id === repo.url && d.type === 'repository')));
      return;
    }

    setIsLoadingGithub(true);
    try {
      const response = await apiClient.get(`/api/github/tree_flat?repo_url=${encodeURIComponent(repo.url)}`);
      const tree = response.data.options || [];
      const treeString = tree.join('\n');

      const contextItem: SelectedContextItem = {
        id: repo.url,
        type: 'repository',
        name: `[GitHub] ${repo.name}`,
        title: repo.name,
        topic: 'GitHub',
        content: `Árbol de archivos del repositorio ${repo.name}:\n${treeString}`
      };

      setSelectedDocuments(prev => [...prev, contextItem]);
      toast.success(`Repositorio ${repo.name} añadido al contexto.`);
    } catch (error) {
      console.error('Error fetching repo tree:', error);
      toast.error('Error al obtener el árbol de archivos del repositorio.');
    } finally {
      setIsLoadingGithub(false);
    }
  };

  const handleAddCustomGithubRepo = async () => {
    if (!githubUrl.trim()) {
      toast.error('Por favor, ingresa una URL de GitHub válida.');
      return;
    }

    // Basic URL validation
    const githubRegex = /^(https?:\/\/)?(www\.)?github\.com\/[a-zA-Z0-9_-]+\/[a-zA-Z0-9_-]+(\/.*)?$/;
    if (!githubRegex.test(githubUrl)) {
      toast.error('La URL de GitHub no es válida.');
      return;
    }

    setIsLoadingGithub(true);
    try {
      const response = await apiClient.get(`/api/github/tree_flat?repo_url=${encodeURIComponent(githubUrl)}`);
      const tree = response.data.options || [];
      const treeString = tree.join('\n');

      const repoNameMatch = githubUrl.match(/github\.com\/([a-zA-Z0-9_-]+)\/([a-zA-Z0-9_-]+)/);
      const repoName = repoNameMatch ? `${repoNameMatch[1]}/${repoNameMatch[2]}` : githubUrl;

      const contextItem: SelectedContextItem = {
        id: githubUrl,
        type: 'repository',
        name: `[GitHub] ${repoName}`,
        title: repoName,
        topic: 'GitHub',
        content: `Árbol de archivos del repositorio ${repoName}:\n${treeString}`
      };

      setSelectedDocuments(prev => {
        // Evitar duplicados si ya se añadió manualmente o estaba en la lista
        const isAlreadySelected = prev.some(d => d.id === githubUrl && d.type === 'repository');
        if (isAlreadySelected) {
          toast.info('Este repositorio ya ha sido añadido al contexto.');
          return prev;
        }
        return [...prev, contextItem];
      });
      toast.success(`Repositorio ${repoName} añadido al contexto.`);
      setGithubUrl(''); // Clear input after adding
    } catch (error) {
      console.error('Error fetching custom repo tree:', error);
      toast.error('Error al obtener el árbol de archivos del repositorio personalizado. Asegúrate de que la URL sea pública o de que el agente tenga acceso.');
    } finally {
      setIsLoadingGithub(false);
    }
  };

  const handleApplyContext = () => {
    onSelectContext(selectedDocuments);
    onClose();
    toast.success(`Contexto actualizado con ${selectedDocuments.length} ítem(s)`);
  };

  const handleSelectNote = (note: Note) => {
    onSelectNote(note);
    onClose();
  };

  const isItemSelected = (item: SelectedContextItem) => {
    return selectedDocuments.some(d => d.id === item.id && d.type === item.type);
  };

  const isGroupSelected = (group: { topic: string; items: SelectedContextItem[] }) => {
    return group.items.every(item => isItemSelected(item));
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[600px] max-h-[80vh]">
        <DialogHeader>
          <DialogTitle>Seleccionar Contexto</DialogTitle>
          <DialogDescription>
            Selecciona documentos, colecciones, notas u otros elementos para añadir al contexto de tu conversación.
          </DialogDescription>
        </DialogHeader>
        <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as any)} className="w-full min-w-0 overflow-hidden">
          <TabsList className="grid w-full grid-cols-5 gap-1 min-w-0 overflow-hidden">
            <TabsTrigger value="context" className="min-w-0 px-2 text-xs sm:text-sm truncate">Contexto</TabsTrigger>
            <TabsTrigger value="notes" className="min-w-0 px-2 text-xs sm:text-sm truncate">Notas</TabsTrigger>
            <TabsTrigger value="onlyoffice" className="min-w-0 px-2 text-xs sm:text-sm truncate">OnlyOffice</TabsTrigger>
            <TabsTrigger value="github" className="min-w-0 px-2 text-xs sm:text-sm truncate">GitHub</TabsTrigger>
            <TabsTrigger value="galleries" className="min-w-0 px-2 text-xs sm:text-sm truncate">Galerías</TabsTrigger>
          </TabsList>
          <TabsContent value="context" className="space-y-4">
            <div className="flex justify-between items-center">
              <p className="text-sm text-muted-foreground">
                {selectedDocuments.length} ítem(s) seleccionado(s)
              </p>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setSelectedDocuments([])}
                disabled={selectedDocuments.length === 0}
              >
                Limpiar
              </Button>
            </div>
            <ScrollArea className="h-60">
              {isLoadingContext ? (
                <div className="flex items-center justify-center p-4">
                  <Loader2 className="h-4 w-4 animate-spin" />
                </div>
              ) : collections.length === 0 ? (
                <div className="p-4 text-center text-sm text-muted-foreground">
                  No hay conocimiento disponible
                </div>
              ) : (
                <div className="p-2">
                  {collections.map((group) => (
                    <Collapsible key={group.topic} open={expandedTopics[group.topic]} onOpenChange={() => toggleTopicExpansion(group.topic)}>
                      <CollapsibleTrigger asChild>
                        <div className="flex items-center space-x-2 p-2 hover:bg-muted rounded-md cursor-pointer">
                          <ChevronRight className={`h-4 w-4 transition-transform ${expandedTopics[group.topic] ? 'rotate-90' : ''}`} />
                          <Checkbox
                            id={`group-${group.topic}`}
                            checked={isGroupSelected(group)}
                            onCheckedChange={() => handleSelectGroup(group)}
                          />
                          <label
                            htmlFor={`group-${group.topic}`}
                            className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 flex-1 cursor-pointer"
                          >
                            <Folder className="inline-block h-4 w-4 mr-2 text-primary" />
                            {group.topic} ({group.items.length})
                          </label>
                        </div>
                      </CollapsibleTrigger>
                      <CollapsibleContent>
                        <div className="ml-6 border-l border-border">
                          {group.items.map((item) => (
                            <div
                              key={`${item.type}-${item.id}`}
                              className="flex items-center space-x-2 p-2 hover:bg-muted rounded-md cursor-pointer"
                              onClick={() => handleSelectItem(item)}
                            >
                              <Checkbox
                                id={`${item.type}-${item.id}`}
                                checked={isItemSelected(item)}
                                onCheckedChange={() => handleSelectItem(item)}
                              />
                              <label
                                htmlFor={`${item.type}-${item.id}`}
                                className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 flex-1 cursor-pointer"
                              >
                                <div className="flex items-center">
                                  {item.type === 'document' ? <FileIcon className="h-4 w-4 mr-2 text-secondary flex-shrink-0" /> : <Folder className="h-4 w-4 mr-2 text-primary flex-shrink-0" />}
                                  <div className="flex-grow">
                                    <div className="font-medium truncate">{item.name || item.title}</div>
                                    <div className="text-xs text-muted-foreground capitalize">{item.type}</div>
                                  </div>
                                </div>
                              </label>
                            </div>
                          ))}
                        </div>
                      </CollapsibleContent>
                    </Collapsible>
                  ))}
                </div>
              )}
            </ScrollArea>
            <Button onClick={handleApplyContext} disabled={isLoadingContext} className="w-full">
              Aplicar Contexto
            </Button>
          </TabsContent>
          <TabsContent value="notes" className="space-y-4">
            <Input
              placeholder="Buscar notas..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  fetchNotes();
                }
              }}
            />
            <ScrollArea className="h-60">
              {loadingNotes ? (
                <div className="flex justify-center items-center h-32">
                  <Loader2 className="h-8 w-8 animate-spin text-primary" />
                </div>
              ) : notes.length === 0 ? (
                <p className="p-4 text-center text-muted-foreground">No se encontraron notas.</p>
              ) : (
                <div className="p-2">
                  {notes.map((note) => (
                    <Button
                      key={note.id}
                      variant="ghost"
                      className="w-full justify-start text-left h-auto py-2 px-3 mb-1"
                      onClick={() => handleSelectNote(note)}
                    >
                      <FileText className="mr-2 h-4 w-4 text-muted-foreground" />
                      <div className="flex flex-col items-start">
                        <span className="font-medium">{note.title || 'Sin título'}</span>
                        <span className="text-xs text-muted-foreground truncate w-full">
                          {note.content.substring(0, 100)}...
                        </span>
                      </div>
                    </Button>
                  ))}
                </div>
              )}
            </ScrollArea>
          </TabsContent>
          <TabsContent value="onlyoffice" className="space-y-4">
            <div className="flex justify-between items-center">
              <p className="text-sm text-muted-foreground">
                {selectedDocuments.length} ítem(s) seleccionado(s)
              </p>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setSelectedDocuments([])}
                disabled={selectedDocuments.length === 0}
              >
                Limpiar
              </Button>
            </div>
            <ScrollArea className="h-60">
              {isLoadingOnlyOffice ? (
                <div className="flex items-center justify-center p-4">
                  <Loader2 className="h-4 w-4 animate-spin" />
                </div>
              ) : onlyOfficeDocuments.length === 0 ? (
                <div className="p-4 text-center text-sm text-muted-foreground">
                  No se encontraron documentos de OnlyOffice.
                </div>
              ) : (
                <div className="p-2 space-y-1">
                  {onlyOfficeDocuments.map((doc) => {
                    const contextItem: SelectedContextItem = {
                      id: doc.id,
                      type: 'document',
                      name: `[OnlyOffice] ${doc.filename}`,
                      title: doc.filename,
                      topic: 'OnlyOffice',
                    };

                    return (
                      <div
                        key={doc.id}
                        className="flex items-center space-x-2 p-2 hover:bg-muted rounded-md cursor-pointer"
                        onClick={() => handleSelectItem(contextItem)}
                      >
                        <Checkbox
                          id={`onlyoffice-${doc.id}`}
                          checked={isItemSelected(contextItem)}
                          onCheckedChange={() => handleSelectItem(contextItem)}
                        />
                        <label
                          htmlFor={`onlyoffice-${doc.id}`}
                          className="text-sm font-medium leading-none flex-1 cursor-pointer"
                        >
                          <div className="font-medium truncate">{doc.filename}</div>
                          <div className="text-xs text-muted-foreground">OnlyOffice</div>
                        </label>
                      </div>
                    );
                  })}
                </div>
              )}
            </ScrollArea>
            <Button onClick={handleApplyContext} disabled={isLoadingOnlyOffice} className="w-full">
              Aplicar Contexto
            </Button>
          </TabsContent>
          <TabsContent value="github" className="space-y-4">
            <div className="flex flex-col gap-2 mb-4">
              <Input
                placeholder="Ingresa URL de GitHub (ej: https://github.com/usuario/repo)"
                value={githubUrl}
                onChange={(e) => setGithubUrl(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    handleAddCustomGithubRepo();
                  }
                }}
              />
              <Button 
                onClick={handleAddCustomGithubRepo} 
                disabled={isLoadingGithub || !githubUrl.trim()}
              >
                {isLoadingGithub ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                Vincular Repositorio por URL
              </Button>
            </div>
            <div className="flex justify-between items-center">
              <p className="text-sm text-muted-foreground">
                {selectedDocuments.length} ítem(s) seleccionado(s)
              </p>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setSelectedDocuments([])}
                disabled={selectedDocuments.length === 0}
              >
                Limpiar
              </Button>
            </div>
            <ScrollArea className="h-60">
              {isLoadingGithub ? (
                <div className="flex items-center justify-center p-4">
                  <Loader2 className="h-4 w-4 animate-spin" />
                </div>
              ) : githubRepos.length === 0 ? (
                <div className="p-4 text-center text-sm text-muted-foreground">
                  No se encontraron repositorios de GitHub vinculados.
                </div>
              ) : (
                <div className="p-2 space-y-1">
                  {githubRepos.map((repo) => {
                    const isSelected = selectedDocuments.some(d => d.id === repo.url && d.type === 'repository');

                    return (
                      <div
                        key={repo.url}
                        className="flex items-center space-x-2 p-2 hover:bg-muted rounded-md cursor-pointer"
                        onClick={() => handleSelectGithubRepo(repo)}
                      >
                        <Checkbox
                          id={`github-${repo.url}`}
                          checked={isSelected}
                          onCheckedChange={() => handleSelectGithubRepo(repo)}
                        />
                        <label
                          htmlFor={`github-${repo.url}`}
                          className="text-sm font-medium leading-none flex-1 cursor-pointer"
                        >
                          <div className="flex items-center">
                            <Github className="h-4 w-4 mr-2 text-foreground flex-shrink-0" />
                            <div className="flex-grow">
                              <div className="font-medium truncate">{repo.name}</div>
                              <div className="text-xs text-muted-foreground">{repo.url}</div>
                            </div>
                          </div>
                        </label>
                      </div>
                    );
                  })}
                </div>
              )}
            </ScrollArea>
            <Button onClick={handleApplyContext} disabled={isLoadingGithub} className="w-full">
              Aplicar Contexto
            </Button>
          </TabsContent>
          <TabsContent value="galleries" className="space-y-4">
            <div className="flex justify-between items-center">
              <p className="text-sm text-muted-foreground">
                {selectedDocuments.filter(d => d.type === 'image').length} foto(s) de galería seleccionada(s)
              </p>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setSelectedDocuments(prev => prev.filter(d => d.type !== 'image'))}
                disabled={!selectedDocuments.some(d => d.type === 'image')}
              >
                Limpiar Selección de Fotos
              </Button>
            </div>
            <ScrollArea className="h-60">
              {isLoadingGalleries ? (
                <div className="flex items-center justify-center p-4">
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  <span className="text-sm text-muted-foreground">Cargando galerías...</span>
                </div>
              ) : albums.length === 0 ? (
                <div className="p-4 text-center text-sm text-muted-foreground">
                  No hay álbumes ni fotos disponibles en este espacio.
                </div>
              ) : (
                <div className="p-2 space-y-2">
                  {albums.map((album) => {
                    const isExpanded = expandedAlbums[album.id];
                    const albumPhotos = album.photos || [];
                    const isGroupSelected = albumPhotos.length > 0 && albumPhotos.every(p => selectedDocuments.some(d => d.id === p.id && d.type === 'image'));

                    return (
                      <Collapsible key={album.id} open={isExpanded} onOpenChange={() => toggleAlbumExpansion(album.id)} className="border rounded-md p-2 bg-card">
                        <div className="flex items-center justify-between">
                          <CollapsibleTrigger asChild>
                            <div className="flex items-center space-x-2 cursor-pointer flex-grow min-w-0 py-1">
                              <ChevronRight className={`h-4 w-4 transition-transform flex-shrink-0 ${isExpanded ? 'rotate-90' : ''}`} />
                              <ImageIcon className="h-4 w-4 text-primary flex-shrink-0" />
                              <span className="font-medium text-sm truncate">{album.name}</span>
                              <span className="text-xs text-muted-foreground">
                                ({album.total_photos !== undefined ? album.total_photos : albumPhotos.length} fotos)
                              </span>
                            </div>
                          </CollapsibleTrigger>
                          <div className="flex items-center space-x-2 pl-2">
                            <Checkbox
                              id={`album-${album.id}`}
                              checked={isGroupSelected}
                              onCheckedChange={() => handleSelectAlbumGroup(album)}
                            />
                            <label htmlFor={`album-${album.id}`} className="text-xs text-muted-foreground cursor-pointer select-none">
                              Seleccionar Todo
                            </label>
                          </div>
                        </div>

                        <CollapsibleContent className="pt-3">
                          {albumPhotos.length === 0 ? (
                            <div className="text-xs text-muted-foreground py-2 pl-6">
                              No hay fotos en este álbum o cargando...
                            </div>
                          ) : (
                            <div className="grid grid-cols-3 sm:grid-cols-4 gap-2 pl-4 pr-1">
                              {albumPhotos.map((photo) => {
                                const isSelected = selectedDocuments.some(d => d.id === photo.id && d.type === 'image');
                                const mediaUrl = `${process.env.NEXT_PUBLIC_API_URL || ''}/media/${photo.thumbnail_path || photo.file_path}`;

                                return (
                                  <div
                                    key={photo.id}
                                    onClick={() => handleSelectPhoto(album, photo)}
                                    className={`relative group rounded-md overflow-hidden border-2 cursor-pointer aspect-square bg-muted transition-all ${
                                      isSelected ? 'border-primary ring-2 ring-primary/20' : 'border-transparent hover:border-border'
                                    }`}
                                  >
                                    {/* eslint-disable-next-line @next/next/no-img-element */}
                                    <img
                                      src={mediaUrl}
                                      alt="Thumbnail"
                                      className="w-full h-full object-cover"
                                    />
                                    <div className={`absolute inset-0 bg-black/40 transition-opacity flex items-top justify-end p-1 ${
                                      isSelected ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'
                                    }`}>
                                      <Checkbox
                                        checked={isSelected}
                                        onCheckedChange={() => handleSelectPhoto(album, photo)}
                                        className="bg-background/80 border-white data-[state=checked]:bg-primary"
                                      />
                                    </div>
                                  </div>
                                );
                              })}
                            </div>
                          )}
                        </CollapsibleContent>
                      </Collapsible>
                    );
                  })}
                </div>
              )}
            </ScrollArea>
            <Button onClick={handleApplyContext} disabled={isLoadingGalleries} className="w-full">
              Aplicar Contexto
            </Button>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
};

export default ContextSelectorDialog;
