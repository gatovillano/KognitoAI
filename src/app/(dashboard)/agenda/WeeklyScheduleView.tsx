// src/app/(dashboard)/agenda/WeeklyScheduleView.tsx

import React from 'react';
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

  const handlePreviousWeek = () => {
    onDateChange(subWeeks(currentDate, 1));
  };

  const handleNextWeek = () => {
    onDateChange(addWeeks(currentDate, 1));
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
    return filtered;
  };

  // Calcular horas activas (que tienen al menos un evento o tarea en la semana)
  const activeHours = hours.filter(hour => {
    return daysOfWeek.some(day => {
      const dayEvents = filterItemsByHour(events, day, hour);
      const dayTasks = filterItemsByHour(tasks, day, hour);
      return dayEvents.length > 0 || dayTasks.length > 0;
    });
  });

  return (
    <div className="flex flex-col h-full space-y-6">
      {/* Navegación de la semana */}
      <div className="flex items-center justify-between shrink-0 bg-card/40 backdrop-blur-md p-2 rounded-2xl border border-border/40">
        <Button variant="ghost" size="icon" onClick={handlePreviousWeek} className="h-10 w-10 rounded-xl hover:bg-primary/10 hover:text-primary transition-all">
          <ChevronLeft className="h-6 w-6" />
        </Button>
        <h2 className="text-sm md:text-lg font-black tracking-tighter uppercase">
          {format(startOfCurrentWeek, 'd MMM', { locale: es })} - {format(endOfCurrentWeek, 'd MMM yyyy', { locale: es })}
        </h2>
        <Button variant="ghost" size="icon" onClick={handleNextWeek} className="h-10 w-10 rounded-xl hover:bg-primary/10 hover:text-primary transition-all">
          <ChevronRight className="h-6 w-6" />
        </Button>
      </div>

      {/* Cuadrícula de la semana */}
      <div className="flex-grow overflow-auto custom-scrollbar pr-2">
        {activeHours.length > 0 ? (
          <div className="min-w-[800px]">
            <div className="grid grid-cols-[80px_repeat(7,1fr)] gap-4 mb-4 px-2">
              <div />
              {daysOfWeek.map(day => (
                <div key={day.toISOString()} className="text-center space-y-1">
                  <p className="text-[10px] font-black uppercase tracking-[0.2em] text-muted-foreground/60">
                    {format(day, 'EEE', { locale: es })}
                  </p>
                  <p className="text-lg font-black tracking-tighter">
                    {format(day, 'd')}
                  </p>
                </div>
              ))}
            </div>

            <div className="space-y-4">
              {activeHours.map(hour => (
                <div key={hour} className="grid grid-cols-[80px_repeat(7,1fr)] gap-4 items-start">
                  <div className="text-center py-4">
                    <span className="text-xs font-black text-muted-foreground/40">{hour}:00</span>
                  </div>
                  {daysOfWeek.map(day => {
                    const dayEvents = filterItemsByHour(events, day, hour);
                    const dayTasks = filterItemsByHour(tasks, day, hour);
                    const allItems = [...dayEvents, ...dayTasks].sort((a, b) => {
                      const timeA = 'event_datetime_local' in a ? new Date(a.event_datetime_local).getTime() : ('end_date' in a && a.end_date ? new Date(a.end_date).getTime() : 0);
                      const timeB = 'event_datetime_local' in b ? new Date(b.event_datetime_local).getTime() : ('end_date' in b && b.end_date ? new Date(b.end_date).getTime() : 0);
                      return timeA - timeB;
                    });

                    return (
                      <div key={day.toISOString()} className="min-h-[100px] p-2 rounded-2xl bg-card/20 border border-border/40 hover:bg-card/40 transition-all duration-300 space-y-2">
                        {allItems.map(item => {
                          if ('event_datetime_local' in item) {
                            return (
                              <div
                                key={item.id}
                                className="p-2 rounded-xl cursor-pointer hover:scale-[1.02] transition-all duration-200 shadow-sm border border-white/10 group relative overflow-hidden"
                                style={{
                                  backgroundColor: item.workspace_color ? `${item.workspace_color}25` : 'rgba(59, 130, 246, 0.1)',
                                  color: item.workspace_color || '#3b82f6'
                                }}
                                onClick={() => onEditEvent(item)}
                              >
                                <p className="font-black text-[10px] uppercase tracking-tighter truncate pr-4">{item.summary}</p>
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  className="h-6 w-6 absolute -top-1 -right-1 opacity-0 group-hover:opacity-100 transition-all hover:bg-destructive/10 hover:text-destructive"
                                  onClick={(e) => { e.stopPropagation(); onDeleteEvent(item); }}
                                >
                                  <Trash2 className="h-3 w-3" />
                                </Button>
                              </div>
                            );
                          } else {
                            const isCompleted = (item as TaskResponse).is_completed;
                            return (
                              <div
                                key={item.id}
                                className={`p-2 rounded-xl cursor-pointer hover:scale-[1.02] transition-all duration-200 shadow-sm border border-white/5 group relative ${isCompleted ? 'bg-green-500/10 text-green-600 line-through' : 'bg-yellow-500/10 text-yellow-700'
                                  }`}
                              >
                                <div className="flex items-center gap-2 pr-4">
                                  <Checkbox
                                    checked={isCompleted}
                                    onCheckedChange={() => onToggleTaskCompleted(item as TaskResponse)}
                                    className="h-3 w-3 rounded-sm border-current/30"
                                  />
                                  <p className="font-bold text-[10px] uppercase tracking-tighter truncate flex-grow" onClick={() => onEditTask(item as TaskResponse)}>
                                    {(item as TaskResponse).description}
                                  </p>
                                </div>
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  className="h-6 w-6 absolute -top-1 -right-1 opacity-0 group-hover:opacity-100 transition-all hover:bg-destructive/10 hover:text-destructive"
                                  onClick={(e) => { e.stopPropagation(); onDeleteTask(item as TaskResponse); }}
                                >
                                  <Trash2 className="h-3 w-3" />
                                </Button>
                              </div>
                            );
                          }
                        })}
                      </div>
                    );
                  })}
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-full py-20 text-muted-foreground bg-card/20 rounded-[2rem] border-2 border-dashed border-border/40">
            <Clock className="h-16 w-16 mb-4 opacity-10 animate-pulse" />
            <p className="font-bold uppercase tracking-widest text-xs">No hay actividad para esta semana</p>
          </div>
        )}
      </div>
    </div>
  );
}
