import React, { useState, useEffect, useRef } from 'react';
import { format, addMonths, subMonths, startOfMonth, endOfMonth, eachDayOfInterval, startOfWeek, endOfWeek, isSameMonth, isToday } from 'date-fns';
import { es } from 'date-fns/locale';
import { ChevronLeft, ChevronRight, Clock, CheckCircle2 } from 'lucide-react';
import { Checkbox } from '../../../components/ui/checkbox';
import { Button } from '@/components/ui/button';
import { AgendaEvent, TaskResponse } from './types';
import { useDrag, useDrop } from 'react-dnd';

interface MonthlyScheduleViewProps {
  currentDate: Date;
  events: AgendaEvent[];
  tasks: TaskResponse[];
  onDateChange: (date: Date) => void;
  onEditEvent: (event: AgendaEvent) => void;
  onEditTask: (task: TaskResponse) => void;
  onToggleTaskCompleted: (task: TaskResponse) => void;
  onCreateEvent: (date: Date) => void; // Nueva prop para crear eventos
  onMoveEvent: (eventId: string, newDate: Date) => void; // Nueva prop para mover eventos
  onMoveTask: (taskId: string, newDate: Date) => void; // Nueva prop para mover tareas
}

// Tipos para los elementos arrastrables
interface DraggedEvent {
  id: string;
  type: 'event';
}

interface DraggedTask {
  id: string;
  type: 'task';
}

interface EventCardProps {
  event: AgendaEvent;
  onEditEvent: (event: AgendaEvent) => void;
}

const EventCard: React.FC<EventCardProps> = ({ event, onEditEvent }) => {
  const ref = useRef<HTMLDivElement>(null);
  const [{ isDragging }, drag] = useDrag(() => ({
    type: 'event',
    item: { id: event.id, type: 'event' },
    collect: (monitor) => ({
      isDragging: monitor.isDragging()
    })
  }), [event.id]);
  drag(ref);

  return (
    <div
      key={event.id}
      ref={ref}
      className="p-1.5 rounded-lg cursor-pointer hover:scale-[1.02] transition-all duration-200 shadow-sm border border-white/10 group"
      style={{
        backgroundColor: event.workspace_color ? `${event.workspace_color}25` : 'rgba(59, 130, 246, 0.1)',
        color: event.workspace_color || '#3b82f6',
        opacity: isDragging ? 0.5 : 1
      }}
      onClick={(e) => { e.stopPropagation(); onEditEvent(event as AgendaEvent); }}
    >
      <div className="flex items-center gap-1.5">
        <div className="h-1.5 w-1.5 rounded-full bg-current animate-pulse" />
        <p className="font-black text-[10px] uppercase tracking-tighter truncate">{event.summary}</p>
      </div>
    </div>
  );
};

interface TaskCardProps {
  task: TaskResponse;
  onEditTask: (task: TaskResponse) => void;
  onToggleTaskCompleted: (task: TaskResponse) => void;
}

const TaskCard: React.FC<TaskCardProps> = ({ task, onEditTask, onToggleTaskCompleted }) => {
  const ref = useRef<HTMLDivElement>(null);
  const [{ isDragging }, drag] = useDrag(() => ({
    type: 'task',
    item: { id: task.id, type: 'task' },
    collect: (monitor) => ({
      isDragging: monitor.isDragging()
    })
  }), [task.id]);
  drag(ref);

  const isPastDue = !task.is_completed && task.end_date && new Date(task.end_date) < new Date();

  return (
    <div
      key={task.id}
      ref={ref}
      className={`p-1.5 rounded-lg cursor-pointer hover:scale-[1.02] transition-all duration-200 shadow-sm border border-white/5 ${task.is_completed
        ? 'bg-green-500/10 text-green-600 dark:text-green-400 line-through'
        : isPastDue
          ? 'bg-red-500/10 text-red-600 dark:text-red-400'
          : 'bg-yellow-500/10 text-yellow-700 dark:text-yellow-400'
        }`}
      style={{ opacity: isDragging ? 0.5 : 1 }}
      onClick={(e) => { e.stopPropagation(); onEditTask(task as TaskResponse); }}
    >
      <div className="flex items-center gap-1.5">
        <Checkbox
          checked={task.is_completed}
          onCheckedChange={() => onToggleTaskCompleted(task as TaskResponse)}
          className="h-3 w-3 rounded-sm border-current/30"
        />
        <p className="font-bold text-[10px] uppercase tracking-tighter truncate">{(task as TaskResponse).description}</p>
      </div>
    </div>
  );
};


