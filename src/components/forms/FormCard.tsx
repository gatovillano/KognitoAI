"use client";

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger, DropdownMenuSeparator } from '@/components/ui/dropdown-menu';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { MessageSquare, MoreHorizontal, FileText, Edit, Trash2, ExternalLink } from 'lucide-react';
import apiClient from '@/lib/api';
import { toast } from 'sonner';
import { motion } from 'framer-motion';

// Define the Form type
interface Form {
  id: string;
  title: string;
  description?: string;
  responseCount: number;
}

interface FormCardProps {
  form: Form;
}

export default function FormCard({ form }: FormCardProps) {
  const router = useRouter();
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);

  const handleCardClick = () => {
    router.push(`/forms/${form.id}`);
  };

  const handleEdit = () => {
    router.push(`/forms/${form.id}/edit`);
  };

  const handleViewResponses = () => {
    router.push(`/forms/${form.id}/responses`);
  };

  const handleDeleteConfirm = async () => {
    const toastId = toast.loading('Eliminando formulario...');
    try {
      await apiClient.delete(`/api/forms/${form.id}`);
      router.refresh();
      toast.success('Formulario eliminado exitosamente.', { id: toastId });
      // Note: In a real app, you might want to call a parent refresh function here
      // since router.refresh() doesn't always trigger a re-fetch in the same page state.
      window.location.reload(); 
    } catch (error) {
      console.error('Error al eliminar el formulario:', error);
      toast.error('Error al eliminar el formulario. Por favor, inténtalo de nuevo.', { id: toastId });
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
          className="h-[280px] flex flex-col relative overflow-hidden hover:bg-card/60 transition-all duration-300 border-border/40 cursor-pointer shadow-sm hover:shadow-xl"
          onClick={handleCardClick}
        >
          {/* Efecto de resplandor en el hover */}
          <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />

          <CardHeader className="pb-3 relative z-10">
            <CardTitle className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-3 min-w-0 flex-1">
                <div className="p-3 rounded-2xl bg-background/50 border border-border/40 shadow-inner group-hover:scale-110 transition-transform duration-500 flex-shrink-0">
                  <FileText className="h-5 w-5 text-primary" />
                </div>
                <span className="font-bold text-lg line-clamp-2 group-hover:text-primary transition-colors leading-tight tracking-tight">
                  {form.title || 'Formulario sin título'}
                </span>
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
                <DropdownMenuContent align="end" className="w-[200px] rounded-2xl border-border/40 bg-card/95 backdrop-blur-xl">
                  <DropdownMenuItem onClick={(e) => {
                    e.stopPropagation();
                    handleEdit();
                  }} className="rounded-xl">
                    <Edit className="mr-2 h-4 w-4" />
                    Editar formulario
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={(e) => {
                    e.stopPropagation();
                    handleViewResponses();
                  }} className="rounded-xl">
                    <MessageSquare className="mr-2 h-4 w-4" />
                    Ver respuestas
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={(e) => {
                    e.stopPropagation();
                    router.push(`/share/f/${form.id}`);
                  }} className="rounded-xl">
                    <ExternalLink className="mr-2 h-4 w-4" />
                    Ver link público
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={(e) => {
                    e.stopPropagation();
                    setIsDeleteDialogOpen(true);
                  }} className="rounded-xl text-red-500 focus:text-red-500 focus:bg-red-500/10">
                    <Trash2 className="mr-2 h-4 w-4" />
                    Eliminar formulario
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </CardTitle>
          </CardHeader>

          <CardContent className="pt-0 flex-grow overflow-hidden relative z-10">
            <div className="text-sm text-muted-foreground/80 line-clamp-4 leading-relaxed">
              {form.description ? (
                <p>{form.description}</p>
              ) : (
                <p className="text-muted-foreground/60 italic">Sin descripción</p>
              )}
            </div>
          </CardContent>

          <CardFooter className="flex justify-between items-center pt-3 mt-auto border-t border-border/20 relative z-10">
            <div className="flex items-center gap-2 text-[10px] font-bold text-muted-foreground/60 uppercase tracking-widest">
              <div className="w-1.5 h-1.5 rounded-full bg-primary/40" />
              <span>{form.responseCount} respuestas</span>
            </div>
            
            <div className="flex items-center gap-2">
               <div className="p-1.5 rounded-lg bg-primary/10 text-primary group-hover:bg-primary group-hover:text-primary-foreground transition-colors">
                  <MessageSquare className="h-3.5 w-3.5" />
               </div>
            </div>
          </CardFooter>
        </Card>
      </motion.div>

      <AlertDialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <AlertDialogContent className="rounded-3xl border-border/40">
          <AlertDialogHeader>
            <AlertDialogTitle>¿Estás absolutamente seguro?</AlertDialogTitle>
            <AlertDialogDescription>
              Esta acción no se puede deshacer. Esto eliminará permanentemente el
              formulario y todas las respuestas asociadas.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={(e) => e.stopPropagation()} className="rounded-xl">Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={(e) => {
                e.stopPropagation();
                handleDeleteConfirm();
              }}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90 rounded-xl"
            >
              Sí, eliminar
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}