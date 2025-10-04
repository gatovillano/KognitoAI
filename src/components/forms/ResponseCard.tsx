"use client";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Tag, Link as LinkIcon, Trash2 } from 'lucide-react';
import { FormResponse, FormFieldData } from '@/types/form';
import { useState } from 'react';
import { FormResponseDialog } from './FormResponseDialog';

interface ResponseCardProps {
  response: FormResponse;
  formFields: FormFieldData[];
  onOpenLinkProfileDialog: (response: FormResponse) => void;
  onDelete: (responseId: string) => Promise<void>; // Nueva prop para eliminar
}

export default function ResponseCard({ response, formFields, onOpenLinkProfileDialog, onDelete }: ResponseCardProps) {
  const [isDeleting, setIsDeleting] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [isDetailsDialogOpen, setIsDetailsDialogOpen] = useState(false);

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      await onDelete(response.id);
      setIsDeleteDialogOpen(false); // Cierra el diálogo al eliminar
    } catch (error) {
      // El error ya se maneja en el padre, pero podrías añadir algo aquí si es necesario
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <>
      <Card className="cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-900/50 transition-colors" onClick={() => setIsDetailsDialogOpen(true)}>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-base">Respuesta #{response.id.slice(-6)}</CardTitle>
            <CardDescription>
              Enviado el: {new Date(response.submitted_at).toLocaleString()}
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            {response.contact_profile_id && (
              <div className="flex items-center gap-1 text-sm text-muted-foreground">
                <Tag className="h-4 w-4 text-primary" />
                <span>{response.contact_profile_name || 'Perfil desconocido'}</span>
              </div>
            )}
            <Button variant="outline" size="sm" onClick={(e) => {
              e.stopPropagation();
              onOpenLinkProfileDialog(response);
            }}>
              {response.contact_profile_id ? <LinkIcon className="h-4 w-4" /> : 'Vincular Perfil'}
            </Button>
            <Button variant="outline" size="sm" onClick={(e) => {
                e.stopPropagation();
                setIsDetailsDialogOpen(true);
            }}>
                Ver Detalles
            </Button>
            
            {/* Botón y Diálogo de Eliminación */}
            <Dialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
            <DialogTrigger asChild>
              <Button variant="destructive" size="icon" onClick={(e) => e.stopPropagation()}>
                <Trash2 className="h-4 w-4" />
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>¿Estás seguro?</DialogTitle>
                <DialogDescription>
                  Esta acción no se puede deshacer. Se eliminará permanentemente la respuesta #{response.id.slice(-6)}.
                </DialogDescription>
              </DialogHeader>
              <DialogFooter>
                <Button variant="outline" onClick={() => setIsDeleteDialogOpen(false)} disabled={isDeleting}>
                  Cancelar
                </Button>
                <Button variant="destructive" onClick={handleDelete} disabled={isDeleting}>
                  {isDeleting ? 'Eliminando...' : 'Eliminar'}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
          </div>
        </CardHeader>
      </Card>
      <FormResponseDialog
        isOpen={isDetailsDialogOpen}
        onOpenChange={setIsDetailsDialogOpen}
        response={response}
      />
    </>
  );
}