'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import apiClient from '@/lib/api';
import { toast } from 'sonner';
import { useAuth } from '@/contexts/AuthContext';

export default function NewChatPage() {
  const router = useRouter();
  const { user } = useAuth();

  useEffect(() => {
    if (!user) {
      // Esperar a que el usuario esté autenticado
      return;
    }

    const createNewThreadAndRedirect = async () => {
      try {
        const response = await apiClient.post('/api/threads', {});
        const newThread = response.data;
        if (!newThread || !newThread.id) {
          throw new Error('No se pudo crear un nuevo hilo de chat.');
        }
        // Usar replace para que el usuario no pueda volver a esta página "de carga"
        router.replace(`/chat/${newThread.id}`);
      } catch (error) {
        console.error('Error creando nuevo hilo de chat:', error);
        toast.error('No se pudo iniciar una nueva conversación. Por favor, inténtalo de nuevo.');
        router.replace('/dashboard'); // Redirigir a una página segura en caso de error
      }
    };

    createNewThreadAndRedirect();
  }, [user, router]);

  return (
    <div className="flex h-full w-full items-center justify-center bg-background">
      <div className="text-center">
        <p className="text-lg text-muted-foreground">Iniciando nueva conversación...</p>
        {/* Aquí se podría añadir un spinner de carga si se desea */}
      </div>
    </div>
  );
}
