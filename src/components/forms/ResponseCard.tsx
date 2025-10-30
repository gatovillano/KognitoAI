"use client";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Tag, Link as LinkIcon, Trash2, MoreHorizontal, Download } from 'lucide-react'; // Añadido MoreHorizontal, Download
import { FormResponse, FormFieldData } from '@/types/form';
import { useState } from 'react';
import { FormResponseDialog } from './FormResponseDialog';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'; // Importar DropdownMenu

interface ResponseCardProps {
  response: FormResponse;
  formFields: FormFieldData[];
  onOpenLinkProfileDialog: (response: FormResponse) => void;
  onDelete: (responseId: string) => Promise<void>;
  onDownloadResponsePdf: (responseId: string) => Promise<void>; // Nueva prop para descargar PDF
}

export default function ResponseCard({ response, formFields, onOpenLinkProfileDialog, onDelete, onDownloadResponsePdf }: ResponseCardProps) {
  const [isDeleting, setIsDeleting] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [isDetailsDialogOpen, setIsDetailsDialogOpen] = useState(false);

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      await onDelete(response.id);
      setIsDeleteDialogOpen(false);
    } catch (error) {
      // El error ya se maneja en el padre, pero podrías añadir algo aquí si es necesario
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <>
      <Card
        className="group cursor-pointer hover:shadow-xl hover:scale-[1.02] transition-all duration-200 border-2 hover:border-primary/20 flex flex-col h-full min-h-[150px]"
        onClick={() => setIsDetailsDialogOpen(true)}
      >
        <CardHeader className="flex flex-row items-start justify-between pb-3"> {/* items-start para alinear */}
          <div>
            <CardTitle className="text-lg font-semibold">Respuesta #{response.id.slice(-6)}</CardTitle>
            <CardDescription className="text-sm text-muted-foreground">
              Enviado el: {new Date(response.submitted_at).toLocaleString()}
            </CardDescription>
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                className="h-8 w-8 p-0 opacity-0 group-hover:opacity-100 transition-opacity"
                onClick={(e) => e.stopPropagation()} // Evita que se abra el diálogo de detalles
              >
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-[180px]">
              <DropdownMenuItem onClick={(e) => {
                e.stopPropagation();
                onDownloadResponsePdf(response.id);
              }}>
                <Download className="mr-2 h-4 w-4" />
                Descargar PDF
              </DropdownMenuItem>
              <DropdownMenuItem onClick={(e) => {
                e.stopPropagation();
                onOpenLinkProfileDialog(response);
              }}>
                <LinkIcon className="mr-2 h-4 w-4" />
                Vincular a Perfil
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={(e) => {
                e.stopPropagation();
                setIsDeleteDialogOpen(true); // Abre el diálogo de confirmación para eliminar
              }} className="text-destructive focus:text-destructive">
                <Trash2 className="mr-2 h-4 w-4" />
                Eliminar
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </CardHeader>
        <CardContent className="pt-0 flex-grow">
          {response.contact_profile_id && (
            <div className="flex items-center gap-1 text-sm text-muted-foreground mt-2">
              <Tag className="h-4 w-4 text-primary" />
              <span>{response.contact_profile_name || 'Perfil desconocido'}</span>
            </div>
          )}
        </CardContent>
      </Card>
      {/* Diálogo de Confirmación de Eliminación */}
      <Dialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
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
      <FormResponseDialog
        isOpen={isDetailsDialogOpen}
        onOpenChange={setIsDetailsDialogOpen}
        response={response}
      />
    </>
  );
}