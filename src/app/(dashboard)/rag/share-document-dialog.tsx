// En: src/app/(dashboard)/rag/share-document-dialog.tsx

'use client';

import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Loader2 } from 'lucide-react';
import apiClient from '@/lib/api';
import { toast } from 'sonner';

import type { Document } from './columns';

interface ShareDocumentDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  onShareSuccess: () => void;
  document: Document | null;
}

export function ShareDocumentDialog({ isOpen, onOpenChange, onShareSuccess, document }: ShareDocumentDialogProps) {
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
    if (!document || !selectedWorkspace) return;

    setIsSharing(true);
    try {
      await apiClient.post(`/api/documents/${document.file_name}/share`, {
        workspace_id: selectedWorkspace,
      });
      toast.success(`Documento compartido con el workspace.`);
      onShareSuccess();
      onOpenChange(false);
    } catch (error) {
      toast.error('Error al compartir el documento.');
    } finally {
      setIsSharing(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md w-full p-4 sm:p-6">
        <DialogHeader>
          <DialogTitle className="text-lg sm:text-xl">Compartir Documento</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <p>Seleccione un workspace para compartir el documento: <strong>{document?.file_name}</strong></p>
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
            Compartir
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
