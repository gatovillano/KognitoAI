// src/app/(dashboard)/agenda/task-dialog.tsx

import React, { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { CalendarIcon } from 'lucide-react';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';
import { Calendar } from '@/components/ui/calendar';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { cn } from '@/lib/utils';
import apiClient from '@/lib/api';
import { toast } from 'sonner';
import { TaskResponse } from './types';
import { ProfileSelectorDialog } from '@/components/dialogs/ProfileSelectorDialog';
import { Tag } from '@/components/ui/tag'; // Assuming a Tag component for displaying linked profiles
import { KanbanStatus } from '../workspaces/[id]/projects/types'; // Correctly placed import

interface TaskDialogProps {
  isOpen: boolean;
  onOpenChange: (isOpen: boolean) => void;
  onSaveSuccess: (task: TaskResponse) => void;
  task?: TaskResponse | null; // Tarea opcional para edición, ahora acepta null
  workspaceId?: string; // Añadir workspaceId
}

export function TaskDialog({ isOpen, onOpenChange, onSaveSuccess, task, workspaceId }: TaskDialogProps) {
  const [description, setDescription] = useState(task?.description || '');
  const [startDate, setStartDate] = useState<Date | undefined>(task?.start_date ? new Date(task.start_date) : undefined); // Nuevo estado
  const [endDate, setEndDate] = useState<Date | undefined>(task?.end_date ? new Date(task.end_date) : undefined); // Nuevo estado
  const [status, setStatus] = useState<KanbanStatus>('Pendiente');
  const [isLoading, setIsLoading] = useState(false);
  const [workspaces, setWorkspaces] = useState<any[]>([]);
  const [loadingWorkspaces, setLoadingWorkspaces] = useState(false);
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState(task?.workspace_id || ''); // NUEVO ESTADO para el selector
  const [isProfileSelectorOpen, setIsProfileSelectorOpen] = useState(false);
  const [linkedProfiles, setLinkedProfiles] = useState<any[]>([]); // State to store linked profiles

  useEffect(() => {
    if (task) {
      setDescription(task.description);
      setStartDate(task.start_date ? new Date(task.start_date) : undefined); // Inicializar startDate
      setEndDate(task.end_date ? new Date(task.end_date) : undefined); // Inicializar endDate
      setStatus(task.status as KanbanStatus || (task.is_completed ? 'Hecho' : 'Pendiente'));
      setSelectedWorkspaceId(task.workspace_id || ''); // Precargar workspace_id si la tarea ya lo tiene
    } else {
      // Resetear el formulario si no hay tarea para editar
      setDescription('');
      setStartDate(undefined); // Resetear startDate
      setEndDate(undefined); // Resetear endDate
      setStatus('Pendiente');
      setSelectedWorkspaceId(workspaceId || ''); // Usar el workspaceId del prop para nueva tarea
    }
  }, [task, isOpen, workspaceId]); // Resetear cuando la tarea o el estado del diálogo cambian

  useEffect(() => { // NUEVO useEffect para workspaces
    const fetchWorkspaces = async () => {
      setLoadingWorkspaces(true);
      try {
        const response = await apiClient.get('/api/workspaces'); // Asumo este endpoint
        setWorkspaces(response.data.workspaces);
      } catch (error) {
        console.error("Error fetching workspaces:", error);
        toast.error('Error al cargar los workspaces.');
      } finally {
        setLoadingWorkspaces(false);
      }
    };

    const fetchLinkedProfiles = async () => {
      if (task?.id) {
        try {
          const response = await apiClient.get(`/api/tasks/${task.id}/linked-profiles`);
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
  }, [isOpen, task?.id]);

  const handleSave = async () => {
    if (!description.trim()) {
      toast.error('La descripción de la tarea no puede estar vacía.');
      return;
    }

    setIsLoading(true);
    const payload = {
      description: description,
      start_date: startDate?.toISOString(), // Nuevo campo
      end_date: endDate?.toISOString(), // Nuevo campo
      status: status,
      is_completed: status === 'Hecho',
      workspace_id: selectedWorkspaceId,
    };

    try {
      let savedTask: TaskResponse;
      if (task) {
        // Actualizar tarea existente
        const response = await apiClient.put(`/api/tasks/${task.id}`, payload);
        savedTask = response.data;
        toast.success('Tarea actualizada con éxito.');
      } else {
        // Crear nueva tarea
        const response = await apiClient.post('/api/tasks', payload);
        savedTask = response.data;
        toast.success('Tarea creada con éxito.');
      }
      onSaveSuccess(savedTask);
      onOpenChange(false); // Cerrar el diálogo
    } catch (error) {
      console.error('Error al guardar la tarea:', error);
      toast.error('Error al guardar la tarea.');
    } finally {
      setIsLoading(false);
    }
  };

  // Function to handle linking a profile
  const handleLinkProfile = async (selectedProfiles: any[]) => {
    if (!task?.id || selectedProfiles.length === 0) return;

    const profileToLink = selectedProfiles[0]; // Assuming single selection for now
    try {
      await apiClient.post(`/api/tasks/${task.id}/link-profile`, { profile_id: profileToLink.id });
      toast.success(`Perfil ${profileToLink.name} vinculado correctamente.`);
      setLinkedProfiles(prev => [...prev, profileToLink]); // Add to linked profiles state
      onSaveSuccess(task); // Trigger a refresh in parent if needed
    } catch (error: any) {
      toast.error(error.response?.data?.detail || `Error al vincular el perfil ${profileToLink.name}.`);
      console.error("Error linking profile:", error);
    }
  };

  // Function to handle unlinking a profile
  const handleUnlinkProfile = async (profileId: string) => {
    if (!task?.id) return;

    try {
      await apiClient.post(`/api/tasks/${task.id}/unlink-profile`, { profile_id: profileId });
      toast.success(`Perfil desvinculado correctamente.`);
      setLinkedProfiles(prev => prev.filter(p => p.id !== profileId)); // Remove from linked profiles state
      onSaveSuccess(task); // Trigger a refresh in parent if needed
    } catch (error: any) {
      toast.error(error.response?.data?.detail || `Error al desvincular el perfil.`);
      console.error("Error unlinking profile:", error);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>{task ? 'Editar Tarea' : 'Crear Nueva Tarea'}</DialogTitle>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <div className="grid grid-cols-4 items-center gap-4">
            <Label htmlFor="description" className="text-right">
              Descripción
            </Label>
            <Textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="col-span-3"
              rows={3}
            />
          </div>
          <div className="grid grid-cols-4 items-center gap-4">
            <Label htmlFor="workspace" className="text-right">
              Workspace
            </Label>
            <select
              id="workspace"
              value={selectedWorkspaceId}
              onChange={(e) => setSelectedWorkspaceId(e.target.value)}
              className="col-span-3 border rounded-md p-2"
              disabled={loadingWorkspaces}
            >
              <option value="">{loadingWorkspaces ? "Cargando workspaces..." : "Ninguno"}</option>
              {workspaces && Array.isArray(workspaces) && workspaces.map(ws => (
                <option key={ws.id} value={ws.id}>
                  {ws.name}
                </option>
              ))}
            </select>
          </div>
          <div className="grid grid-cols-4 items-center gap-4">
            <Label htmlFor="status" className="text-right">
              Estado
            </Label>
            <select
              id="status"
              value={status}
              onChange={(e) => setStatus(e.target.value as KanbanStatus)}
              className="col-span-3 border rounded-md p-2 bg-background"
            >
              <option value="Pendiente">Pendiente</option>
              <option value="En Progreso">En Progreso</option>
              <option value="Hecho">Hecho</option>
            </select>
          </div>
          <div className="grid grid-cols-4 items-center gap-4">
            <Label htmlFor="startDate" className="text-right">
              Fecha Inicio
            </Label>
            <Popover>
              <PopoverTrigger asChild>
                <Button
                  variant={"outline"}
                  className={cn(
                    "col-span-3 justify-start text-left font-normal",
                    !startDate && "text-muted-foreground"
                  )}
                >
                  <CalendarIcon className="mr-2 h-4 w-4" />
                  {startDate ? format(startDate, "PPP", { locale: es }) : <span>Selecciona una fecha</span>}
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-auto p-0">
                <Calendar
                  mode="single"
                  selected={startDate}
                  onSelect={setStartDate}
                  initialFocus
                  locale={es}
                />
              </PopoverContent>
            </Popover>
          </div>
          <div className="grid grid-cols-4 items-center gap-4">
            <Label htmlFor="endDate" className="text-right">
              Fecha Fin
            </Label>
            <Popover>
              <PopoverTrigger asChild>
                <Button
                  variant={"outline"}
                  className={cn(
                    "col-span-3 justify-start text-left font-normal",
                    !endDate && "text-muted-foreground"
                  )}
                >
                  <CalendarIcon className="mr-2 h-4 w-4" />
                  {endDate ? format(endDate, "PPP", { locale: es }) : <span>Selecciona una fecha</span>}
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-auto p-0">
                <Calendar
                  mode="single"
                  selected={endDate}
                  onSelect={setEndDate}
                  initialFocus
                  locale={es}
                />
              </PopoverContent>
            </Popover>
          </div>
        </div>
        {task && ( // Only show if editing an existing task
          <div className="space-y-2">
            <Label>Perfiles Vinculados</Label>
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
        )}
        <DialogFooter>
          <Button onClick={() => onOpenChange(false)} variant="outline">
            Cancelar
          </Button>
          <Button onClick={handleSave} disabled={isLoading}>
            {isLoading ? 'Guardando...' : 'Guardar Tarea'}
          </Button>
        </DialogFooter>
      </DialogContent>

      {/* Profile Selector Dialog */}
      <ProfileSelectorDialog
        isOpen={isProfileSelectorOpen}
        onOpenChange={setIsProfileSelectorOpen}
        onSelectProfiles={handleLinkProfile}
        multiselect={false} // Tasks link to single profile at a time
        preSelectedProfileIds={linkedProfiles.map(p => p.id)}
      />
    </Dialog>
  );
}