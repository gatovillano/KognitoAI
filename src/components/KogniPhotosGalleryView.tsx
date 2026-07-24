'use client';

import React, { useState, useEffect, useCallback } from 'react';
import NextImage from 'next/image';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { toast } from 'sonner';
import apiClient from '@/lib/api';
import {
  Image as ImageIcon,
  Search,
  Grid,
  Share2,
  Plus,
  Star,
  Trash2,
  MoreVertical,
  FolderHeart,
  Info,
  Edit,
  Link as LinkIcon,
  CheckSquare,
  Square,
  CheckCircle2,
  XCircle,
  GripVertical,
} from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '@/components/ui/sheet';
import { AlbumResponse, PhotoResponse } from '@/types/gallery';
import { ExtensionShareModal } from './ExtensionShareModal';
import { ReceivedSelectionsView } from './ReceivedSelectionsView';
import CreateAlbumModal from '@/components/CreateAlbumModal';
import { EditAlbumModal } from '@/components/EditAlbumModal';
import { ManageLinkedProfilesDialog } from '@/app/(dashboard)/notes/ManageLinkedProfilesDialog';
import { UploadPhotosModal } from '@/components/UploadPhotosModal';
import Lightbox from 'yet-another-react-lightbox';
import 'yet-another-react-lightbox/styles.css';

// DnD Kit imports
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  rectSortingStrategy,
  useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

interface PhotoThumbnailProps {
  photo: PhotoResponse;
  apiBase: string;
}

const PhotoThumbnail: React.FC<PhotoThumbnailProps> = ({ photo, apiBase }) => {
  const [failed, setFailed] = useState(false);
  const src = (photo.thumbnail_path && !failed)
    ? `${apiBase}/thumbnails/${photo.thumbnail_path}`
    : `${apiBase}/media/${photo.file_path}`;

  return (
    <img
      src={src}
      alt="Foto"
      className="w-full h-auto object-cover transition-transform duration-300 group-hover:scale-[1.05]"
      loading="lazy"
      onError={() => setFailed(true)}
    />
  );
};

interface SortablePhotoItemProps {
  photo: PhotoResponse;
  index: number;
  apiBase: string;
  isSelectionMode: boolean;
  isSelected: boolean;
  isCover: boolean;
  onSelect: () => void;
  onOpenLightbox: () => void;
  onToggleFavorite: () => void;
  onSetCover: () => void;
  onDelete: () => void;
}

