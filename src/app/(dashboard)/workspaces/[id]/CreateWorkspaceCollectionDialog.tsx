'use client';

import { useState, useEffect } from 'react';
import { toast } from 'sonner';
import apiClient from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';

interface CreateWorkspaceCollectionDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  onCreateSuccess: (newTopic: string) => void;
  workspaceId: string;
  parentId?: string | null; // Nuevo
}

export function CreateWorkspaceCollectionDialog({ isOpen, onOpenChange, onCreateSuccess, workspaceId, parentId }: CreateWorkspaceCollectionDialogProps) {
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
      console.log('DEBUG: Creating collection with workspaceId:', workspaceId, 'parentId:', parentId, 'name:', topicName);
      const response = await apiClient.post(`/api/collections`, {
        topic: topicName,
        description: description,
        workspaceId: workspaceId,
        parent_id: parentId // Enviamos el parent_id al backend
      });
      toast.success(`Colección "${topicName}" creada.`);
      onCreateSuccess(topicName);
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
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md w-full max-h-[90vh] p-4 sm:p-6">
        <DialogHeader>
          <DialogTitle>Crear Nueva Colección en Workspace</DialogTitle>
          <DialogDescription>
            Dale un nombre a tu nueva base de conocimiento para este workspace. Podrás añadir documentos después.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="topic-name">Nombre de la Colección</Label>
            <Input
              id="topic-name"
              value={topicName}
              onChange={(e) => setTopicName(e.target.value)}
              placeholder="Ej: Proyectos 2025"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="description">Descripción (Opcional)</Label>
            <Textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe el propósito de esta colección..."
              rows={3}
              className="resize-none max-h-[150px]"
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
