import { ReactRenderer } from '@tiptap/react';
import tippy from 'tippy.js';
import { MentionList } from '@/components/MentionList';
import apiClient from '@/lib/api';

export const createMentionSuggestion = (fromTeam?: string) => ({
  items: async ({ query }: { query: string }) => {
    try {
      const payload: { search_term: string; workspace_id?: string } = { search_term: query };
      if (fromTeam) {
        payload.workspace_id = fromTeam;
      }
      const response = await apiClient.post('/api/list-notes', payload);
      // Asegúrate de que la respuesta tenga el formato esperado por MentionList
      return response.data.notes.map((note: any) => ({
        id: note.id,
        label: note.title,
      }));
    } catch (error) {
      console.error("Failed to fetch notes for mention:", error);
      return [];
    }
  },

  render: () => {
    let component: ReactRenderer;
    let popup: any;

    return {
      onStart: (props: any) => {
        component = new ReactRenderer(MentionList, {
          props,
          editor: props.editor,
        });

        if (!props.clientRect) {
          return;
        }

        popup = tippy('body', {
          getReferenceClientRect: props.clientRect,
          appendTo: () => document.body,
          content: component.element,
          showOnCreate: true,
          interactive: true,
          trigger: 'manual',
          placement: 'bottom-start',
        });
      },

      onUpdate(props: any) {
        component.updateProps(props);

        if (!props.clientRect) {
          return;
        }

        popup[0].setProps({
          getReferenceClientRect: props.clientRect,
        });
      },

      onKeyDown({ event }: { event: KeyboardEvent }) {
        if (event.key === 'Escape') {
          popup[0].hide();
          return true;
        }
        return (component.ref as any)?.onKeyDown({ event });
      },

      onExit() {
        popup[0].destroy();
        component.destroy();
      },
    };
  },
});
