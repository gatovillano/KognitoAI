// src/app/(dashboard)/agenda/task-dialog.tsx

import React, { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Checkbox } from '@/components/ui/checkbox';
import { CalendarIcon } from 'lucide-react';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';
import { Calendar } from '@/components/ui/calendar';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { cn } from '@/lib/utils';
import apiClient from '@/lib/api';
import { toast } from 'sonner';
import { TaskResponse } from './page'; // Importar el tipo TaskResponse
import { ProfileSelectorDialog } from '@/components/dialogs/ProfileSelectorDialog';
import { Tag } from '@/components/ui/tag'; // Assuming a Tag component for displaying linked profiles

interface TaskDialogProps {
  isOpen: boolean;
  onOpenChange: (isOpen: boolean) => void;
  onSaveSuccess: (task: TaskResponse) => void;
  task?: TaskResponse | null; // Tarea opcional para edición, ahora acepta null
  workspaceId?: string; // Añadir workspaceId
}

export function TaskDialog({ isOpen, onOpenChange, onSaveSuccess, task, workspaceId }: TaskDialogProps) {
  const [description, setDescription] = useState(task?.description || '');
  const [dueDate, setDueDate] = useState<Date | undefined>(task?.due_date ? new Date(task.due_date) : undefined);
  const [isCompleted, setIsCompleted] = useState(task?.is_completed || false);
  const [isLoading, setIsLoading] = useState(false);
  const [workspaces, setWorkspaces] = useState<any[]>([]);
  const [loadingWorkspaces, setLoadingWorkspaces] = useState(false);
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState(task?.workspace_id || ''); // NUEVO ESTADO para el selector
  const [isProfileSelectorOpen, setIsProfileSelectorOpen] = useState(false);
  const [linkedProfiles, setLinkedProfiles] = useState<any[]>([]); // State to store linked profiles

  useEffect(() => {
    if (task) {
      setDescription(task.description);
      setDueDate(task.due_date ? new Date(task.due_date) : undefined);
      setIsCompleted(task.is_completed);
      setSelectedWorkspaceId(task.workspace_id || ''); // Precargar workspace_id si la tarea ya lo tiene
    } else {
      // Resetear el formulario si no hay tarea para editar
      setDescription('');
      setDueDate(undefined);
      setIsCompleted(false);
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
    try {
      let savedTask: TaskResponse;
      if (task) {
        // Actualizar tarea existente
        const response = await apiClient.put(`/api/tasks/${task.id}`, {
          description: description,
          due_date: dueDate?.toISOString(),
          is_completed: isCompleted,
        });
        savedTask = response.data;
        toast.success('Tarea actualizada con éxito.');
      } else {
        // Crear nueva tarea
        const response = await apiClient.post('/api/tasks', {
          description: description,
          due_date: dueDate?.toISOString(),
          workspace_id: selectedWorkspaceId, // Usar el estado del selector
        });
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
            <Label htmlFor="dueDate" className="text-right">
              Fecha Límite
            </Label>
            <Popover>
              <PopoverTrigger asChild>
                <Button
                  variant={"outline"}
                  className={cn(
                    "col-span-3 justify-start text-left font-normal",
                    !dueDate && "text-muted-foreground"
                  )}
                >
                  <CalendarIcon className="mr-2 h-4 w-4" />
                  {dueDate ? format(dueDate, "PPP", { locale: es }) : <span>Selecciona una fecha</span>}
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-auto p-0">
                <Calendar
                  mode="single"
                  selected={dueDate}
                  onSelect={setDueDate}
                  initialFocus
                  locale={es}
                />
              </PopoverContent>
            </Popover>
          </div>
          {task && ( // Solo mostrar el checkbox si estamos editando una tarea existente
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="isCompleted" className="text-right">
                Completada
              </Label>
              <Checkbox
                id="isCompleted"
                checked={isCompleted}
                onCheckedChange={(checked) => setIsCompleted(Boolean(checked))}
                className="col-span-3"
              />
            </div>
          )}
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
