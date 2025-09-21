'use client';

import { useEffect, useState, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';
import NextImage from 'next/image';
import { Button } from '@/components/ui/button';
import { PlusCircle, Star, Trash2, Image as ImageIcon, ArrowLeft, XCircle, Share2, Info, ArrowRight, MoreVertical } from 'lucide-react';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { PhotoResponse, AlbumResponse } from '@/types/gallery';
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
  const [isViewerOpen, setIsViewerOpen] = useState(false);
  const [currentImageIndex, setCurrentImageIndex] = useState(0);

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

  const handleToggleFavorite = async (photoId: string) => {
    try {
      await apiClient.put(`/api/galleries/photos/${photoId}/favorite`);
      fetchAlbum(); // Refresh album to show updated favorite status
    } catch (e: any) {
      console.error('Error toggling favorite:', e);
      alert(`Error al cambiar favorito: ${e.message}`);
    }
  };

  const handleDeletePhoto = async (photoId: string) => {
    if (!confirm('¿Estás seguro de que quieres eliminar esta foto?')) return;
    try {
      await apiClient.delete(`/api/galleries/photos/${photoId}`);
      fetchAlbum(); // Refresh album to remove deleted photo
    } catch (e: any) {
      console.error('Error deleting photo:', e);
      alert(`Error al eliminar foto: ${e.message}`);
    }
  };

  const handleSetCover = async (photoId: string) => {
    if (!albumId) return;
    try {
      await apiClient.put(`/api/galleries/albums/${albumId}/cover`, { photo_id: photoId });
      fetchAlbum(); // Refresh album to show new cover
    } catch (e: any) {
      console.error('Error setting cover:', e);
      alert(`Error al establecer portada: ${e.message}`);
    }
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
          <Button onClick={() => setShowUploadModal(true)}> {/* New Upload Button */}
            <PlusCircle className="mr-2 h-4 w-4" /> Subir Fotos
          </Button>
        </div>
      </div>



      <section>
        <h2 className="text-2xl font-semibold text-gray-800 dark:text-white mb-4">Fotos del Álbum ({album.photos.length})</h2>
        {album.photos.length === 0 ? (
          <div className="text-center py-16 border-2 border-dashed border-border rounded-xl">
            <ImageIcon className="mx-auto h-16 w-16 text-muted-foreground/50 mb-4" />
            <h3 className="text-xl font-semibold mb-2">Este álbum no tiene fotos aún</h3>
            <p className="text-muted-foreground mb-6 max-w-md mx-auto">
              Sube tus fotos para empezar a organizar tus recuerdos.
            </p>
            <Button onClick={() => fileInputRef.current?.click()} size="lg">
              <PlusCircle className="mr-2 h-5 w-5" />
              Subir tu primera Foto
            </Button>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {album.photos.map((photo, index) => (
              <div key={photo.id} className="relative bg-white dark:bg-gray-700 rounded-lg shadow-md overflow-hidden group cursor-pointer aspect-square"
                onClick={() => {
                  setCurrentImageIndex(index);
                  setIsViewerOpen(true);
                }}
              >

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
                      <DropdownMenuItem onClick={(e) => { e.stopPropagation(); handleToggleFavorite(photo.id); }}>
                        <Star className="mr-2 h-4 w-4" />
                        {photo.is_favorite ? 'Quitar de favoritos' : 'Marcar como favorito'}
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={(e) => { e.stopPropagation(); handleSetCover(photo.id); }}>
                        <ImageIcon className="mr-2 h-4 w-4" />
                        Establecer como portada
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={(e) => { e.stopPropagation(); handleDeletePhoto(photo.id); }} className="text-red-600">
                        <Trash2 className="mr-2 h-4 w-4" />
                        Eliminar foto
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
                {photo.id === album.cover_photo_id && (
                  <span className="absolute top-2 left-2 bg-blue-500 text-white text-xs px-2 py-1 rounded-full">Portada</span>
                )}
                {photo.is_favorite && photo.id !== album.cover_photo_id && (
                  <span className="absolute top-2 right-2 bg-yellow-500 text-white text-xs px-2 py-1 rounded-full">Favorita</span>
                )}
              </div>
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

      {/* Image Viewer Dialog */}
      <Dialog open={isViewerOpen} onOpenChange={setIsViewerOpen}>
        <DialogContent className="h-[90vh] flex flex-col p-0">
          {album && album.photos.length > 0 && (
            <>
              <div className="flex-grow flex items-center justify-center bg-black relative">
                <NextImage
                  src={`/media/${album.photos[currentImageIndex].file_path}`}
                  alt={album.photos[currentImageIndex].file_path}
                  width={800} /* Adjust as needed */
                  height={600} /* Adjust as needed */
                  className="max-h-full max-w-full object-contain"
                />
                {/* Navigation Buttons */}
                <Button
                  variant="ghost"
                  size="icon"
                  className="absolute left-4 top-1/2 -translate-y-1/2 text-white hover:bg-white/20"
                  onClick={(e) => {
                    e.stopPropagation();
                    setCurrentImageIndex((prevIndex) => Math.max(0, prevIndex - 1));
                  }}
                  disabled={currentImageIndex === 0}
                >
                  <ArrowLeft className="h-8 w-8" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-white hover:bg-white/20"
                  onClick={(e) => {
                    e.stopPropagation();
                    setCurrentImageIndex((prevIndex) => Math.min(album.photos.length - 1, prevIndex + 1));
                  }}
                  disabled={currentImageIndex === album.photos.length - 1}
                >
                  <ArrowRight className="h-8 w-8" />
                </Button>
              </div>
              <DialogFooter className="flex justify-between items-center p-4 bg-gray-800 text-white">
                <span className="text-sm">{currentImageIndex + 1} / {album.photos.length}</span>
                <span className="text-sm truncate">{album.photos[currentImageIndex].file_path.split('/').pop()}</span>
                <Button variant="ghost" size="icon" onClick={() => setIsViewerOpen(false)}>
                  <XCircle className="h-6 w-6" />
                </Button>
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
