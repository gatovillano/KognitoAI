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
  workspace_id?: string; // Add workspace_id
}

interface EditCollectionDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  onEditSuccess: () => void;
  collection: Collection | null;
  workspaceId?: string; // Pass workspaceId from parent
  teamId?: string;     // Pass teamId from parent
}

export function EditCollectionDialog({ isOpen, onOpenChange, onEditSuccess, collection, workspaceId, teamId }: EditCollectionDialogProps) {
  const [topicName, setTopicName] = useState('');
  const [description, setDescription] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState<string>('');
  const [workspaces, setWorkspaces] = useState<Array<{ id: string; name: string; color?: string }>>([]);
  const [loadingWorkspaces, setLoadingWorkspaces] = useState(false);

  useEffect(() => {
    if (isOpen && collection) {
      setTopicName(collection.topic);
      setDescription(collection.description || '');
      setSelectedWorkspaceId(collection.workspace_id || '');
    }
  }, [isOpen, collection]);

  useEffect(() => {
    const fetchWorkspaces = async () => {
      setLoadingWorkspaces(true);
      try {
        const response = await apiClient.get('/api/workspaces');
        if (Array.isArray(response.data)) {
          setWorkspaces(response.data);
        } else if (response.data && Array.isArray(response.data.workspaces)) {
          setWorkspaces(response.data.workspaces);
        } else {
          console.warn("API /api/workspaces did not return an array:", response.data);
          setWorkspaces([]);
        }
      } catch (error) {
        console.error("Error fetching workspaces:", error);
        toast.error('Error al cargar los workspaces.');
      } finally {
        setLoadingWorkspaces(false);
      }
    };
    if (isOpen) {
      fetchWorkspaces();
    }
  }, [isOpen]);

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
        new_description: description.trim() !== (collection.description || '') ? description.trim() : undefined,
        workspace_id: selectedWorkspaceId || undefined, // Send selected workspace
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
    setSelectedWorkspaceId('');
  };

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md w-full p-4 sm:p-6">
        <DialogHeader>
          <DialogTitle className="text-lg sm:text-xl">Editar Colección</DialogTitle>
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
          <div className="space-y-2">
            <Label htmlFor="workspace">Workspace (Opcional)</Label>
            <select
              id="workspace"
              className="w-full border rounded-md p-2"
              value={selectedWorkspaceId}
              onChange={(e) => setSelectedWorkspaceId(e.target.value)}
              disabled={loadingWorkspaces}
            >
              <option value="">{loadingWorkspaces ? "Cargando workspaces..." : "Ninguno"}</option>
              {workspaces.map(workspace => (
                <option key={workspace.id} value={workspace.id}>
                  {workspace.name}
                </option>
              ))}
            </select>
          </div>
        </div>
        <DialogFooter className="flex flex-col-reverse sm:flex-row sm:justify-end gap-2 mt-4">
          <Button variant="outline" onClick={handleClose} disabled={isLoading} className="w-full sm:w-auto">
            Cancelar
          </Button>
          <Button onClick={handleEdit} disabled={isLoading || !topicName.trim()} className="w-full sm:w-auto">
            {isLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
            Guardar Cambios
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
