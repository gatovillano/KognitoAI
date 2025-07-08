'use client';

import { useState, useEffect } from 'react';
import { toast } from 'sonner';
import apiClient from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Loader2 } from 'lucide-react';

interface Collection {
  topic: string;
  description?: string;
  document_count: number;
}

interface EditCollectionDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  onEditSuccess: () => void;
  collection: Collection | null;
}

export function EditCollectionDialog({ isOpen, onOpenChange, onEditSuccess, collection }: EditCollectionDialogProps) {
  const [topicName, setTopicName] = useState('');
  const [description, setDescription] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (isOpen && collection) {
      setTopicName(collection.topic);
      setDescription(collection.description || '');
    }
  }, [isOpen, collection]);

  const handleEdit = async () => {
    if (!collection) return;
    
    if (!topicName.trim() || topicName.trim().length < 3) {
      toast.error("El nombre de la colección debe tener al menos 3 caracteres.");
      return;
    }
    
    setIsLoading(true);
    try {
      await apiClient.post('/api/update-collection', { 
        old_topic: collection.topic,
        new_topic: topicName.trim() !== collection.topic ? topicName.trim() : undefined,
        new_description: description.trim() !== (collection.description || '') ? description.trim() : undefined
      });
      
      toast.success(`Colección "${topicName}" actualizada exitosamente.`);
      onEditSuccess();
      onOpenChange(false);
    } catch (error) {
      console.error("Error al actualizar la colección:", error);
      toast.error('Error al actualizar la colección.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleClose = () => {
    onOpenChange(false);
    setTopicName('');
    setDescription('');
  };

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Editar Colección</DialogTitle>
          <DialogDescription>
            Modifica el nombre y descripción de tu colección de conocimiento.
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
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={isLoading}>
            Cancelar
          </Button>
          <Button onClick={handleEdit} disabled={isLoading || !topicName.trim()}>
            {isLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
            Guardar Cambios
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
