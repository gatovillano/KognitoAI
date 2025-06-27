// En: src/app/(dashboard)/agenda/event-dialog.tsx
'use client';

import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { toast } from 'sonner';
import { useState, useEffect } from 'react';

import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form';
import apiClient from '@/lib/api';

// Schema actualizado para campos específicos
const formSchema = z.object({
  description: z.string().min(3, "La descripción es muy corta."),
  date: z.string().min(1, "Debes seleccionar una fecha."),
  time: z.string().min(1, "Debes especificar una hora."),
  team_id: z.string().optional(), // Optional field for sharing with a team
});

interface EventDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  onSaveSuccess: (event: any) => void;
}

export function EventDialog({ isOpen, onOpenChange, onSaveSuccess }: EventDialogProps) {
  const [teams, setTeams] = useState<any[]>([]);
  const [loadingTeams, setLoadingTeams] = useState(false);

  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: { description: '' },
  });

  useEffect(() => {
    const fetchTeams = async () => {
      setLoadingTeams(true);
      try {
        const response = await apiClient.get('/api/teams');
        setTeams(response.data);
      } catch (error) {
        console.error("Error fetching teams:", error);
        toast.error('Error al cargar los equipos.');
      } finally {
        setLoadingTeams(false);
      }
    };
    if (isOpen) {
      fetchTeams();
    }
  }, [isOpen]);

async function onSubmit(values: z.infer<typeof formSchema>) {
    // --- CAMBIO CLAVE: Combinamos fecha y hora en un formato estándar ---
    // En lugar de "2025-06-27 a las 10:00", ahora será "2025-06-27 10:00"
    const standardDateTime = `${values.date} ${values.time}`;
    
    const toastId = toast.loading('Agendando evento...');
    try {
      const response = await apiClient.post('/api/add-event', {
        description: values.description,
        event_datetime: standardDateTime,
        team_id: values.team_id ? parseInt(values.team_id) : null, // Send team ID if selected
      });
      toast.success('¡Evento agendado!', { id: toastId });
      onSaveSuccess(response.data);
      onOpenChange(false);
      form.reset();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Error al agendar el evento.', { id: toastId });
    }
}

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Agendar Nuevo Evento</DialogTitle>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField control={form.control} name="description" render={({ field }) => (
              <FormItem><FormLabel>Descripción</FormLabel><FormControl><Input placeholder="Reunión de equipo..." {...field} /></FormControl><FormMessage /></FormItem>
            )} />
            <div className="grid grid-cols-2 gap-4">
                <FormField control={form.control} name="date" render={({ field }) => (
                <FormItem><FormLabel>Fecha</FormLabel><FormControl><Input type="date" {...field} /></FormControl><FormMessage /></FormItem>
                )} />
                <FormField control={form.control} name="time" render={({ field }) => (
                <FormItem><FormLabel>Hora</FormLabel><FormControl><Input type="time" {...field} /></FormControl><FormMessage /></FormItem>
                )} />
            </div>
            <FormField control={form.control} name="team_id" render={({ field }) => (
              <FormItem>
                <FormLabel>Compartir con Equipo</FormLabel>
                <FormControl>
                  <select 
                    className="w-full border rounded-md p-2"
                    onChange={field.onChange} 
                    value={field.value || ''}
                    disabled={loadingTeams}
                  >
                    <option value="">{loadingTeams ? "Cargando equipos..." : "Seleccionar equipo (opcional)"}</option>
                    {teams.map(team => (
                      <option key={team.id} value={team.id.toString()}>
                        {team.name}
                      </option>
                    ))}
                  </select>
                </FormControl>
                <FormMessage />
              </FormItem>
            )} />
            <DialogFooter>
              <Button type="submit" disabled={form.formState.isSubmitting}>
                {form.formState.isSubmitting ? 'Agendando...' : 'Agendar'}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
