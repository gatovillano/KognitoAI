// src/app/(dashboard)/agenda/WeeklyScheduleView.tsx

import React, { useState } from 'react';
import { format, addWeeks, subWeeks, startOfWeek, endOfWeek, eachDayOfInterval } from 'date-fns';
import { es } from 'date-fns/locale';
import { ChevronLeft, ChevronRight, Clock, Trash2, MoreHorizontal, CheckCircle2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { AgendaEvent, TaskResponse } from './types';
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
  const hours = Array.from({ length: 24 }, (_, i) => i);
  const [showEarlyHours, setShowEarlyHours] = useState(false);
  const visibleHours = showEarlyHours ? hours : hours.filter(h => h >= 6);
  console.log('Rendering WeeklyScheduleView, showEarlyHours:', showEarlyHours, 'visibleHours length:', visibleHours.length);

  const handlePreviousWeek = () => {
    onDateChange(subWeeks(currentDate, 1));
  };

  const handleNextWeek = () => {
    onDateChange(addWeeks(currentDate, 1));
  };

  // Función para filtrar eventos/tareas por día
  const filterItemsByDay = (items: (AgendaEvent | TaskResponse)[], day: Date) => {
    return items.filter(item => {
      let itemDate: Date;
      if ('event_datetime_local' in item) {
        itemDate = new Date(item.event_datetime_local);
      } else if ('end_date' in item && item.end_date) {
        itemDate = new Date(item.end_date);
      } else if ('start_date' in item && item.start_date) {
        itemDate = new Date(item.start_date);
      } else {
        return false; // Si no hay fecha, no se usa para ordenamiento por día específico aquí
      }

      return (
        itemDate.getDate() === day.getDate() &&
        itemDate.getMonth() === day.getMonth() &&
        itemDate.getFullYear() === day.getFullYear()
      );
    }).sort((a, b) => {
      const dateA = 'event_datetime_local' in a ? new Date(a.event_datetime_local) : ('end_date' in a && a.end_date ? new Date(a.end_date) : new Date(0));
      const dateB = 'event_datetime_local' in b ? new Date(b.event_datetime_local) : ('end_date' in b && b.end_date ? new Date(b.end_date) : new Date(0));
      return dateA.getTime() - dateB.getTime();
    });
  };

  // Función para filtrar eventos/tareas por día y hora
  const filterItemsByHour = (items: (AgendaEvent | TaskResponse)[], day: Date, hour: number) => {
    const filtered = items.filter(item => {
      let itemDate: Date;
      let itemHour: number;
      if ('event_datetime_local' in item) {
        itemDate = new Date(item.event_datetime_local);
        itemHour = itemDate.getHours();
      } else if ('end_date' in item && item.end_date) {
        itemDate = new Date(item.end_date);
        itemHour = itemDate.getHours();
      } else if ('start_date' in item && item.start_date) {
        itemDate = new Date(item.start_date);
        itemHour = itemDate.getHours();
      } else {
        return false;
      }

      return (
        itemDate.getDate() === day.getDate() &&
        itemDate.getMonth() === day.getMonth() &&
        itemDate.getFullYear() === day.getFullYear() &&
        itemHour === hour
      );
    }).sort((a, b) => {
      const timeA = 'event_datetime_local' in a ? new Date(a.event_datetime_local).getTime() : ('end_date' in a && a.end_date ? new Date(a.end_date).getTime() : 0);
      const timeB = 'event_datetime_local' in b ? new Date(b.event_datetime_local).getTime() : ('end_date' in b && b.end_date ? new Date(b.end_date).getTime() : 0);
      return timeA - timeB;
    });
    console.log(`Filtrando para ${format(day, 'yyyy-MM-dd')} hora ${hour}: ${filtered.length} elementos`);
    return filtered;
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
      <div className="mb-2">
        <Button onClick={() => { console.log('Toggling showEarlyHours from', showEarlyHours, 'to', !showEarlyHours); setShowEarlyHours(!showEarlyHours); }} variant="outline" size="sm">
          {showEarlyHours ? 'Ocultar horas de madrugada' : 'Mostrar horas de madrugada'}
        </Button>
      </div>
      <div className="flex-grow overflow-auto">
        <table className="w-full border-collapse">
          <thead>
            <tr>
              <th className="border p-2"></th>
              {daysOfWeek.map(day => (
                <th key={day.toISOString()} className="border p-2 text-center font-medium">
                  {format(day, 'EEE d', { locale: es })}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {visibleHours.map(hour => (
              <tr key={hour}>
                <td className="border p-2 text-center font-medium">{hour}:00</td>
                {daysOfWeek.map(day => {
                  const dayEvents = filterItemsByHour(events, day, hour);
                  const dayTasks = filterItemsByHour(tasks, day, hour);
                  const allItems = [...dayEvents, ...dayTasks].sort((a, b) => {
                    const timeA = 'event_datetime_local' in a ? new Date(a.event_datetime_local).getTime() : ('end_date' in a && a.end_date ? new Date(a.end_date).getTime() : 0);
                    const timeB = 'event_datetime_local' in b ? new Date(b.event_datetime_local).getTime() : ('end_date' in b && b.end_date ? new Date(b.end_date).getTime() : 0);
                    return timeA - timeB;
                  });
                  return (
                    <td key={day.toISOString()} className="border p-2">
                      <div className="space-y-2">
                        {allItems.map(item => {
                          if ('event_datetime_local' in item) {
                            return (
                              <div
                                key={item.id}
                                className="p-2 bg-blue-100 text-blue-800 rounded-md text-sm cursor-pointer hover:bg-blue-200 relative"
                                onClick={() => onEditEvent(item)}
                              >
                                <p className="font-semibold">{item.summary}</p>
                                <Button variant="ghost" size="icon" className="h-6 w-6 absolute bottom-0 right-0" onClick={(e) => { e.stopPropagation(); onDeleteEvent(item); }}>
                                  <Trash2 className="h-3 w-3 text-destructive" />
                                </Button>
                              </div>
                            );
                          } else {
                            return (
                              <div
                                key={item.id}
                                className={`p-2 rounded-md text-sm ${(item as TaskResponse).is_completed ? 'bg-green-100 text-green-800 line-through' : 'bg-yellow-100 text-yellow-800'} cursor-pointer hover:opacity-80`}
                              >
                                <div className="flex items-center gap-2">
                                  <Checkbox
                                    checked={(item as TaskResponse).is_completed}
                                    onCheckedChange={() => onToggleTaskCompleted(item as TaskResponse)}
                                    className="h-4 w-4"
                                  />
                                  <p className="font-semibold flex-grow" onClick={() => onEditTask(item as TaskResponse)}>{(item as TaskResponse).description}</p>
                                  <Button variant="ghost" size="icon" className="h-6 w-6" onClick={(e) => { e.stopPropagation(); onDeleteTask(item as TaskResponse); }}>
                                    <Trash2 className="h-3 w-3 text-destructive" />
                                  </Button>
                                </div>
                              </div>
                            );
                          }
                        })}
                        {allItems.length === 0 && <p className="text-xs text-muted-foreground text-center py-4">Sin elementos</p>}
                      </div>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
