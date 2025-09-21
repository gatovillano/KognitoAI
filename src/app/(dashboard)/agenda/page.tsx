// En: src/app/(dashboard)/agenda/page.tsx (VERSIÓN FINAL Y ROBUSTA)

'use client';

import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import apiClient from '@/lib/api';
import { toast } from 'sonner';
import { PlusCircle, Clock, Trash2, Users, MoreHorizontal, Info, CheckCircle2, Link as LinkIcon, CalendarIcon } from 'lucide-react';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { EventDialog } from './event-dialog';
import { Calendar } from '@/components/ui/calendar';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog';
import { format, startOfWeek, endOfWeek } from 'date-fns';
import { es } from 'date-fns/locale';
import { EventDetailsDialog } from './EventDetailsDialog';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { TaskDialog } from './task-dialog'; // Importar TaskDialog
import { Checkbox } from '@/components/ui/checkbox'; // Importar Checkbox para las tareas
import { WeeklyScheduleView } from './WeeklyScheduleView'; // Importar WeeklyScheduleView
import { MonthlyScheduleView } from './MonthlyScheduleView'; // Importar MonthlyScheduleView

export interface AgendaEvent {
  id: number;
  description: string;
  event_datetime_utc: string;
  event_datetime_local: string;
  user_timezone: string;
  team_shared?: boolean | string; // Indicates if shared with a team, can be boolean or team name/id
  workspace_id?: string;
  workspace_name?: string;
  workspace_color?: string;
  linked_profiles?: any[]; // Add linked_profiles to AgendaEvent interface
}

// Nuevo tipo para las tareas
export interface TaskResponse {
  id: string;
  description: string;
  is_completed: boolean;
  due_date?: string; // Usar string para la fecha, luego convertir a Date si es necesario
  created_at: string;
  updated_at: string;
  account_id: string;
  workspace_id?: string;
  team_id?: string;
  linked_profiles?: any[]; // Add linked_profiles to TaskResponse interface
}

