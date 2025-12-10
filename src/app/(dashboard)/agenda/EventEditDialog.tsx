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
import { ProfileSelectorDialog } from '@/components/dialogs/ProfileSelectorDialog';
import { Tag } from '@/components/ui/tag'; // Assuming a Tag component for displaying linked profiles

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
  onCloseDetails: () => void; // Nueva prop para cerrar el diálogo de detalles
  event: any;
}

export function EventEditDialog({ isOpen, onOpenChange, onSaveSuccess, onCloseDetails, event }: EventEditDialogProps) {
  const [workspaces, setWorkspaces] = useState<any[]>([]);
  const [loadingWorkspaces, setLoadingWorkspaces] = useState(false);
  const [isProfileSelectorOpen, setIsProfileSelectorOpen] = useState(false);
  const [linkedProfiles, setLinkedProfiles] = useState<any[]>([]); // State to store linked profiles

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
        // Solución al problema: /api/workspaces did not return an array
        if (response.data && Array.isArray(response.data.workspaces)) {
          setWorkspaces(response.data.workspaces);
        } else if (Array.isArray(response.data)) { // En caso de que la respuesta sea directamente el array
          setWorkspaces(response.data);
        }
        else {
          console.warn("/api/workspaces did not return an array in expected format:", response.data);
          setWorkspaces([]);
        }
      } catch (error) {
        console.error("Error fetching workspaces:", error);
        toast.error('Error al cargar los workspaces.');
        setWorkspaces([]);
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
          toast.error("Error al cargar perfiles vinculados.");
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
        workspace_id: values.workspace_id || null,
      });
      toast.success('¡Evento actualizado!', { id: toastId });
      onSaveSuccess(response.data);
      onOpenChange(false);
      onCloseDetails(); // Cerrar el diálogo de detalles después de la edición
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Error al actualizar el evento.', { id: toastId });
    }
  }

  // Function to handle linking a profile
  const handleLinkProfile = async (selectedProfiles: any[]) => {
    if (!event?.id || selectedProfiles.length === 0) return;

    const profileToLink = selectedProfiles[0]; // Assuming single selection for now
    try {
      await apiClient.post(`/api/agenda/events/${event.id}/link-profile`, { profile_id: profileToLink.id });
      toast.success(`Perfil ${profileToLink.name} vinculado correctamente.`);
      setLinkedProfiles(prev => [...prev, profileToLink]); // Add to linked profiles state
      onSaveSuccess(event); // Trigger a refresh in parent if needed
    } catch (error: any) {
      toast.error(error.response?.data?.detail || `Error al vincular el perfil ${profileToLink.name}.`);
      console.error("Error linking profile:", error);
    }
  };

  // Function to handle unlinking a profile
  const handleUnlinkProfile = async (profileId: string) => {
    if (!event?.id) return;

    try {
      await apiClient.post(`/api/agenda/events/${event.id}/unlink-profile`, { profile_id: profileId });
      toast.success(`Perfil desvinculado correctamente.`);
      setLinkedProfiles(prev => prev.filter(p => p.id !== profileId)); // Remove from linked profiles state
      onSaveSuccess(event); // Trigger a refresh in parent if needed
    } catch (error: any) {
      toast.error(error.response?.data?.detail || `Error al desvincular el perfil.`);
      console.error("Error unlinking profile:", error);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Editar Evento</DialogTitle>
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
            <div className="grid grid-cols-2 gap-4">
              <FormField control={form.control} name="date" render={({ field }) => (
                <FormItem><FormLabel>Fecha</FormLabel><FormControl><Input type="date" {...field} /></FormControl><FormMessage /></FormItem>
              )} />
              <FormField control={form.control} name="time" render={({ field }) => (
                <FormItem><FormLabel>Hora</FormLabel><FormControl><Input type="time" {...field} /></FormControl><FormMessage /></FormItem>
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
            <FormField control={form.control} name="status" render={({ field }) => (
              <FormItem>
                <FormLabel>Estado</FormLabel>
                <FormControl>
                  <select
                    className="w-full border rounded-md p-2"
                    onChange={field.onChange}
                    value={field.value || 'Pendiente'}
                  >
                    <option value="Pendiente">Pendiente</option>
                    <option value="En Progreso">En Progreso</option>
                    <option value="Hecho">Hecho</option>
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
            {/* New section for Linked Profiles */}
            <div className="space-y-2">
              <FormLabel>Perfiles Vinculados</FormLabel>
              <div className="flex flex-wrap gap-2 p-2 border rounded-md min-h-[40px]">
                {linkedProfiles.length === 0 ? (
                  <span className="text-sm text-muted-foreground">Ningún perfil vinculado.</span>
                ) : (
                  linkedProfiles.map(profile => (
                    <Tag key={profile.id} variant="outline" className="flex items-center gap-1">
                      {profile.name}
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-auto p-1"
                        onClick={() => handleUnlinkProfile(profile.id)}
                      >
                        x
                      </Button>
                    </Tag>
                  ))
                )}
              </div>
              <Button
                type="button"
                variant="outline"
                onClick={() => setIsProfileSelectorOpen(true)}
                className="w-full"
              >
                Vincular Perfil
              </Button>
            </div>
            <DialogFooter>
              <Button type="submit" disabled={form.formState.isSubmitting}>
                {form.formState.isSubmitting ? 'Actualizando...' : 'Actualizar'}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>

      {/* Profile Selector Dialog */}
      <ProfileSelectorDialog
        isOpen={isProfileSelectorOpen}
        onOpenChange={setIsProfileSelectorOpen}
        onSelectProfiles={handleLinkProfile}
        multiselect={false} // Events link to single profile at a time
        preSelectedProfileIds={linkedProfiles.map(p => p.id)}
      />
    </Dialog>
  );
}