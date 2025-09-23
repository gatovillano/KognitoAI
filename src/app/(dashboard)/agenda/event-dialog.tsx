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
import { AgendaEvent } from './page';

// Schema actualizado para campos específicos
const formSchema = z.object({
  description: z.string().min(3, "La descripción es muy corta."),
  date: z.string().min(1, "Debes seleccionar una fecha."),
  time: z.string().min(1, "Debes especificar una hora."),
  team_id: z.string().optional(), // Optional field for sharing with a team
  workspace_id: z.string().optional(), // New field for workspace
});

interface EventDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  onSaveSuccess: (event: any) => void;
  workspaceId?: string;
  event?: AgendaEvent | null;
}

export function EventDialog({ isOpen, onOpenChange, onSaveSuccess, workspaceId, event }: EventDialogProps) {
  const [teams, setTeams] = useState<any[]>([]);
  const [loadingTeams, setLoadingTeams] = useState(false);
  const [workspaces, setWorkspaces] = useState<any[]>([]);
  const [loadingWorkspaces, setLoadingWorkspaces] = useState(false);

  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      description: '',
      date: '',
      time: '',
      team_id: '',
      workspace_id: '',
    },
  });

  useEffect(() => {
    const fetchTeamsAndWorkspaces = async () => {
      setLoadingTeams(true);
      setLoadingWorkspaces(true);
      try {
        const [teamsRes, workspacesRes] = await Promise.all([
          apiClient.get('/api/teams'),
          apiClient.get('/api/workspaces'),
        ]);
        setTeams(teamsRes.data);
        setWorkspaces(workspacesRes.data.workspaces);
        console.log("Workspaces cargados:", workspacesRes.data.workspaces);
      } catch (error) {
        console.error("Error fetching teams or workspaces:", error);
        toast.error('Error al cargar datos necesarios.');
      } finally {
        setLoadingTeams(false);
        setLoadingWorkspaces(false);
      }
    };

    if (isOpen) {
      fetchTeamsAndWorkspaces();
    }
  }, [isOpen]);

  // Efecto para inicializar el formulario cuando se abre el diálogo o cambia el evento
  useEffect(() => {
    if (isOpen) {
      if (event) {
        const eventDateTime = new Date(event.event_datetime_utc);
        form.reset({
          description: event.description,
          date: eventDateTime.toLocaleDateString('en-CA'), // 'en-CA' para formato YYYY-MM-DD
          time: eventDateTime.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit', hour12: false }),
          team_id: (typeof event.team_shared === 'string' ? event.team_shared : '') || '',
          // workspace_id se establecerá en un useEffect separado
        });
        console.log("Formulario reseteado para edición (sin workspace_id inicial).");
      } else {
        form.reset({
          description: '',
          date: '',
          time: '',
          team_id: '',
          workspace_id: workspaceId || '',
        });
        console.log("Formulario reseteado para nuevo evento.");
      }
    }
  }, [isOpen, event, form, workspaceId]);

  // Efecto para establecer el workspace_id una vez que los workspaces estén cargados
  useEffect(() => {
    if (isOpen && event && workspaces.length > 0) {
      const eventWorkspaceId = event?.workspace_id?.toString() || workspaceId || '';
      form.setValue('workspace_id', eventWorkspaceId);
      console.log("Workspace_id establecido con setValue:", eventWorkspaceId);
    }
  }, [isOpen, event, form, workspaceId, workspaces]);

  async function onSubmit(values: z.infer<typeof formSchema>) {
    const toastId = toast.loading(event ? 'Actualizando evento...' : 'Agendando evento...');

    try {
      let response;
      if (event) {
        const localDateTime = new Date(`${values.date}T${values.time}:00`); // Crear un objeto Date con la hora local
        const eventDateTimeUTC = localDateTime.toISOString(); // Convertir a ISO 8601 (UTC)

        response = await apiClient.put(`/api/agenda/events/${event.id}`, {
          description: values.description,
          event_datetime: eventDateTimeUTC, // Enviar la hora en formato ISO 8601 (UTC)
          team_id: values.team_id ? parseInt(values.team_id) : null,
          workspace_id: values.workspace_id || null,
        });
      } else {
        const localDateTime = new Date(`${values.date}T${values.time}:00`); // Crear un objeto Date con la hora local
        const eventDateTimeUTC = localDateTime.toISOString(); // Convertir a ISO 8601 (UTC)

        response = await apiClient.post('/api/add-event', {
          description: values.description,
          event_date: values.date,
          event_time: values.time,
          workspace_id: values.workspace_id || null,
        });
      }
      toast.success(event ? '¡Evento actualizado!' : '¡Evento agendado!', { id: toastId });
      onSaveSuccess(response.data);
      onOpenChange(false);
    } catch (error: any) {
      const errorMessage = typeof error.response?.data?.detail === 'object'
        ? JSON.stringify(error.response.data.detail)
        : error.response?.data?.detail || (event ? 'Error al actualizar el evento.' : 'Error al agendar el evento.');
      toast.error(errorMessage, { id: toastId });
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{event ? 'Editar Evento' : 'Agendar Nuevo Evento'}</DialogTitle>
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
                    {...field}
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
            <FormField control={form.control} name="workspace_id" render={({ field }) => {
              console.log("Renderizando select de Workspace:", { fieldValue: field.value, workspaces });
              return (
              <FormItem>
                <FormLabel>Asociar a Workspace</FormLabel>
                <FormControl>
                  <select
                    key={event?.id ? event.id + workspaces.length : 'new' + workspaces.length} // Añadir key para forzar re-render
                    className="w-full border rounded-md p-2"
                    {...field}
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
            )}} />
            <DialogFooter>
              <Button type="submit" disabled={form.formState.isSubmitting}>
                {form.formState.isSubmitting ? (event ? 'Guardando...' : 'Agendando...') : (event ? 'Guardar Cambios' : 'Agendar')}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}