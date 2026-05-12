"use client";

import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '@/components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Tag, Link as LinkIcon, Trash2, MoreHorizontal, Download, Calendar, MessageSquare } from 'lucide-react'; 
import { FormResponse, FormFieldData } from '@/types/form';
import { useState } from 'react';
import { FormResponseDialog } from './FormResponseDialog';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { motion } from 'framer-motion';

interface ResponseCardProps {
  response: FormResponse;
  formFields: FormFieldData[];
  onOpenLinkProfileDialog: (response: FormResponse) => void;
  onDelete: (responseId: string) => Promise<void>;
  onDownloadResponsePdf: (responseId: string) => Promise<void>;
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
      // Error handled by parent
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <>
      <motion.div
        layout
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        whileHover={{ y: -4 }}
        transition={{ duration: 0.3 }}
        className="h-full group"
      >
        <Card
          className="h-full min-h-[180px] flex flex-col relative overflow-hidden hover:bg-card/60 transition-all duration-300 border-border/40 cursor-pointer shadow-sm hover:shadow-xl"
          onClick={() => setIsDetailsDialogOpen(true)}
        >
          {/* Efecto de resplandor en el hover */}
          <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />

          <CardHeader className="pb-3 relative z-10">
            <CardTitle className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-3 min-w-0 flex-1">
                <div className="p-3 rounded-2xl bg-background/50 border border-border/40 shadow-inner group-hover:scale-110 transition-transform duration-500 flex-shrink-0">
                  <MessageSquare className="h-5 w-5 text-primary" />
                </div>
                <div className="min-w-0">
                  <span className="font-bold text-lg group-hover:text-primary transition-colors leading-tight tracking-tight block">
                    Respuesta #{response.id.slice(-6)}
                  </span>
                  <div className="flex items-center gap-1 text-xs text-muted-foreground/60 mt-1">
                    <Calendar className="h-3 w-3" />
                    <span>{new Date(response.submitted_at).toLocaleDateString('es-ES', { day: 'numeric', month: 'short' })}</span>
                  </div>
                </div>
              </div>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-8 w-8 p-0 opacity-0 group-hover:opacity-100 transition-opacity rounded-xl hover:bg-primary/10"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <MoreHorizontal className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-[180px] rounded-2xl border-border/40 bg-card/95 backdrop-blur-xl">
                  <DropdownMenuItem onClick={(e) => {
                    e.stopPropagation();
                    onDownloadResponsePdf(response.id);
                  }} className="rounded-xl">
                    <Download className="mr-2 h-4 w-4" />
                    Descargar PDF
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={(e) => {
                    e.stopPropagation();
                    onOpenLinkProfileDialog(response);
                  }} className="rounded-xl">
                    <LinkIcon className="mr-2 h-4 w-4" />
                    Vincular a Perfil
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={(e) => {
                    e.stopPropagation();
                    setIsDeleteDialogOpen(true);
                  }} className="rounded-xl text-red-500 focus:text-red-500 focus:bg-red-500/10">
                    <Trash2 className="mr-2 h-4 w-4" />
                    Eliminar
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </CardTitle>
          </CardHeader>

          <CardContent className="pt-0 flex-grow relative z-10">
             {response.contact_profile_id && (
              <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-xl bg-primary/10 text-primary border border-primary/10">
                <Tag className="h-3.5 w-3.5" />
                <span className="text-xs font-bold truncate max-w-[150px]">
                  {response.contact_profile_name || 'Perfil vinculado'}
                </span>
              </div>
            )}
          </CardContent>

          <CardFooter className="flex justify-between items-center pt-3 mt-auto border-t border-border/20 relative z-10">
            <span className="text-[10px] font-black text-muted-foreground/40 uppercase tracking-widest">
              ID: {response.id.slice(0, 8)}...
            </span>
            <div className="p-1.5 rounded-lg bg-primary/10 text-primary">
              <MessageSquare className="h-3.5 w-3.5" />
            </div>
          </CardFooter>
        </Card>
      </motion.div>

      {/* Diálogo de Confirmación de Eliminación */}
      <Dialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <DialogContent className="rounded-3xl border-border/40">
          <DialogHeader>
            <DialogTitle>¿Estás seguro?</DialogTitle>
            <DialogDescription>
              Esta acción no se puede deshacer. Se eliminará permanentemente la respuesta #{response.id.slice(-6)}.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={() => setIsDeleteDialogOpen(false)} disabled={isDeleting} className="rounded-xl">
              Cancelar
            </Button>
            <Button variant="destructive" onClick={handleDelete} disabled={isDeleting} className="rounded-xl">
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