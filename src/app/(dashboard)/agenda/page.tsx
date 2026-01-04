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
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog';
import { format, startOfWeek, endOfWeek } from 'date-fns';
import { es } from 'date-fns/locale';
import { EventDetailsDialog } from './EventDetailsDialog';
import { EventEditDialog } from './EventEditDialog'; // Importar EventEditDialog
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '@/components/ui/sheet'; // Importar Sheet
import { TaskDialog } from './task-dialog'; // Importar TaskDialog
import { Checkbox } from '@/components/ui/checkbox'; // Importar Checkbox para las tareas
import { WeeklyScheduleView } from './WeeklyScheduleView'; // Importar WeeklyScheduleView
import { MonthlyScheduleView } from './MonthlyScheduleView'; // Importar MonthlyScheduleView
import { AgendaEvent, TaskResponse } from './types';



export default function AgendaPage() {
  const [allEvents, setAllEvents] = useState<AgendaEvent[]>([]);
  const [allTasks, setAllTasks] = useState<TaskResponse[]>([]); // Nuevo estado para todas las tareas
  const [isLoading, setIsLoading] = useState(true);
  const [selectedDate, setSelectedDate] = useState<Date | undefined>(new Date());
  const [viewType, setViewType] = useState<'day' | 'week' | 'month'>('month'); // Nuevo estado para el tipo de vista
  const [workspaceId, setWorkspaceId] = useState<string | null>(null); // Nuevo estado para workspace_id

  const [isEventDialogOpen, setIsEventDialogOpen] = useState(false);
  const [isTaskDialogOpen, setIsTaskDialogOpen] = useState(false); // Nuevo estado para el diálogo de tareas
  const [deletingEvent, setDeletingEvent] = useState<AgendaEvent | null>(null);
  const [deletingTask, setDeletingTask] = useState<TaskResponse | null>(null); // Nuevo estado para eliminar tarea
  const [selectedEvent, setSelectedEvent] = useState<AgendaEvent | null>(null);
  const [selectedTask, setSelectedTask] = useState<TaskResponse | null>(null); // Nuevo estado para editar tarea
  const [isDetailsDialogOpen, setIsDetailsDialogOpen] = useState(false);
  const [isEventEditDialogOpen, setIsEventEditDialogOpen] = useState(false); // Nuevo estado para el diálogo de edición
  const [isInfoSheetOpen, setIsInfoSheetOpen] = useState(false); // Nuevo estado para controlar la visibilidad del Sheet

  // Detectar workspace_id desde la URL
  useEffect(() => {
    const pathSegments = window.location.pathname.split('/');
    const workspacesIndex = pathSegments.indexOf('workspaces');
    if (workspacesIndex !== -1 && pathSegments[workspacesIndex + 1]) {
      setWorkspaceId(pathSegments[workspacesIndex + 1]);
    }
  }, []);

  const fetchEvents = async () => {
    setIsLoading(true);
    try {
      const eventsPayload: { include_past: boolean; workspace_id?: string } = { include_past: true };
      const tasksParams: { workspace_id?: string } = {};

      if (workspaceId) {
        eventsPayload.workspace_id = workspaceId;
        tasksParams.workspace_id = workspaceId;
      }

      const [eventsResponse, tasksResponse] = await Promise.all([
        apiClient.post('/api/list-events', eventsPayload),
        apiClient.get('/api/tasks', { params: tasksParams })
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

  useEffect(() => { fetchEvents(); }, [workspaceId]);

  const handleSaveSuccess = (updatedEvent: AgendaEvent) => {
    setAllEvents(prev => {
      const existingIndex = prev.findIndex(e => e.id === updatedEvent.id);
      if (existingIndex > -1) {
        const updatedEvents = [...prev];
        updatedEvents[existingIndex] = updatedEvent;
        return updatedEvents.sort((a, b) => new Date(a.event_datetime_utc).getTime() - new Date(b.event_datetime_utc).getTime());
      } else {
        return [...prev, updatedEvent].sort((a, b) => new Date(a.event_datetime_utc).getTime() - new Date(b.event_datetime_utc).getTime());
      }
    });
    setIsEventEditDialogOpen(false); // Cerrar el diálogo de edición después de guardar
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
      await apiClient.post('/api/cancel-event', { event_id: String(deletingEvent.id) });
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

  const handleCreateEvent = (date: Date) => {
    setSelectedEvent({ // Prellenar el evento con la fecha seleccionada
      id: 'temp-event-id', // ID temporal
      summary: '',
      description: '',
      event_datetime_utc: date.toISOString(),
      event_datetime_local: date.toISOString(),
      user_timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    });
    setInitialEventDate(date); // Establecer la fecha inicial para el diálogo
    setIsEventDialogOpen(true);
  };

  const [initialEventDate, setInitialEventDate] = useState<Date | undefined>(undefined); // Nuevo estado para la fecha inicial del evento

  const handleMoveEvent = async (eventId: string, newDate: Date) => {
    const eventToMove = allEvents.find(event => event.id === eventId);
    if (!eventToMove) return;

    const originalEventDateTime = new Date(eventToMove.event_datetime_local);
    const updatedDateTime = new Date(
      newDate.getFullYear(),
      newDate.getMonth(),
      newDate.getDate(),
      originalEventDateTime.getHours(),
      originalEventDateTime.getMinutes(),
      originalEventDateTime.getSeconds()
    );

    const toastId = toast.loading('Moviendo evento...');
    try {
      // Actualizar el evento en el backend
      await apiClient.put(`/api/agenda/events/${eventId}`, {
        event_date: format(updatedDateTime, 'yyyy-MM-dd'),
        event_time: format(updatedDateTime, 'HH:mm'),
      });

      // Actualizar el estado local
      setAllEvents(prev => prev.map(event =>
        event.id === eventId ? { ...event, event_datetime_local: updatedDateTime.toISOString() } : event
      ));
      toast.success('Evento movido exitosamente.', { id: toastId });
    } catch (error) {
      toast.error('Error al mover el evento.', { id: toastId });
      console.error('Error moving event:', error);
    }
  };

  const handleMoveTask = async (taskId: string, newDate: Date) => {
    const taskToMove = allTasks.find(task => task.id === taskId);
    if (!taskToMove) return;

    const originalTaskDueDate = taskToMove.end_date ? new Date(taskToMove.end_date) : new Date();
    const updatedDateTime = new Date(
      newDate.getFullYear(),
      newDate.getMonth(),
      newDate.getDate(),
      originalTaskDueDate.getHours(),
      originalTaskDueDate.getMinutes(),
      originalTaskDueDate.getSeconds()
    );

    const toastId = toast.loading('Moviendo tarea...');
    try {
      // Optimistic update
      setAllTasks(prev => prev.map(task =>
        task.id === taskId ? { ...task, end_date: updatedDateTime.toISOString() } : task
      ));

      // API call
      await apiClient.put(`/api/tasks/${taskId}`, {
        end_date: updatedDateTime.toISOString(),
      });

      toast.success('Tarea movida exitosamente.', { id: toastId });
    } catch (error) {
      toast.error('Error al mover la tarea.', { id: toastId });
      console.error('Error moving task:', error);
      // Revert on error
      setAllTasks(prev => prev.map(task =>
        task.id === taskId ? { ...task, end_date: taskToMove.end_date } : task
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
    // Si la tarea no tiene fechas, se muestra siempre (o se podría decidir no mostrarla)
    if (!task.start_date && !task.end_date) return true;

    if (!selectedDate) return false;

    const viewStart = new Date(selectedDate);
    const viewEnd = new Date(selectedDate);

    if (viewType === 'month') {
      viewStart.setDate(1);
      viewStart.setHours(0, 0, 0, 0);
      viewEnd.setMonth(viewEnd.getMonth() + 1);
      viewEnd.setDate(0); // Último día del mes
      viewEnd.setHours(23, 59, 59, 999);
    } else if (viewType === 'week') {
      const start = startOfWeek(selectedDate, { weekStartsOn: 1 });
      viewStart.setTime(start.getTime());
      viewStart.setHours(0, 0, 0, 0);

      const end = endOfWeek(selectedDate, { weekStartsOn: 1 });
      viewEnd.setTime(end.getTime());
      viewEnd.setHours(23, 59, 59, 999);
    } else { // 'day' view
      viewStart.setHours(0, 0, 0, 0);
      viewEnd.setHours(23, 59, 59, 999);
    }

    // Si tiene rango (start_date y end_date)
    if (task.start_date && task.end_date) {
      const taskStart = new Date(task.start_date);
      taskStart.setHours(0, 0, 0, 0);
      const taskEnd = new Date(task.end_date);
      taskEnd.setHours(23, 59, 59, 999);

      // Verificar solapamiento de rangos
      return taskStart <= viewEnd && taskEnd >= viewStart;
    }

    // Solo end_date
    if (task.end_date) {
      const taskEnd = new Date(task.end_date);
      return taskEnd >= viewStart && taskEnd <= viewEnd;
    }

    // Solo start_date
    if (task.start_date) {
      const taskStart = new Date(task.start_date);
      return taskStart >= viewStart && taskStart <= viewEnd;
    }

    return false;
  }).sort((a, b) => {
    // Sort: undated tasks first, then by end_date (or start_date)
    if (!a.end_date && !b.end_date) return 0;
    if (!a.end_date) return -1; // a comes before b
    if (!b.end_date) return 1;  // b comes before a

    return new Date(a.end_date!).getTime() - new Date(b.end_date!).getTime();
  });

  const periodText = viewType === 'week' ? "esta semana" : viewType === 'month' ? "este mes" : "este día";

  return (
    <div className="p-4 sm:p-8 max-w-7xl mx-auto overflow-x-hidden animate-in fade-in duration-700">
      <div className="h-full flex flex-col space-y-10">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 shrink-0">
          <div className="space-y-1">
            <div className="flex items-center gap-3">
              <div className="p-3 rounded-2xl bg-primary/10 text-primary shadow-lg shadow-primary/10">
                <CalendarIcon className="h-8 w-8" />
              </div>
              <h1 className="text-4xl font-black tracking-tighter bg-gradient-to-r from-foreground to-foreground/70 bg-clip-text text-transparent">
                Agenda
              </h1>
              <Button variant="ghost" size="icon" className="h-10 w-10 rounded-2xl bg-primary/5 text-primary hover:bg-primary/10 transition-all" onClick={() => setIsInfoSheetOpen(true)}>
                <Info className="h-5 w-5" />
              </Button>
            </div>
            <p className="text-muted-foreground font-medium">Gestiona tus eventos, reuniones y tareas con inteligencia.</p>
          </div>

          <div className="flex items-center gap-3">
            <div className="bg-card/40 backdrop-blur-md p-1 rounded-2xl border border-border/40 flex gap-1">
              {(['day', 'week', 'month'] as const).map((type) => (
                <Button
                  key={type}
                  variant={viewType === type ? 'default' : 'ghost'}
                  size="sm"
                  onClick={() => setViewType(type)}
                  className={`rounded-xl px-4 font-bold text-xs uppercase tracking-widest transition-all ${viewType === type ? 'shadow-lg shadow-primary/20' : 'text-muted-foreground hover:text-foreground'}`}
                >
                  {type === 'day' ? 'Día' : type === 'week' ? 'Semana' : 'Mes'}
                </Button>
              ))}
            </div>

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button className="h-12 px-6 rounded-2xl bg-primary shadow-lg shadow-primary/20 hover:shadow-primary/40 transition-all gap-2 font-bold">
                  <PlusCircle className="h-5 w-5" />
                  <span className="hidden md:inline">Crear</span>
                  <MoreHorizontal className="h-4 w-4 opacity-50" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56 bg-card/95 backdrop-blur-xl border-border/40 rounded-2xl p-2">
                <DropdownMenuItem onClick={() => setIsEventDialogOpen(true)} className="rounded-xl focus:bg-primary/10 focus:text-primary cursor-pointer py-2.5 gap-3">
                  <PlusCircle className="h-4 w-4" /> Agendar Evento
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => { setSelectedTask(null); setIsTaskDialogOpen(true); }} className="rounded-xl focus:bg-primary/10 focus:text-primary cursor-pointer py-2.5 gap-3">
                  <CheckCircle2 className="h-4 w-4" /> Añadir Tarea
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>

        <div className={`flex-grow grid gap-8 min-h-0 ${viewType === 'week' || viewType === 'month' ? 'md:grid-cols-1' : 'md:grid-cols-12'}`}>
          <div className={`${viewType === 'week' || viewType === 'month' ? 'hidden' : 'md:col-span-4'} flex flex-col gap-6`}>
            <Card className="border-border/40 bg-card/40 backdrop-blur-xl rounded-[2rem] overflow-hidden shadow-sm">
              <Calendar
                mode="single"
                selected={selectedDate}
                onSelect={setSelectedDate}
                className="p-4"
                classNames={{
                  month: "space-y-4",
                  caption_label: "text-sm font-black uppercase tracking-widest",
                  day_selected: "bg-primary text-primary-foreground hover:bg-primary hover:text-primary-foreground focus:bg-primary focus:text-primary-foreground rounded-xl shadow-lg shadow-primary/30",
                  day_today: "bg-primary/10 text-primary font-bold rounded-xl",
                  day: "h-10 w-10 p-0 font-medium aria-selected:opacity-100 hover:bg-primary/5 rounded-xl transition-colors",
                }}
              />
            </Card>

            {/* Mini estadísticas o info adicional podría ir aquí */}
            <div className="bg-gradient-to-br from-primary/10 to-secondary/10 p-6 rounded-[2rem] border border-primary/10">
              <h4 className="text-xs font-black uppercase tracking-widest text-primary mb-3">Resumen del día</h4>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-muted-foreground">Eventos</span>
                  <span className="text-sm font-bold">{eventsForSelectedPeriod.length}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-muted-foreground">Tareas</span>
                  <span className="text-sm font-bold">{tasksForSelectedPeriod.length}</span>
                </div>
              </div>
            </div>
          </div>

          <div className={`${viewType === 'week' || viewType === 'month' ? 'md:col-span-1' : 'md:col-span-8'} flex flex-col min-h-0`}>
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
                onCreateEvent={handleCreateEvent}
                onMoveEvent={handleMoveEvent}
                onMoveTask={handleMoveTask}
              />
            ) : (
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <h2 className="text-2xl font-black tracking-tight">
                    {selectedDate ? format(selectedDate, "EEEE, d 'de' MMMM", { locale: es }) : "Cargando..."}
                  </h2>
                  <div className="h-px flex-1 bg-gradient-to-r from-border/60 to-transparent ml-6" />
                </div>

                <div className="flex-grow overflow-y-auto pr-2 space-y-8 custom-scrollbar">
                  {isLoading ? (
                    <div className="flex flex-col items-center justify-center py-20 gap-4">
                      <div className="h-10 w-10 border-4 border-primary/30 border-t-primary rounded-full animate-spin" />
                      <p className="text-muted-foreground font-medium">Sincronizando tu agenda...</p>
                    </div>
                  ) : (
                    <>
                      {/* Sección de Tareas */}
                      <div className="space-y-4">
                        <div className="flex items-center gap-2">
                          <CheckCircle2 className="h-5 w-5 text-green-500" />
                          <h3 className="text-sm font-black uppercase tracking-widest text-muted-foreground/70">Tareas Prioritarias</h3>
                        </div>

                        {tasksForSelectedPeriod.length > 0 ? (
                          <div className="grid gap-3">
                            {tasksForSelectedPeriod.map((task) => (
                              <Card key={task.id} className="group relative overflow-hidden border-border/40 bg-card/40 backdrop-blur-md rounded-2xl hover:bg-card/60 transition-all duration-300 hover:shadow-lg hover:shadow-primary/5">
                                <div className="p-4 flex items-center justify-between gap-4">
                                  <div className="flex items-center gap-4 min-w-0">
                                    <Checkbox
                                      checked={task.is_completed}
                                      onCheckedChange={() => handleToggleTaskCompleted(task)}
                                      className="h-6 w-6 rounded-lg border-2 border-primary/20 data-[state=checked]:bg-primary data-[state=checked]:border-primary transition-all"
                                    />
                                    <div className={task.is_completed ? "opacity-50" : ""}>
                                      <p className={`font-bold text-sm sm:text-base truncate ${task.is_completed ? "line-through" : ""}`}>
                                        {task.description}
                                      </p>
                                      {task.end_date && (
                                        <div className="text-[10px] font-bold text-muted-foreground/60 uppercase tracking-wider flex items-center gap-1.5 mt-1">
                                          <Clock className="h-3 w-3" />
                                          {format(new Date(task.end_date!), "p", { locale: es })}
                                        </div>
                                      )}
                                    </div>
                                  </div>
                                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                    <Button variant="ghost" size="icon" className="h-8 w-8 rounded-xl hover:bg-primary/10 hover:text-primary" onClick={() => { setSelectedTask(task); setIsTaskDialogOpen(true); }}>
                                      <MoreHorizontal className="h-4 w-4" />
                                    </Button>
                                    <Button variant="ghost" size="icon" className="h-8 w-8 rounded-xl hover:bg-destructive/10 hover:text-destructive" onClick={() => setDeletingTask(task)}>
                                      <Trash2 className="h-4 w-4" />
                                    </Button>
                                  </div>
                                </div>
                              </Card>
                            ))}
                          </div>
                        ) : (
                          <div className="py-8 text-center border-2 border-dashed border-border/40 rounded-3xl bg-card/20">
                            <p className="text-xs font-bold text-muted-foreground/60 uppercase tracking-widest">Sin tareas pendientes</p>
                          </div>
                        )}
                      </div>

                      {/* Sección de Eventos */}
                      <div className="space-y-4">
                        <div className="flex items-center gap-2">
                          <CalendarIcon className="h-5 w-5 text-primary" />
                          <h3 className="text-sm font-black uppercase tracking-widest text-muted-foreground/70">Eventos Programados</h3>
                        </div>

                        {eventsForSelectedPeriod.length > 0 ? (
                          <div className="grid gap-4">
                            {eventsForSelectedPeriod.map((event) => (
                              <Card
                                key={event.id}
                                className="group relative overflow-hidden border-border/40 bg-card/40 backdrop-blur-md rounded-[2rem] hover:bg-card/60 transition-all duration-500 hover:shadow-xl hover:shadow-primary/5 cursor-pointer"
                                onClick={() => { setSelectedEvent(event); setIsDetailsDialogOpen(true); }}
                              >
                                <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                                <div className="p-5 flex items-center justify-between gap-4 relative z-10">
                                  <div className="flex items-center gap-5 min-w-0">
                                    <div className="p-3 rounded-2xl bg-background/50 border border-border/40 shadow-inner group-hover:scale-110 transition-transform duration-500">
                                      <Clock className="h-5 w-5 text-primary" />
                                    </div>
                                    <div className="min-w-0">
                                      <p className="font-black text-lg tracking-tight truncate group-hover:text-primary transition-colors">
                                        {event.summary}
                                      </p>
                                      <div className="flex items-center gap-3 mt-1.5">
                                        <div className="text-[10px] font-bold text-muted-foreground/60 uppercase tracking-widest flex items-center gap-1.5">
                                          {new Date(event.event_datetime_local).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}
                                        </div>
                                        {event.workspace_name && (
                                          <Badge variant="outline" className="text-[9px] font-black uppercase tracking-tighter px-2 py-0 border-none" style={{ backgroundColor: `${event.workspace_color}15`, color: event.workspace_color }}>
                                            {event.workspace_name}
                                          </Badge>
                                        )}
                                      </div>
                                    </div>
                                  </div>
                                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-all duration-300 translate-x-2 group-hover:translate-x-0" onClick={(e) => e.stopPropagation()}>
                                    <Button variant="ghost" size="icon" className="h-9 w-9 rounded-xl hover:bg-destructive/10 hover:text-destructive" onClick={() => setDeletingEvent(event)}>
                                      <Trash2 className="h-4 w-4" />
                                    </Button>
                                  </div>
                                </div>
                              </Card>
                            ))}
                          </div>
                        ) : (
                          <div className="py-12 text-center border-2 border-dashed border-border/40 rounded-[2rem] bg-card/20">
                            <p className="text-xs font-bold text-muted-foreground/60 uppercase tracking-widest">No hay eventos para hoy</p>
                          </div>
                        )}
                      </div>
                    </>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      <EventDialog
        isOpen={isEventDialogOpen}
        onOpenChange={setIsEventDialogOpen}
        onSaveSuccess={handleSaveSuccess}
        initialDate={initialEventDate} // Pasar la fecha inicial
        workspaceId={workspaceId || undefined} // Pasar el workspaceId
      />        <TaskDialog
        isOpen={isTaskDialogOpen}
        onOpenChange={setIsTaskDialogOpen}
        onSaveSuccess={handleTaskSaveSuccess}
        task={selectedTask} // Pasar la tarea seleccionada para edición
        workspaceId={workspaceId || undefined} // Pasar el workspaceId
      />
      {selectedEvent && (
        <EventDetailsDialog
          isOpen={isDetailsDialogOpen}
          onOpenChange={setIsDetailsDialogOpen}
          onEditClick={(eventToEdit) => { // Manejar el clic en editar desde EventDetailsDialog
            setSelectedEvent(eventToEdit);
            setIsDetailsDialogOpen(false); // Cerrar el diálogo de detalles
            setIsEventEditDialogOpen(true); // Abrir el diálogo de edición
          }}
          onDeleteClick={(eventToDelete) => {
            setDeletingEvent(eventToDelete);
            setIsDetailsDialogOpen(false);
          }}
          event={selectedEvent}
        />
      )}
      {selectedEvent && (
        <EventEditDialog
          isOpen={isEventEditDialogOpen}
          onOpenChange={setIsEventEditDialogOpen}
          onSaveSuccess={handleSaveSuccess}
          onCloseDetails={() => setIsDetailsDialogOpen(false)} // Pasar función para cerrar detalles
          event={selectedEvent}
        />
      )}

      <AlertDialog open={!!deletingEvent} onOpenChange={(open) => !open && setDeletingEvent(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>¿Cancelar este evento?</AlertDialogTitle>
            <AlertDialogDescription>
              Esta acción es irreversible y cancelará el recordatorio para "{deletingEvent?.description}".
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
              Esta acción es irreversible y eliminará la tarea "{deletingTask?.description}" permanentemente.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction onClick={handleTaskDeleteConfirm} className="bg-destructive hover:bg-destructive/90">Sí, eliminar tarea</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <Sheet open={isInfoSheetOpen} onOpenChange={setIsInfoSheetOpen}>
        <SheetContent side="right" className="w-full sm:max-w-md overflow-y-auto">
          <SheetHeader>
            <SheetTitle className="text-xl font-bold text-primary">Módulo de Agenda</SheetTitle>
            <SheetDescription className="text-sm text-muted-foreground">
              Gestiona tus eventos, reuniones y tareas de forma centralizada y eficiente.
            </SheetDescription>
          </SheetHeader>
          <div className="py-4 text-sm text-gray-700 dark:text-gray-300 space-y-4">
            <p><strong>¿Qué puedes hacer en tu Agenda?</strong></p>
            <ul className="list-disc pl-5 space-y-2">
              <li><strong>Agendar Eventos:</strong> Crea eventos con detalles como resumen, descripción, ubicación y participantes.</li>
              <li><strong>Añadir Tareas:</strong> Registra tus tareas pendientes, márcalas como completadas y establece fechas de vencimiento.</li>
              <li><strong>Vistas Personalizadas:</strong> Visualiza tu agenda por día, semana o mes para una mejor organización.</li>
              <li><strong>Integración con Contactos:</strong> Vincula eventos y tareas a perfiles de contacto para tener toda la información contextualizada.</li>
              <li><strong>Compartir con Equipos:</strong> Comparte eventos con tu equipo para una colaboración fluida.</li>
              <li><strong>Edición y Eliminación:</strong> Modifica o cancela eventos y tareas de forma sencilla.</li>
            </ul>

            <p><strong>Interacción con IA:</strong></p>
            <p>Además de la gestión manual, puedes interactuar con tu agenda a través del chat de IA. La IA dispone de herramientas especializadas para:</p>
            <ul className="list-disc pl-5 space-y-2">
              <li>Crear, modificar y cancelar eventos.</li>
              <li>Añadir, completar y eliminar tareas.</li>
              <li>Consultar tu disponibilidad y próximos compromisos.</li>
              <li>Generar resúmenes de tus actividades y recordatorios.</li>
            </ul>

            <p><strong>Beneficios Clave:</strong></p>
            <ul className="list-disc pl-5 space-y-2">
              <li><strong>Organización Centralizada:</strong> Ten un control total sobre tus compromisos y responsabilidades.</li>
              <li><strong>Productividad Mejorada:</strong> Prioriza tus tareas y eventos importantes para optimizar tu tiempo.</li>
              <li><strong>Colaboración Efectiva:</strong> Facilita la coordinación con tu equipo en proyectos y reuniones.</li>
              <li><strong>Recordatorios Inteligentes:</strong> Mantente al tanto de tus próximos eventos y plazos.</li>
            </ul>

            <p>¡Organiza tu día a día y optimiza tu productividad con el Módulo de Agenda!</p>
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
}