const SortablePhotoItem: React.FC<SortablePhotoItemProps> = ({
  photo,
  index,
  apiBase,
  isSelectionMode,
  isSelected,
  isCover,
  onSelect,
  onOpenLightbox,
  onToggleFavorite,
  onSetCover,
  onDelete,
}) => {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: photo.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.6 : 1,
    zIndex: isDragging ? 50 : 'auto',
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`relative break-inside-avoid mb-4 rounded-2xl overflow-hidden bg-muted cursor-pointer shadow-sm group border transition-all duration-300 ${
        isSelected ? 'ring-4 ring-primary border-primary' : 'border-border/40'
      }`}
      onClick={(e) => {
        if (isSelectionMode) {
          onSelect();
        } else {
          onOpenLightbox();
        }
      }}
    >
      <PhotoThumbnail photo={photo} apiBase={apiBase} />

      {/* Drag Handle - only visible when not in selection mode */}
      {!isSelectionMode && (
        <div
          {...attributes}
          {...listeners}
          onClick={(e) => {
            e.stopPropagation();
            e.preventDefault();
          }}
          className="absolute top-2 left-2 bg-black/60 hover:bg-black/80 text-white p-1.5 rounded-lg shadow-md z-20 cursor-grab active:cursor-grabbing opacity-0 group-hover:opacity-100 transition-opacity"
          title="Arrastrar para reordenar"
        >
          <GripVertical className="h-4 w-4" />
        </div>
      )}

      {/* Favorite Badge */}
      {photo.is_favorite && (
        <div className="absolute top-2 right-2 bg-yellow-500 text-white p-1 rounded-full shadow-md z-10">
          <Star className="h-3 w-3 fill-white" />
        </div>
      )}

      {/* Cover Indicator */}
      {isCover && (
        <div className={`absolute top-2 bg-primary text-white text-[10px] font-bold px-2 py-0.5 rounded-md shadow-md z-10 ${
          !isSelectionMode ? 'left-10' : 'left-2'
        }`}>
          Portada
        </div>
      )}

      {/* Selection Checkbox */}
      {isSelectionMode && (
        <div className="absolute inset-0 bg-black/30 flex items-center justify-center z-20">
          <div className={`h-7 w-7 rounded-full flex items-center justify-center border-2 ${isSelected ? 'bg-primary border-primary text-white' : 'bg-black/50 border-white'}`}>
            {isSelected && <CheckCircle2 className="h-5 w-5 text-white" />}
          </div>
        </div>
      )}

      {/* Action Menu (Normal mode) */}
      {!isSelectionMode && (
        <div className="absolute bottom-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity z-10">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                className="h-7 w-7 p-0 text-white bg-black/60 hover:bg-black/80 rounded-full"
                onClick={(e) => { e.preventDefault(); e.stopPropagation(); }}
              >
                <MoreVertical className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-[180px]">
              <DropdownMenuItem onClick={(e) => { e.preventDefault(); e.stopPropagation(); onToggleFavorite(); }}>
                <Star className="mr-2 h-4 w-4 text-yellow-500" /> {photo.is_favorite ? 'Quitar Favorito' : 'Marcar Favorito'}
              </DropdownMenuItem>
              <DropdownMenuItem onClick={(e) => { e.preventDefault(); e.stopPropagation(); onSetCover(); }}>
                <ImageIcon className="mr-2 h-4 w-4" /> Portada del Álbum
              </DropdownMenuItem>
              <DropdownMenuItem onClick={(e) => { e.preventDefault(); e.stopPropagation(); onDelete(); }} className="text-destructive focus:text-destructive">
                <Trash2 className="mr-2 h-4 w-4" /> Eliminar Foto
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      )}
    </div>
  );
};