interface DayCellProps {
  day: Date;
  dayEvents: AgendaEvent[];
  dayTasks: TaskResponse[];
  isCurrentMonth: boolean;
  isTodayDay: boolean;
  onCreateEvent: (date: Date) => void;
  onEditEvent: (event: AgendaEvent) => void;
  onEditTask: (task: TaskResponse) => void;
  onToggleTaskCompleted: (task: TaskResponse) => void;
  onMoveEvent: (eventId: string, newDate: Date) => void;
  onMoveTask: (taskId: string, newDate: Date) => void;
}

const DayCell: React.FC<DayCellProps> = ({
  day,
  dayEvents,
  dayTasks,
  isCurrentMonth,
  isTodayDay,
  onCreateEvent,
  onEditEvent,
  onEditTask,
  onToggleTaskCompleted,
  onMoveEvent,
  onMoveTask,
}) => {
  const dropRef = useRef<HTMLDivElement>(null);
  const [{ isOver }, drop] = useDrop<DraggedEvent | DraggedTask, unknown, { isOver: boolean }>(
    () => ({
      accept: ['event', 'task'],
      drop: (item, monitor) => {
        if (monitor.didDrop()) {
          return;
        }
        if (item.type === 'event') {
          onMoveEvent(item.id, day);
        } else if (item.type === 'task') {
          onMoveTask(item.id, day);
        }
      },
      collect: (monitor) => ({
        isOver: monitor.isOver(),
      }),
    })
    , [day, onMoveEvent, onMoveTask]);
  drop(dropRef);

  return (
    <div
      key={day.toISOString()}
      ref={dropRef}
      className={`group flex flex-col border border-border/40 rounded-2xl p-2 min-h-[120px] transition-all duration-300 ${!isCurrentMonth ? 'opacity-30 grayscale' : 'bg-card/20 hover:bg-card/40'
        } ${isTodayDay ? 'ring-2 ring-primary bg-primary/5 border-primary/50' : ''} ${isOver ? 'bg-primary/20 scale-[0.98]' : ''}`}
      onClick={() => onCreateEvent(day)}
    >
      <div className={`text-right font-black text-xs mb-2 transition-colors ${isTodayDay ? 'text-primary' : 'text-muted-foreground/60 group-hover:text-foreground'}`}>
        {format(day, 'd')}
      </div>
      <div className="flex-grow space-y-1.5 overflow-y-auto custom-scrollbar pr-1">
        {dayEvents.map(event => (
          <EventCard key={event.id} event={event} onEditEvent={onEditEvent} />
        ))}
        {dayTasks.map(task => (
          <TaskCard
            key={task.id}
            task={task}
            onEditTask={onEditTask}
            onToggleTaskCompleted={onToggleTaskCompleted}
          />
        ))}
      </div>
    </div>
  );
};

