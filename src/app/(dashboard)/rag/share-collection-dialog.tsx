'use client';

import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Loader2 } from 'lucide-react';
import apiClient from '@/lib/api';
import { toast } from 'sonner';

import { Collection } from '@/components/CollectionDisplay';

interface ShareCollectionDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  onShareSuccess: () => void;
  collection: Collection | null;
}

export function ShareCollectionDialog({ isOpen, onOpenChange, onShareSuccess, collection }: ShareCollectionDialogProps) {
  const [workspaces, setWorkspaces] = useState<any[]>([]);
  const [selectedWorkspace, setSelectedWorkspace] = useState<string | null>(null);
  const [isLoadingWorkspaces, setIsLoadingWorkspaces] = useState(false);
  const [isSharing, setIsSharing] = useState(false);

  useEffect(() => {
    if (isOpen) {
      fetchWorkspaces();
    }
  }, [isOpen]);

  const fetchWorkspaces = async () => {
    setIsLoadingWorkspaces(true);
    try {
      const response = await apiClient.get('/api/workspaces', { params: { limit: 100 } });
      setWorkspaces(response.data.workspaces);
    } catch (error) {
      toast.error('Error al cargar los workspaces.');
    } finally {
      setIsLoadingWorkspaces(false);
    }
  };

  const handleShare = async () => {
    if (!collection || !selectedWorkspace) return;

    setIsSharing(true);
    try {
      await apiClient.post(`/api/collections/${collection.topic}/share`, {
        workspace_id: selectedWorkspace,
      });
      toast.success(`Colección "${collection.topic}" compartida con el workspace.`);
      onShareSuccess();
      onOpenChange(false);
    } catch (error) {
      toast.error('Error al compartir la colección.');
    } finally {
      setIsSharing(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md w-full p-4 sm:p-6">
        <DialogHeader>
          <DialogTitle className="text-lg sm:text-xl">Compartir Colección</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <p>
            Seleccione un workspace para compartir la colección: <strong>{collection?.topic}</strong>
          </p>
          <p className="text-sm text-muted-foreground">
            Se compartirán todos los documentos de esta colección ({collection?.document_count || 0} documentos) con el workspace seleccionado.
          </p>
          {isLoadingWorkspaces ? (
            <div className="flex justify-center items-center p-4">
              <Loader2 className="h-6 w-6 animate-spin" />
            </div>
          ) : workspaces.length > 0 ? (
            <Select value={selectedWorkspace || undefined} onValueChange={setSelectedWorkspace}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Seleccione un workspace" />
              </SelectTrigger>
              <SelectContent>
                {workspaces.map((workspace) => (
                  <SelectItem key={workspace.id} value={workspace.id}>
                    {workspace.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          ) : (
            <p className="text-muted-foreground">No se encontraron workspaces para compartir.</p>
          )}
        </div>
        <DialogFooter className="flex flex-col-reverse sm:flex-row sm:justify-end gap-2 mt-4">
          <Button variant="outline" onClick={() => onOpenChange(false)} className="w-full sm:w-auto">
            Cancelar
          </Button>
          <Button
            onClick={handleShare}
            disabled={!selectedWorkspace || isSharing || isLoadingWorkspaces}
            className="w-full sm:w-auto"
          >
            {isSharing ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
            Compartir Colección
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
