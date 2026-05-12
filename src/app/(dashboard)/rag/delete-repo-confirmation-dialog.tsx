'use client';

import { useState } from 'react';
import { toast } from 'sonner';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import apiClient from '@/lib/api';

interface DeleteRepoConfirmationDialogProps {
  repoName: string | null;
  repoUrl: string | null;
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  onDeleteSuccess: () => void;
}

export function DeleteRepoConfirmationDialog({ repoName, repoUrl, isOpen, onOpenChange, onDeleteSuccess }: DeleteRepoConfirmationDialogProps) {
  const [isDeleting, setIsDeleting] = useState(false);

  const handleDelete = async () => {
    if (!repoUrl) return;
    setIsDeleting(true);
    toast.info(`Eliminando repositorio ${repoName}...`);
    
    try {
      await apiClient.delete('/api/github/delete-repository', { data: { repo_url: repoUrl } });
      toast.success('Repositorio eliminado con éxito.');
      onDeleteSuccess();
      onOpenChange(false);
    } catch (error) {
      toast.error('Error al eliminar el repositorio.');
      console.error(error);
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <AlertDialog open={isOpen} onOpenChange={onOpenChange}>
      <AlertDialogContent className="max-w-md w-full p-4 sm:p-6">
        <AlertDialogHeader>
          <AlertDialogTitle className="text-lg sm:text-xl">¿Eliminar repositorio?</AlertDialogTitle>
          <AlertDialogDescription>
            Esta acción es irreversible. Se eliminarán permanentemente todos los documentos y fragmentos de memoria asociados al repositorio
            <strong className="mx-1 block mt-1 break-all">{repoName} ({repoUrl})</strong>
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter className="flex flex-col-reverse sm:flex-row sm:justify-end gap-2 mt-4">
          <AlertDialogCancel disabled={isDeleting} className="w-full sm:w-auto">Cancelar</AlertDialogCancel>
          <AlertDialogAction onClick={handleDelete} disabled={isDeleting} className="w-full sm:w-auto bg-destructive hover:bg-destructive/90">
            {isDeleting ? 'Eliminando...' : 'Sí, eliminar'}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
