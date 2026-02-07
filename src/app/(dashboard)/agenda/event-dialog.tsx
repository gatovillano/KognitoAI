// src/app/(dashboard)/agenda/event-dialog.tsx
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
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Calendar as CalendarIcon, Clock, MapPin, AlignLeft, Users, Briefcase, Activity, X } from 'lucide-react';
import apiClient from '@/lib/api';
import { AgendaEvent } from './types';

const formSchema = z.object({
  summary: z.string().min(3, "El título es muy corto."),
  description: z.string().optional(),
  location: z.string().optional(),
  date: z.string().min(1, "Debes seleccionar una fecha."),
  time: z.string().min(1, "Debes especificar una hora."),
  end_date: z.string().optional(),
  end_time: z.string().optional(),
  attendee_ids: z.array(z.string()).optional(),
  external_attendees: z.array(z.string()).optional(),
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
  initialDate?: Date;
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
      end_date: '',
      end_time: '',
      attendee_ids: [],
      external_attendees: [],
      workspace_id: 'none',
      status: 'Pendiente',
    },
  });

  useEffect(() => {
    const fetchWorkspaces = async () => {
      setLoadingWorkspaces(true);
      try {
        const response = await apiClient.get('/api/workspaces');
        if (response.data && Array.isArray(response.data.workspaces)) {
          setWorkspaces(response.data.workspaces);
        } else if (Array.isArray(response.data)) {
          setWorkspaces(response.data);
        }
      } catch (error) {
        console.error("Error fetching workspaces:", error);
      } finally {
        setLoadingWorkspaces(false);
      }
    };

    if (isOpen) {
      fetchWorkspaces();
    }
  }, [isOpen]);

  useEffect(() => {
    if (isOpen) {
      if (event) {
        const eventDateTime = new Date(event.event_datetime_utc);
        const endDateTime = event.end_date ? new Date(event.end_date) : undefined;
        form.reset({
          summary: event.summary || '',
          description: event.description || '',
          location: event.location || '',
          date: eventDateTime.toLocaleDateString('en-CA'),
          time: eventDateTime.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit', hour12: false }),
          end_date: endDateTime ? endDateTime.toLocaleDateString('en-CA') : '',
          end_time: endDateTime ? endDateTime.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit', hour12: false }) : '',
          attendee_ids: event.attendees ? event.attendees.map(String) : [],
          external_attendees: event.external_attendees || [],
          status: (event as any).status || 'Pendiente',
          duration_minutes: (event as any).duration_minutes || undefined,
          workspace_id: event.workspace_id?.toString() || 'none',
        });
      } else {
        form.reset({
          summary: '',
          description: '',
          location: '',
          date: initialDate ? initialDate.toLocaleDateString('en-CA') : new Date().toLocaleDateString('en-CA'),
          time: new Date().toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit', hour12: false }),
          end_date: '',
          end_time: '',
          attendee_ids: [],
          external_attendees: [],
          workspace_id: workspaceId || 'none',
          status: 'Pendiente',
        });
      }
    }
  }, [isOpen, event, initialDate, workspaceId, form]);

  async function onSubmit(values: z.infer<typeof formSchema>) {
    const toastId = toast.loading(event ? 'Actualizando evento...' : 'Agendando evento...');
    try {
      const payload = {
        summary: values.summary,
        description: values.description,
        location: values.location,
        event_date: values.date,
        event_time: values.time,
        end_date: values.end_date || null,
        end_time: values.end_time || null,
        attendee_ids: values.attendee_ids,
        external_attendees: values.external_attendees,
        workspace_id: values.workspace_id === 'none' ? null : values.workspace_id,
        status: values.status,
        duration_minutes: values.duration_minutes,
      };

      let response;
      if (event) {
        response = await apiClient.put(`/api/agenda/events/${event.id}`, payload);
      } else {
        response = await apiClient.post('/api/add-event', payload);
      }

      toast.success(event ? '¡Evento actualizado!' : '¡Evento agendado!', { id: toastId });
      onSaveSuccess(response.data);
      onOpenChange(false);
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Error al procesar el evento.', { id: toastId });
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[550px] bg-white/80 dark:bg-card/40 backdrop-blur-2xl border-white/20 dark:border-border/40 rounded-[2.5rem] shadow-2xl overflow-hidden p-0">
        <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-transparent pointer-events-none" />

        <DialogHeader className="p-8 pb-4 relative z-10">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2.5 rounded-2xl bg-primary/10 text-primary shadow-inner">
              <CalendarIcon className="h-6 w-6" />
            </div>
            <DialogTitle className="text-3xl font-black tracking-tighter bg-gradient-to-r from-foreground to-foreground/70 bg-clip-text text-transparent">
              {event ? 'Editar Evento' : 'Agendar Evento'}
            </DialogTitle>
          </div>
          <DialogDescription className="text-muted-foreground font-medium">
            {event ? 'Modifica los detalles de tu evento.' : 'Organiza tu tiempo y mantén el control de tus actividades.'}
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="p-8 pt-0 space-y-6 relative z-10 max-h-[75vh] overflow-y-auto custom-scrollbar">
            <FormField control={form.control} name="summary" render={({ field }) => (
              <FormItem className="space-y-2">
                <FormLabel className="flex items-center gap-2 font-bold text-xs uppercase tracking-widest text-muted-foreground/80 mb-2">
                  <Activity className="h-3.5 w-3.5 text-primary" /> Título del Evento
                </FormLabel>
                <FormControl>
                  <Input placeholder="Reunión de equipo..." {...field} className="h-12 rounded-2xl bg-background/50 border-border/40 focus:ring-primary/20 transition-all font-medium" />
                </FormControl>
                <FormMessage />
              </FormItem>
            )} />

            <FormField control={form.control} name="location" render={({ field }) => (
              <FormItem className="space-y-2">
                <FormLabel className="flex items-center gap-2 font-bold text-xs uppercase tracking-widest text-muted-foreground/80 mb-2">
                  <MapPin className="h-3.5 w-3.5 text-primary" /> Ubicación
                </FormLabel>
                <FormControl>
                  <Input placeholder="Oficina, Sala de Juntas, Zoom..." {...field} className="h-12 rounded-2xl bg-background/50 border-border/40 focus:ring-primary/20 transition-all font-medium" />
                </FormControl>
                <FormMessage />
              </FormItem>
            )} />

            <FormField control={form.control} name="description" render={({ field }) => (
              <FormItem className="space-y-2">
                <FormLabel className="flex items-center gap-2 font-bold text-xs uppercase tracking-widest text-muted-foreground/80 mb-2">
                  <AlignLeft className="h-3.5 w-3.5 text-primary" /> Descripción
                </FormLabel>
                <FormControl>
                  <Textarea placeholder="Detalles de la reunión..." {...field} className="min-h-[100px] rounded-2xl bg-background/50 border-border/40 focus:ring-primary/20 transition-all resize-none leading-relaxed" />
                </FormControl>
                <FormMessage />
              </FormItem>
            )} />

            <div className="p-6 rounded-[2rem] bg-primary/5 border border-primary/10 space-y-6">
              <div className="grid grid-cols-2 gap-4">
                <FormField control={form.control} name="date" render={({ field }) => (
                  <FormItem className="space-y-2">
                    <FormLabel className="flex items-center gap-2 font-bold text-[10px] uppercase tracking-widest text-primary/70 mb-2">
                      <CalendarIcon className="h-3 w-3" /> Fecha Inicio
                    </FormLabel>
                    <FormControl>
                      <Input type="date" className="h-10 rounded-xl bg-background/80 border-primary/20 font-bold text-xs" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )} />
                <FormField control={form.control} name="time" render={({ field }) => (
                  <FormItem className="space-y-2">
                    <FormLabel className="flex items-center gap-2 font-bold text-[10px] uppercase tracking-widest text-primary/70 mb-2">
                      <Clock className="h-3 w-3" /> Hora Inicio
                    </FormLabel>
                    <FormControl>
                      <Input type="time" className="h-10 rounded-xl bg-background/80 border-primary/20 font-bold text-xs" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )} />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <FormField control={form.control} name="end_date" render={({ field }) => (
                  <FormItem className="space-y-2">
                    <FormLabel className="flex items-center gap-2 font-bold text-[10px] uppercase tracking-widest text-primary/70 mb-2">
                      <CalendarIcon className="h-3 w-3" /> Fecha Fin
                    </FormLabel>
                    <FormControl>
                      <Input type="date" className="h-10 rounded-xl bg-background/80 border-primary/20 font-bold text-xs" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )} />
                <FormField control={form.control} name="end_time" render={({ field }) => (
                  <FormItem className="space-y-2">
                    <FormLabel className="flex items-center gap-2 font-bold text-[10px] uppercase tracking-widest text-primary/70 mb-2">
                      <Clock className="h-3 w-3" /> Hora Fin
                    </FormLabel>
                    <FormControl>
                      <Input type="time" className="h-10 rounded-xl bg-background/80 border-primary/20 font-bold text-xs" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )} />
              </div>
            </div>

            <FormField control={form.control} name="workspace_id" render={({ field }) => (
              <FormItem>
                <FormLabel className="flex items-center gap-2 font-bold text-xs uppercase tracking-widest text-muted-foreground/80">
                  <Briefcase className="h-3.5 w-3.5 text-primary" /> Asociar a Workspace
                </FormLabel>
                <Select onValueChange={field.onChange} value={field.value || "none"}>
                  <FormControl>
                    <SelectTrigger className="h-12 rounded-2xl bg-background/50 border-border/40 focus:ring-primary/20 transition-all" disabled={loadingWorkspaces}>
                      <SelectValue placeholder={loadingWorkspaces ? "Cargando..." : "Seleccionar workspace"} />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent className="rounded-2xl bg-card/95 backdrop-blur-xl border-border/40">
                    <SelectItem value="none" className="rounded-xl">Ninguno</SelectItem>
                    {workspaces.map(ws => (
                      <SelectItem key={ws.id} value={ws.id.toString()} className="rounded-xl">
                        {ws.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            )} />

            <DialogFooter className="p-8 pt-4 bg-background/20 backdrop-blur-md border-t border-border/40">
              <Button type="submit" disabled={form.formState.isSubmitting} className="w-full h-14 rounded-2xl bg-primary shadow-lg shadow-primary/20 hover:shadow-primary/40 transition-all font-black uppercase tracking-widest text-xs gap-3">
                {form.formState.isSubmitting ? (
                  <div className="h-5 w-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  <Activity className="h-5 w-5" />
                )}
                {form.formState.isSubmitting ? (event ? 'Guardando...' : 'Agendando...') : (event ? 'Guardar Cambios' : 'Agendar Evento')}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}