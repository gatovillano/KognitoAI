// src/api/workspaceService.ts
import api from './config';

export interface Workspace {
    id: string;
    name: string;
    color?: string;
    description?: string;
}

export interface PaginatedWorkspacesResponse {
    total: number;
    workspaces: Workspace[];
}

export const workspaceService = {
    listWorkspaces: async (): Promise<PaginatedWorkspacesResponse> => {
        const response = await api.get('/workspaces');
        // El backend devuelve { total: X, workspaces: [...] }
        return response.data;
    }
};
