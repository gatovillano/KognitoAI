'use client';

import React, { useState, useMemo, useEffect } from 'react';
import { useDrag, useDrop } from 'react-dnd';
import { ProjectItem, KanbanStatus, ProjectTask, ProjectEvent } from './types';
import apiClient from '@/lib/api';
import { Card, CardContent } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { Calendar, Clock, MapPin, ChevronLeft, ChevronRight } from 'lucide-react';

const ItemTypes = {
  ITEM: 'item',
};

const columns: KanbanStatus[] = ['Pendiente', 'En Progreso', 'Hecho'];

const KanbanCard = ({ item, moveCard }: { item: ProjectItem; moveCard: (id: string, newStatus: KanbanStatus, type: 'task' | 'event') => void }) => {
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
        "mb-3 cursor-grab active:cursor-grabbing hover:shadow-md transition-all duration-200 border-l-4",
        item.type === 'task' ? "border-l-blue-500" : "border-l-green-500"
      )}
    >
      <CardContent className="p-3">
        <div className="flex items-start justify-between mb-2">
          <span className={cn(
            "text-xs font-medium px-2 py-0.5 rounded-full",
            item.type === 'task' ? "bg-blue-100 text-blue-700" : "bg-green-100 text-green-700"
          )}>
            {item.type === 'task' ? 'Tarea' : 'Evento'}
          </span>
        </div>
        <p className="font-medium text-sm mb-2 text-gray-800 line-clamp-2">
          {item.type === 'task' ? item.description : item.summary}
        </p>

        <div className="flex flex-col gap-1 text-xs text-gray-500">
          {item.type === 'event' && (
            <>
              <div className="flex items-center gap-1">
                <Calendar className="w-3 h-3" />
                <span>{item.event_date} {item.event_time}</span>
              </div>
              {item.location && (
                <div className="flex items-center gap-1">
                  <MapPin className="w-3 h-3" />
                  <span className="truncate">{item.location}</span>
                </div>
              )}
            </>
          )}
          {item.type === 'task' && item.due_date && (
            <div className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              <span>{new Date(item.due_date).toLocaleDateString()}</span>
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
  onToggleCollapse
}: {
  status: KanbanStatus;
  items: ProjectItem[];
  moveCard: (id: string, newStatus: KanbanStatus, type: 'task' | 'event') => void;
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
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
          "bg-gray-50/50 rounded-xl p-2 w-14 min-h-[500px] border border-gray-100 transition-all duration-300 flex flex-col items-center py-4 cursor-pointer hover:bg-gray-100",
          isOver && "bg-blue-50/50 border-blue-200"
        )}
        onClick={onToggleCollapse}
        title="Expandir columna"
      >
        <div className="mt-2 mb-4">
          <ChevronLeft className="w-5 h-5 text-gray-400" />
        </div>
        <div className="[writing-mode:vertical-rl] transform rotate-180 font-semibold text-gray-600 whitespace-nowrap tracking-wide flex items-center gap-2">
          <span>{status}</span>
        </div>
        <div className="mt-4 bg-gray-200 text-gray-600 text-xs w-6 h-6 flex items-center justify-center rounded-full font-medium">
          {items.length}
        </div>
      </div>
    );
  }

  return (
    <div
      ref={ref}
      className={cn(
        "bg-gray-50/50 rounded-xl p-4 min-h-[500px] border border-gray-100 transition-all duration-300 flex-1 min-w-[300px]",
        isOver && "bg-blue-50/50 border-blue-200"
      )}
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <h3 className="font-semibold text-gray-700">{status}</h3>
          <span className="bg-gray-200 text-gray-600 text-xs px-2 py-1 rounded-full font-medium">
            {items.length}
          </span>
        </div>
        {onToggleCollapse && (
          <button
            onClick={onToggleCollapse}
            className="text-gray-400 hover:text-gray-600 transition-colors p-1 hover:bg-gray-200 rounded-full"
            title="Contraer columna"
          >
            <ChevronRight className="w-5 h-5" />
          </button>
        )}
      </div>
      <div className="space-y-3">
        {items.map((item) => (
          <KanbanCard key={item.id} item={item} moveCard={moveCard} />
        ))}
      </div>
    </div>
  );
};

interface KanbanBoardProps {
  items: ProjectItem[];
  workspaceId: string;
  onItemsChange: () => void;
}

export const KanbanBoard: React.FC<KanbanBoardProps> = ({ items: initialItems, workspaceId, onItemsChange }) => {
  const [items, setItems] = useState(initialItems);
  const [filter, setFilter] = useState<'all' | 'task' | 'event'>('all');
  const [isDoneCollapsed, setIsDoneCollapsed] = useState(false);

  useEffect(() => {
    setItems(initialItems);
  }, [initialItems]);

  const moveCard = async (id: string, newStatus: KanbanStatus, type: 'task' | 'event') => {
    const originalItems = items;
    // Optimistic update
    const updatedItems = items.map((item) =>
      item.id === id ? { ...item, status: newStatus } : item
    );
    setItems(updatedItems);

    try {
      if (type === 'task') {
        const is_completed = newStatus === 'Hecho';
        await apiClient.put(`/api/tasks/${id}`, { status: newStatus, is_completed, workspace_id: workspaceId });
        onItemsChange();
      } else if (type === 'event') {
        await apiClient.put(`/api/agenda/events/${id}`, { status: newStatus });
        onItemsChange();
      }
    } catch (error) {
      console.error('Error updating item status:', error);
      setItems(originalItems); // Revert state if API call fails
    }
  };

  const filteredItems = useMemo(() => {
    if (filter === 'all') return items;
    return items.filter((item) => item.type === filter);
  }, [items, filter]);

  return (
    <div className="h-full">
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-xl font-bold text-gray-800">Tablero de Proyecto</h2>
        <select
          onChange={(e) => setFilter(e.target.value as 'all' | 'task' | 'event')}
          value={filter}
          className="p-2 border border-gray-200 rounded-lg bg-white text-sm focus:ring-2 focus:ring-blue-500 outline-none shadow-sm"
        >
          <option value="all">Todos los items</option>
          <option value="task">Solo Tareas</option>
          <option value="event">Solo Eventos</option>
        </select>
      </div>

      <div className="flex gap-6 h-full overflow-x-auto pb-4">
        {columns.map((status) => (
          <KanbanColumn
            key={status}
            status={status}
            items={filteredItems.filter((item) => item.status === status)}
            moveCard={moveCard}
            isCollapsed={status === 'Hecho' ? isDoneCollapsed : undefined}
            onToggleCollapse={status === 'Hecho' ? () => setIsDoneCollapsed(!isDoneCollapsed) : undefined}
          />
        ))}
      </div>
    </div>
  );
};