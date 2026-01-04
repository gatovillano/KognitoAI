'use client';

import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { toast } from 'sonner';
import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Calendar as CalendarIcon, Clock, MapPin, AlignLeft, Users, Briefcase, Activity, X, UserPlus, Pencil } from 'lucide-react';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';
import apiClient from '@/lib/api';
import { ProfileSelectorDialog } from '@/components/dialogs/ProfileSelectorDialog';

const formSchema = z.object({
  summary: z.string().min(3, "El título es muy corto."),
  description: z.string().optional(),
  location: z.string().optional(),
  date: z.string().min(1, "Debes seleccionar una fecha."),
  time: z.string().min(1, "Debes especificar una hora."),
  end_date: z.string().optional(),
  end_time: z.string().optional(),
  status: z.string().optional(),
  attendee_ids: z.array(z.string()).optional(),
  external_attendees: z.array(z.string()).optional(),
  workspace_id: z.string().optional(),
});

interface EventEditDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  onSaveSuccess: (event: any) => void;
  onCloseDetails: () => void;
  event: any;
}

export function EventEditDialog({ isOpen, onOpenChange, onSaveSuccess, onCloseDetails, event }: EventEditDialogProps) {
  const [workspaces, setWorkspaces] = useState<any[]>([]);
  const [loadingWorkspaces, setLoadingWorkspaces] = useState(false);
  const [isProfileSelectorOpen, setIsProfileSelectorOpen] = useState(false);
  const [linkedProfiles, setLinkedProfiles] = useState<any[]>([]);

  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      summary: event?.summary || '',
      description: event?.description || '',
      location: event?.location || '',
      date: event?.event_datetime_local ? event.event_datetime_local.split('T')[0] : '',
      time: event?.event_datetime_local ? event.event_datetime_local.split('T')[1].substring(0, 5) : '',
      end_date: event?.end_date ? event.end_date.split('T')[0] : '',
      end_time: event?.end_date ? event.end_date.split('T')[1].substring(0, 5) : '',
      status: event?.status || 'Pendiente',
      attendee_ids: event?.attendee_ids || [],
      external_attendees: event?.external_attendees || [],
      workspace_id: event?.workspace_id?.toString() || '',
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

    const fetchLinkedProfiles = async () => {
      if (event?.id) {
        try {
          const response = await apiClient.get(`/api/agenda/events/${event.id}/linked-profiles`);
          setLinkedProfiles(response.data);
        } catch (error) {
          console.error("Error fetching linked profiles:", error);
        }
      }
    };

    if (isOpen) {
      fetchWorkspaces();
      fetchLinkedProfiles();
    }
  }, [isOpen, event?.id]);

  useEffect(() => {
    if (event) {
      form.reset({
        summary: event.summary || '',
        description: event.description || '',
        location: event.location || '',
        date: event.event_datetime_local ? new Date(event.event_datetime_local).toLocaleDateString('en-CA') : '',
        time: event.event_datetime_local ? new Date(event.event_datetime_local).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit', hour12: false }) : '',
        end_date: event.end_date ? new Date(event.end_date).toLocaleDateString('en-CA') : '',
        end_time: event.end_date ? new Date(event.end_date).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit', hour12: false }) : '',
        status: event.status || 'Pendiente',
        attendee_ids: event.attendee_ids || [],
        external_attendees: event.external_attendees || [],
        workspace_id: event.workspace_id?.toString() || '',
      });
    }
  }, [event, form]);

  async function onSubmit(values: z.infer<typeof formSchema>) {
    const toastId = toast.loading('Actualizando evento...');
    try {
      const response = await apiClient.put(`/api/agenda/events/${event.id}`, {
        summary: values.summary,
        description: values.description,
        location: values.location,
        event_date: values.date,
        event_time: values.time,
        end_date: values.end_date,
        end_time: values.end_time,
        status: values.status,
        attendee_ids: values.attendee_ids,
        external_attendees: values.external_attendees,
        workspace_id: values.workspace_id === 'none' ? null : values.workspace_id,
      });
      toast.success('¡Evento actualizado!', { id: toastId });
      onSaveSuccess(response.data);
      onOpenChange(false);
      onCloseDetails();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Error al actualizar el evento.', { id: toastId });
    }
  }

  const handleLinkProfile = async (selectedProfiles: any[]) => {
    if (!event?.id || selectedProfiles.length === 0) return;
    const profileToLink = selectedProfiles[0];
    try {
      await apiClient.post(`/api/agenda/events/${event.id}/link-profile`, { profile_id: profileToLink.id });
      toast.success(`Perfil ${profileToLink.name} vinculado.`);
      setLinkedProfiles(prev => [...prev, profileToLink]);
      onSaveSuccess(event);
    } catch (error: any) {
      toast.error(`Error al vincular el perfil.`);
    }
  };

  const handleUnlinkProfile = async (profileId: string) => {
    if (!event?.id) return;
    try {
      await apiClient.post(`/api/agenda/events/${event.id}/unlink-profile`, { profile_id: profileId });
      toast.success(`Perfil desvinculado.`);
      setLinkedProfiles(prev => prev.filter(p => p.id !== profileId));
      onSaveSuccess(event);
    } catch (error: any) {
      toast.error(`Error al desvincular el perfil.`);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[550px] bg-white/80 dark:bg-card/40 backdrop-blur-2xl border-white/20 dark:border-border/40 rounded-[2.5rem] shadow-2xl overflow-hidden p-0">
        <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-transparent pointer-events-none" />

        <DialogHeader className="p-8 pb-4 relative z-10">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2.5 rounded-2xl bg-primary/10 text-primary shadow-inner">
              <Pencil className="h-6 w-6" />
            </div>
            <DialogTitle className="text-3xl font-black tracking-tighter bg-gradient-to-r from-foreground to-foreground/70 bg-clip-text text-transparent">
              Editar Evento
            </DialogTitle>
          </div>
          <DialogDescription className="text-muted-foreground font-medium">
            Ajusta los detalles de tu evento para mantener todo en orden.
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

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <FormField control={form.control} name="location" render={({ field }) => (
                <FormItem className="space-y-2">
                  <FormLabel className="flex items-center gap-2 font-bold text-xs uppercase tracking-widest text-muted-foreground/80 mb-2">
                    <MapPin className="h-3.5 w-3.5 text-primary" /> Ubicación
                  </FormLabel>
                  <FormControl>
                    <Input placeholder="Oficina, Zoom..." {...field} className="h-12 rounded-2xl bg-background/50 border-border/40 focus:ring-primary/20 transition-all font-medium" />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )} />

              <FormField control={form.control} name="workspace_id" render={({ field }) => (
                <FormItem className="space-y-2">
                  <FormLabel className="flex items-center gap-2 font-bold text-xs uppercase tracking-widest text-muted-foreground/80 mb-2">
                    <Briefcase className="h-3.5 w-3.5 text-primary" /> Workspace
                  </FormLabel>
                  <Select onValueChange={field.onChange} value={field.value || 'none'}>
                    <FormControl>
                      <SelectTrigger className="h-12 rounded-2xl bg-background/50 border-border/40 focus:ring-primary/20 transition-all">
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
            </div>

            <FormField control={form.control} name="description" render={({ field }) => (
              <FormItem className="space-y-2">
                <FormLabel className="flex items-center gap-2 font-bold text-xs uppercase tracking-widest text-muted-foreground/80 mb-2">
                  <AlignLeft className="h-3.5 w-3.5 text-primary" /> Descripción
                </FormLabel>
                <FormControl>
                  <Textarea placeholder="Detalles adicionales..." {...field} className="min-h-[100px] rounded-2xl bg-background/50 border-border/40 focus:ring-primary/20 transition-all resize-none leading-relaxed" />
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
                      <Input type="date" {...field} className="h-10 rounded-xl bg-background/80 border-primary/20 font-bold text-xs" />
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
                      <Input type="time" {...field} className="h-10 rounded-xl bg-background/80 border-primary/20 font-bold text-xs" />
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
                      <Input type="date" {...field} className="h-10 rounded-xl bg-background/80 border-primary/20 font-bold text-xs" />
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
                      <Input type="time" {...field} className="h-10 rounded-xl bg-background/80 border-primary/20 font-bold text-xs" />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )} />
              </div>
            </div>

            <div className="space-y-4 pt-2">
              <FormLabel className="flex items-center gap-2 font-bold text-xs uppercase tracking-widest text-muted-foreground/80">
                <UserPlus className="h-3.5 w-3.5 text-primary" /> Perfiles Vinculados
              </FormLabel>
              <div className="flex flex-wrap gap-2 p-4 rounded-2xl bg-background/30 border border-border/40 min-h-[60px] items-center">
                {linkedProfiles.length === 0 ? (
                  <span className="text-xs font-medium text-muted-foreground/60 italic">Ningún perfil vinculado aún...</span>
                ) : (
                  linkedProfiles.map(profile => (
                    <div key={profile.id} className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-primary/10 border border-primary/20 text-primary text-[10px] font-black uppercase tracking-tighter group/tag transition-all hover:bg-primary/20">
                      {profile.name}
                      <button
                        type="button"
                        onClick={() => handleUnlinkProfile(profile.id)}
                        className="hover:text-destructive transition-colors"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </div>
                  ))
                )}
              </div>
              <Button
                type="button"
                variant="ghost"
                onClick={() => setIsProfileSelectorOpen(true)}
                className="w-full h-10 rounded-xl border border-dashed border-primary/30 text-primary hover:bg-primary/5 transition-all text-[10px] font-black uppercase tracking-widest"
              >
                + Vincular Perfil
              </Button>
            </div>

            <DialogFooter className="pt-4">
              <Button type="submit" disabled={form.formState.isSubmitting} className="w-full h-14 rounded-2xl bg-primary shadow-lg shadow-primary/20 hover:shadow-primary/40 transition-all font-black uppercase tracking-widest text-xs gap-3">
                {form.formState.isSubmitting ? (
                  <div className="h-5 w-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  <Activity className="h-5 w-5" />
                )}
                {form.formState.isSubmitting ? 'Actualizando...' : 'Guardar Cambios'}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>

      <ProfileSelectorDialog
        isOpen={isProfileSelectorOpen}
        onOpenChange={setIsProfileSelectorOpen}
        onSelectProfiles={handleLinkProfile}
        multiselect={false}
        preSelectedProfileIds={linkedProfiles.map(p => p.id)}
      />
    </Dialog>
  );
}