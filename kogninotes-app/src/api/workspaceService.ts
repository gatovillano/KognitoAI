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

// Obtiene TODOS los workspaces del usuario, paginando automáticamente
// para evitar cualquier límite por página del backend.
export const workspaceService = {
    listWorkspaces: async (limit?: number, skip: number = 0): Promise<PaginatedWorkspacesResponse> => {
        const pageSize = limit && limit > 0 ? limit : 100;
        const all: Workspace[] = [];
        let currentSkip = skip;
        let total = 0;

        // Primer request para conocer el total
        const first = await api.get('/workspaces', { params: { skip: currentSkip, limit: pageSize } });
        const firstData = first.data as PaginatedWorkspacesResponse;
        total = firstData?.total ?? 0;
        const firstBatch = firstData?.workspaces ?? [];
        all.push(...firstBatch);
        currentSkip += firstBatch.length;

        // Seguir pidiendo mientras falten workspaces
        while (all.length < total && firstBatch.length > 0) {
            const res = await api.get('/workspaces', { params: { skip: currentSkip, limit: pageSize } });
            const batch = (res.data as PaginatedWorkspacesResponse)?.workspaces ?? [];
            if (batch.length === 0) break;
            all.push(...batch);
            currentSkip += batch.length;
        }

        return { total: total || all.length, workspaces: all };
    }
};
