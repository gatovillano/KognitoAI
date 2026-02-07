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

export const agendaService = {
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
};