export default function AgendaPage() {
  const [allEvents, setAllEvents] = useState<AgendaEvent[]>([]);
  const [allTasks, setAllTasks] = useState<TaskResponse[]>([]); // Nuevo estado para todas las tareas
  const [isLoading, setIsLoading] = useState(true);
  const [selectedDate, setSelectedDate] = useState<Date | undefined>(new Date());
  const [viewType, setViewType] = useState<'day' | 'week' | 'month'>('day'); // Nuevo estado para el tipo de vista
  
  const [isEventDialogOpen, setIsEventDialogOpen] = useState(false);
  const [isTaskDialogOpen, setIsTaskDialogOpen] = useState(false); // Nuevo estado para el diálogo de tareas
  const [deletingEvent, setDeletingEvent] = useState<AgendaEvent | null>(null);
  const [deletingTask, setDeletingTask] = useState<TaskResponse | null>(null); // Nuevo estado para eliminar tarea
  const [selectedEvent, setSelectedEvent] = useState<AgendaEvent | null>(null);
  const [selectedTask, setSelectedTask] = useState<TaskResponse | null>(null); // Nuevo estado para editar tarea
  const [isDetailsDialogOpen, setIsDetailsDialogOpen] = useState(false);

  const fetchEvents = async () => {
    setIsLoading(true);
    try {
      const [eventsResponse, tasksResponse] = await Promise.all([
        apiClient.post('/api/list-events', { include_past: true }),
        apiClient.get('/api/tasks') // Nuevo endpoint para listar tareas
      ]);
      setAllEvents(eventsResponse.data);
      setAllTasks(tasksResponse.data); // Guardar las tareas
    } catch (error) {
      toast.error('Error al cargar los datos de la agenda.');
      console.error('Error fetching agenda data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => { fetchEvents(); }, []);

  const handleSaveSuccess = (newEvent: AgendaEvent) => {
    setAllEvents(prev => [...prev, newEvent].sort((a,b) => new Date(a.event_datetime_utc).getTime() - new Date(b.event_datetime_utc).getTime()));
  };

  const handleTaskSaveSuccess = (newTask: TaskResponse) => {
    setAllTasks(prev => {
      const existingIndex = prev.findIndex(t => t.id === newTask.id);
      if (existingIndex > -1) {
        // Actualizar tarea existente
        const updatedTasks = [...prev];
        updatedTasks[existingIndex] = newTask;
        return updatedTasks;
      } else {
        // Añadir nueva tarea
        return [...prev, newTask];
      }
    });
  };

  const handleDeleteConfirm = async () => {
    if (!deletingEvent) return;
    const toastId = toast.loading('Cancelando evento...');
    try {
      await apiClient.post('/api/cancel-event', { event_id: deletingEvent.id });
      setAllEvents(allEvents.filter(e => e.id !== deletingEvent.id));
      toast.success('Evento cancelado', { id: toastId });
      setDeletingEvent(null);
    } catch (error) {
      toast.error('Error al cancelar el evento', { id: toastId });
    }
  };

  const handleTaskDeleteConfirm = async () => {
    if (!deletingTask) return;
    const toastId = toast.loading('Eliminando tarea...');
    try {
      await apiClient.delete(`/api/tasks/${deletingTask.id}`);
      setAllTasks(allTasks.filter(t => t.id !== deletingTask.id));
      toast.success('Tarea eliminada', { id: toastId });
      setDeletingTask(null);
    } catch (error) {
      toast.error('Error al eliminar la tarea', { id: toastId });
    }
  };

  const handleToggleTaskCompleted = async (task: TaskResponse) => {
    const originalIsCompleted = task.is_completed;
    // Optimistic update
    setAllTasks(prev => prev.map(t => 
      t.id === task.id ? { ...t, is_completed: !originalIsCompleted } : t
    ));

    try {
      await apiClient.put(`/api/tasks/${task.id}`, { is_completed: !originalIsCompleted });
      toast.success(`Tarea "${task.description}" ${!originalIsCompleted ? 'marcada como completada' : 'marcada como pendiente'}.`);
    } catch (error) {
      toast.error('Error al actualizar el estado de la tarea.');
      console.error('Error toggling task completion:', error);
      // Revert optimistic update on error
      setAllTasks(prev => prev.map(t => 
        t.id === task.id ? { ...t, is_completed: originalIsCompleted } : t
      ));
    }
  };

  // Filtrado de eventos y tareas para la vista diaria
  const eventsForSelectedPeriod = allEvents.filter(event => {
    if (!selectedDate) return false;
    const eventDate = new Date(event.event_datetime_local);
    
    if (viewType === 'month') {
      return eventDate.getMonth() === selectedDate.getMonth() && eventDate.getFullYear() === selectedDate.getFullYear();
    } else if (viewType === 'week') {
      const startOfWeekDate = startOfWeek(selectedDate, { weekStartsOn: 1 }); // Lunes como inicio de semana
      const endOfWeekDate = endOfWeek(selectedDate, { weekStartsOn: 1 });
      
      return eventDate >= startOfWeekDate && eventDate <= endOfWeekDate;
    } else { // 'day' view
      return (
        eventDate.getDate() === selectedDate.getDate() &&
        eventDate.getMonth() === selectedDate.getMonth() &&
        eventDate.getFullYear() === selectedDate.getFullYear()
      );
    }
  }).sort((a, b) => new Date(a.event_datetime_local).getTime() - new Date(b.event_datetime_local).getTime());

  const tasksForSelectedPeriod = allTasks.filter(task => {
    // If task has no due_date, always include it in the current period view
    if (!task.due_date) return true; // <--- Changed this line

    if (!selectedDate) return false; // Still need a selectedDate for dated tasks

    const taskDueDate = new Date(task.due_date);

    if (viewType === 'month') {
      return taskDueDate.getMonth() === selectedDate.getMonth() && taskDueDate.getFullYear() === selectedDate.getFullYear();
    } else if (viewType === 'week') {
      const startOfWeekDate = startOfWeek(selectedDate, { weekStartsOn: 1 }); // Lunes como inicio de semana
      const endOfWeekDate = endOfWeek(selectedDate, { weekStartsOn: 1 });

      return taskDueDate >= startOfWeekDate && taskDueDate <= endOfWeekDate;
    } else { // 'day' view
      return (
        taskDueDate.getDate() === selectedDate.getDate() &&
        taskDueDate.getMonth() === selectedDate.getMonth() &&
        taskDueDate.getFullYear() === selectedDate.getFullYear()
      );
    }
  }).sort((a, b) => {
    // Sort: undated tasks first, then by due_date
    if (!a.due_date && !b.due_date) return 0;
    if (!a.due_date) return -1; // a comes before b
    if (!b.due_date) return 1;  // b comes before a

    return new Date(a.due_date).getTime() - new Date(b.due_date).getTime();
  });

  const periodText = viewType === 'week' ? "esta semana" : viewType === 'month' ? "este mes" : "este día";

  return (
    <div className="p-4 sm:p-8 max-w-7xl mx-auto overflow-x-hidden">
      <div className="p-6 h-full flex flex-col">
        <div className="flex items-center justify-between mb-6 shrink-0">
          <div>
            <h1 className="text-3xl font-bold flex items-center">
                <CalendarIcon className="mr-2 h-8 w-8 text-primary" />
                Agenda
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button variant="ghost" size="icon" className="ml-2 h-6 w-6 text-muted-foreground">
                        <Info className="h-4 w-4" />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>Tus próximos eventos y tareas.</p> {/* Texto actualizado */}
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
            </h1>
          </div>
          <div className="flex gap-2">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm" className="h-8 px-2 md:px-4">
                  <span className="hidden md:inline">Acciones</span> <MoreHorizontal className="md:ml-2 h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-[180px]"> {/* Ancho ajustado */}
                <DropdownMenuItem onClick={() => setIsEventDialogOpen(true)}>
                  <PlusCircle className="mr-2 h-4 w-4" /> Agendar Evento
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setIsTaskDialogOpen(true)}> {/* Nuevo botón para tarea */}
                  <CheckCircle2 className="mr-2 h-4 w-4" /> Añadir Tarea
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => setViewType('week')} className={viewType === 'week' ? "font-bold" : ""}>
                  Vista Semanal
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setViewType('day')} className={viewType === 'day' ? "font-bold" : ""}>
                  Vista Diaria
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setViewType('month')} className={viewType === 'month' ? "font-bold" : ""}>
                  Vista Mensual
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
        
        {/* ---- ESTRUCTURA DE LAYOUT CORREGIDA ---- */}
        <div className={`flex-grow grid gap-6 min-h-0 ${viewType === 'week' || viewType === 'month' ? 'md:grid-cols-1' : 'md:grid-cols-3'}`}>
          <div className={`${viewType === 'week' || viewType === 'month' ? 'hidden' : 'md:col-span-1'} flex justify-center md:justify-start`}>
              <Calendar
                  mode="single"
                  selected={selectedDate}
                  onSelect={setSelectedDate}
                  className="rounded-md border p-0"
                  classNames={{
                    month: "space-y-4 p-3",
                    caption_label: "text-sm font-medium",
                  }}
              />
          </div>

          <div className={`${viewType === 'week' || viewType === 'month' ? 'md:col-span-1' : 'md:col-span-2'} flex flex-col min-h-0`}>
              {viewType === 'week' ? (
                <WeeklyScheduleView
                  currentDate={selectedDate || new Date()}
                  events={allEvents}
                  tasks={allTasks}
                  onDateChange={setSelectedDate}
                  onEditEvent={(event) => { setSelectedEvent(event); setIsDetailsDialogOpen(true); }}
                  onDeleteEvent={(event) => setDeletingEvent(event)}
                  onEditTask={(task) => { setSelectedTask(task); setIsTaskDialogOpen(true); }}
                  onDeleteTask={(task) => setDeletingTask(task)}
                  onToggleTaskCompleted={handleToggleTaskCompleted}
                />
              ) : viewType === 'month' ? (
                <MonthlyScheduleView
                  currentDate={selectedDate || new Date()}
                  events={allEvents}
                  tasks={allTasks}
                  onDateChange={setSelectedDate}
                  onEditEvent={(event) => { setSelectedEvent(event); setIsDetailsDialogOpen(true); }}
                  onEditTask={(task) => { setSelectedTask(task); setIsTaskDialogOpen(true); }}
                  onToggleTaskCompleted={handleToggleTaskCompleted}
                />
              ) : (
                <>
                  <h2 className="text-xl font-semibold mb-4 shrink-0">
                      Agenda para {selectedDate ? format(selectedDate, "PPP", { locale: es }) : "..."}
                  </h2>
                  <div className="flex-grow overflow-y-auto pr-2">
                    {isLoading ? <p>Cargando agenda...</p> : (
                        <div className="space-y-4">
                            {/* Sección de Tareas */}
                            {tasksForSelectedPeriod.length > 0 && (
                              <>
                                <h3 className="text-lg font-semibold mt-4 mb-2">Tareas</h3>
                                {tasksForSelectedPeriod.map((task) => (
                                  <div key={task.id} className="p-4 border rounded-lg flex items-center justify-between hover:border-primary/50">
                                    <div className="flex items-center gap-3">
                                      <Checkbox
                                        checked={task.is_completed}
                                        onCheckedChange={() => handleToggleTaskCompleted(task)}
                                        className="h-5 w-5"
                                      />
                                      <div className={task.is_completed ? "line-through text-muted-foreground" : ""}>
                                        <p className="font-semibold">{task.description}</p>
                                        {task.due_date && (
                                          <div className="text-sm text-muted-foreground flex items-center gap-1.5 mt-1">
                                            <Clock className="h-4 w-4" />
                                            {format(new Date(task.due_date), "PPP", { locale: es })}
                                          </div>
                                        )}
                                      </div>
                                    </div>
                                    <div className="flex items-center gap-2">
                                      <Button variant="ghost" size="icon" onClick={() => { setSelectedTask(task); setIsTaskDialogOpen(true); }}>
                                        <MoreHorizontal className="h-4 w-4" />
                                      </Button>
                                      <Button variant="ghost" size="icon" onClick={() => setDeletingTask(task)}>
                                        <Trash2 className="h-4 w-4 text-destructive" />
                                      </Button>
                                      {task.linked_profiles && task.linked_profiles.length > 0 && (
                                        <TooltipProvider>
                                          <Tooltip>
                                            <TooltipTrigger asChild>
                                              <Button variant="ghost" size="icon" className="text-primary">
                                                <LinkIcon className="h-4 w-4" />
                                              </Button>
                                            </TooltipTrigger>
                                            <TooltipContent>
                                              <p>Vinculado a: {task.linked_profiles.map(p => p.name).join(', ')}</p>
                                            </TooltipContent>
                                          </Tooltip>
                                        </TooltipProvider>
                                      )}
                                      <Button variant="ghost" size="icon" onClick={() => { setSelectedTask(task); setIsTaskDialogOpen(true); }}>
                                        <LinkIcon className="h-4 w-4" />
                                      </Button>
                                    </div>
                                  </div>
                                ))}
                              </>
                            )}

                            {/* Sección de Eventos */}
                            {eventsForSelectedPeriod.length > 0 && (
                              <>
                                <h3 className="text-lg font-semibold mt-4 mb-2">Eventos</h3>
                                {eventsForSelectedPeriod.map((event) => (
                                <div key={event.id} className="p-4 border rounded-lg flex items-center justify-between hover:border-primary/50 cursor-pointer" onClick={() => { setSelectedEvent(event); setIsDetailsDialogOpen(true); }}>
                                    <div>
                                        <p className="font-semibold flex items-center">
                                            {event.description}
                                            {event.team_shared && (
                                                <span title="Compartido con equipo">
                                                    <Users className="ml-2 h-4 w-4 text-blue-500" />
                                                </span>
                                            )}
                                        </p>
                                        {event.workspace_name && (
                                            <div 
                                                className="inline-flex items-center gap-1.5 mt-2 text-xs font-medium px-2 py-0.5 rounded-full"
                                                style={{
                                                    backgroundColor: event.workspace_color ? `${event.workspace_color}20` : '#f3f4f6', // bg-gray-100
                                                }}
                                            >
                                                <span
                                                    className="h-2 w-2 rounded-full"
                                                    style={{ backgroundColor: event.workspace_color || '#888888' }}
                                                ></span>
                                                <span style={{ color: event.workspace_color || '#374151' }}>
                                                    {event.workspace_name}
                                                </span>
                                            </div>
                                        )}
                                        <div className="text-sm text-muted-foreground flex items-center gap-1.5 mt-1">
                                            <Clock className="h-4 w-4" /> 
                                            {new Date(event.event_datetime_local).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}
                                        </div>
                                    </div>
                                    <div onClick={(e) => e.stopPropagation()}>
                                        {event.linked_profiles && event.linked_profiles.length > 0 && (
                                            <TooltipProvider>
                                                <Tooltip>
                                                    <TooltipTrigger asChild>
                                                        <Button variant="ghost" size="icon" className="text-primary">
                                                            <LinkIcon className="h-4 w-4" />
                                                        </Button>
                                                    </TooltipTrigger>
                                                    <TooltipContent>
                                                        <p>Vinculado a: {event.linked_profiles.map(p => p.name).join(', ')}</p>
                                                    </TooltipContent>
                                                </Tooltip>
                                            </TooltipProvider>
                                        )}
                                        <Button variant="ghost" size="icon" onClick={() => { setSelectedEvent(event); setIsDetailsDialogOpen(true); }}>
                                            <LinkIcon className="h-4 w-4" />
                                        </Button>
                                        <Button variant="ghost" size="icon" onClick={() => setDeletingEvent(event)}>
                                            <Trash2 className="h-4 w-4 text-destructive" />
                                        </Button>
                                    </div>
                                </div>
                                ))}
                              </>
                            )}

                            {tasksForSelectedPeriod.length === 0 && eventsForSelectedPeriod.length === 0 && (
                                <p className="text-center text-muted-foreground pt-10">No tienes eventos ni tareas para {periodText}.</p>
                            )}
                        </div>
                    )}
                  </div>
                </>
              )}
            </div>
        </div>
      </div>

      <EventDialog
        isOpen={isEventDialogOpen}
        onOpenChange={setIsEventDialogOpen}
        onSaveSuccess={handleSaveSuccess}
      />
      <TaskDialog
        isOpen={isTaskDialogOpen}
        onOpenChange={setIsTaskDialogOpen}
        onSaveSuccess={handleTaskSaveSuccess}
        task={selectedTask} // Pasar la tarea seleccionada para edición
      />
      {selectedEvent && (
        <EventDetailsDialog
          isOpen={isDetailsDialogOpen}
          onOpenChange={setIsDetailsDialogOpen}
          onSaveSuccess={(updatedEvent) => {
            setAllEvents(allEvents.map(e => e.id === updatedEvent.id ? updatedEvent : e));
          }}
          event={selectedEvent}
        />
      )}
      
      <AlertDialog open={!!deletingEvent} onOpenChange={(open) => !open && setDeletingEvent(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>¿Cancelar este evento?</AlertDialogTitle>
            <AlertDialogDescription>
              Esta acción es irreversible y cancelará el recordatorio para &quot;{deletingEvent?.description}&quot;.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction onClick={handleDeleteConfirm}>Sí, cancelar evento</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog open={!!deletingTask} onOpenChange={(open) => !open && setDeletingTask(null)}> {/* Nuevo AlertDialog para tareas */}
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>¿Eliminar esta tarea?</AlertDialogTitle>
            <AlertDialogDescription>
              Esta acción es irreversible y eliminará la tarea &quot;{deletingTask?.description}&quot; permanentemente.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction onClick={handleTaskDeleteConfirm} className="bg-destructive hover:bg-destructive/90">Sí, eliminar tarea</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}