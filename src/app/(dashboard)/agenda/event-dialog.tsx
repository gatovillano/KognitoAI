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
import { AgendaEvent } from './types';

// Schema actualizado para campos específicos
import { KanbanStatus } from '../workspaces/[id]/projects/types';
const formSchema = z.object({
  summary: z.string().min(3, "El título es muy corto."),
  description: z.string().optional(),
  location: z.string().optional(),
  date: z.string().min(1, "Debes seleccionar una fecha."),
  time: z.string().min(1, "Debes especificar una hora."),
  end_date: z.string().optional(), // Nuevo campo
  end_time: z.string().optional(), // Nuevo campo
  attendee_ids: z.array(z.string()).optional(), // Asistentes registrados (UUIDs)
  external_attendees: z.array(z.string()).optional(), // Asistentes externos (nombres)
  workspace_id: z.string().optional(),
  status: z.enum(['Pendiente', 'En Progreso', 'Hecho']).optional(),
  duration_minutes: z.number().optional(),
});

interface EventDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  onSaveSuccess: (event: any) => void;
  workspaceId?: string;
  event?: AgendaEvent | null;
  initialDate?: Date; // Nueva prop para la fecha inicial
}

export function EventDialog({ isOpen, onOpenChange, onSaveSuccess, workspaceId, event, initialDate }: EventDialogProps) {
  const [workspaces, setWorkspaces] = useState<any[]>([]);
  const [loadingWorkspaces, setLoadingWorkspaces] = useState(false);

  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      summary: '',
      description: '',
      location: '',
      date: '',
      time: '',
      end_date: '', // Nuevo campo
      end_time: '', // Nuevo campo
      attendee_ids: [],
      external_attendees: [],
      workspace_id: '',
    },
  });

  useEffect(() => {
    const fetchTeamsAndWorkspaces = async () => {
      setLoadingWorkspaces(true);
      try {
        const workspacesRes = await apiClient.get('/api/workspaces');
        setWorkspaces(workspacesRes.data.workspaces);
        console.log("Workspaces cargados:", workspacesRes.data.workspaces);
      } catch (error) {
        console.error("Error fetching teams or workspaces:", error);
      } finally {
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
        const endDateTime = event.end_date ? new Date(event.end_date) : undefined; // Obtener end_date
        form.reset({
          summary: event.summary || '',
          description: event.description || '',
          location: event.location || '',
          date: eventDateTime.toLocaleDateString('en-CA'), // 'en-CA' para formato YYYY-MM-DD
          time: eventDateTime.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit', hour12: false }),
          end_date: endDateTime ? endDateTime.toLocaleDateString('en-CA') : '', // Inicializar end_date
          end_time: endDateTime ? endDateTime.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit', hour12: false }) : '', // Inicializar end_time
          attendee_ids: event.attendees ? event.attendees.map(String) : [],
          external_attendees: event.external_attendees || [],
          status: (event as any).status || 'Pendiente',
          duration_minutes: (event as any).duration_minutes || undefined,
          // workspace_id se establecerá en un useEffect separado
        });
        console.log("Formulario reseteado para edición (sin workspace_id inicial).");
      } else {
        // Para nuevo evento, usar initialDate si está disponible
        const defaultDate = initialDate ? initialDate.toLocaleDateString('en-CA') : '';
        const defaultTime = initialDate ? initialDate.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit', hour12: false }) : '';
        form.reset({
          summary: '',
          description: '',
          date: defaultDate,
          time: defaultTime,
          end_date: '', // Resetear end_date
          end_time: '', // Resetear end_time
          workspace_id: workspaceId || '',
          status: 'Pendiente',
          duration_minutes: undefined,
        });
        console.log("Formulario reseteado para nuevo evento con fecha inicial:", defaultDate, defaultTime);
      }
    }
  }, [isOpen, event, form, workspaceId, initialDate]); // Añadir initialDate como dependencia

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
        response = await apiClient.put(`/api/agenda/events/${event.id}`, {
          summary: values.summary,
          description: values.description,
          location: values.location,
          event_date: values.date,
          event_time: values.time,
          end_date: values.end_date || null, // Nuevo campo
          end_time: values.end_time || null, // Nuevo campo
          attendee_ids: values.attendee_ids,
          external_attendees: values.external_attendees,
          workspace_id: values.workspace_id || null,
          status: values.status,
          duration_minutes: values.duration_minutes,
        });
      } else {
        response = await apiClient.post('/api/add-event', {
          summary: values.summary,
          description: values.description,
          location: values.location,
          event_date: values.date,
          event_time: values.time,
          end_date: values.end_date || null, // Nuevo campo
          end_time: values.end_time || null, // Nuevo campo
          attendee_ids: values.attendee_ids,
          external_attendees: values.external_attendees,
          workspace_id: values.workspace_id || null,
          status: values.status,
          duration_minutes: values.duration_minutes,
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
            <FormField control={form.control} name="summary" render={({ field }) => (
              <FormItem><FormLabel>Título</FormLabel><FormControl><Input placeholder="Reunión de equipo..." {...field} /></FormControl><FormMessage /></FormItem>
            )} />
            <FormField control={form.control} name="description" render={({ field }) => (
              <FormItem><FormLabel>Descripción</FormLabel><FormControl><Input placeholder="Detalles de la reunión..." {...field} /></FormControl><FormMessage /></FormItem>
            )} />
            <FormField control={form.control} name="location" render={({ field }) => (
              <FormItem><FormLabel>Ubicación</FormLabel><FormControl><Input placeholder="Oficina, Sala de Juntas, Enlace de Zoom..." {...field} /></FormControl><FormMessage /></FormItem>
            )} />
            <FormField control={form.control} name="attendee_ids" render={({ field }) => (
              <FormItem><FormLabel>IDs de Asistentes (separados por comas)</FormLabel><FormControl><Input placeholder="uuid1, uuid2..." {...field} value={field.value ? field.value.join(', ') : ''} onChange={e => field.onChange(e.target.value.split(',').map(s => s.trim()).filter(Boolean))} /></FormControl><FormMessage /></FormItem>
            )} />
            <FormField control={form.control} name="external_attendees" render={({ field }) => (
              <FormItem><FormLabel>Asistentes Externos (nombres separados por comas)</FormLabel><FormControl><Input placeholder="Juan Pérez, María García..." {...field} value={field.value ? field.value.join(', ') : ''} onChange={e => field.onChange(e.target.value.split(',').map(s => s.trim()).filter(Boolean))} /></FormControl><FormMessage /></FormItem>
            )} />
            <FormField control={form.control} name="status" render={({ field }) => (
              <FormItem>
                <FormLabel>Estado</FormLabel>
                <FormControl>
                  <select
                    className="w-full border rounded-md p-2 bg-background"
                    {...field}
                  >
                    <option value="Pendiente">Pendiente</option>
                    <option value="En Progreso">En Progreso</option>
                    <option value="Hecho">Hecho</option>
                  </select>
                </FormControl>
                <FormMessage />
              </FormItem>
            )} />
            <FormField control={form.control} name="duration_minutes" render={({ field }) => (
              <FormItem>
                <FormLabel>Duración (minutos)</FormLabel>
                <FormControl>
                  <Input type="number" placeholder="60" {...field} onChange={e => field.onChange(e.target.value ? Number(e.target.value) : undefined)} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )} />
            <div className="grid grid-cols-2 gap-4">
              <FormField control={form.control} name="date" render={({ field }) => (
                <FormItem><FormLabel>Fecha Inicio</FormLabel><FormControl><Input type="date" {...field} /></FormControl><FormMessage /></FormItem>
              )} />
              <FormField control={form.control} name="time" render={({ field }) => (
                <FormItem><FormLabel>Hora Inicio</FormLabel><FormControl><Input type="time" {...field} /></FormControl><FormMessage /></FormItem>
              )} />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <FormField control={form.control} name="end_date" render={({ field }) => (
                <FormItem><FormLabel>Fecha Fin</FormLabel><FormControl><Input type="date" {...field} /></FormControl><FormMessage /></FormItem>
              )} />
              <FormField control={form.control} name="end_time" render={({ field }) => (
                <FormItem><FormLabel>Hora Fin</FormLabel><FormControl><Input type="time" {...field} /></FormControl><FormMessage /></FormItem>
              )} />
            </div>
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
              )
            }} />
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