export const KogniPhotosGalleryView: React.FC = () => {
  const [albums, setAlbums] = useState<AlbumResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');

  // Selected album for detail view / share / submissions
  const [selectedAlbumId, setSelectedAlbumId] = useState<string | null>(null);
  const [selectedAlbum, setSelectedAlbum] = useState<AlbumResponse | null>(null);
  const [photos, setPhotos] = useState<PhotoResponse[]>([]);
  const [subTab, setSubTab] = useState<'photos' | 'received_selections'>('photos');

  // DnD Sensors
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  // Sync photos local state with selectedAlbum
  useEffect(() => {
    if (selectedAlbum) {
      setPhotos(selectedAlbum.photos);
    } else {
      setPhotos([]);
    }
  }, [selectedAlbum]);

  const handleDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    let oldIndex = -1;
    let newIndex = -1;

    setPhotos((prevPhotos) => {
      oldIndex = prevPhotos.findIndex((p) => p.id === active.id);
      newIndex = prevPhotos.findIndex((p) => p.id === over.id);

      if (oldIndex === -1 || newIndex === -1) return prevPhotos;

      const newPhotos = arrayMove(prevPhotos, oldIndex, newIndex);
      return newPhotos.map((p, idx) => ({ ...p, order: idx }));
    });

    if (selectedAlbumId) {
      const activeIdx = photos.findIndex((p) => p.id === active.id);
      const overIdx = photos.findIndex((p) => p.id === over.id);
      if (activeIdx !== -1 && overIdx !== -1) {
        const movedPhotos = arrayMove(photos, activeIdx, overIdx);
        const payload = movedPhotos.map((photo, index) => ({
          photo_id: photo.id,
          order: index
        }));

        try {
          await apiClient.post(`${apiBase}/api/galleries/albums/${selectedAlbumId}/reorder-photos`, payload);
          toast.success('Orden de fotos guardado.');
          fetchAlbumDetail(selectedAlbumId);
        } catch (error) {
          toast.error('Error al guardar el orden de las fotos.');
          console.error('Error reordering photos:', error);
        }
      }
    }
  };

  // Photo Selection & Batch Operations
  const [selectedPhotos, setSelectedPhotos] = useState<Set<string>>(new Set());
  const [isSelectionMode, setIsSelectionMode] = useState(false);

  // Modals and Dialogs
  const [showShareModal, setShowShareModal] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [isEditAlbumDialogOpen, setIsEditAlbumDialogOpen] = useState(false);
  const [editingAlbum, setEditingAlbum] = useState<AlbumResponse | null>(null);
  const [showManageProfilesDialog, setShowManageProfilesDialog] = useState(false);
  const [itemToManageProfiles, setItemToManageProfiles] = useState<{ id: string; name?: string; title?: string; } | null>(null);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [isInfoSheetOpen, setIsInfoSheetOpen] = useState(false);

  // Lightbox
  const [lightboxOpen, setLightboxOpen] = useState(false);
  const [lightboxIndex, setLightboxIndex] = useState(0);

  const apiBase = process.env.NEXT_PUBLIC_API_URL || '';

  const fetchAlbums = useCallback(async () => {
    setLoading(true);
    try {
      const res = await apiClient.get<AlbumResponse[]>(`${apiBase}/api/galleries/albums`);
      setAlbums(res.data);
    } catch (e: any) {
      toast.error('Error al cargar los álbumes.');
      console.error('Error fetching albums:', e);
    } finally {
      setLoading(false);
    }
  }, [apiBase]);

  const fetchAlbumDetail = useCallback(async (id: string) => {
    try {
      const res = await apiClient.get<AlbumResponse>(`${apiBase}/api/galleries/albums/${id}`);
      setSelectedAlbum(res.data);
    } catch (e: any) {
      toast.error('Error al cargar el álbum.');
    }
  }, [apiBase]);

  const handleDeleteAlbum = async (albumId: string) => {
    if (!window.confirm('¿Estás seguro de que quieres eliminar este álbum? Esta acción no se puede deshacer.')) {
      return;
    }
    try {
      await apiClient.delete(`${apiBase}/api/galleries/albums/${albumId}`);
      toast.success('Álbum eliminado exitosamente.');
      if (selectedAlbumId === albumId) {
        setSelectedAlbumId(null);
      }
      fetchAlbums();
    } catch (e: any) {
      toast.error('Error al eliminar el álbum.');
      console.error('Error deleting album:', e);
    }
  };

  // Photo Management Actions
  const handleToggleFavorite = async (photoIds: string[]) => {
    try {
      for (const photoId of photoIds) {
        await apiClient.put(`${apiBase}/api/galleries/photos/${photoId}/favorite`);
      }
      toast.success(`Se ${photoIds.length > 1 ? 'marcaron/desmarcaron' : 'marcó/desmarcó'} como favorito.`);
      if (selectedAlbumId) fetchAlbumDetail(selectedAlbumId);
      setSelectedPhotos(new Set());
    } catch (e: any) {
      toast.error(`Error al cambiar favorito: ${e.message}`);
    }
  };

  const handleDeletePhotos = async (photoIds: string[]) => {
    if (!confirm(`¿Estás seguro de que quieres eliminar ${photoIds.length} foto(s)? Esta acción no se puede deshacer.`)) return;
    try {
      for (const photoId of photoIds) {
        await apiClient.delete(`${apiBase}/api/galleries/photos/${photoId}`);
      }
      toast.success(`Se eliminaron ${photoIds.length} foto(s) exitosamente.`);
      if (selectedAlbumId) fetchAlbumDetail(selectedAlbumId);
      setSelectedPhotos(new Set());
    } catch (e: any) {
      toast.error(`Error al eliminar foto(s): ${e.message}`);
    }
  };

  const handleSetCover = async (photoId: string) => {
    if (!selectedAlbumId) return;
    try {
      await apiClient.put(`${apiBase}/api/galleries/albums/${selectedAlbumId}/cover`, { photo_id: photoId });
      toast.success('Portada del álbum actualizada.');
      fetchAlbumDetail(selectedAlbumId);
      fetchAlbums();
    } catch (e: any) {
      toast.error(`Error al establecer portada: ${e.message}`);
    }
  };

  const togglePhotoSelection = (photoId: string) => {
    setSelectedPhotos((prev) => {
      const next = new Set(prev);
      if (next.has(photoId)) {
        next.delete(photoId);
      } else {
        next.add(photoId);
      }
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selectedAlbum && selectedPhotos.size === photos.length) {
      setSelectedPhotos(new Set());
    } else if (selectedAlbum) {
      setSelectedPhotos(new Set(photos.map(p => p.id)));
    }
  };

  useEffect(() => {
    fetchAlbums();
  }, [fetchAlbums]);

  useEffect(() => {
    if (selectedAlbumId) {
      fetchAlbumDetail(selectedAlbumId);
    } else {
      setSelectedAlbum(null);
    }
    setSelectedPhotos(new Set());
    setIsSelectionMode(false);
  }, [selectedAlbumId, fetchAlbumDetail]);

  const filteredAlbums = albums.filter(a =>
    a.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (a.description && a.description.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  return (
    <div className="min-h-screen bg-background text-foreground p-4 sm:p-8 max-w-7xl mx-auto space-y-6">
      {/* Top Header Bar */}
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 rounded-3xl bg-card/70 backdrop-blur-xl border border-border shadow-md">
        <div className="flex items-center gap-3">
          <div className="h-12 w-12 rounded-2xl bg-primary/10 flex items-center justify-center flex-shrink-0">
            <ImageIcon className="h-7 w-7 text-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-black tracking-tight flex items-center gap-2">
              KogniPhotos
              <Button variant="ghost" size="icon" className="h-6 w-6 text-muted-foreground" onClick={() => setIsInfoSheetOpen(true)}>
                <Info className="h-4 w-4" />
              </Button>
            </h1>
            <p className="text-xs text-muted-foreground">Gestión inteligente visual y paneles de selección interactivos</p>
          </div>
        </div>

        {/* Search bar */}
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Buscar fotos, recuerdos o álbumes..."
            className="pl-10 rounded-2xl bg-muted/50 border-border/60 focus:bg-background transition-all"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          <Button onClick={() => setShowCreateModal(true)} className="rounded-2xl shadow-md bg-primary hover:bg-primary/90">
            <Plus className="mr-2 h-4 w-4" /> Nuevo Álbum
          </Button>
        </div>
      </header>

      {/* Main Content Area */}
      {!selectedAlbumId ? (
        // ALBUMS OVERVIEW
        <div className="space-y-6">
          <div className="flex items-center justify-between border-b border-border/60 pb-3">
            <h2 className="text-xl font-bold flex items-center gap-2">
              <FolderHeart className="h-5 w-5 text-primary" /> Mis Álbumes ({filteredAlbums.length})
            </h2>
          </div>

          {loading ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
              {[1, 2, 3, 4].map(i => (
                <div key={i} className="h-64 rounded-3xl bg-muted animate-pulse"></div>
              ))}
            </div>
          ) : filteredAlbums.length === 0 ? (
            <div className="text-center py-16 rounded-3xl border-2 border-dashed border-border p-8">
              <ImageIcon className="mx-auto h-16 w-16 text-muted-foreground/40 mb-3" />
              <h3 className="text-lg font-bold">No tienes álbumes aún</h3>
              <p className="text-sm text-muted-foreground max-w-md mx-auto mb-6">
                Los álbumes te ayudan a organizar tus fotos y videos. ¡Crea tu primer álbum para empezar!
              </p>
              <Button onClick={() => setShowCreateModal(true)} className="rounded-2xl">
                <Plus className="mr-2 h-4 w-4" /> Crear tu primer Álbum
              </Button>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
              {filteredAlbums.map((album) => {
                const cover = album.cover_photo || album.photos.find(p => p.id === album.cover_photo_id) || album.photos[0];
                const coverUrl = cover ? `${apiBase}/media/${cover.file_path}` : null;

                return (
                  <motion.div
                    key={album.id}
                    whileHover={{ scale: 1.02, y: -4 }}
                    transition={{ type: 'spring', stiffness: 300, damping: 25 }}
                    className="group cursor-pointer rounded-3xl overflow-hidden bg-card border border-border/80 shadow-md hover:shadow-2xl transition-all duration-300 flex flex-col h-72 relative"
                  >
                    <div className="relative w-full flex-1 bg-muted overflow-hidden" onClick={() => setSelectedAlbumId(album.id)}>
                      {coverUrl ? (
                        <NextImage
                          src={coverUrl}
                          alt={album.name}
                          fill
                          className="object-cover group-hover:scale-110 transition-transform duration-500"
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center text-muted-foreground/40">
                          <ImageIcon className="h-12 w-12" />
                        </div>
                      )}
                      <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent opacity-80 group-hover:opacity-90 transition-opacity"></div>

                      <div className="absolute top-3 right-3 z-10 flex items-center gap-1">
                        <Badge className="bg-black/60 backdrop-blur-md text-white border-none text-[11px] px-2.5 py-1 rounded-full">
                          {album.total_photos} fotos
                        </Badge>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-7 w-7 p-0 text-white hover:bg-white/20 rounded-full"
                              onClick={(e) => { e.preventDefault(); e.stopPropagation(); }}
                            >
                              <MoreVertical className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end" className="w-[180px]">
                            <DropdownMenuItem onClick={(e) => { e.preventDefault(); e.stopPropagation(); setEditingAlbum(album); setIsEditAlbumDialogOpen(true); }}>
                              <Edit className="mr-2 h-4 w-4" /> Editar Álbum
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={(e) => { e.preventDefault(); e.stopPropagation(); setItemToManageProfiles({ id: album.id, name: album.name }); setShowManageProfilesDialog(true); }}>
                              <LinkIcon className="mr-2 h-4 w-4" /> Vincular a Perfil
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={(e) => { e.preventDefault(); e.stopPropagation(); handleDeleteAlbum(album.id); }} className="text-destructive focus:text-destructive">
                              <Trash2 className="mr-2 h-4 w-4" /> Eliminar Álbum
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </div>

                      <div className="absolute bottom-3 inset-x-3 text-white">
                        <h3 className="font-bold text-lg truncate drop-shadow-md">{album.name}</h3>
                        {album.description && <p className="text-xs text-white/80 line-clamp-1 mt-0.5">{album.description}</p>}
                      </div>
                    </div>
                  </motion.div>
                );
              })}
            </div>
          )}
        </div>
      ) : (
        // ALBUM DETAIL VIEW WITH PHOTO MANAGEMENT
        <div className="space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-3xl bg-card border border-border/80 shadow-sm">
            <div className="flex items-center gap-3">
              <Button variant="outline" size="sm" className="rounded-xl" onClick={() => setSelectedAlbumId(null)}>
                ← Volver
              </Button>
              <div>
                <h2 className="text-xl font-bold">{selectedAlbum?.name}</h2>
                <p className="text-xs text-muted-foreground">{selectedAlbum?.total_photos || selectedAlbum?.photos.length || 0} fotos en total</p>
              </div>
            </div>

            <div className="flex items-center gap-2 flex-wrap">
              <Button
                variant={isSelectionMode ? "secondary" : "outline"}
                size="sm"
                className="rounded-xl"
                onClick={() => {
                  setIsSelectionMode(!isSelectionMode);
                  setSelectedPhotos(new Set());
                }}
              >
                {isSelectionMode ? <CheckSquare className="mr-1.5 h-4 w-4 text-primary" /> : <Square className="mr-1.5 h-4 w-4" />}
                {isSelectionMode ? "Salir de Selección" : "Seleccionar Fotos"}
              </Button>
              <Button variant="outline" size="sm" className="rounded-xl" onClick={() => setShowShareModal(true)}>
                <Share2 className="mr-1.5 h-4 w-4 text-primary" /> Compartir
              </Button>
              <Button size="sm" className="rounded-xl" onClick={() => setShowUploadModal(true)}>
                <Plus className="mr-1.5 h-4 w-4" /> Subir Fotos
              </Button>
            </div>
          </div>

          {/* BATCH OPERATIONS TOOLBAR */}
          {isSelectionMode && selectedAlbum && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex items-center justify-between p-3 rounded-2xl bg-primary/10 border border-primary/20"
            >
              <div className="flex items-center gap-3">
                <Button size="sm" variant="ghost" onClick={toggleSelectAll} className="text-xs">
                  {selectedPhotos.size === selectedAlbum.photos.length ? "Desmarcar Todo" : "Marcar Todo"}
                </Button>
                <span className="text-xs font-semibold text-primary">
                  {selectedPhotos.size} foto(s) seleccionada(s)
                </span>
              </div>

              {selectedPhotos.size > 0 && (
                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    className="rounded-xl text-xs"
                    onClick={() => handleToggleFavorite(Array.from(selectedPhotos))}
                  >
                    <Star className="mr-1.5 h-3.5 w-3.5 text-yellow-500 fill-yellow-500" /> Favorito
                  </Button>
                  <Button
                    size="sm"
                    variant="destructive"
                    className="rounded-xl text-xs"
                    onClick={() => handleDeletePhotos(Array.from(selectedPhotos))}
                  >
                    <Trash2 className="mr-1.5 h-3.5 w-3.5" /> Eliminar ({selectedPhotos.size})
                  </Button>
                </div>
              )}
            </motion.div>
          )}

          {/* Subtabs: Photos Grid vs Received Selections */}
          <Tabs value={subTab} onValueChange={(v) => setSubTab(v as any)} className="w-full">
            <TabsList className="p-1 bg-muted rounded-2xl mb-6">
              <TabsTrigger value="photos" className="rounded-xl font-medium px-6 py-2 data-[state=active]:bg-card data-[state=active]:shadow-sm">
                🖼️ Fotos del Álbum
              </TabsTrigger>
              <TabsTrigger value="received_selections" className="rounded-xl font-medium px-6 py-2 data-[state=active]:bg-card data-[state=active]:shadow-sm">
                🎯 Selecciones Recibidas
              </TabsTrigger>
            </TabsList>

            <TabsContent value="photos">
              {!selectedAlbum || photos.length === 0 ? (
                <div className="text-center py-16 rounded-3xl border-2 border-dashed border-border p-8">
                  <ImageIcon className="mx-auto h-16 w-16 text-muted-foreground/40 mb-3" />
                  <h3 className="text-lg font-bold">Sin fotos en este álbum</h3>
                  <Button onClick={() => setShowUploadModal(true)} className="mt-4 rounded-2xl">
                    <Plus className="mr-2 h-4 w-4" /> Subir primeras fotos
                  </Button>
                </div>
              ) : (
                <DndContext
                  sensors={sensors}
                  collisionDetection={closestCenter}
                  onDragEnd={handleDragEnd}
                >
                  <SortableContext
                    items={photos.map((p) => p.id)}
                    strategy={rectSortingStrategy}
                  >
                    <div className="columns-2 sm:columns-3 md:columns-4 lg:columns-5 gap-4">
                      {photos.map((photo, index) => {
                        const isSelected = selectedPhotos.has(photo.id);
                        return (
                          <SortablePhotoItem
                            key={photo.id}
                            photo={photo}
                            index={index}
                            apiBase={apiBase}
                            isSelectionMode={isSelectionMode}
                            isSelected={isSelected}
                            isCover={selectedAlbum.cover_photo_id === photo.id}
                            onSelect={() => togglePhotoSelection(photo.id)}
                            onOpenLightbox={() => {
                              setLightboxIndex(index);
                              setLightboxOpen(true);
                            }}
                            onToggleFavorite={() => handleToggleFavorite([photo.id])}
                            onSetCover={() => handleSetCover(photo.id)}
                            onDelete={() => handleDeletePhotos([photo.id])}
                          />
                        );
                      })}
                    </div>
                  </SortableContext>
                </DndContext>
              )}
            </TabsContent>

            <TabsContent value="received_selections">
              <ReceivedSelectionsView albumId={selectedAlbumId} />
            </TabsContent>
          </Tabs>
        </div>
      )}

      {/* Modals and Dialogs */}
      {selectedAlbumId && (
        <ExtensionShareModal
          isOpen={showShareModal}
          onClose={() => setShowShareModal(false)}
          albumId={selectedAlbumId}
        />
      )}

      <CreateAlbumModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onAlbumCreated={fetchAlbums}
      />

      <EditAlbumModal
        isOpen={isEditAlbumDialogOpen}
        onOpenChange={setIsEditAlbumDialogOpen}
        album={editingAlbum}
        onSaveSuccess={fetchAlbums}
      />

      <ManageLinkedProfilesDialog
        isOpen={showManageProfilesDialog}
        onOpenChange={setShowManageProfilesDialog}
        item={itemToManageProfiles}
        itemType="album"
        onLinkedProfilesUpdated={fetchAlbums}
        onLink={async (profileId, albumId) => {
          try {
            await apiClient.post(`/api/galleries/albums/${albumId}/link-profile`, { profile_id: profileId });
            toast.success('Perfil vinculado exitosamente.');
            fetchAlbums();
          } catch (error) {
            toast.error('Error al vincular el perfil.');
          }
        }}
        onUnlink={async (profileId, albumId) => {
          try {
            await apiClient.post(`/api/galleries/albums/${albumId}/unlink-profile`, { profile_id: profileId });
            toast.success('Perfil desvinculado exitosamente.');
            fetchAlbums();
          } catch (error) {
            toast.error('Error al desvincular el perfil.');
          }
        }}
      />

      {selectedAlbumId && (
        <UploadPhotosModal
          isOpen={showUploadModal}
          onOpenChange={setShowUploadModal}
          albumId={selectedAlbumId}
          onUploadSuccess={() => fetchAlbumDetail(selectedAlbumId)}
        />
      )}

      {selectedAlbum && (
        <Lightbox
          open={lightboxOpen}
          close={() => setLightboxOpen(false)}
          slides={selectedAlbum.photos.map(p => ({ src: `${apiBase}/media/${p.file_path}` }))}
          index={lightboxIndex}
        />
      )}

      <Sheet open={isInfoSheetOpen} onOpenChange={setIsInfoSheetOpen}>
        <SheetContent side="right" className="w-full sm:max-w-md overflow-y-auto">
          <SheetHeader>
            <SheetTitle className="text-xl font-bold text-primary">Módulo KogniPhotos</SheetTitle>
            <SheetDescription className="text-sm text-muted-foreground">
              Organiza, gestiona y visualiza tus imágenes en álbumes personalizados.
            </SheetDescription>
          </SheetHeader>
          <div className="py-4 text-sm text-gray-700 dark:text-gray-300 space-y-4">
            <p><strong>¿Qué puedes hacer en KogniPhotos?</strong></p>
            <ul className="list-disc pl-5 space-y-2">
              <li><strong>Crear y Editar Álbumes:</strong> Organiza tus imágenes en álbumes temáticos con nombres y descripciones personalizadas.</li>
              <li><strong>Subir y Gestionar Fotos:</strong> Añade nuevas fotos a tus álbumes, edita sus detalles y elimínalas cuando sea necesario.</li>
              <li><strong>Gestión Individual y en Lote:</strong> Marca favoritos, establece portadas de álbum o realiza acciones sobre múltiples fotos a la vez.</li>
              <li><strong>Panel de Selección:</strong> Comparte galerías interactivas para que tus clientes elijan sus fotos preferidas.</li>
            </ul>
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
};
