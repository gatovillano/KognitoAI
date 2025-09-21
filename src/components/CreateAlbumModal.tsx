'use client';

import React, { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';
import apiClient from '@/lib/api'; // Import apiClient

interface CreateAlbumModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAlbumCreated: () => void; // Callback to refresh album list
}

const CreateAlbumModal: React.FC<CreateAlbumModalProps> = ({ isOpen, onClose, onAlbumCreated }) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const response = await apiClient.post(`${process.env.NEXT_PUBLIC_API_URL}/api/galleries/albums`, { name, description }); // Use apiClient.post

      if (response.status !== 201) { // Assuming 201 Created for successful album creation
        const errorData = response.data; // apiClient usually puts response body in .data
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }

      // Album created successfully
      setName('');
      setDescription('');
      console.log('CreateAlbumModal: Album created, calling onAlbumCreated()'); // Debug log
      onAlbumCreated(); // Notify parent to refresh list
      onClose(); // Close the modal
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Crear Nuevo Álbum</DialogTitle>
          <DialogDescription>
            Crea un nuevo álbum de fotos para organizar tus recuerdos.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit}>
          <div className="grid gap-4 py-4">
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="name" className="text-right">
                Nombre
              </Label>
              <Input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="col-span-3"
                required
                disabled={loading}
              />
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="description" className="text-right">
                Descripción
              </Label>
              <Input
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="col-span-3"
                disabled={loading}
              />
            </div>
          </div>
          {error && <p className="text-red-500 text-sm">Error: {error}</p>}
          <DialogFooter>
            <Button type="submit" disabled={loading}>
              {loading ? 'Creando...' : 'Crear Álbum'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};

export default CreateAlbumModal;