// En: src/app/(dashboard)/agenda/page.tsx (VERSIÓN FINAL Y ROBUSTA)

'use client';

import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import apiClient from '@/lib/api';
import { toast } from 'sonner';
import { PlusCircle, Clock, Trash2, Users, Calendar as CalendarIcon, MoreHorizontal, Info, CheckCircle2 } from 'lucide-react'; // Añadido CheckCircle2
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { EventDialog } from './event-dialog';
import { Calendar } from '@/components/ui/calendar';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';
import { EventDetailsDialog } from './EventDetailsDialog';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { TaskDialog } from './task-dialog'; // Importar TaskDialog
import { Checkbox } from '@/components/ui/checkbox'; // Importar Checkbox para las tareas
import { WeeklyScheduleView } from './WeeklyScheduleView'; // Importar WeeklyScheduleView

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
}

export default function AgendaPage() {
  const [allEvents, setAllEvents] = useState<AgendaEvent[]>([]);
  const [allTasks, setAllTasks] = useState<TaskResponse[]>([]); // Nuevo estado para todas las tareas
  const [isLoading, setIsLoading] = useState(true);
  const [selectedDate, setSelectedDate] = useState<Date | undefined>(new Date());
  const [isWeekView, setIsWeekView] = useState(false);
  
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
        apiClient.post('/api/list-events'),
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

  const eventsForSelectedPeriod = allEvents.filter(event => {
    if (!selectedDate) return false;
    const eventDate = new Date(event.event_datetime_local);
    // DEBUG: Log de fechas para depuración
    console.log(`Event: ${event.description}, Event Date: ${event.event_datetime_local} (${eventDate}), Selected Date: ${selectedDate}`);

    if (isWeekView) {
      const startOfWeek = new Date(selectedDate);
      startOfWeek.setDate(selectedDate.getDate() - selectedDate.getDay());
      startOfWeek.setHours(0, 0, 0, 0);
      
      const endOfWeek = new Date(startOfWeek);
      endOfWeek.setDate(startOfWeek.getDate() + 6);
      endOfWeek.setHours(23, 59, 59, 999);
      
      return eventDate >= startOfWeek && eventDate <= endOfWeek;
    } else {
      return (
        eventDate.getDate() === selectedDate.getDate() &&
        eventDate.getMonth() === selectedDate.getMonth() &&
        eventDate.getFullYear() === selectedDate.getFullYear()
      );
    }
  }).sort((a, b) => new Date(a.event_datetime_local).getTime() - new Date(b.event_datetime_local).getTime()); // Ordenar eventos

  const tasksForSelectedPeriod = allTasks.filter(task => {
    if (!selectedDate || !task.due_date) return false;
    const taskDueDate = new Date(task.due_date);
    if (isWeekView) {
      const startOfWeek = new Date(selectedDate);
      startOfWeek.setDate(selectedDate.getDate() - selectedDate.getDay());
      startOfWeek.setHours(0, 0, 0, 0);
      
      const endOfWeek = new Date(startOfWeek);
      endOfWeek.setDate(startOfWeek.getDate() + 6);
      endOfWeek.setHours(23, 59, 59, 999);
      
      return taskDueDate >= startOfWeek && taskDueDate <= endOfWeek;
    } else {
      return (
        taskDueDate.getDate() === selectedDate.getDate() &&
        taskDueDate.getMonth() === selectedDate.getMonth() &&
        taskDueDate.getFullYear() === selectedDate.getFullYear()
      );
    }
  }).sort((a, b) => new Date(a.due_date!).getTime() - new Date(b.due_date!).getTime()); // Ordenar tareas

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
                <DropdownMenuItem onClick={() => setIsWeekView(true)} className={isWeekView ? "font-bold" : ""}>
                  Vista Semanal
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setIsWeekView(false)} className={!isWeekView ? "font-bold" : ""}>
                  Vista Diaria
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
        
        {/* ---- ESTRUCTURA DE LAYOUT CORREGIDA ---- */}
        <div className={`flex-grow grid gap-6 min-h-0 ${isWeekView ? 'md:grid-cols-1' : 'md:grid-cols-3'}`}>
          <div className={`${isWeekView ? 'hidden' : 'md:col-span-1'} flex justify-center md:justify-start`}>
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

          <div className={`${isWeekView ? 'md:col-span-1' : 'md:col-span-2'} flex flex-col min-h-0`}>
              {isWeekView ? (
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
                                            <div className="flex items-center gap-2 mt-2 text-xs">
                                                <span
                                                    className="h-2.5 w-2.5 rounded-full"
                                                    style={{ backgroundColor: event.workspace_color || '#888888' }}
                                                ></span>
                                                <span className="font-medium text-muted-foreground">{event.workspace_name}</span>
                                            </div>
                                        )}
                                        <div className="text-sm text-muted-foreground flex items-center gap-1.5 mt-1">
                                            <Clock className="h-4 w-4" /> 
                                            {new Date(event.event_datetime_local).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}
                                        </div>
                                    </div>
                                    <div onClick={(e) => e.stopPropagation()}>
                                        <Button variant="ghost" size="icon" onClick={() => setDeletingEvent(event)}>
                                            <Trash2 className="h-4 w-4 text-destructive" />
                                        </Button>
                                    </div>
                                </div>
                                ))}
                              </>
                            )}

                            {tasksForSelectedPeriod.length === 0 && eventsForSelectedPeriod.length === 0 && (
                                <p className="text-center text-muted-foreground pt-10">No tienes eventos ni tareas para {isWeekView ? "esta semana" : "este día"}.</p>
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