export function MonthlyScheduleView({
  currentDate,
  events,
  tasks,
  onDateChange,
  onEditEvent,
  onEditTask,
  onToggleTaskCompleted,
  onCreateEvent,
  onMoveEvent,
  onMoveTask,
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
      // Lógica para Eventos (AgendaEvent) - PRIORIDAD ALTA
      if ('event_datetime_local' in item) {
        const itemDate = new Date(item.event_datetime_local);
        return (
          itemDate.getDate() === day.getDate() &&
          itemDate.getMonth() === day.getMonth() &&
          itemDate.getFullYear() === day.getFullYear()
        );
      }

      // Lógica específica para Tareas con rango
      if ('start_date' in item || 'end_date' in item) {
        const task = item as unknown as TaskResponse;

        // Si no tiene fechas, usar created_at como fecha de visualización
        if (!task.start_date && !task.end_date) {
          const createdAt = new Date(task.created_at);
          return (
            createdAt.getDate() === day.getDate() &&
            createdAt.getMonth() === day.getMonth() &&
            createdAt.getFullYear() === day.getFullYear()
          );
        }

        const currentDayStart = new Date(day);
        currentDayStart.setHours(0, 0, 0, 0);

        const currentDayEnd = new Date(day);
        currentDayEnd.setHours(23, 59, 59, 999);

        // Rango completo
        if (task.start_date && task.end_date) {
          const taskStart = new Date(task.start_date);
          taskStart.setHours(0, 0, 0, 0);
          const taskEnd = new Date(task.end_date);
          taskEnd.setHours(23, 59, 59, 999);
          return currentDayStart <= taskEnd && currentDayEnd >= taskStart;
        }

        // Solo end_date
        if (task.end_date) {
          const taskEnd = new Date(task.end_date);
          return taskEnd.getDate() === day.getDate() &&
            taskEnd.getMonth() === day.getMonth() &&
            taskEnd.getFullYear() === day.getFullYear();
        }

        // Solo start_date
        if (task.start_date) {
          const taskStart = new Date(task.start_date);
          return taskStart.getDate() === day.getDate() &&
            taskStart.getMonth() === day.getMonth() &&
            taskStart.getFullYear() === day.getFullYear();
        }

        return false;
      }

      return false;
    }).sort((a: T, b: T) => {
      const dateA = 'event_datetime_local' in a ? new Date(a.event_datetime_local) : ('end_date' in a && a.end_date ? new Date(a.end_date) : new Date(0));
      const dateB = 'event_datetime_local' in b ? new Date(b.event_datetime_local) : ('end_date' in b && b.end_date ? new Date(b.end_date) : new Date(0));
      return dateA.getTime() - dateB.getTime();
    });
  };

  return (
    <div className="flex flex-col h-full space-y-6">
      {/* Navegación del mes */}
      <div className="flex items-center justify-between shrink-0 bg-card/40 backdrop-blur-md p-2 rounded-2xl border border-border/40">
        <Button variant="ghost" size="icon" onClick={handlePreviousMonth} className="h-10 w-10 rounded-xl hover:bg-primary/10 hover:text-primary transition-all">
          <ChevronLeft className="h-6 w-6" />
        </Button>
        <h2 className="text-xl font-black tracking-tighter uppercase">
          {format(currentDate, 'MMMM yyyy', { locale: es })}
        </h2>
        <Button variant="ghost" size="icon" onClick={handleNextMonth} className="h-10 w-10 rounded-xl hover:bg-primary/10 hover:text-primary transition-all">
          <ChevronRight className="h-6 w-6" />
        </Button>
      </div>

      {/* Nombres de los días de la semana */}
      <div className="grid grid-cols-7 gap-4 px-2">
        {['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'].map(dayName => (
          <div key={dayName} className="text-center font-black text-[10px] uppercase tracking-[0.2em] text-muted-foreground/60">
            {dayName}
          </div>
        ))}
      </div>

      {/* Cuadrícula del mes */}
      <div className="flex-grow grid grid-cols-7 gap-3 overflow-auto custom-scrollbar pr-2">
        {daysInMonthView.map(day => {
          const dayEvents = filterItemsByDay(events, day);
          const dayTasks = filterItemsByDay(tasks, day);
          const isCurrentMonth = isSameMonth(day, currentDate);
          const isTodayDay = isToday(day);

          return (
            <DayCell
              key={day.toISOString()}
              day={day}
              dayEvents={dayEvents}
              dayTasks={dayTasks}
              isCurrentMonth={isCurrentMonth}
              isTodayDay={isTodayDay}
              onCreateEvent={onCreateEvent}
              onEditEvent={onEditEvent}
              onEditTask={onEditTask}
              onToggleTaskCompleted={onToggleTaskCompleted}
              onMoveEvent={onMoveEvent}
              onMoveTask={onMoveTask}
            />
          );
        })}
      </div>
    </div>
  );
}