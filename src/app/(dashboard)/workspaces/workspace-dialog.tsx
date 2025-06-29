'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import apiClient from '@/lib/api';

interface WorkspaceDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  workspace: { id: string; name: string; system_prompt: string | null } | null;
}

export function WorkspaceDialog({ isOpen, onClose, onSuccess, workspace }: WorkspaceDialogProps) {
  const [name, setName] = useState(workspace?.name || '');
  const [systemPrompt, setSystemPrompt] = useState(workspace?.system_prompt || '');
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setName(workspace?.name || '');
      setSystemPrompt(workspace?.system_prompt || '');
    }
  }, [workspace, isOpen]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      if (workspace) {
        await apiClient.put(`/api/workspaces/${workspace.id}`, { name, system_prompt: systemPrompt || null });
      } else {
        await apiClient.post('/api/workspaces', { name, system_prompt: systemPrompt || null });
      }
      onSuccess();
      onClose();
    } catch (error) {
      console.error('Error saving workspace:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{workspace ? 'Editar Workspace' : 'Crear Nuevo Workspace'}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label htmlFor="name">Nombre</Label>
            <Input id="name" value={name} onChange={(e) => setName(e.target.value)} required />
          </div>
          <div>
            <Label htmlFor="systemPrompt">Prompt de Sistema (Opcional)</Label>
            <Textarea 
              id="systemPrompt" 
              value={systemPrompt} 
              onChange={(e) => setSystemPrompt(e.target.value)} 
              placeholder="Escribe un prompt de sistema personalizado para este workspace..."
              rows={5}
            />
          </div>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={onClose}>Cancelar</Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Guardando...' : workspace ? 'Actualizar' : 'Crear'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
