// src/api/inboxService.ts
import api from './config';

export interface AgentMessage {
  id: number;
  title?: string | null;
  content: string;
  category?: string | null;
  created_at: string;
  workspace_name?: string | null;
  workspace_color?: string | null;
}

export interface InsightItem {
  id: string;
  title?: string;
  summary: string;
  created_at: string;
  action_suggestion?: string;
  workspace_name?: string | null;
  workspace_color?: string | null;
}

export interface InboxItem {
  kind: 'agent_message' | 'insight';
  id: string;
  created_at: string;
  title: string;
  preview: string;
  payload: any;
}

export const inboxService = {
  fetchInbox: async (): Promise<InboxItem[]> => {
    const [messagesRes, insightsRes] = await Promise.all([
      api.post('/notes/list-notes', {
        only_agent_messages: true,
        limit: 100,
        skip: 0,
      }),
      api.post('/get-all-analysis', {
        analysis_type: 'insight',
        limit: 100,
        offset: 0,
      }),
    ]);

    const messages: AgentMessage[] = (messagesRes.data?.notes || []).map((n: any) => ({
      id: n.id,
      title: n.title,
      content: n.content,
      category: n.category,
      created_at: n.created_at,
      workspace_name: n.workspace_name,
      workspace_color: n.workspace_color,
    }));

    const insights: InsightItem[] = (insightsRes.data?.analysis || []).map((i: any) => ({
      id: i.id,
      title: i.title,
      summary: i.summary,
      created_at: i.created_at,
      action_suggestion: i.action_suggestion,
      workspace_name: i.workspace_name,
      workspace_color: i.workspace_color,
    }));

    const merged: InboxItem[] = [
      ...messages.map((msg) => ({
        kind: 'agent_message' as const,
        id: `msg-${msg.id}`,
        created_at: msg.created_at,
        title: msg.title || 'Mensaje del agente',
        preview: msg.content,
        payload: msg,
      })),
      ...insights.map((insight) => ({
        kind: 'insight' as const,
        id: `insight-${insight.id}`,
        created_at: insight.created_at,
        title: insight.title || 'Insight',
        preview: insight.summary,
        payload: insight,
      })),
    ].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

    return merged;
  },

  deleteAgentMessage: async (noteId: number): Promise<void> => {
    await api.post('/delete-note', { note_id: noteId });
  },

  deleteInsight: async (insightId: number): Promise<void> => {
    await api.delete('/delete-proactive-insight', {
      data: { insight_id: insightId },
    });
  },
};
