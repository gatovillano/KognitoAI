"use client";

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
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
import { MessageSquare, MoreVertical } from 'lucide-react';

// Define the Form type
interface Form {
  id: string;
  title: string;
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

  const handleDeleteConfirm = async () => {
    try {
      const response = await fetch(`/api/forms/${form.id}`, {
        method: 'DELETE',
      });
      if (response.ok) {
        router.refresh();
      } else {
        console.error('Failed to delete form');
        // Consider using a toast notification here instead of alert
        alert('No se pudo eliminar el formulario.');
      }
    } catch (error) {
      console.error('An error occurred:', error);
      alert('Ocurrió un error al eliminar el formulario.');
    }
  };

  return (
    <>
      <Card 
        className="flex flex-col relative"
      >
        <div 
          className="absolute top-2 right-2 z-10"
          onClick={(e) => e.stopPropagation()}
        >
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon">
                <MoreVertical className="h-5 w-5 text-muted-foreground" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={(e) => { e.stopPropagation(); handleEdit(); }}>
                Editar
              </DropdownMenuItem>
              <DropdownMenuItem 
                onClick={(e) => {
                  e.stopPropagation();
                  setIsDeleteDialogOpen(true);
                }} 
                className="text-red-500 focus:text-red-500"
              >
                Eliminar
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
        <div 
          className="flex flex-col flex-grow cursor-pointer hover:shadow-lg transition-shadow duration-200 rounded-lg h-full"
          onClick={handleCardClick}
        >
          <CardHeader>
            <CardTitle className="text-lg truncate pr-10">{form.title}</CardTitle>
          </CardHeader>
          <CardContent className="flex-grow">
            {/* Content can be added here in the future, e.g., a short description */}
          </CardContent>
          <CardFooter className="flex justify-between items-center text-sm text-muted-foreground">
            <div className="flex items-center">
              <MessageSquare className="mr-2 h-4 w-4" />
              <span>{form.responseCount} respuestas</span>
            </div>
          </CardFooter>
        </div>
      </Card>

      <AlertDialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>¿Estás absolutamente seguro?</AlertDialogTitle>
            <AlertDialogDescription>
              Esta acción no se puede deshacer. Esto eliminará permanentemente el
              formulario y todas las respuestas asociadas.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={(e) => e.stopPropagation()}>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={(e) => {
                e.stopPropagation();
                handleDeleteConfirm();
              }}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Sí, eliminar
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}