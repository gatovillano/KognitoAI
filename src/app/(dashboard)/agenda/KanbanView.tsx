'use client';

import React, { useState, useMemo, useEffect, useCallback } from 'react';
import { useDrag, useDrop } from 'react-dnd';
import apiClient from '@/lib/api';
import { Card, CardContent } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { Calendar, Clock, MapPin, ChevronLeft, ChevronRight, Filter, CheckCircle2, X, Plus } from 'lucide-react';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { Checkbox } from '@/components/ui/checkbox';
import { Button } from '@/components/ui/button';
import { AgendaEvent, TaskResponse } from './types';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { toast } from 'sonner';

const ItemTypes = {
  ITEM: 'item',
};

type KanbanStatus = 'Pendiente' | 'En Progreso' | 'Hecho';
const columns: KanbanStatus[] = ['Pendiente', 'En Progreso', 'Hecho'];

interface KanbanItem {
  id: string;
  type: 'task' | 'event';
  title: string;
  status: KanbanStatus;
  date?: string;
  time?: string;
  location?: string;
  workspace_id?: string;
  workspace_name?: string;
  workspace_color?: string;
}

interface KanbanCardProps {
  item: KanbanItem;
  moveCard: (id: string, newStatus: KanbanStatus, type: 'task' | 'event') => void;
  isSelected: boolean;
  onToggleSelect: (id: string) => void;
}

