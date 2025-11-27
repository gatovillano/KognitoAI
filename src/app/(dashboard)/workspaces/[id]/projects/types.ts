
export type KanbanStatus = 'Pendiente' | 'En Progreso' | 'Hecho';

export interface ProjectTask {
  id: string;
  type: 'task';
  description: string;
  status: KanbanStatus;
  due_date?: string;
  start_date?: string;
  end_date?: string;
  is_completed: boolean;
  workspace_id: string;
}

export interface ProjectEvent {
  id: string;
  type: 'event';
  summary: string;
  status: KanbanStatus;
  event_date: string;
  event_time: string;
  end_date?: string;
  location?: string;
  workspace_id: string;
}

export type ProjectItem = ProjectTask | ProjectEvent;
