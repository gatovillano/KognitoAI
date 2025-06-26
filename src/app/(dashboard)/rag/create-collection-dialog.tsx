// En: src/app/(dashboard)/rag/create-collection-dialog.tsx
'use client';

import { useState } from 'react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

interface CreateCollectionDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  onCreateSuccess: (newTopic: string) => void;
}

export function CreateCollectionDialog({ isOpen, onOpenChange, onCreateSuccess }: CreateCollectionDialogProps) {
  const [topicName, setTopicName] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleCreate = () => {
    if (!topicName.trim() || topicName.trim().length < 3) {
      toast.error("El nombre de la colección debe tener al menos 3 caracteres.");
      return;
    }
    setIsLoading(true);
    // Simplemente llamamos al callback de éxito. No hay llamada a la API.
    toast.success(`Colección "${topicName}" creada.`);
    onCreateSuccess(topicName);
    onOpenChange(false);
    setTopicName('');
    setIsLoading(false);
  };

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Crear Nueva Colección</DialogTitle>
          <DialogDescription>
            Dale un nombre a tu nueva base de conocimiento. Podrás añadir documentos después.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-2">
          <Label htmlFor="topic-name">Nombre de la Colección</Label>
          <Input 
            id="topic-name" 
            value={topicName}
            onChange={(e) => setTopicName(e.target.value)}
            placeholder="Ej: Proyectos 2025"
          />
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