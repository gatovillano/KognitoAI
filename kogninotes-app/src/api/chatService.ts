// src/api/chatService.ts
import api from './config';

export interface ChatThread {
    id: string;
    title: string;
    isPinned: boolean;
    platform: string;
    workspace_id: string | null;
    created_at: string;
}

export interface MessageContentPart {
    type: 'text' | 'reasoning' | 'tool_call' | 'tool_result';
    content: string;
    id?: string;
    status?: 'start' | 'end' | 'error';
    tool_name?: string;
}

export interface ChatMessage {
    text: string;
    sender: 'user' | 'ai';
    created_at: string;
    image_base64?: string;
    images_base64?: string[];
    document_url?: string;
    sources?: any[];
    ragContext?: any[];
    reasoning?: string;
    reasoning_chunks?: string[];
    content_parts?: MessageContentPart[];
    tool_code?: string;
    chunks?: string[];
}

export const chatService = {
    listThreads: async (workspaceId?: string): Promise<ChatThread[]> => {
        try {
            const response = await api.get('/threads', {
                params: {
                    workspace_id: workspaceId || 'none',
                    limit: 50
                }
            });
            return response.data.threads;
        } catch (error) {
            console.error('Error listing threads:', error);
            throw error;
        }
    },

    createThread: async (title: string = 'Nuevo Chat', workspaceId?: string): Promise<ChatThread> => {
        try {
            const response = await api.post('/threads', {
                title,
                platform: 'kognitomovil',
                workspace_id: workspaceId
            });
            return response.data;
        } catch (error) {
            console.error('Error creating thread:', error);
            throw error;
        }
    },

    listMessages: async (threadId: string): Promise<ChatMessage[]> => {
        try {
            const response = await api.get(`/threads/${threadId}/messages`, {
                params: { limit: 100 }
            });
            return response.data.messages;
        } catch (error) {
            console.error('Error listing messages:', error);
            throw error;
        }
    },

    sendMessage: async (threadId: string, accountId: string, message: string, workspaceId?: string): Promise<{taskId: string}> => {
        try {
            const response = await api.post('/chat', {
                thread_id: threadId,
                account_id: accountId,
                user_message: message,
                workspace_id: workspaceId
            });
            return response.data;
        } catch (error) {
            console.error('Error sending message:', error);
            throw error;
        }
    }
};
