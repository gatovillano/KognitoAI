
'use client';

import { useState, useEffect, useCallback } from 'react';
import apiClient from '@/lib/api';
import { KanbanBoard } from './KanbanBoard';
import { ProjectItem, KanbanStatus } from './types';
import { AgendaEvent, TaskResponse } from '@/app/(dashboard)/agenda/types';
import { LoadingSpinner } from '@/components/LoadingSpinner';

interface KanbanBoardWrapperProps {
  workspaceId: string;
}

type ApiItem = (Omit<AgendaEvent, 'status'> | Omit<TaskResponse, 'status'>) & { type: 'event' | 'task', status?: string };

const mapApiItemsToProjectItems = (items: ApiItem[]): ProjectItem[] => {
  return items.map((item) => {
    let status: KanbanStatus = 'Pendiente'; // Default status

    if (item.type === 'task') {
      const task = item as TaskResponse & { status?: string };
      if (task.status && ['Pendiente', 'En Progreso', 'Hecho'].includes(task.status)) {
        status = task.status as KanbanStatus;
      } else if (task.is_completed) {
        status = 'Hecho';
      }
    } else {
        const event = item as AgendaEvent & { status?: string };
        if (event.status && ['Pendiente', 'En Progreso', 'Hecho'].includes(event.status)) {
            status = event.status as KanbanStatus;
        }
    }

    if (item.type === 'task') {
      const task = item as TaskResponse;
      return {
        ...task,
        type: 'task',
        status,
        workspace_id: task.workspace_id || '',
      };
    } else {
      const event = item as AgendaEvent;
      return {
        ...event,
        id: event.id,
        summary: event.summary,
        type: 'event',
        status,
        event_date: new Date(event.event_datetime_local).toLocaleDateString(),
        event_time: new Date(event.event_datetime_local).toLocaleTimeString(),
        workspace_id: event.workspace_id || '',
      };
    }
  });
};

export const KanbanBoardWrapper: React.FC<KanbanBoardWrapperProps> = ({ workspaceId }) => {
  const [projectItems, setProjectItems] = useState<ProjectItem[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchItems = useCallback(async () => {
    setLoading(true);
    try {
      const response = await apiClient.get(`/api/workspaces/${workspaceId}/items`);
      const mappedItems = mapApiItemsToProjectItems(response.data);
      setProjectItems(mappedItems);
    } catch (error) {
      console.error('Error fetching project items:', error);
    } finally {
      setLoading(false);
    }
  }, [workspaceId]);

  useEffect(() => {
    fetchItems();
  }, [fetchItems]);

  if (loading) {
    return <LoadingSpinner />;
  }

  return <KanbanBoard items={projectItems} workspaceId={workspaceId} onItemsChange={fetchItems} />;
};
