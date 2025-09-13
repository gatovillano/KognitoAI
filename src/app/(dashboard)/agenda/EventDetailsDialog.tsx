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

const formSchema = z.object({
  description: z.string().min(3, "La descripción es muy corta."),
  date: z.string().min(1, "Debes seleccionar una fecha."),
  time: z.string().min(1, "Debes especificar una hora."),
  team_id: z.string().optional(),
  workspace_id: z.string().optional(),
});

interface EventDetailsDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  onSaveSuccess: (event: any) => void;
  event: any;
}

export function EventDetailsDialog({ isOpen, onOpenChange, onSaveSuccess, event }: EventDetailsDialogProps) {
  const [teams, setTeams] = useState<any[]>([]);
  const [loadingTeams, setLoadingTeams] = useState(false);
  const [workspaces, setWorkspaces] = useState<any[]>([]);
  const [loadingWorkspaces, setLoadingWorkspaces] = useState(false);

  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      description: event?.description || '',
      date: event?.event_datetime_local ? new Date(event.event_datetime_local).toISOString().split('T')[0] : '',
      time: event?.event_datetime_local ? new Date(event.event_datetime_local).toISOString().split('T')[1].substring(0, 5) : '',
      team_id: event?.team_id?.toString() || '',
    },
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

    const fetchWorkspaces = async () => {
      setLoadingWorkspaces(true);
      try {
        const response = await apiClient.get('/api/workspaces');
        setWorkspaces(response.data);
      } catch (error) {
        console.error("Error fetching workspaces:", error);
        toast.error('Error al cargar los workspaces.');
      } finally {
        setLoadingWorkspaces(false);
      }
    };

    if (isOpen) {
      fetchTeams();
      fetchWorkspaces();
    }
  }, [isOpen]);

  useEffect(() => {
    if (event) {
      form.reset({
        description: event.description || '',
        date: event.event_datetime_local ? new Date(event.event_datetime_local).toISOString().split('T')[0] : '',
        time: event.event_datetime_local ? new Date(event.event_datetime_local).toISOString().split('T')[1].substring(0, 5) : '',
        team_id: event.team_id?.toString() || '',
        workspace_id: event.workspace_id?.toString() || '',
      });
    }
  }, [event, form]);

  async function onSubmit(values: z.infer<typeof formSchema>) {
    const standardDateTime = `${values.date} ${values.time}`;
    const toastId = toast.loading('Actualizando evento...');
    try {
      const response = await apiClient.put(`/api/events/${event.id}`, {
        description: values.description,
        event_datetime: standardDateTime,
        team_id: values.team_id ? parseInt(values.team_id) : null,
        workspace_id: values.workspace_id || null,
      });
      toast.success('¡Evento actualizado!', { id: toastId });
      onSaveSuccess(response.data);
      onOpenChange(false);
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Error al actualizar el evento.', { id: toastId });
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Detalles del Evento</DialogTitle>
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
            <FormField control={form.control} name="workspace_id" render={({ field }) => (
              <FormItem>
                <FormLabel>Asociar a Workspace</FormLabel>
                <FormControl>
                  <select
                    className="w-full border rounded-md p-2"
                    onChange={field.onChange}
                    value={field.value || ''}
                    disabled={loadingWorkspaces}
                  >
                    <option value="">{loadingWorkspaces ? "Cargando workspaces..." : "Seleccionar workspace (opcional)"}</option>
                    {workspaces.map(ws => (
                      <option key={ws.id} value={ws.id.toString()}>
                        {ws.name}
                      </option>
                    ))}
                  </select>
                </FormControl>
                <FormMessage />
              </FormItem>
            )} />
            <DialogFooter>
              <Button type="submit" disabled={form.formState.isSubmitting}>
                {form.formState.isSubmitting ? 'Actualizando...' : 'Actualizar'}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
