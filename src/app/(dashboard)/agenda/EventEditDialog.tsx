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
  description: z.string().min(3, "La descripción es muy corta."),
  date: z.string().min(1, "Debes seleccionar una fecha."),
  time: z.string().min(1, "Debes especificar una hora."),
  team_id: z.string().optional(),
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
  const [teams, setTeams] = useState<any[]>([]);
  const [loadingTeams, setLoadingTeams] = useState(false);
  const [workspaces, setWorkspaces] = useState<any[]>([]);
  const [loadingWorkspaces, setLoadingWorkspaces] = useState(false);
  const [isProfileSelectorOpen, setIsProfileSelectorOpen] = useState(false);
  const [linkedProfiles, setLinkedProfiles] = useState<any[]>([]); // State to store linked profiles

  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      description: event?.description || '',
      date: event?.event_datetime_local ? event.event_datetime_local.split('T')[0] : '',
      time: event?.event_datetime_local ? event.event_datetime_local.split('T')[1].substring(0, 5) : '',
      team_id: event?.team_id?.toString() || '',
      workspace_id: event?.workspace_id?.toString() || '',
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
      fetchTeams();
      fetchWorkspaces();
      fetchLinkedProfiles();
    }
  }, [isOpen, event?.id]);

  useEffect(() => {
    if (event) {
      form.reset({
        description: event.description || '',
        date: event.event_datetime_local ? new Date(event.event_datetime_local).toLocaleDateString('en-CA') : '',
        time: event.event_datetime_local ? new Date(event.event_datetime_local).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit', hour12: false }) : '',
        team_id: event.team_id?.toString() || '',
        workspace_id: event.workspace_id?.toString() || '',
      });
    }
  }, [event, form]);

  async function onSubmit(values: z.infer<typeof formSchema>) {
    // Convertir la fecha y hora local a un objeto Date
    const localDateTime = new Date(`${values.date}T${values.time}:00`);
    // Obtener la diferencia horaria del usuario en minutos y convertirla a milisegundos
    const timezoneOffsetMs = localDateTime.getTimezoneOffset() * 60 * 1000;
    // Ajustar la fecha y hora local para obtener la hora UTC
    const eventDateTimeUTC = new Date(localDateTime.getTime() - timezoneOffsetMs).toISOString();

    const toastId = toast.loading('Actualizando evento...');
    try {
      const response = await apiClient.put(`/api/agenda/events/${event.id}`, {
        description: values.description,
        event_datetime: eventDateTimeUTC, // Enviar la hora en formato ISO 8601 (UTC)
        team_id: values.team_id ? parseInt(values.team_id) : null,
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