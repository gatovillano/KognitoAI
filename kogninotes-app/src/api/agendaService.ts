// src/api/agendaService.ts
import api from './config';

export interface AgendaEvent {
    id: number;
    account_id: string;
    creator_name: string;
    workspace_id: string | null;
    workspace_name: string | null;
    workspace_color: string | null;
    summary: string;
    description: string | null;
    location: string | null;
    event_datetime_utc: string;
    event_datetime_local: string;
    end_date: string | null;
    user_timezone: string;
    is_active: boolean;
    is_private: boolean;
    attendees: string[];
    external_attendees: string[];
    duration_minutes: number | null;
    status: string;
    etag: string | null;
}

export interface Task {
    id: string;
    description: string;
    is_completed: boolean;
    start_date: string | null;
    end_date: string | null;
    status: string;
    created_at: string;
    updated_at: string;
    account_id: string;
    workspace_id: string | null;
}

export const agendaService = {
    // Events
    listEvents: async (includePast = false, workspaceId?: string): Promise<AgendaEvent[]> => {
        try {
            const response = await api.get('/agenda/events', {
                params: {
                    include_past: includePast,
                    workspace_id: workspaceId,
                },
            });
            return Array.isArray(response.data) ? response.data : [];
        } catch (error) {
            console.error('Error listing events:', error);
            throw error;
        }
    },

    createEvent: async (eventData: {
        summary: string;
        description: string;
        event_date: string;
        event_time: string;
        location?: string;
        workspace_id?: string;
        end_date?: string;
        end_time?: string;
    }): Promise<AgendaEvent> => {
        try {
            const response = await api.post('/add-event', eventData);
            return response.data;
        } catch (error) {
            console.error('Error creating event:', error);
            throw error;
        }
    },

    updateEvent: async (eventId: number, eventData: Partial<AgendaEvent>): Promise<AgendaEvent> => {
        try {
            const response = await api.put(`/agenda/events/${eventId}`, eventData);
            return response.data;
        } catch (error) {
            console.error('Error updating event:', error);
            throw error;
        }
    },

    cancelEvent: async (eventId: number, workspaceId?: string): Promise<void> => {
        try {
            await api.post('/cancel-event', { event_id: eventId, workspace_id: workspaceId });
        } catch (error) {
            console.error('Error cancelling event:', error);
            throw error;
        }
    },

    // Tasks
    listTasks: async (params?: {
        workspace_id?: string;
        is_completed?: boolean;
        status?: string;
        search_term?: string;
    }): Promise<Task[]> => {
        try {
            const response = await api.get('/tasks', { params });
            return Array.isArray(response.data) ? response.data : [];
        } catch (error) {
            console.error('Error listing tasks:', error);
            throw error;
        }
    },

    createTask: async (taskData: {
        description: string;
        start_date?: string;
        end_date?: string;
        workspace_id?: string;
    }): Promise<Task> => {
        try {
            const response = await api.post('/tasks', taskData);
            return response.data;
        } catch (error) {
            console.error('Error creating task:', error);
            throw error;
        }
    },

    updateTask: async (taskId: string, taskData: Partial<Task>): Promise<Task> => {
        try {
            const response = await api.put(`/tasks/${taskId}`, taskData);
            return response.data;
        } catch (error) {
            console.error('Error updating task:', error);
            throw error;
        }
    },

    deleteTask: async (taskId: string): Promise<void> => {
        try {
            await api.delete(`/tasks/${taskId}`);
        } catch (error) {
            console.error('Error deleting task:', error);
            throw error;
        }
    },
};