const KanbanCard = ({ item, moveCard, isSelected, onToggleSelect }: KanbanCardProps) => {
  const ref = React.useRef<HTMLDivElement>(null);
  const [{ isDragging }, drag] = useDrag({
    type: ItemTypes.ITEM,
    item: { id: item.id, status: item.status, type: item.type },
    collect: (monitor) => ({
      isDragging: monitor.isDragging(),
    }),
  });

  drag(ref);

  return (
    <Card
      ref={ref}
      style={{ opacity: isDragging ? 0.5 : 1 }}
      className={cn(
        "mb-4 cursor-grab active:cursor-grabbing hover:shadow-xl transition-all duration-300 border-l-4 rounded-2xl overflow-hidden bg-card/40 backdrop-blur-md",
        item.type === 'task' ? "border-l-primary" : "border-l-secondary",
        isSelected && "ring-2 ring-primary bg-primary/5 shadow-primary/10"
      )}
    >
      <CardContent className="p-4 relative">
        <div className="absolute top-4 right-4 z-20">
            <Checkbox 
                checked={isSelected} 
                onCheckedChange={() => onToggleSelect(item.id)}
                className="h-5 w-5 rounded-md border-2 border-primary/20 data-[state=checked]:bg-primary data-[state=checked]:border-primary"
            />
        </div>
        <div className="flex items-start justify-between mb-3">
          <span className={cn(
            "text-[10px] font-black uppercase tracking-widest px-2.5 py-1 rounded-lg",
            item.type === 'task' ? "bg-primary/10 text-primary" : "bg-secondary/10 text-secondary"
          )}>
            {item.type === 'task' ? 'Tarea' : 'Evento'}
          </span>
          {item.workspace_name && (
             <span className="text-[9px] font-bold uppercase tracking-tighter opacity-70 px-2 py-0.5 rounded-md" style={{ backgroundColor: `${item.workspace_color}15`, color: item.workspace_color }}>
                {item.workspace_name}
             </span>
          )}
        </div>
        <p className="font-bold text-sm mb-3 text-foreground line-clamp-2 leading-relaxed">
          {item.title}
        </p>

        <div className="flex flex-col gap-2 text-[11px] font-medium text-muted-foreground">
          {item.date && (
            <div className="flex items-center gap-2">
              <Calendar className="w-3.5 h-3.5 opacity-60" />
              <span>{item.date} {item.time ? `• ${item.time}` : ''}</span>
            </div>
          )}
          {item.location && (
            <div className="flex items-center gap-2">
              <MapPin className="w-3.5 h-3.5 opacity-60" />
              <span className="truncate">{item.location}</span>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

const KanbanColumn = ({
  status,
  items,
  moveCard,
  isCollapsed,
  onToggleCollapse,
  selectedIds,
  onToggleSelect,
  onCreateEvent,
  onCreateTask
}: {
  status: KanbanStatus;
  items: KanbanItem[];
  moveCard: (id: string, newStatus: KanbanStatus, type: 'task' | 'event') => void;
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
  selectedIds: string[];
  onToggleSelect: (id: string) => void;
  onCreateEvent?: (status: KanbanStatus) => void;
  onCreateTask?: (status: KanbanStatus) => void;
}) => {
  const ref = React.useRef<HTMLDivElement>(null);
  const [{ isOver }, drop] = useDrop({
    accept: ItemTypes.ITEM,
    drop: (item: { id: string, type: 'task' | 'event' }) => {
      moveCard(item.id, status, item.type);
    },
    collect: (monitor) => ({
      isOver: monitor.isOver(),
    }),
  });

  drop(ref);

  if (isCollapsed) {
    return (
      <div
        ref={ref}
        className={cn(
          "bg-card/20 rounded-[2rem] p-2 w-16 min-h-[600px] border border-border/40 transition-all duration-500 flex flex-col items-center py-6 cursor-pointer hover:bg-card/40",
          isOver && "bg-primary/5 border-primary/20 scale-[0.98]"
        )}
        onClick={onToggleCollapse}
      >
        <div className="mb-6 opacity-40">
           <ChevronLeft className="w-5 h-5" />
        </div>
        <div className="[writing-mode:vertical-rl] transform rotate-180 font-black text-foreground/40 text-xs uppercase tracking-[0.3em] flex items-center gap-4">
          <span>{status}</span>
        </div>
        <div className="mt-6 bg-primary/10 text-primary text-[10px] w-7 h-7 flex items-center justify-center rounded-xl font-black">
          {items.length}
        </div>
      </div>
    );
  }

  return (
    <div
      ref={ref}
      className={cn(
        "bg-card/20 rounded-[2.5rem] p-6 min-h-[600px] border border-border/40 transition-all duration-500 flex-1 min-w-[320px] shadow-inner",
        isOver && "bg-primary/5 border-primary/20 scale-[0.99]"
      )}
    >
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-3">
          <h3 className="font-black text-foreground/80 tracking-tight text-lg uppercase">{status}</h3>
          <span className="bg-primary/10 text-primary text-[10px] px-3 py-1.5 rounded-xl font-black">
            {items.length}
          </span>
        </div>
        <div className="flex items-center gap-1">
          {(onCreateEvent || onCreateTask) && (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button className="text-muted-foreground hover:text-primary transition-all p-2 hover:bg-primary/10 rounded-xl">
                  <Plus className="w-5 h-5" />
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-48 bg-card/95 backdrop-blur-xl border-border/40 rounded-2xl p-2 shadow-2xl">
                {onCreateEvent && (
                  <DropdownMenuItem onClick={() => onCreateEvent(status)} className="rounded-xl focus:bg-primary/10 focus:text-primary cursor-pointer py-2.5 gap-3 font-bold text-xs uppercase tracking-tight">
                    <Calendar className="h-4 w-4" /> Crear Evento
                  </DropdownMenuItem>
                )}
                {onCreateTask && (
                  <DropdownMenuItem onClick={() => onCreateTask(status)} className="rounded-xl focus:bg-primary/10 focus:text-primary cursor-pointer py-2.5 gap-3 font-bold text-xs uppercase tracking-tight">
                    <CheckCircle2 className="h-4 w-4" /> Nueva Tarea
                  </DropdownMenuItem>
                )}
              </DropdownMenuContent>
            </DropdownMenu>
          )}
          {onToggleCollapse && (
            <button
              onClick={onToggleCollapse}
              className="text-muted-foreground hover:text-foreground transition-all p-2 hover:bg-card/60 rounded-xl"
            >
              <ChevronRight className="w-5 h-5" />
            </button>
          )}
        </div>
      </div>
      <div className="space-y-4">
        {items.map((item) => (
          <KanbanCard 
            key={`${item.type}-${item.id}`} 
            item={item} 
            moveCard={moveCard} 
            isSelected={selectedIds.includes(item.id)}
            onToggleSelect={onToggleSelect}
          />
        ))}
        {items.length === 0 && (
           <div className="h-32 border-2 border-dashed border-border/20 rounded-3xl flex items-center justify-center opacity-30">
              <span className="text-[10px] font-black uppercase tracking-widest leading-none">Vacío</span>
           </div>
        )}
      </div>
    </div>
  );
};

export function KanbanView({ 
  onCreateEvent, 
  onCreateTask 
}: { 
  onCreateEvent?: (status: KanbanStatus) => void;
  onCreateTask?: (status: KanbanStatus) => void;
}) {
  const [items, setItems] = useState<KanbanItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'task' | 'event'>('all');
  const [isDoneCollapsed, setIsDoneCollapsed] = useState(false);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  const toggleSelect = (id: string) => {
    setSelectedIds(prev => 
      prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
    );
  };

  const fetchItems = useCallback(async () => {
    setIsLoading(true);
    try {
      const [eventsResponse, tasksResponse] = await Promise.all([
        apiClient.post('/api/list-events', { include_past: true }),
        apiClient.get('/api/tasks')
      ]);

      const mappedEvents: KanbanItem[] = eventsResponse.data.map((event: AgendaEvent) => ({
        id: event.id,
        type: 'event',
        title: event.summary,
        status: (event.status as KanbanStatus) || 'Pendiente',
        date: new Date(event.event_datetime_local).toLocaleDateString(),
        time: new Date(event.event_datetime_local).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        location: event.location,
        workspace_id: event.workspace_id,
        workspace_name: event.workspace_name,
        workspace_color: event.workspace_color,
      }));

      const mappedTasks: KanbanItem[] = tasksResponse.data.map((task: TaskResponse) => {
        let status: KanbanStatus = (task.status as KanbanStatus) || 'Pendiente';
        if (task.is_completed) status = 'Hecho';
        
        return {
          id: task.id,
          type: 'task',
          title: task.description,
          status,
          date: task.end_date ? new Date(task.end_date).toLocaleDateString() : undefined,
          workspace_id: task.workspace_id,
        };
      });

      setItems([...mappedEvents, ...mappedTasks]);
    } catch (error) {
      console.error('Error fetching items for Kanban:', error);
      toast.error('Error al cargar datos del tablero.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchItems();
  }, [fetchItems]);

  const moveCard = async (id: string, newStatus: KanbanStatus, type: 'task' | 'event') => {
    const originalItems = [...items];
    const updatedItems = items.map((item) =>
      item.id === id && item.type === type ? { ...item, status: newStatus } : item
    );
    setItems(updatedItems);

    try {
      if (type === 'task') {
        const is_completed = newStatus === 'Hecho';
        await apiClient.put(`/api/tasks/${id}`, { status: newStatus, is_completed });
      } else {
        await apiClient.put(`/api/agenda/events/${id}`, { status: newStatus });
      }
      toast.success('Estado actualizado correctamente.');
    } catch (error) {
      console.error('Error updating item status:', error);
      toast.error('Error al actualizar el estado.');
      setItems(originalItems);
    }
  };

  const handleBulkMove = async (newStatus: KanbanStatus) => {
    if (selectedIds.length === 0) return;
    
    const itemsToMove = items.filter(i => selectedIds.includes(i.id));
    const originalItems = [...items];
    
    // Optimistic update
    setItems(prev => prev.map(item => 
      selectedIds.includes(item.id) ? { ...item, status: newStatus } : item
    ));
    setSelectedIds([]);

    const toastId = toast.loading(`Moviendo ${itemsToMove.length} elementos a ${newStatus}...`);

    try {
      await Promise.all(itemsToMove.map(item => {
        if (item.type === 'task') {
          return apiClient.put(`/api/tasks/${item.id}`, { status: newStatus, is_completed: newStatus === 'Hecho' });
        } else {
          return apiClient.put(`/api/agenda/events/${item.id}`, { status: newStatus });
        }
      }));
      toast.success(`${itemsToMove.length} elementos movidos correctamente.`, { id: toastId });
    } catch (error) {
      console.error('Error in bulk move:', error);
      toast.error('Error al mover algunos elementos.', { id: toastId });
      setItems(originalItems);
    }
  };

  const filteredItems = useMemo(() => {
    if (filter === 'all') return items;
    return items.filter((item) => item.type === filter);
  }, [items, filter]);

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-4">
        <LoadingSpinner />
        <p className="text-muted-foreground font-medium animate-pulse">Cargando tablero...</p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
             <div className="p-2.5 rounded-xl bg-primary/10 text-primary">
                <Filter className="w-5 h-5" />
             </div>
             <h2 className="text-xl font-black tracking-tight text-foreground/90 uppercase">Tablero de Control</h2>
          </div>
          
          <div className="bg-card/40 backdrop-blur-md p-1 rounded-2xl border border-border/40 flex items-center gap-1">
            {(['all', 'task', 'event'] as const).map((t) => (
              <button
                key={t}
                onClick={() => setFilter(t)}
                className={cn(
                  "px-4 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all duration-300",
                  filter === t 
                    ? "bg-primary text-primary-foreground shadow-lg shadow-primary/20 scale-105" 
                    : "text-muted-foreground hover:text-foreground hover:bg-primary/5"
                )}
              >
                {t === 'all' ? 'Todo' : t === 'task' ? 'Tareas' : 'Eventos'}
              </button>
            ))}
          </div>
        </div>

        <div className="flex gap-8 h-full overflow-x-auto pb-10 pt-2 custom-scrollbar mask-fade-right">
          {columns.map((status) => (
            <KanbanColumn
              key={status}
              status={status}
              items={filteredItems.filter((item) => item.status === status)}
              moveCard={moveCard}
              isCollapsed={status === 'Hecho' ? isDoneCollapsed : undefined}
              onToggleCollapse={status === 'Hecho' ? () => setIsDoneCollapsed(!isDoneCollapsed) : undefined}
              selectedIds={selectedIds}
              onToggleSelect={toggleSelect}
            />
          ))}
      </div>

        {/* Barra de Acciones Masivas */}
        {selectedIds.length > 0 && (
          <div className="fixed bottom-8 left-1/2 -translate-x-1/2 z-50 animate-in slide-in-from-bottom-10 fade-in duration-500">
            <div className="bg-foreground text-background px-8 py-5 rounded-[2.5rem] shadow-2xl shadow-black/40 flex items-center gap-8 backdrop-blur-xl bg-opacity-90 border border-white/10">
              <div className="flex items-center gap-4 border-r border-white/20 pr-6">
                <div className="bg-primary text-primary-foreground text-[10px] font-black w-7 h-7 flex items-center justify-center rounded-xl">
                  {selectedIds.length}
                </div>
                <span className="text-xs font-black uppercase tracking-widest whitespace-nowrap">Seleccionados</span>
              </div>
              
              <div className="flex items-center gap-3">
                {columns.map(status => (
                  <Button
                    key={status}
                    size="sm"
                    variant="ghost"
                    onClick={() => handleBulkMove(status)}
                    className="rounded-xl hover:bg-white/10 text-[10px] font-black uppercase tracking-widest px-4 py-2"
                  >
                    Mover a {status}
                  </Button>
                ))}
              </div>

              <div className="h-6 w-px bg-white/20 mx-2" />

              <button 
                onClick={() => setSelectedIds([])}
                className="hover:scale-110 transition-transform p-2 bg-white/5 rounded-full hover:bg-red-500 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>
        )}
      </div>
  );
}
