'use client';

import { useEffect, useState, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';
import NextImage from 'next/image';
import { Button } from '@/components/ui/button';
import { PlusCircle, Star, Trash2, Image as ImageIcon, ArrowLeft, XCircle, Share2, Info, ArrowRight, MoreVertical } from 'lucide-react';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { PhotoResponse, AlbumResponse } from '@/types/gallery';
import { LightboxExternalProps } from 'yet-another-react-lightbox';
import { toast } from 'sonner';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from '@/components/ui/alert-dialog';
import { Skeleton } from '@/components/ui/skeleton';
import { Progress } from '@/components/ui/progress';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import apiClient from '@/lib/api';
import { useDropzone } from 'react-dropzone';
import ShareAlbumModal from '@/components/ShareAlbumModal';
import { UploadPhotosModal } from '@/components/UploadPhotosModal';
import { useDrag, useDrop } from 'react-dnd';
import Lightbox from "yet-another-react-lightbox";
import "yet-another-react-lightbox/styles.css";

const ItemTypes = {
  PHOTO: 'photo',
};

interface AlbumClientPageProps {
  albumId: string;
}

export default function AlbumDetailPageClient({ albumId }: AlbumClientPageProps) {
  const router = useRouter();

  const [album, setAlbum] = useState<AlbumResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showShareModal, setShowShareModal] = useState(false); // State for share modal
  const [showUploadModal, setShowUploadModal] = useState(false); // State for upload modal
  const [isViewerOpen, setIsViewerOpen] = useState(false); // State for the old image viewer
  const [currentImageIndex, setCurrentImageIndex] = useState(0); // State for the old image viewer
  const [selectedPhotos, setSelectedPhotos] = useState<Set<string>>(new Set());
  const [isSelectionMode, setIsSelectionMode] = useState(false);
  const [lightboxOpen, setLightboxOpen] = useState(false); // State for the new lightbox
  const [lightboxIndex, setLightboxIndex] = useState(0); // State for the new lightbox

  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchAlbum = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
        const response = await apiClient.get<AlbumResponse>(`${process.env.NEXT_PUBLIC_API_URL}/api/galleries/albums/${albumId}`);
      setAlbum(response.data);
    } catch (e: any) {
      setError(e.message);
      toast.error(`Error al cargar el álbum: ${e.message}`);
    } finally {
      setLoading(false);
    }
  }, [albumId]);

  useEffect(() => {
    fetchAlbum();
  }, [fetchAlbum]);

  const handleToggleFavorite = async (photoIds: string[]) => {
    try {
      for (const photoId of photoIds) {
        await apiClient.put(`/api/galleries/photos/${photoId}/favorite`);
      }
      toast.success(`Se ${photoIds.length > 1 ? 'marcaron/desmarcaron' : 'marcó/desmarcó'} como favorito ${photoIds.length} foto(s).`);
      fetchAlbum(); // Refresh album to show updated favorite status
      setSelectedPhotos(new Set()); // Clear selection
    } catch (e: any) {
      console.error('Error toggling favorite:', e);
      toast.error(`Error al cambiar favorito: ${e.message}`);
    }
  };

  const handleDeletePhoto = async (photoIds: string[]) => {
    if (!confirm(`¿Estás seguro de que quieres eliminar ${photoIds.length} foto(s)? Esta acción no se puede deshacer.`)) return;
    try {
      for (const photoId of photoIds) {
        await apiClient.delete(`/api/galleries/photos/${photoId}`);
      }
      toast.success(`Se eliminaron ${photoIds.length} foto(s) exitosamente.`);
      fetchAlbum(); // Refresh album to remove deleted photo
      setSelectedPhotos(new Set()); // Clear selection
    } catch (e: any) {
      console.error('Error deleting photo:', e);
      toast.error(`Error al eliminar foto: ${e.message}`);
    }
  };

  const handleSetCover = async (photoId: string) => {
    if (!albumId) return;
    try {
      await apiClient.put(`/api/galleries/albums/${albumId}/cover`, { photo_id: photoId });
      toast.success('Portada del álbum actualizada.');
      fetchAlbum(); // Refresh album to show new cover
    } catch (e: any) {
      console.error('Error setting cover:', e);
      toast.error(`Error al establecer portada: ${e.message}`);
    }
  };

  const toggleSelection = (photoId: string) => {
    setSelectedPhotos((prevSelected) => {
      const newSelected = new Set(prevSelected);
      if (newSelected.has(photoId)) {
        newSelected.delete(photoId);
      } else {
        newSelected.add(photoId);
      }
      return newSelected;
    });
  };

  const toggleSelectAll = () => {
    if (album && selectedPhotos.size === album.photos.length) {
      setSelectedPhotos(new Set());
    } else if (album) {
      setSelectedPhotos(new Set(album.photos.map(photo => photo.id)));
    }
  };

  const handleSaveOrder = useCallback(async () => {
    if (!album) return;

    const reorderData = album.photos.map((photo, index) => ({
      photo_id: photo.id,
      order: index,
    }));

    try {
      await apiClient.post(`/api/galleries/albums/${album.id}/reorder-photos`, reorderData);
      toast.success('Orden de fotos guardado exitosamente.');
      // Opcional: Refrescar el álbum para asegurar que el estado del frontend coincide con el backend
      // fetchAlbum();
    } catch (e: any) {
      console.error('Error saving photo order:', e);
      toast.error(`Error al guardar el orden de las fotos: ${e.message}`);
    }
  }, [album]);

  const handleInvertOrder = useCallback(() => {
    setAlbum((prevAlbum) => {
      if (!prevAlbum) return prevAlbum;

      const invertedPhotos = [...prevAlbum.photos].reverse().map((photo, index) => ({
        ...photo,
        order: index,
      }));

      return { ...prevAlbum, photos: invertedPhotos };
    });
    toast.info('Orden de fotos invertido localmente. Guardando cambios...');
    handleSaveOrder(); // Call handleSaveOrder automatically
  }, [handleSaveOrder]);

  const movePhoto = useCallback((draggedId: string, hoverId: string) => {
    setAlbum((prevAlbum) => {
      if (!prevAlbum) return prevAlbum;

      const draggedPhoto = prevAlbum.photos.find((p) => p.id === draggedId);
      const hoverPhoto = prevAlbum.photos.find((p) => p.id === hoverId);

      if (!draggedPhoto || !hoverPhoto) return prevAlbum;

      const newPhotos = [...prevAlbum.photos];
      const draggedIndex = newPhotos.findIndex((p) => p.id === draggedId);
      const hoverIndex = newPhotos.findIndex((p) => p.id === hoverId);

      // Remove dragged photo and insert it at hover position
      newPhotos.splice(draggedIndex, 1);
      newPhotos.splice(hoverIndex, 0, draggedPhoto);

      // Update the order property for all photos based on their new index
      const reorderedPhotos = newPhotos.map((photo, index) => ({
        ...photo,
        order: index, // Assign new order based on current index
      }));

      return { ...prevAlbum, photos: reorderedPhotos };
    });
  }, []);

  const PhotoCard = ({ photo, index }: { photo: PhotoResponse; index: number }) => {
    const ref = useRef<HTMLDivElement>(null);

    const [, drop] = useDrop({
      accept: ItemTypes.PHOTO,
      hover(item: { id: string; index: number }, monitor) {
        if (!ref.current) {
          return;
        }
        const draggedId = item.id;
        const hoverId = photo.id;

        if (draggedId === hoverId) {
          return;
        }

        const hoverBoundingRect = ref.current?.getBoundingClientRect();
        const hoverMiddleY = (hoverBoundingRect.bottom - hoverBoundingRect.top) / 2;
        const clientOffset = monitor.getClientOffset();
        const hoverClientY = clientOffset ? clientOffset.y - hoverBoundingRect.top : 0;

        // Only perform the move when the mouse has crossed half of the items height
        // When dragging downwards, only move when the cursor is below 50% of the hover item
        // When dragging upwards, only move when the cursor is above 50% of the hover item

        // Dragging downwards
        if (draggedId < hoverId && hoverClientY < hoverMiddleY) {
          return;
        }

        // Dragging upwards
        if (draggedId > hoverId && hoverClientY > hoverMiddleY) {
          return;
        }

        movePhoto(draggedId, hoverId);
        item.index = index;
      },
    });

    const [{ isDragging }, drag] = useDrag({
      type: ItemTypes.PHOTO,
      item: { id: photo.id, index: index },
      collect: (monitor) => ({
        isDragging: monitor.isDragging(),
      }),
    });

    drag(drop(ref));

    return (
      <div ref={ref} style={{ opacity: isDragging ? 0.5 : 1 }} className="relative bg-white dark:bg-gray-700 rounded-lg shadow-md overflow-hidden group cursor-pointer aspect-square"
        onClick={() => {
          if (isSelectionMode) {
            toggleSelection(photo.id);
          } else {
            setLightboxIndex(index);
            setLightboxOpen(true);
          }
        }}
      >
        {isSelectionMode && (
          <div className="absolute top-2 left-2 z-10">
            <input
              type="checkbox"
              checked={selectedPhotos.has(photo.id)}
              onChange={() => toggleSelection(photo.id)}
              className="form-checkbox h-5 w-5 text-primary-600 rounded-md"
              onClick={(e) => e.stopPropagation()} // Prevent opening image viewer
            />
          </div>
        )}
        <NextImage src={`/media/${photo.file_path}`} alt="Album Photo" fill className="object-cover" />
        <div className="absolute inset-0 bg-black bg-opacity-50 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-300">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="absolute top-2 right-2 text-white hover:bg-white/20 z-10"
                onClick={(e) => e.stopPropagation()} // Prevent opening image viewer
              >
                <MoreVertical className="h-5 w-5" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={(e) => { e.stopPropagation(); handleToggleFavorite([photo.id]); }}>
                <Star className="mr-2 h-4 w-4" />
                {photo.is_favorite ? 'Quitar de favoritos' : 'Marcar como favorito'}
              </DropdownMenuItem>
              <DropdownMenuItem onClick={(e) => { e.stopPropagation(); handleSetCover(photo.id); }}>
                <ImageIcon className="mr-2 h-4 w-4" />
                Establecer como portada
              </DropdownMenuItem>
              <DropdownMenuItem onClick={(e) => { e.stopPropagation(); handleDeletePhoto([photo.id]); }} className="text-red-600">
                <Trash2 className="mr-2 h-4 w-4" />
                Eliminar foto
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
        {photo.id === album?.cover_photo_id && (
          <span className="absolute top-2 left-2 bg-blue-500 text-white text-xs px-2 py-1 rounded-full">Portada</span>
        )}
        {photo.is_favorite && photo.id !== album?.cover_photo_id && (
          <span className="absolute top-2 right-2 bg-yellow-500 text-white text-xs px-2 py-1 rounded-full">Favorita</span>
        )}
      </div>
    );
  };


  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Cargando álbum...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-16">
        <ImageIcon className="mx-auto h-16 w-16 text-muted-foreground/50 mb-4" /> {/* Using ImageIcon for consistency */}
        <h3 className="text-xl font-semibold mb-2">Error al cargar el álbum</h3>
        <p className="text-muted-foreground mb-6 max-w-md mx-auto">
          Ocurrió un problema al intentar cargar el álbum: {error}
        </p>
        <Button onClick={() => router.push('/galleries')} size="lg">
          <ArrowLeft className="mr-2 h-4 w-4" />
          Volver a Galerías
        </Button>
      </div>
    );
  }

  if (!album) {
    return (
      <div className="container mx-auto px-4 py-8 text-center text-gray-600 dark:text-gray-300">
        Álbum no encontrado.
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-8 max-w-7xl mx-auto overflow-x-hidden">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold flex items-center">
            <ImageIcon className="mr-3 h-8 w-8 text-primary" /> {/* Using ImageIcon for consistency */}
            {album.name}
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="ghost" size="icon" className="ml-2 h-6 w-6 text-muted-foreground">
                    <Info className="h-4 w-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>{album.description || 'Álbum de fotos.'}</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </h1>
          <p className="text-muted-foreground mt-1">Gestiona tus fotos y recuerdos.</p> {/* Consistent description */}
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => router.push('/galleries')}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Volver a Galerías
          </Button>
          <Button
            variant="outline"
            onClick={() => setShowShareModal(true)}
          >
            <Share2 className="mr-2 h-4 w-4" /> Compartir
          </Button>
          <Button onClick={() => setShowUploadModal(true)}>
            <PlusCircle className="mr-2 h-4 w-4" /> Subir Fotos
          </Button>
          <Button
            variant="outline"
            onClick={() => {
              setIsSelectionMode(!isSelectionMode);
              setSelectedPhotos(new Set()); // Clear selection when toggling mode
            }}
          >
            {isSelectionMode ? 'Cancelar Selección' : 'Seleccionar'}
          </Button>
        </div>
      </div>

      {isSelectionMode && selectedPhotos.size > 0 && (
        <div className="fixed bottom-0 left-0 right-0 bg-background border-t border-border p-4 flex items-center justify-between shadow-lg z-50">
          <span className="text-lg font-semibold">
            {selectedPhotos.size} foto(s) seleccionada(s)
          </span>
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={() => handleToggleFavorite(Array.from(selectedPhotos))}
            >
              <Star className="mr-2 h-4 w-4" /> Marcar/Desmarcar Favoritas
            </Button>
            <Button
              variant="destructive"
              onClick={() => handleDeletePhoto(Array.from(selectedPhotos))}
            >
              <Trash2 className="mr-2 h-4 w-4" /> Eliminar
            </Button>
          </div>
        </div>
      )}

      <section>
        <h2 className="text-2xl font-semibold text-gray-800 dark:text-white mb-4">Fotos del Álbum ({album.photos.length})</h2>
        {album.photos.length === 0 ? (
          <div className="text-center py-16 border-2 border-dashed border-border rounded-xl">
            <ImageIcon className="mx-auto h-16 w-16 text-muted-foreground/50 mb-4" />
            <h3 className="text-xl font-semibold mb-2">Este álbum no tiene fotos aún</h3>
            <p className="text-muted-foreground mb-6 max-w-md mx-auto">
              Sube tus fotos para empezar a organizar tus recuerdos.
            </p>
            <Button onClick={() => setShowUploadModal(true)} size="lg">
              <PlusCircle className="mr-2 h-5 w-5" />
              Subir tu primera Foto
            </Button>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {isSelectionMode && (
              <div className="col-span-full flex justify-between items-center mb-4">
                <Button variant="outline" onClick={toggleSelectAll}>
                  {selectedPhotos.size === album.photos.length ? 'Deseleccionar Todo' : 'Seleccionar Todo'}
                </Button>
                <Button variant="outline" onClick={handleInvertOrder}>
                  Invertir Orden
                </Button>
                {album.photos.some(photo => photo.order !== album.photos.indexOf(photo)) && (
                  <Button onClick={handleSaveOrder}>
                    Guardar Orden
                  </Button>
                )}
              </div>
            )}
            {album.photos.map((photo, index) => (
              <PhotoCard key={photo.id} photo={photo} index={index} />
            ))}
          </div>
        )}
      </section>

      {album && (
        <ShareAlbumModal
          isOpen={showShareModal}
          onClose={() => setShowShareModal(false)}
          albumId={album.id}
        />
      )}

      {album && (
        <UploadPhotosModal
          isOpen={showUploadModal}
          onOpenChange={setShowUploadModal}
          albumId={album.id}
          onUploadSuccess={fetchAlbum}
        />
      )}

      {album && (
        <Lightbox
          open={lightboxOpen}
          close={() => setLightboxOpen(false)}
          slides={album.photos.map((photo) => ({
            src: `/media/${photo.file_path}`,
          }))}
          index={lightboxIndex}
        />
      )}
    </div>
  );
}
