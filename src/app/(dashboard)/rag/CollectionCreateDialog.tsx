'use client';

import { useState } from 'react';
import { toast } from 'sonner';
import apiClient from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';

interface CollectionCreateDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated: () => void;
  parentId?: string;
  workspaceId?: string;
}

export default function CollectionCreateDialog({ open, onOpenChange, onCreated, parentId, workspaceId }: CollectionCreateDialogProps) {
  const [topicName, setTopicName] = useState('');
  const [description, setDescription] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleCreate = async () => {
    if (!topicName.trim() || topicName.trim().length < 3) {
      toast.error("El nombre de la colección debe tener al menos 3 caracteres.");
      return;
    }
    setIsLoading(true);
    try {
      await apiClient.post(`/api/collections`, {
        topic: topicName,
        description: description,
        workspaceId: workspaceId,
        parent_id: parentId // Pasamos el parent_id para crear subcolección
      });
      toast.success(`Colección "${topicName}" creada.`);
      onCreated();
      onOpenChange(false);
      setTopicName('');
      setDescription('');
    } catch (error) {
      console.error("Error al crear la colección:", error);
      toast.error('Error al crear la colección.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md w-full p-6">
        <DialogHeader>
          <DialogTitle>{parentId ? "Crear Subcolección" : "Crear Nueva Colección"}</DialogTitle>
          <DialogDescription>
            {parentId ? "Añade una subcolección dentro de esta categoría." : "Dale un nombre a tu nueva base de conocimiento."}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-2">
          <div className="space-y-2">
            <Label htmlFor="topic-name">Nombre</Label>
            <Input
              id="topic-name"
              value={topicName}
              onChange={(e) => setTopicName(e.target.value)}
              placeholder="Ej: Análisis 2025"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="description">Descripción (Opcional)</Label>
            <Textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe el propósito..."
              rows={3}
            />
          </div>
        </div>
        <DialogFooter>
          <Button onClick={handleCreate} disabled={isLoading}>
            {isLoading ? 'Creando...' : 'Crear'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
