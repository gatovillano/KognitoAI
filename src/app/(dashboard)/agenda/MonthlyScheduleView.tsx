// src/app/(dashboard)/agenda/MonthlyScheduleView.tsx

import React from 'react';
import { format, addMonths, subMonths, startOfMonth, endOfMonth, eachDayOfInterval, startOfWeek, endOfWeek, isSameMonth, isToday } from 'date-fns';
import { es } from 'date-fns/locale';
import { ChevronLeft, ChevronRight, Clock, CheckCircle2 } from 'lucide-react';
import { Checkbox } from '../../../components/ui/checkbox';
import { Button } from '@/components/ui/button';
import { AgendaEvent, TaskResponse } from './page'; // Importar los tipos

interface MonthlyScheduleViewProps {
  currentDate: Date;
  events: AgendaEvent[];
  tasks: TaskResponse[];
  onDateChange: (date: Date) => void;
  onEditEvent: (event: AgendaEvent) => void;
  onEditTask: (task: TaskResponse) => void;
  onToggleTaskCompleted: (task: TaskResponse) => void;
}

export function MonthlyScheduleView({
  currentDate,
  events,
  tasks,
  onDateChange,
  onEditEvent,
  onEditTask,
  onToggleTaskCompleted,
}: MonthlyScheduleViewProps) {
  const startOfCurrentMonth = startOfMonth(currentDate);
  const endOfCurrentMonth = endOfMonth(currentDate);

  // Generar todos los días del mes, incluyendo los días de la semana anterior y siguiente para completar la cuadrícula
  const startDay = startOfWeek(startOfCurrentMonth, { weekStartsOn: 1 }); // Lunes como inicio de semana
  const endDay = endOfWeek(endOfCurrentMonth, { weekStartsOn: 1 });

  const daysInMonthView = eachDayOfInterval({ start: startDay, end: endDay });

  const handlePreviousMonth = () => {
    onDateChange(subMonths(currentDate, 1));
  };

  const handleNextMonth = () => {
    onDateChange(addMonths(currentDate, 1));
  };

  // Función para filtrar eventos/tareas por día
  const filterItemsByDay = <T extends AgendaEvent | TaskResponse>(items: T[], day: Date): T[] => {
    return items.filter(item => {
      const itemDate = 'event_datetime_local' in item ? new Date(item.event_datetime_local) : new Date(item.due_date!);
      return (
        itemDate.getDate() === day.getDate() &&
        itemDate.getMonth() === day.getMonth() &&
        itemDate.getFullYear() === day.getFullYear()
      );
    }).sort((a: T, b: T) => {
      const dateA = 'event_datetime_local' in a ? new Date(a.event_datetime_local) : new Date(a.due_date!);
      const dateB = 'event_datetime_local' in b ? new Date(b.event_datetime_local) : new Date(b.due_date!);
      return dateA.getTime() - dateB.getTime();
    });
  };

  return (
    <div className="flex flex-col h-full">
      {/* Navegación del mes */}
      <div className="flex items-center justify-between mb-4 shrink-0">
        <Button variant="ghost" size="icon" onClick={handlePreviousMonth}>
          <ChevronLeft className="h-5 w-5" />
        </Button>
        <h2 className="text-xl font-semibold">
          {format(currentDate, 'MMMM yyyy', { locale: es })}
        </h2>
        <Button variant="ghost" size="icon" onClick={handleNextMonth}>
          <ChevronRight className="h-5 w-5" />
        </Button>
      </div>

      {/* Nombres de los días de la semana */}
      <div className="grid grid-cols-7 gap-2 mb-2">
        {['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'].map(dayName => (
          <div key={dayName} className="text-center font-medium text-sm">
            {dayName}
          </div>
        ))}
      </div>

      {/* Cuadrícula del mes */}
      <div className="flex-grow grid grid-cols-7 gap-2 overflow-auto border rounded-lg p-2">
        {daysInMonthView.map(day => {
          const dayEvents = filterItemsByDay(events, day);
          const dayTasks = filterItemsByDay(tasks, day);
          const isCurrentMonth = isSameMonth(day, currentDate);
          const isTodayDay = isToday(day);

          return (
            <div
              key={day.toISOString()}
              className={`flex flex-col border rounded-lg p-2 min-h-[100px] ${!isCurrentMonth ? 'text-gray-400' : ''} ${isTodayDay ? 'border-blue-500 ring-2 ring-blue-500' : ''}`}>
              <div className={`text-right font-medium mb-2 ${isTodayDay ? 'text-blue-600' : ''}`}>
                {format(day, 'd')}
              </div>
              <div className="flex-grow space-y-1 overflow-y-auto text-xs">
                {dayEvents.map(event => (
                  <div
                    key={event.id}
                    className="p-1 rounded-md cursor-pointer hover:opacity-80 text-blue-900"
                    style={{ backgroundColor: event.workspace_color || '#DBEAFE' }} // bg-blue-100
                    onClick={() => onEditEvent(event as AgendaEvent)}
                  >
                    <p className="font-semibold truncate">{event.summary}</p>
                    {'event_datetime_local' in event && (
                      <div className="flex items-center mt-1">
                        <Clock className="h-3 w-3 mr-1" />
                        {new Date(event.event_datetime_local).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}
                      </div>
                    )}
                  </div>
                ))}
                {dayTasks.map(task => {
                  const isPastDue = !task.is_completed && new Date(task.due_date!) < new Date();
                  return (
                    <div
                      key={task.id}
                      className={`p-1 rounded-md ${task.is_completed ? 'bg-green-100 text-green-800 line-through' : 'bg-yellow-100 text-yellow-800'} ${isPastDue ? 'bg-red-200 text-red-800' : ''} cursor-pointer hover:opacity-80`}
                    >
                      <div className="flex items-center gap-1">
                        <Checkbox
                          checked={task.is_completed}
                          onCheckedChange={() => onToggleTaskCompleted(task as TaskResponse)}
                          className="h-3 w-3"
                        />
                        <p className="font-semibold flex-grow truncate" onClick={() => onEditTask(task as TaskResponse)}>{(task as TaskResponse).description}</p>
                      </div>
                      {(task as TaskResponse).due_date && (
                        <div className="flex items-center mt-1">
                          <Clock className="h-3 w-3 mr-1" />
                          {format(new Date((task as TaskResponse).due_date!), 'HH:mm', { locale: es })}
                        </div>
                      )}
                    </div>
                  );
                })}
                {dayEvents.length === 0 && dayTasks.length === 0 && (
                  <p className="text-center text-muted-foreground py-4">Sin elementos</p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}