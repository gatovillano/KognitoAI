// src/app/(dashboard)/agenda/WeeklyScheduleView.tsx

import React from 'react';
import { format, addWeeks, subWeeks, startOfWeek, endOfWeek, eachDayOfInterval } from 'date-fns';
import { es } from 'date-fns/locale';
import { ChevronLeft, ChevronRight, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { AgendaEvent, TaskResponse } from './types';
import { Checkbox } from '@/components/ui/checkbox';
import { useDrag, useDrop } from 'react-dnd';

interface DroppableDayColumnProps {
  day: Date;
  onMoveEvent?: (eventId: string, newDate: Date) => void;
  onMoveTask?: (taskId: string, newDate: Date) => void;
  hours: number[];
  HOUR_HEIGHT: number;
  children: React.ReactNode;
}
const DroppableDayColumn: React.FC<DroppableDayColumnProps> = ({ day, onMoveEvent, onMoveTask, hours, HOUR_HEIGHT, children }) => {
  const ref = React.useRef<HTMLDivElement>(null);
  const [{ isOver }, drop] = useDrop(() => ({
    accept: ['event', 'task'],
    drop: (item: any, monitor) => {
      const offset = monitor.getClientOffset();
      if (!offset || !ref.current) return;
      const rect = ref.current.getBoundingClientRect();
      const y = offset.y - rect.top;
      let newHour = Math.floor(y / HOUR_HEIGHT);
      let minutes = ((y % HOUR_HEIGHT) / HOUR_HEIGHT) * 60;
      let snappedMinutes = Math.round(minutes / 15) * 15;
      if (snappedMinutes === 60) {
        snappedMinutes = 0;
        newHour += 1;
      }
      const newDate = new Date(day);
      newDate.setHours(newHour, snappedMinutes, 0, 0);
      if (item.type === 'event' && onMoveEvent) {
        onMoveEvent(item.id, newDate);
      } else if (item.type === 'task' && onMoveTask) {
        onMoveTask(item.id, newDate);
      }
    },
    collect: (monitor) => ({ isOver: monitor.isOver() })
  }), [day, onMoveEvent, onMoveTask, HOUR_HEIGHT]);
  drop(ref);

  return (
    <div ref={ref} className={`relative border-r border-border/10 last:border-r-0 h-full group ${isOver ? 'bg-primary/5' : ''}`}>
      {hours.map(hour => (
        <div key={`line-${hour}`} className="border-b border-border/10 absolute w-full pointer-events-none" style={{ top: `${hour * HOUR_HEIGHT}px`, height: `${HOUR_HEIGHT}px` }} />
      ))}
      {children}
    </div>
  );
};

interface DraggableWeeklyEventProps {
  eventItem: AgendaEvent;
  top: number;
  height: number;
  start: Date;
  end: Date;
  onEditEvent: (event: AgendaEvent) => void;
  onDeleteEvent: (event: AgendaEvent) => void;
}
const DraggableWeeklyEvent: React.FC<DraggableWeeklyEventProps> = ({ eventItem, top, height, start, end, onEditEvent, onDeleteEvent }) => {
  const ref = React.useRef<HTMLDivElement>(null);
  const [{ isDragging }, drag] = useDrag(() => ({
    type: 'event',
    item: { id: eventItem.id, type: 'event' },
    collect: monitor => ({ isDragging: monitor.isDragging() })
  }), [eventItem.id]);
  drag(ref);

  return (
    <div
      ref={ref}
      className="absolute left-1 right-1 rounded-lg p-1.5 md:p-2 cursor-pointer shadow-sm border border-black/5 hover:scale-[1.01] hover:shadow-md hover:z-50 transition-all overflow-hidden flex flex-col group/item"
      style={{
        top: `${top}px`,
        height: `${height}px`,
        backgroundColor: eventItem.workspace_color ? `${eventItem.workspace_color}30` : 'rgba(59, 130, 246, 0.15)',
        borderColor: eventItem.workspace_color ? `${eventItem.workspace_color}50` : 'rgba(59, 130, 246, 0.3)',
        color: eventItem.workspace_color || '#3b82f6',
        opacity: isDragging ? 0.5 : 1
      }}
      onClick={(e) => { e.stopPropagation(); onEditEvent(eventItem); }}
    >
      <p className="font-extrabold text-[9px] md:text-xs tracking-tight truncate leading-tight drop-shadow-sm pr-4">
        {eventItem.summary}
      </p>
      {height > 40 && (
        <p className="text-[8px] md:text-[10px] font-semibold opacity-80 uppercase mt-0.5 truncate tracking-widest">
          {format(start, 'HH:mm')} - {format(end, 'HH:mm')}
        </p>
      )}
      <Button
        variant="ghost"
        size="icon"
        className="h-5 w-5 absolute top-1 right-1 opacity-0 group-hover/item:opacity-100 transition-opacity hover:bg-destructive/20 hover:text-destructive hidden md:flex"
        onClick={(e) => { e.stopPropagation(); onDeleteEvent(eventItem); }}
      >
        <Trash2 className="h-3 w-3" />
      </Button>
    </div>
  );
};

interface DraggableWeeklyTaskProps {
  taskItem: TaskResponse;
  top: number;
  height: number;
  onEditTask: (task: TaskResponse) => void;
  onDeleteTask: (task: TaskResponse) => void;
  onToggleTaskCompleted: (task: TaskResponse) => void;
}
const DraggableWeeklyTask: React.FC<DraggableWeeklyTaskProps> = ({ taskItem, top, height, onEditTask, onDeleteTask, onToggleTaskCompleted }) => {
  const ref = React.useRef<HTMLDivElement>(null);
  const [{ isDragging }, drag] = useDrag(() => ({
    type: 'task',
    item: { id: taskItem.id, type: 'task' },
    collect: (monitor) => ({ isDragging: monitor.isDragging() })
  }), [taskItem.id]);
  drag(ref);

  const isCompleted = taskItem.is_completed;
  
  return (
    <div
      ref={ref}
      className={`absolute left-1 right-1 rounded-lg p-1.5 md:p-2 shadow-sm border border-black/5 hover:scale-[1.01] hover:shadow-md hover:z-50 overflow-hidden flex flex-col justify-start items-start transition-all group/item ${isCompleted ? 'bg-green-500/10 text-green-700 border-green-500/30 line-through opacity-80' : 'bg-yellow-500/15 text-yellow-700 border-yellow-500/30'}`}
      style={{
        top: `${top}px`,
        height: `${height}px`,
        opacity: isDragging ? 0.5 : 1
      }}
      onClick={(e) => { e.stopPropagation(); onEditTask(taskItem); }}
    >
       <div className="flex items-start gap-1.5 md:gap-2 w-full pr-4">
         <div className="pt-0.5 pointer-events-auto shrink-0" onClick={(e) => e.stopPropagation()}>
           <Checkbox
             checked={isCompleted}
             onCheckedChange={() => onToggleTaskCompleted(taskItem)}
             className="h-3 w-3 rounded-[3px] border-current/40 shrink-0 bg-background/50 cursor-pointer hover:border-current mt-0.5 md:mt-0"
           />
         </div>
         <p className="font-extrabold text-[9px] md:text-xs tracking-tight leading-tight line-clamp-3 overflow-hidden cursor-pointer" title={taskItem.description}>
           {taskItem.description}
         </p>
       </div>
       <Button
         variant="ghost"
         size="icon"
         className="h-5 w-5 absolute top-1 right-1 opacity-0 group-hover/item:opacity-100 transition-opacity hover:bg-destructive/20 hover:text-destructive hidden md:flex"
         onClick={(e) => { e.stopPropagation(); onDeleteTask(taskItem); }}
       >
         <Trash2 className="h-3 w-3" />
       </Button>
    </div>
  );
};

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
  onMoveEvent?: (eventId: string, newDate: Date) => void;
  onMoveTask?: (taskId: string, newDate: Date) => void;
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
  onMoveEvent,
  onMoveTask,
}: WeeklyScheduleViewProps) {
  const startOfCurrentWeek = startOfWeek(currentDate, { weekStartsOn: 1 });
  const endOfCurrentWeek = endOfWeek(currentDate, { weekStartsOn: 1 });

  const daysOfWeek = eachDayOfInterval({ start: startOfCurrentWeek, end: endOfCurrentWeek });
  const hours = Array.from({ length: 24 }, (_, i) => i);

  const handlePreviousWeek = () => {
    onDateChange(subWeeks(currentDate, 1));
  };

  const handleNextWeek = () => {
    onDateChange(addWeeks(currentDate, 1));
  };

  const getItemTime = (item: AgendaEvent | TaskResponse) => {
    let start: Date;
    let end: Date;

    if ('event_datetime_local' in item) {
      start = new Date(item.event_datetime_local);
      end = item.end_date ? new Date(item.end_date) : new Date(start.getTime() + 60 * 60 * 1000);
    } else {
      start = item.start_date ? new Date(item.start_date) : item.end_date ? new Date(item.end_date) : new Date();
      end = item.end_date ? new Date(item.end_date) : new Date(start.getTime() + 60 * 60 * 1000);
    }

    return { start, end };
  };

  const isSameDay = (date1: Date, date2: Date) => {
    return (
      date1.getDate() === date2.getDate() &&
      date1.getMonth() === date2.getMonth() &&
      date1.getFullYear() === date2.getFullYear()
    );
  };

  const filterItemsForDay = (items: (AgendaEvent | TaskResponse)[], day: Date) => {
    return items.filter(item => {
      const { start } = getItemTime(item);
      return isSameDay(start, day);
    });
  };

  const HOUR_HEIGHT = 60; // 60px por hora

  return (
    <div className="flex flex-col h-[calc(100vh-220px)] min-h-[600px] bg-card/10 rounded-2xl border border-border/40 overflow-hidden shadow-sm">
      {/* Navegación de la semana */}
      <div className="flex flex-col md:flex-row items-center justify-between shrink-0 bg-card/60 backdrop-blur-md p-3 md:p-4 border-b border-border/40 gap-4">
        <div className="flex items-center gap-2">
           <Button variant="ghost" size="icon" onClick={handlePreviousWeek} className="h-10 w-10 rounded-xl hover:bg-primary/10 hover:text-primary transition-all">
             <ChevronLeft className="h-6 w-6" />
           </Button>
           <h2 className="text-base md:text-xl font-black tracking-tighter uppercase whitespace-pre-wrap text-center">
             {format(startOfCurrentWeek, 'd MMM yyyy', { locale: es })} {' - '} {format(endOfCurrentWeek, 'd MMM yyyy', { locale: es })}
           </h2>
           <Button variant="ghost" size="icon" onClick={handleNextWeek} className="h-10 w-10 rounded-xl hover:bg-primary/10 hover:text-primary transition-all">
             <ChevronRight className="h-6 w-6" />
           </Button>
        </div>
      </div>

      <div className="flex-grow overflow-auto custom-scrollbar relative bg-card/20">
        <div className="min-w-[700px] flex flex-col">
          {/* Cabeceras de días (Sticky) */}
          <div className="grid grid-cols-[60px_repeat(7,1fr)] md:grid-cols-[80px_repeat(7,1fr)] border-b border-border/40 bg-card/95 backdrop-blur-md sticky top-0 z-40 shadow-sm">
            <div className="sticky left-0 z-50 bg-card/95 border-r border-border/40" /> {/* Cuadro superior izquierdo vacío */}
            {daysOfWeek.map(day => {
              const isToday = isSameDay(day, new Date());
              return (
                <div key={day.toISOString()} className="text-center py-2 md:py-3 border-l border-border/20">
                  <p className={`text-[9px] md:text-[11px] font-black uppercase tracking-[0.1em] md:tracking-[0.2em] ${isToday ? 'text-primary' : 'text-muted-foreground/80'}`}>
                    {format(day, 'EEE', { locale: es })}
                  </p>
                  <div className="mt-1 flex justify-center">
                     <div className={`w-8 h-8 md:w-10 md:h-10 flex items-center justify-center rounded-full ${isToday ? 'bg-primary text-primary-foreground' : 'text-foreground'}`}>
                       <p className="text-base md:text-xl font-black tracking-tighter">
                         {format(day, 'd')}
                       </p>
                     </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Cuadrícula de horas y eventos */}
          <div className="grid grid-cols-[60px_repeat(7,1fr)] md:grid-cols-[80px_repeat(7,1fr)] relative flex-grow" style={{ height: `${24 * HOUR_HEIGHT}px` }}>
            {/* Etiquetas de horas (Sticky horizontal) */}
            <div className="border-r border-border/40 bg-card/95 sticky left-0 z-30">
              {hours.map(hour => (
                <div key={`label-${hour}`} className="text-center md:text-right pr-2" style={{ height: `${HOUR_HEIGHT}px` }}>
                   {/* Se ajusta con un translate negativo para centrar el texto con la línea */}
                   <span className="text-[10px] md:text-xs font-black uppercase text-muted-foreground/50 inline-block -translate-y-2 lg:-translate-y-3">
                     {hour}:00
                   </span>
                </div>
              ))}
            </div>

          {/* Columnas de los días */}
          {daysOfWeek.map(day => {
            const dayEvents = filterItemsForDay(events, day);
            const dayTasks = filterItemsForDay(tasks, day);
            const allItems = [...dayEvents, ...dayTasks];

            return (
              <DroppableDayColumn
                key={`col-${day.toISOString()}`}
                day={day}
                hours={hours}
                HOUR_HEIGHT={HOUR_HEIGHT}
                onMoveEvent={onMoveEvent}
                onMoveTask={onMoveTask}
              >
                {/* Eventos / Tareas */}
                {allItems.map(item => {
                  const { start, end } = getItemTime(item);
                  const startHours = start.getHours() + start.getMinutes() / 60;
                  let durationHours = (end.getTime() - start.getTime()) / (1000 * 60 * 60);
                  
                  // Mínimo de duración visual de 30 mins para que no colapse
                  if (durationHours <= 0) durationHours = 0.5;

                  const top = startHours * HOUR_HEIGHT;
                  const height = durationHours * HOUR_HEIGHT;
                  const isEvent = 'event_datetime_local' in item;

                  if (isEvent) {
                    return (
                      <DraggableWeeklyEvent
                        key={`event-${item.id}`}
                        eventItem={item as AgendaEvent}
                        top={top}
                        height={height}
                        start={start}
                        end={end}
                        onEditEvent={onEditEvent}
                        onDeleteEvent={onDeleteEvent}
                      />
                    );
                  } else {
                    return (
                      <DraggableWeeklyTask
                        key={`task-${item.id}`}
                        taskItem={item as TaskResponse}
                        top={top}
                        height={height}
                        onEditTask={onEditTask}
                        onDeleteTask={onDeleteTask}
                        onToggleTaskCompleted={onToggleTaskCompleted}
                      />
                    );
                  }
                })}
              </DroppableDayColumn>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
