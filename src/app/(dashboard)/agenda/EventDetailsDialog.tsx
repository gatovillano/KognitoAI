'use client';

import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { toast } from 'sonner';
import { useState, useEffect } from 'react';
import { Pencil } from 'lucide-react'; // Importar el icono de lápiz

import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Form, FormControl, FormField, FormItem, FormLabel } from '@/components/ui/form'; // Eliminar FormMessage
import apiClient from '@/lib/api';
import { ProfileSelectorDialog } from '@/components/dialogs/ProfileSelectorDialog';
import { Tag } from '@/components/ui/tag'; // Assuming a Tag component for displaying linked profiles

const formSchema = z.object({
  description: z.string(),
  date: z.string(),
  time: z.string(),
  team_id: z.string().optional(),
  workspace_id: z.string().optional(),
});

interface EventDetailsDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  onEditClick: (event: any) => void; // Nueva prop para manejar la edición
  event: any;
}

export function EventDetailsDialog({ isOpen, onOpenChange, onEditClick, event }: EventDetailsDialogProps) {
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

  // No hay onSubmit en este diálogo de solo lectura

  // Function to handle linking a profile (se mantiene para visualización)
  const handleLinkProfile = async (selectedProfiles: any[]) => {
    if (!event?.id || selectedProfiles.length === 0) return;
    // Esta función no debería ser llamada en un diálogo de solo lectura,
    // pero la mantengo para evitar errores si el botón de "Vincular Perfil" se muestra por error.
    // En el modo de visualización, este botón debería estar deshabilitado o no visible.
    toast.info("Para vincular perfiles, por favor edita el evento.");
  };

  // Function to handle unlinking a profile (se mantiene para visualización)
  const handleUnlinkProfile = async (profileId: string) => {
    if (!event?.id) return;
    // Similar a handleLinkProfile, esta función no debería ser llamada.
    toast.info("Para desvincular perfiles, por favor edita el evento.");
  };

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Detalles del Evento</DialogTitle>
        </DialogHeader>
        <Form {...form}>
          <form className="space-y-4"> {/* Eliminar onSubmit */}
            <FormField control={form.control} name="description" render={({ field }) => (
              <FormItem><FormLabel>Descripción</FormLabel><FormControl><Input readOnly {...field} /></FormControl></FormItem>
            )} />
            <div className="grid grid-cols-2 gap-4">
              <FormField control={form.control} name="date" render={({ field }) => (
                <FormItem><FormLabel>Fecha</FormLabel><FormControl><Input type="date" readOnly {...field} /></FormControl></FormItem>
              )} />
              <FormField control={form.control} name="time" render={({ field }) => (
                <FormItem><FormLabel>Hora</FormLabel><FormControl><Input type="time" readOnly {...field} /></FormControl></FormItem>
              )} />
            </div>
            <FormField control={form.control} name="team_id" render={({ field }) => (
              <FormItem>
                <FormLabel>Compartir con Equipo</FormLabel>
                <FormControl>
                  <select 
                    className="w-full border rounded-md p-2"
                    value={field.value || ''}
                    disabled // Deshabilitar el select
                  >
                    <option value="">{loadingTeams ? "Cargando equipos..." : "Seleccionar equipo (opcional)"}</option>
                    {teams.map(team => (
                      <option key={team.id} value={team.id.toString()}>
                        {team.name}
                      </option>
                    ))}
                  </select>
                </FormControl>
              </FormItem>
            )} />
            <FormField control={form.control} name="workspace_id" render={({ field }) => (
              <FormItem>
                <FormLabel>Asociar a Workspace</FormLabel>
                <FormControl>
                  <select
                    className="w-full border rounded-md p-2"
                    value={field.value || ''}
                    disabled // Deshabilitar el select
                  >
                    <option value="">{loadingWorkspaces ? "Cargando workspaces..." : "Seleccionar workspace (opcional)"}</option>
                    {workspaces.map(ws => (
                      <option key={ws.id} value={ws.id.toString()}>
                        {ws.name}
                      </option>
                    ))}
                  </select>
                </FormControl>
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
                      {/* Botón de desvincular deshabilitado en modo visualización */}
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-auto p-1"
                        disabled
                      >
                        x
                      </Button>
                    </Tag>
                  ))
                )}
              </div>
              {/* Botón de vincular perfil deshabilitado en modo visualización */}
              <Button
                type="button"
                variant="outline"
                disabled
                className="w-full"
              >
                Vincular Perfil
              </Button>
            </div>
            <DialogFooter>
              <Button type="button" onClick={() => onEditClick(event)}>
                <Pencil className="mr-2 h-4 w-4" /> Editar Evento
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>

      {/* Profile Selector Dialog (se mantiene pero no debería ser interactivo) */}
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
