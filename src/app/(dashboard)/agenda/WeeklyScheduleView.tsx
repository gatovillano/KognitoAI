// src/app/(dashboard)/agenda/WeeklyScheduleView.tsx

import React from 'react';
import { format, addWeeks, subWeeks, startOfWeek, endOfWeek, eachDayOfInterval } from 'date-fns';
import { es } from 'date-fns/locale';
import { ChevronLeft, ChevronRight, Clock, Trash2, MoreHorizontal, CheckCircle2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { AgendaEvent, TaskResponse } from './page'; // Importar los tipos
import { Checkbox } from '@/components/ui/checkbox'; // Importar Checkbox

interface WeeklyScheduleViewProps {
  currentDate: Date;
  events: AgendaEvent[];
  tasks: TaskResponse[];
  onDateChange: (date: Date) => void;
  onEditEvent: (event: AgendaEvent) => void;
  onDeleteEvent: (event: AgendaEvent) => void;
  onEditTask: (task: TaskResponse) => void;
  onDeleteTask: (task: TaskResponse) => void;
  onToggleTaskCompleted: (task: TaskResponse) => void;
}

export function WeeklyScheduleView({
  currentDate,
  events,
  tasks,
  onDateChange,
  onEditEvent,
  onDeleteEvent,
  onEditTask,
  onDeleteTask,
  onToggleTaskCompleted,
}: WeeklyScheduleViewProps) {
  const startOfCurrentWeek = startOfWeek(currentDate, { weekStartsOn: 1 }); // Lunes como inicio de semana
  const endOfCurrentWeek = endOfWeek(currentDate, { weekStartsOn: 1 });

  const daysOfWeek = eachDayOfInterval({ start: startOfCurrentWeek, end: endOfCurrentWeek });

  const handlePreviousWeek = () => {
    onDateChange(subWeeks(currentDate, 1));
  };

  const handleNextWeek = () => {
    onDateChange(addWeeks(currentDate, 1));
  };

  // Función para filtrar eventos/tareas por día
  const filterItemsByDay = (items: (AgendaEvent | TaskResponse)[], day: Date) => {
    return items.filter(item => {
      const itemDate = 'event_datetime_local' in item ? new Date(item.event_datetime_local) : new Date(item.due_date!);
      return (
        itemDate.getDate() === day.getDate() &&
        itemDate.getMonth() === day.getMonth() &&
        itemDate.getFullYear() === day.getFullYear()
      );
    }).sort((a, b) => {
      const dateA = 'event_datetime_local' in a ? new Date(a.event_datetime_local) : new Date(a.due_date!);
      const dateB = 'event_datetime_local' in b ? new Date(b.event_datetime_local) : new Date(b.due_date!);
      return dateA.getTime() - dateB.getTime();
    });
  };

  return (
    <div className="flex flex-col h-full">
      {/* Navegación de la semana */}
      <div className="flex items-center justify-between mb-4 shrink-0">
        <Button variant="ghost" size="icon" onClick={handlePreviousWeek}>
          <ChevronLeft className="h-5 w-5" />
        </Button>
        <h2 className="text-xl font-semibold">
          {format(startOfCurrentWeek, 'PPP', { locale: es })} - {format(endOfCurrentWeek, 'PPP', { locale: es })}
        </h2>
        <Button variant="ghost" size="icon" onClick={handleNextWeek}>
          <ChevronRight className="h-5 w-5" />
        </Button>
      </div>

      {/* Cuadrícula de la semana */}
      <div className="flex-grow grid grid-cols-7 gap-2 overflow-auto">
        {daysOfWeek.map(day => (
          <div key={day.toISOString()} className="flex flex-col border rounded-lg p-2">
            <div className="text-center font-medium mb-2">
              {format(day, 'EEE d', { locale: es })}
            </div>
            <div className="flex-grow space-y-2 overflow-y-auto">
              {/* Eventos del día */}
              {filterItemsByDay(events, day).map(event => (
                <div
                  key={event.id}
                  className="p-2 bg-blue-100 text-blue-800 rounded-md text-sm cursor-pointer hover:bg-blue-200 relative"
                  onClick={() => onEditEvent(event as AgendaEvent)}
                >
                  {'event_datetime_local' in event ? <p className="font-semibold">{event.summary}</p> : <p className="font-semibold">{event.description}</p>}
                  {'event_datetime_local' in event && (
                    <div className="flex items-center text-xs mt-1">
                      <Clock className="h-3 w-3 mr-1" />
                      {new Date(event.event_datetime_local).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}
                    </div>
                  )}
                  <Button variant="ghost" size="icon" className="h-6 w-6 absolute bottom-0 right-0" onClick={(e) => { e.stopPropagation(); onDeleteEvent(event as AgendaEvent); }}>
                    <Trash2 className="h-3 w-3 text-destructive" />
                  </Button>
                </div>
              ))}

              {/* Tareas del día */}
              {tasks.filter(task => {
                  // If task has no due_date, always include it for this day
                  if (!task.due_date) return true; // <--- CHANGE HERE

                  const taskDueDate = new Date(task.due_date);
                  return taskDueDate.toDateString() === day.toDateString();
                }).map(task => (
                <div
                  key={task.id}
                  className={`p-2 rounded-md text-sm ${(task as TaskResponse).is_completed ? 'bg-green-100 text-green-800 line-through' : 'bg-yellow-100 text-yellow-800'} cursor-pointer hover:opacity-80`}
                >
                  <div className="flex items-center gap-2">
                    <Checkbox
                      checked={(task as TaskResponse).is_completed}
                      onCheckedChange={() => onToggleTaskCompleted(task as TaskResponse)}
                      className="h-4 w-4"
                    />
                    <p className="font-semibold flex-grow" onClick={() => onEditTask(task as TaskResponse)}>{(task as TaskResponse).description}</p>
                    <Button variant="ghost" size="icon" className="h-6 w-6" onClick={(e) => { e.stopPropagation(); onDeleteTask(task as TaskResponse); }}>
                      <Trash2 className="h-3 w-3 text-destructive" />
                    </Button>
                  </div>
                  {(task as TaskResponse).due_date && (
                    <div className="flex items-center text-xs mt-1">
                      <Clock className="h-3 w-3 mr-1" />
                      {format(new Date((task as TaskResponse).due_date!), 'HH:mm', { locale: es })}
                    </div>
                  )}
                </div>
              ))}

              {filterItemsByDay(events, day).length === 0 && filterItemsByDay(tasks, day).length === 0 && (
                <p className="text-xs text-muted-foreground text-center py-4">Sin elementos</p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
