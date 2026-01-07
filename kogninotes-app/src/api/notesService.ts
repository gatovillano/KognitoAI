// src/api/notesService.ts
import api from './config';

export interface Note {
    id: number;
    title: string;
    content: string;
    category?: string;
    created_at: string;
    updated_at: string;
    workspace_id?: string;
    workspace_name?: string;
    workspace_color?: string;
}

export interface PaginatedNotesResponse {
    total: number;
    notes: Note[];
}

export const notesService = {
    listNotes: async (
        searchTerm = '',
        workspaceId?: string | null,
        category?: string | null,
        skip = 0,
        limit = 20
    ): Promise<PaginatedNotesResponse> => {
        const response = await api.post('/notes/list-notes', {
            search_term: searchTerm,
            workspace_id: workspaceId || undefined,
            category: category || undefined,
            skip,
            limit,
        });
        return response.data;
    },

    getNote: async (id: number): Promise<Note> => {
        const response = await api.get(`/notes/${id}`);
        return response.data;
    },

    createNote: async (noteData: { title: string; content: string; category?: string; workspace_id?: string }): Promise<Note> => {
        const response = await api.post('/add-note', noteData);
        return response.data;
    },

    updateNote: async (id: number, noteData: { title?: string; content?: string; category?: string; workspace_id?: string }): Promise<Note> => {
        const response = await api.post('/update-note', { note_id: id, ...noteData });
        return response.data;
    }
};
