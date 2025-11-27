'use client';

import { toast } from 'sonner';
import { useState, useEffect } from 'react';
import { Pencil, Trash2 } from 'lucide-react'; // Importar el icono de lápiz y basura

import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import apiClient from '@/lib/api';
import { ProfileSelectorDialog } from '@/components/dialogs/ProfileSelectorDialog';
import { Tag } from '@/components/ui/tag'; // Assuming a Tag component for displaying linked profiles

interface EventDetailsDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  onEditClick: (event: any) => void; // Nueva prop para manejar la edición
  onDeleteClick: (event: any) => void; // Nueva prop para manejar la eliminación
  event: any;
}

export function EventDetailsDialog({ isOpen, onOpenChange, onEditClick, onDeleteClick, event }: EventDetailsDialogProps) {
  const [teams, setTeams] = useState<any[]>([]);
  const [loadingTeams, setLoadingTeams] = useState(false);
  const [workspaces, setWorkspaces] = useState<any[]>([]);
  const [loadingWorkspaces, setLoadingWorkspaces] = useState(false);
  const [isProfileSelectorOpen, setIsProfileSelectorOpen] = useState(false);
  const [linkedProfiles, setLinkedProfiles] = useState<any[]>([]); // State to store linked profiles

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
        <form className="space-y-4"> {/* Eliminar onSubmit */}
          <div className="space-y-2">
            <p className="text-sm font-medium">Título</p>
            <p className="text-sm font-medium">{event?.summary || 'N/A'}</p>
          </div>
          <div className="space-y-2">
            <p className="text-sm font-medium">Estado</p>
            <p className="text-sm text-muted-foreground">{event?.status || 'Pendiente'}</p>
          </div>
          <div className="space-y-2">
            <p className="text-sm font-medium">Descripción</p>
            <p className="text-sm text-muted-foreground">{event?.description || 'N/A'}</p>
          </div>
          <div className="space-y-2">
            <p className="text-sm font-medium">Ubicación</p>
            <p className="text-sm text-muted-foreground">{event?.location || 'N/A'}</p>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <p className="text-sm font-medium">Fecha</p>
              <p className="text-sm text-muted-foreground">{event?.event_datetime_local ? new Date(event.event_datetime_local).toLocaleDateString('es-ES') : 'N/A'}</p>
            </div>
            <div className="space-y-2">
              <p className="text-sm font-medium">Hora</p>
              <p className="text-sm text-muted-foreground">{event?.event_datetime_local ? new Date(event.event_datetime_local).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' }) : 'N/A'}</p>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <p className="text-sm font-medium">Fecha Fin</p>
              <p className="text-sm text-muted-foreground">{event?.end_date ? new Date(event.end_date).toLocaleDateString('es-ES') : 'N/A'}</p>
            </div>
            <div className="space-y-2">
              <p className="text-sm font-medium">Hora Fin</p>
              <p className="text-sm text-muted-foreground">{event?.end_date ? new Date(event.end_date).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' }) : 'N/A'}</p>
            </div>
          </div>
          <div className="space-y-2">
            <p className="text-sm font-medium">IDs de Asistentes</p>
            <p className="text-sm text-muted-foreground">{event?.attendees?.join(', ') || 'N/A'}</p>
          </div>
          <div className="space-y-2">
            <p className="text-sm font-medium">Asistentes Externos</p>
            <p className="text-sm text-muted-foreground">{event?.external_attendees?.join(', ') || 'N/A'}</p>
          </div>
          <div className="space-y-2">
            <p className="text-sm font-medium">Compartir con Equipo</p>
            <p className="text-sm text-muted-foreground">{event?.team_shared ? (teams.find(t => t.id.toString() === event.team_shared)?.name || event.team_shared) : 'N/A'}</p>
          </div>
          <div className="space-y-2">
            <p className="text-sm font-medium">Asociar a Workspace</p>
            <p className="text-sm text-muted-foreground">{event?.workspace_id ? (workspaces.find(ws => ws.id.toString() === event.workspace_id)?.name || event.workspace_name || event.workspace_id) : 'N/A'}</p>
          </div>
          {/* New section for Linked Profiles */}
          <div className="space-y-2">
            <p className="text-sm font-medium">Perfiles Vinculados</p>
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
          <DialogFooter className="flex justify-between sm:justify-between">
            <Button
              type="button"
              variant="destructive"
              onClick={() => onDeleteClick(event)}
            >
              <Trash2 className="mr-2 h-4 w-4" /> Eliminar Evento
            </Button>
            <Button type="button" onClick={() => onEditClick(event)}>
              <Pencil className="mr-2 h-4 w-4" /> Editar Evento
            </Button>
          </DialogFooter>
        </form>
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
