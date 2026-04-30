// src/app/(dashboard)/agenda/task-dialog.tsx

import React, { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Clock, Briefcase, Activity, AlignLeft, Calendar as CalendarIconLucide, UserPlus, X } from 'lucide-react';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';
import { Calendar } from '@/components/ui/calendar';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { cn } from '@/lib/utils';
import apiClient from '@/lib/api';
import { toast } from 'sonner';
import { TaskResponse } from './types';
import { ProfileSelectorDialog } from '@/components/dialogs/ProfileSelectorDialog';
import { KanbanStatus } from '../workspaces/[id]/projects/types';

interface TaskDialogProps {
  isOpen: boolean;
  onOpenChange: (isOpen: boolean) => void;
  onSaveSuccess: (task: TaskResponse) => void;
  task?: TaskResponse | null;
  workspaceId?: string;
  initialStatus?: KanbanStatus;
}

export function TaskDialog({ isOpen, onOpenChange, onSaveSuccess, task, workspaceId, initialStatus }: TaskDialogProps) {
  const [description, setDescription] = useState(task?.description || '');
  const [startDate, setStartDate] = useState<Date | undefined>(task?.start_date ? new Date(task.start_date) : undefined);
  const [endDate, setEndDate] = useState<Date | undefined>(task?.end_date ? new Date(task.end_date) : undefined);
  const [startTime, setStartTime] = useState(task?.start_date ? format(new Date(task.start_date), "HH:mm") : "09:00");
  const [endTime, setEndTime] = useState(task?.end_date ? format(new Date(task.end_date), "HH:mm") : "18:00");
  const [status, setStatus] = useState<KanbanStatus>('Pendiente');
  const [isLoading, setIsLoading] = useState(false);
  const [workspaces, setWorkspaces] = useState<any[]>([]);
  const [loadingWorkspaces, setLoadingWorkspaces] = useState(false);
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState(task?.workspace_id || '');
  const [isProfileSelectorOpen, setIsProfileSelectorOpen] = useState(false);
  const [linkedProfiles, setLinkedProfiles] = useState<any[]>([]);

  useEffect(() => {
    if (task) {
      setDescription(task.description);
      const sDate = task.start_date ? new Date(task.start_date) : undefined;
      const eDate = task.end_date ? new Date(task.end_date) : undefined;
      setStartDate(sDate);
      setEndDate(eDate);
      setStartTime(sDate ? format(sDate, "HH:mm") : "09:00");
      setEndTime(eDate ? format(eDate, "HH:mm") : "18:00");
      setStatus(task.status as KanbanStatus || (task.is_completed ? 'Hecho' : 'Pendiente'));
      setSelectedWorkspaceId(task.workspace_id || '');
    } else {
      setDescription('');
      setStartDate(undefined);
      setEndDate(undefined);
      setStartTime("09:00");
      setEndTime("18:00");
      setStatus(initialStatus || 'Pendiente');
      setSelectedWorkspaceId(workspaceId || '');
    }
  }, [task, isOpen, workspaceId, initialStatus]);

  useEffect(() => {
    const fetchWorkspaces = async () => {
      setLoadingWorkspaces(true);
      try {
        const response = await apiClient.get('/api/workspaces?limit=100');
        setWorkspaces(response.data.workspaces);
      } catch (error) {
        console.error("Error fetching workspaces:", error);
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
    const combineDateAndTime = (date: Date | undefined, time: string) => {
      if (!date) return undefined;
      const [hours, minutes] = time.split(':').map(Number);
      const newDate = new Date(date);
      newDate.setHours(hours, minutes, 0, 0);
      return newDate;
    };

    const finalStartDate = combineDateAndTime(startDate, startTime);
    const finalEndDate = combineDateAndTime(endDate, endTime);

    const payload = {
      description: description,
      start_date: finalStartDate?.toISOString(),
      end_date: finalEndDate?.toISOString(),
      status: status,
      is_completed: status === 'Hecho',
      workspace_id: selectedWorkspaceId === 'none' ? null : selectedWorkspaceId,
    };

    try {
      let savedTask: TaskResponse;
      if (task) {
        const response = await apiClient.put(`/api/tasks/${task.id}`, payload);
        savedTask = response.data;
        toast.success('Tarea actualizada con éxito.');
      } else {
        const response = await apiClient.post('/api/tasks', payload);
        savedTask = response.data;
        toast.success('Tarea creada con éxito.');
      }
      onSaveSuccess(savedTask);
      onOpenChange(false);
    } catch (error) {
      console.error('Error al guardar la tarea:', error);
      toast.error('Error al guardar la tarea.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleLinkProfile = async (selectedProfiles: any[]) => {
    if (!task?.id || selectedProfiles.length === 0) return;
    const profileToLink = selectedProfiles[0];
    try {
      await apiClient.post(`/api/tasks/${task.id}/link-profile`, { profile_id: profileToLink.id });
      toast.success(`Perfil ${profileToLink.name} vinculado.`);
      setLinkedProfiles(prev => [...prev, profileToLink]);
    } catch (error: any) {
      toast.error(`Error al vincular el perfil.`);
    }
  };

  const handleUnlinkProfile = async (profileId: string) => {
    if (!task?.id) return;
    try {
      await apiClient.post(`/api/tasks/${task.id}/unlink-profile`, { profile_id: profileId });
      toast.success(`Perfil desvinculado.`);
      setLinkedProfiles(prev => prev.filter(p => p.id !== profileId));
    } catch (error: any) {
      toast.error(`Error al desvincular el perfil.`);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px] bg-white/80 dark:bg-card/40 backdrop-blur-2xl border-white/20 dark:border-border/40 rounded-[2.5rem] shadow-2xl overflow-hidden p-0">
        <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-transparent pointer-events-none" />

        <DialogHeader className="p-8 pb-4 relative z-10">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2.5 rounded-2xl bg-primary/10 text-primary shadow-inner">
              <Activity className="h-6 w-6" />
            </div>
            <DialogTitle className="text-3xl font-black tracking-tighter bg-gradient-to-r from-foreground to-foreground/70 bg-clip-text text-transparent">
              {task ? 'Editar Tarea' : 'Nueva Tarea'}
            </DialogTitle>
          </div>
          <DialogDescription className="text-muted-foreground font-medium">
            Define tus objetivos y mantén el control de tu progreso.
          </DialogDescription>
        </DialogHeader>

        <div className="p-8 pt-0 space-y-6 relative z-10 max-h-[75vh] overflow-y-auto custom-scrollbar">
          <div className="space-y-2">
            <Label className="flex items-center gap-2 font-bold text-xs uppercase tracking-widest text-muted-foreground/80 mb-2">
              <AlignLeft className="h-3.5 w-3.5 text-primary" /> Descripción
            </Label>
            <Textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="¿Qué necesitas hacer?"
              className="min-h-[100px] rounded-2xl bg-background/50 border-border/40 focus:ring-primary/20 transition-all resize-none leading-relaxed"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-2">
              <Label className="flex items-center gap-2 font-bold text-xs uppercase tracking-widest text-muted-foreground/80 mb-2">
                <Briefcase className="h-3.5 w-3.5 text-primary" /> Workspace
              </Label>
              <Select onValueChange={setSelectedWorkspaceId} value={selectedWorkspaceId || 'none'}>
                <SelectTrigger className="h-12 rounded-2xl bg-background/50 border-border/40 focus:ring-primary/20 transition-all">
                  <SelectValue placeholder={loadingWorkspaces ? "Cargando..." : "Ninguno"} />
                </SelectTrigger>
                <SelectContent className="rounded-2xl bg-card/95 backdrop-blur-xl border-border/40">
                  <SelectItem value="none" className="rounded-xl">Ninguno</SelectItem>
                  {workspaces && Array.isArray(workspaces) && workspaces.map(ws => (
                    <SelectItem key={ws.id} value={ws.id.toString()} className="rounded-xl">
                      {ws.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label className="flex items-center gap-2 font-bold text-xs uppercase tracking-widest text-muted-foreground/80 mb-2">
                <Activity className="h-3.5 w-3.5 text-primary" /> Estado
              </Label>
              <Select onValueChange={(val) => setStatus(val as KanbanStatus)} value={status}>
                <SelectTrigger className="h-12 rounded-2xl bg-background/50 border-border/40 focus:ring-primary/20 transition-all">
                  <SelectValue placeholder="Seleccionar estado" />
                </SelectTrigger>
                <SelectContent className="rounded-2xl bg-card/95 backdrop-blur-xl border-border/40">
                  <SelectItem value="Pendiente" className="rounded-xl">Pendiente</SelectItem>
                  <SelectItem value="En Progreso" className="rounded-xl">En Progreso</SelectItem>
                  <SelectItem value="Hecho" className="rounded-xl">Hecho</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="p-6 rounded-[2rem] bg-primary/5 border border-primary/10 space-y-6">
            <div className="grid grid-cols-1 gap-6">
              <div className="space-y-2">
                <Label className="flex items-center gap-2 font-bold text-[10px] uppercase tracking-widest text-primary/70 mb-2">
                  <CalendarIconLucide className="h-3 w-3" /> Fecha Inicio
                </Label>
                <div className="flex gap-3">
                  <Popover>
                    <PopoverTrigger asChild>
                      <Button
                        variant={"outline"}
                        className={cn(
                          "flex-grow h-11 rounded-xl bg-background/80 border-primary/20 justify-start text-left font-bold text-xs",
                          !startDate && "text-muted-foreground"
                        )}
                      >
                        <CalendarIconLucide className="mr-2 h-4 w-4 text-primary/50" />
                        {startDate ? format(startDate, "PPP", { locale: es }) : <span>Seleccionar fecha</span>}
                      </Button>
                    </PopoverTrigger>
                    <PopoverContent className="w-auto p-0 rounded-2xl border-border/40 shadow-2xl overflow-hidden">
                      <Calendar
                        mode="single"
                        selected={startDate}
                        onSelect={setStartDate}
                        initialFocus
                        locale={es}
                        className="bg-card/95 backdrop-blur-xl"
                      />
                    </PopoverContent>
                  </Popover>
                  <div className="flex items-center gap-2 bg-background/80 border border-primary/20 rounded-xl px-3 h-11">
                    <Clock className="w-4 h-4 text-primary/50" />
                    <input
                      type="time"
                      value={startTime}
                      onChange={(e) => setStartTime(e.target.value)}
                      className="bg-transparent border-none text-xs font-bold focus:outline-none [color-scheme:dark]"
                    />
                  </div>
                </div>
              </div>

              <div className="space-y-2">
                <Label className="flex items-center gap-2 font-bold text-[10px] uppercase tracking-widest text-primary/70 mb-2">
                  <CalendarIconLucide className="h-3 w-3" /> Fecha Fin
                </Label>
                <div className="flex gap-3">
                  <Popover>
                    <PopoverTrigger asChild>
                      <Button
                        variant={"outline"}
                        className={cn(
                          "flex-grow h-11 rounded-xl bg-background/80 border-primary/20 justify-start text-left font-bold text-xs",
                          !endDate && "text-muted-foreground"
                        )}
                      >
                        <CalendarIconLucide className="mr-2 h-4 w-4 text-primary/50" />
                        {endDate ? format(endDate, "PPP", { locale: es }) : <span>Seleccionar fecha</span>}
                      </Button>
                    </PopoverTrigger>
                    <PopoverContent className="w-auto p-0 rounded-2xl border-border/40 shadow-2xl overflow-hidden">
                      <Calendar
                        mode="single"
                        selected={endDate}
                        onSelect={setEndDate}
                        initialFocus
                        locale={es}
                        className="bg-card/95 backdrop-blur-xl"
                      />
                    </PopoverContent>
                  </Popover>
                  <div className="flex items-center gap-2 bg-background/80 border border-primary/20 rounded-xl px-3 h-11">
                    <Clock className="w-4 h-4 text-primary/50" />
                    <input
                      type="time"
                      value={endTime}
                      onChange={(e) => setEndTime(e.target.value)}
                      className="bg-transparent border-none text-xs font-bold focus:outline-none [color-scheme:dark]"
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>

          {task && (
            <div className="space-y-4 pt-2">
              <Label className="flex items-center gap-2 font-bold text-xs uppercase tracking-widest text-muted-foreground/80">
                <UserPlus className="h-3.5 w-3.5 text-primary" /> Perfiles Vinculados
              </Label>
              <div className="flex flex-wrap gap-2 p-4 rounded-2xl bg-background/30 border border-border/40 min-h-[60px] items-center">
                {linkedProfiles.length === 0 ? (
                  <span className="text-xs font-medium text-muted-foreground/60 italic">Ningún perfil vinculado aún...</span>
                ) : (
                  linkedProfiles.map(profile => (
                    <div key={profile.id} className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-primary/10 border border-primary/20 text-primary text-[10px] font-black uppercase tracking-tighter group/tag transition-all hover:bg-primary/20">
                      {profile.name}
                      <button
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
          )}
        </div>

        <DialogFooter className="p-8 pt-4 bg-background/20 backdrop-blur-md border-t border-border/40">
          <Button onClick={handleSave} disabled={isLoading} className="w-full h-14 rounded-2xl bg-primary shadow-lg shadow-primary/20 hover:shadow-primary/40 transition-all font-black uppercase tracking-widest text-xs gap-3">
            {isLoading ? (
              <div className="h-5 w-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <Activity className="h-5 w-5" />
            )}
            {isLoading ? 'Guardando...' : task ? 'Guardar Cambios' : 'Crear Tarea'}
          </Button>
        </DialogFooter>
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