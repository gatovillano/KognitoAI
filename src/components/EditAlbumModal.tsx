import React, { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import apiClient from '@/lib/api';
import { toast } from 'sonner';
import { AlbumResponse } from '@/types/gallery';

interface EditAlbumModalProps {
  isOpen: boolean;
  onOpenChange: (isOpen: boolean) => void;
  album: AlbumResponse | null;
  onSaveSuccess: () => void;
}

export const EditAlbumModal: React.FC<EditAlbumModalProps> = ({
  isOpen,
  onOpenChange,
  album,
  onSaveSuccess,
}) => {
  const [name, setName] = useState(album?.name || '');
  const [description, setDescription] = useState(album?.description || '');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (album) {
      setName(album.name);
      setDescription(album.description || '');
    } else {
      setName('');
      setDescription('');
    }
  }, [album]);

  const handleSave = async () => {
    if (!album) return;
    setLoading(true);
    try {
      await apiClient.put(`/api/galleries/albums/${album.id}`, {
        name: name,
        description: description,
      });
      toast.success('Álbum actualizado correctamente.');
      onSaveSuccess();
      onOpenChange(false);
    } catch (error) {
      toast.error('Error al actualizar el álbum.');
      console.error('Error updating album:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>{album ? 'Editar Álbum' : 'Crear Álbum'}</DialogTitle>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <div className="grid grid-cols-4 items-center gap-4">
            <Label htmlFor="name" className="text-right">
              Nombre
            </Label>
            <Input
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}              className="col-span-3"
            />
          </div>
          <div className="grid grid-cols-4 items-center gap-4">
            <Label htmlFor="description" className="text-right">
              Descripción
            </Label>
            <Textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="col-span-3"
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancelar
          </Button>
          <Button onClick={handleSave} disabled={loading}>
            {loading ? 'Guardando...' : 'Guardar Cambios'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};