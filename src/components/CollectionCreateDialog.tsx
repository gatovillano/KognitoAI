import React, { useState } from 'react';
import { Dialog, DialogContent, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import apiClient from '@/lib/api';
import { toast } from 'sonner';

type Props = {
  parentId?: string;
  workspaceId?: string;
  onCreated?: () => void;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
};

export default function CollectionCreateDialog({ parentId, workspaceId, onCreated, open: openProp, onOpenChange }: Props) {
  const [internalOpen, setInternalOpen] = useState(false);
  const open = typeof openProp === 'boolean' ? openProp : internalOpen;
  const setOpen = (v: boolean) => {
    if (onOpenChange) onOpenChange(v);
    else setInternalOpen(v);
  };

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(false);

  const handleClose = () => {
    setOpen(false);
    setName('');
    setDescription('');
  };

  const create = async () => {
    if (!name.trim()) return toast.error('El nombre es requerido');
    if (!description.trim()) return toast.error('La descripción es requerida');
    setLoading(true);
    try {
      const payload: any = {
        topic: name.trim(),
        description: description.trim(),
        workspaceId: workspaceId || undefined,
        parent_id: parentId || undefined,
        item_type: 'folder',
      };
      await apiClient.post('/api/collections', payload);
      toast.success('Subcolección creada');
      handleClose();
      onCreated && onCreated();
    } catch (e) {
      console.error(e);
      toast.error('Error creando subcolección');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="sm:max-w-md">
        <DialogTitle>Crear subcolección</DialogTitle>
        <DialogDescription>
          Define un nombre identitario y una descripción para la nueva subcolección.
        </DialogDescription>
        <div className="mt-4 space-y-4">
          <div className="space-y-2">
            <Label htmlFor="subcol-name">
              Nombre <span className="text-destructive">*</span>
            </Label>
            <Input
              id="subcol-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Ej: Capítulo 1 — Introducción"
              onKeyDown={(e) => e.key === 'Enter' && create()}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="subcol-description">
              Descripción <span className="text-destructive">*</span>
            </Label>
            <Textarea
              id="subcol-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe el contenido o propósito de esta subcolección..."
              rows={3}
              className="resize-none"
            />
          </div>
        </div>
        <div className="mt-6 flex justify-end gap-2">
          <Button variant="ghost" onClick={handleClose} disabled={loading}>
            Cancelar
          </Button>
          <Button onClick={create} disabled={loading || !name.trim() || !description.trim()}>
            {loading ? 'Creando...' : 'Crear subcolección'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
