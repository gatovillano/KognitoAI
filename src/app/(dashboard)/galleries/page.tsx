'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import { toast } from 'sonner';
import {
  Image as ImageIcon,
  Plus,
  MoreHorizontal,
  Info,
  Edit,
  Trash2,
  Link as LinkIcon,
} from 'lucide-react';

import apiClient from '@/lib/api';
import CreateAlbumModal from '../../../components/CreateAlbumModal';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { PhotoResponse, AlbumResponse } from '@/types/gallery';
import { EditAlbumModal } from '@/components/EditAlbumModal';
import { ManageLinkedProfilesDialog } from '@/app/(dashboard)/notes/ManageLinkedProfilesDialog'; // Import the generic dialog

import Image from 'next/image';

// AlbumCard Component
const AlbumCard = ({ album, onEditClick, onDeleteClick, onLinkProfileClick }: { album: AlbumResponse; onEditClick: (album: AlbumResponse) => void; onDeleteClick: (albumId: string) => void; onLinkProfileClick: (album: { id: string; name: string; }) => void }) => {
  const coverPhoto = album.cover_photo || album.photos.find(p => p.id === album.cover_photo_id);



  return (
    <motion.div
      layout
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.8 }}
      transition={{ type: 'spring', stiffness: 300, damping: 30 }}
      className="h-full"
    >
      <Link href={`/galleries/${album.id}`} passHref>
        <Card className="group cursor-pointer hover:shadow-xl hover:scale-[1.02] transition-all duration-200 border-2 hover:border-primary/30 flex flex-col h-full min-h-[320px]">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-3 min-w-0 flex-1">
                <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                  <ImageIcon className="h-5 w-5 text-primary" />
                </div>
                <span className="font-semibold text-lg truncate">{album.name}</span>
              </div>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-8 w-8 p-0 opacity-0 group-hover:opacity-100 transition-opacity"
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                    }}
                  >
                    <MoreHorizontal className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-[180px]">
                  <DropdownMenuItem
                    onClick={(e) => { e.preventDefault(); e.stopPropagation(); onEditClick(album); }}
                  >
                    <Edit className="mr-2 h-4 w-4" />
                    Editar Álbum
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    onClick={(e) => { e.preventDefault(); e.stopPropagation(); onLinkProfileClick({ id: album.id, name: album.name }); }}
                  >
                    <LinkIcon className="mr-2 h-4 w-4" />
                    Vincular a Perfil
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    onClick={(e) => { e.preventDefault(); e.stopPropagation(); onDeleteClick(album.id); }}
                    className="text-destructive focus:text-destructive"
                  >
                    <Trash2 className="mr-2 h-4 w-4" />
                    Eliminar Álbum
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0 flex-grow flex flex-col">
            <div className="relative w-full aspect-square bg-muted rounded-md overflow-hidden mb-3">
              {coverPhoto ? (
                <Image
                  src={`${process.env.NEXT_PUBLIC_API_URL}/media/${coverPhoto.file_path}`}
                  alt={album.name}
                  width={500}
                  height={500}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center text-muted-foreground">
                  <ImageIcon className="h-10 w-10 opacity-50" />
                </div>
              )}
            </div>
            <p className="text-sm text-muted-foreground line-clamp-2">
              {album.description || 'Sin descripción'}
            </p>
          </CardContent>
          <CardFooter className="flex justify-between items-center text-xs text-muted-foreground pt-3 mt-auto border-t border-border/50">
            <span>{album.photos.length} foto(s)</span>
            <span>{new Date(album.created_at).toLocaleDateString()}</span>
          </CardFooter>
        </Card>
      </Link>
    </motion.div>
  );
};

