"use client";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Tag, Link as LinkIcon, Trash2 } from 'lucide-react';
import { FormResponse, FormFieldData } from '@/types/form';
import { useState } from 'react';

interface ResponseCardProps {
  response: FormResponse;
  formFields: FormFieldData[];
  onOpenLinkProfileDialog: (response: FormResponse) => void;
  onDelete: (responseId: string) => Promise<void>; // Nueva prop para eliminar
}

export default function ResponseCard({ response, formFields, onOpenLinkProfileDialog, onDelete }: ResponseCardProps) {
  const [isDeleting, setIsDeleting] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);

  const getFieldLabel = (field_id: string) => {
    const field = formFields.find(f => f.id === field_id);
    return field ? field.label : 'Pregunta no encontrada';
  };

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
    <Card className="cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-900/50 transition-colors">
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
          <Dialog>
            <DialogTrigger asChild>
              <Button variant="outline" size="sm">Ver Detalles</Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[600px]">
              <DialogHeader>
                <DialogTitle>Detalles de la Respuesta</DialogTitle>
              </DialogHeader>
              <div className="py-4 space-y-4">
                {response.answers.map(({ field_id, value }) => (
                  <div key={field_id} className="grid grid-cols-3 gap-4">
                    <p className="font-semibold col-span-1">{getFieldLabel(field_id)}</p>
                    <p className="col-span-2 text-muted-foreground">{Array.isArray(value) ? value.join(', ') : String(value)}</p>
                  </div>
                ))}
              </div>
            </DialogContent>
          </Dialog>
          
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
  );
}