// Main Page Component
const GalleriesPage = () => {
  const [albums, setAlbums] = useState<AlbumResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateAlbumModal, setShowCreateAlbumModal] = useState(false);
  const [isEditAlbumDialogOpen, setIsEditAlbumDialogOpen] = useState(false);
  const [editingAlbum, setEditingAlbum] = useState<AlbumResponse | null>(null);
  const [showManageProfilesDialog, setShowManageProfilesDialog] = useState(false); // New state for generic dialog
  const [itemToManageProfiles, setItemToManageProfiles] = useState<{ id: string; name?: string; title?: string; } | null>(null); // New state for item to link/unlink profiles
  const fetchAlbums = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.get<AlbumResponse[]>(`${process.env.NEXT_PUBLIC_API_URL}/api/galleries/albums`);
      setAlbums(response.data);
    } catch (e: any) {
      setError(e.message);
      toast.error('Error al cargar los álbumes.');
      console.error('Error fetching albums:', e);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteAlbum = async (albumId: string) => {
    if (!window.confirm('¿Estás seguro de que quieres eliminar este álbum? Esta acción no se puede deshacer.')) {
      return;
    }
    try {
      await apiClient.delete(`${process.env.NEXT_PUBLIC_API_URL}/api/galleries/albums/${albumId}`);
      toast.success('Álbum eliminado exitosamente.');
      fetchAlbums(); // Refetch albums to update the list
    } catch (e: any) {
      toast.error('Error al eliminar el álbum.');
      console.error('Error deleting album:', e);
    }
  };

  useEffect(() => {
    fetchAlbums();
  }, []);

  const renderContent = () => {
    if (loading) {
      return <p className="text-center py-10">Cargando álbumes...</p>;
    }

    if (error) {
      return (
        <div className="text-center py-10 text-red-500">
          Error al cargar los álbumes: {error}
        </div>
      );
    }

    if (albums.length === 0) {
      return (
        <div className="text-center py-16">
          <ImageIcon className="mx-auto h-16 w-16 text-muted-foreground/50 mb-4" />
          <h3 className="text-xl font-semibold mb-2">No tienes álbumes aún</h3>
          <p className="text-muted-foreground mb-6 max-w-md mx-auto">
            Los álbumes te ayudan a organizar tus fotos y videos. ¡Crea tu primer álbum para empezar!
          </p>
          <Button onClick={() => setShowCreateAlbumModal(true)} size="lg">
            <Plus className="mr-2 h-5 w-5" />
            Crear tu primer Álbum
          </Button>
        </div>
      );
    }

    return (
      <motion.div
        layout
        className="grid gap-6 md:grid-cols-3 lg:grid-cols-3"
      >
        <AnimatePresence>
                      {albums.map((album) => (
                        <AlbumCard
                          key={album.id}
                          album={album}
                          onEditClick={(albumToEdit) => {
                            setEditingAlbum(albumToEdit);
                            setIsEditAlbumDialogOpen(true);
                          }}
                          onDeleteClick={handleDeleteAlbum}
                          onLinkProfileClick={(albumToLink) => {
                            setItemToManageProfiles({ id: albumToLink.id, name: albumToLink.name });
                            setShowManageProfilesDialog(true);
                          }}
                        />
                      ))}        </AnimatePresence>
      </motion.div>
    );
  };

  return (
    <div className="p-4 sm:p-8 max-w-7xl mx-auto overflow-x-hidden">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold flex items-center">
            <ImageIcon className="mr-3 h-8 w-8 text-primary" />
            Galería de Álbumes
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="ghost" size="icon" className="ml-2 h-6 w-6 text-muted-foreground">
                    <Info className="h-4 w-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>Organiza tus imágenes en álbumes visuales.</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </h1>
        </div>
        <div className="flex items-center gap-2">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm" className="h-9">
                <span className="hidden md:inline mr-2">Acciones</span>
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-[180px]">
              <DropdownMenuItem onClick={() => setShowCreateAlbumModal(true)}>
                <Plus className="mr-2 h-4 w-4" />
                Nuevo Álbum
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      <main>{renderContent()}</main>

      <CreateAlbumModal
        isOpen={showCreateAlbumModal}
        onClose={() => setShowCreateAlbumModal(false)}
        onAlbumCreated={fetchAlbums}
      />

      <EditAlbumModal
        isOpen={isEditAlbumDialogOpen}
        onOpenChange={setIsEditAlbumDialogOpen}
        album={editingAlbum}
        onSaveSuccess={fetchAlbums}
      />

      {/* Replaced LinkAlbumModal with ManageLinkedProfilesDialog */}
      <ManageLinkedProfilesDialog
        isOpen={showManageProfilesDialog}
        onOpenChange={setShowManageProfilesDialog}
        item={itemToManageProfiles}
        itemType="album"
                onLinkedProfilesUpdated={fetchAlbums}
        onLink={async (profileId, albumId) => {
          try {
            await apiClient.post(`/api/galleries/albums/${albumId}/link-profile`, { profileId });
            toast.success('Perfil vinculado exitosamente.');
            fetchAlbums();
          } catch (error) {
            toast.error('Error al vincular el perfil.');
            console.error('Error linking profile:', error);
          }
        }}
        onUnlink={async (profileId, albumId) => {
          try {
            await apiClient.post(`/api/galleries/albums/${albumId}/unlink-profile`, { profileId });
            toast.success('Perfil desvinculado exitosamente.');
            fetchAlbums();
          } catch (error) {
            toast.error('Error al desvincular el perfil.');
            console.error('Error unlinking profile:', error);
          }
        }}

      />
    </div>
  );
};

export default GalleriesPage;