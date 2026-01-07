// src/lib/chatUtils.ts
// Utility functions for chat components to handle citations and sources processing

import { Source, ContentPart } from '@/components/SourceButton';

export const processMessageWithCitations = (text: string, allSources: Source[] | undefined): {
  contentParts: ContentPart[];
  uncitedSources: Source[]
} => {
  if (!allSources || allSources.length === 0) {
    return {
      contentParts: [{ type: 'text', content: text }],
      uncitedSources: []
    };
  }

  const contentParts: ContentPart[] = [];
  let lastIndex = 0;
  const citedSourceIds = new Set<string | number>();

  // Expresión regular para buscar citas individuales como [1], [2], etc.
  const citationRegex = /\[(\d+)\]/g;
  let match: RegExpExecArray | null;

  while ((match = citationRegex.exec(text)) !== null) {
    const citationNumber = parseInt(match[1], 10);
    const fullMatch = match[0];
    const index = match.index!;

    const source = allSources.find(s => s.id == citationNumber); // Usar == para comparar string | number

    if (source) {
      // Añadir el texto antes de la cita
      if (index > lastIndex) {
        contentParts.push({ type: 'text', content: text.substring(lastIndex, index) });
      }

      // Añadir la cita como un componente
      contentParts.push({ type: 'citation', source: source, citationNumber: citationNumber });
      citedSourceIds.add(source.id);

      lastIndex = index + fullMatch.length;
    }
  }

  // Añadir cualquier texto restante después de la última cita
  if (lastIndex < text.length) {
    contentParts.push({ type: 'text', content: text.substring(lastIndex) });
  }

  const uncitedSources = allSources.filter(s => !citedSourceIds.has(s.id));

  return { contentParts, uncitedSources };
};

// Helper function to collect and deduplicate sources from various message fields
export const collectSourcesFromMessage = (
  sources?: Source[],
  ragContext?: any[]
): { additionalSources: Source[], processedRagContext: any[] } => {
  const additionalSourcesToDisplay: Source[] = [];
  const seenSourceIdentifiers = new Set<string | number>();

  // Helper para añadir fuentes y evitar duplicados
  const addSourceToDisplay = (source: Source) => {
    const identifier = source.url ? source.url : `${source.type}-${source.name || source.title}-${source.id}`;
    if (!seenSourceIdentifiers.has(identifier)) {
      additionalSourcesToDisplay.push(source);
      seenSourceIdentifiers.add(identifier);
    }
  };

  // Process ragContext
  if (ragContext && Array.isArray(ragContext)) {
    ragContext.forEach((ragItem) => {
      let ragId: number | string;
      if (typeof ragItem.id === 'number') {
        ragId = ragItem.id;
      } else if (ragItem.metadata?.document_id) {
        ragId = ragItem.metadata.document_id;
      } else {
        ragId = `rag-${Math.random().toString(36).substr(2, 9)}`; // Generate unique ID if not numeric
      }

      const newSource: Source = {
        id: ragId,
        title: ragItem.name || ragItem.title || 'Contexto RAG',
        url: ragItem.url || ragItem.metadata?.document_id || '',
        snippet: ragItem.snippet || ragItem.content || '',
        type: ragItem.type || ragItem.metadata?.type || 'document',
        metadata: ragItem.metadata || {},
        name: ragItem.name || ragItem.title || 'Contexto RAG',
      };
      addSourceToDisplay(newSource);
    });
  }

  return {
    additionalSources: additionalSourcesToDisplay,
    processedRagContext: ragContext || []
  };
};

/**
 * Limpia el texto de símbolos de Markdown para que sea apto para TTS (Text-to-Speech).
 */
export const stripMarkdown = (text: string): string => {
  if (!text) return '';

  let cleanText = text;

  // 1. Eliminar bloques de código (``` ... ```)
  cleanText = cleanText.replace(/```[\s\S]*?```/g, '');

  // 2. Eliminar código en línea (`...`)
  cleanText = cleanText.replace(/`(.+?)`/g, '$1');

  // 3. Eliminar encabezados (# Título) - Solo los símbolos #
  cleanText = cleanText.replace(/^#+\s*/gm, '');

  // 4. Eliminar negritas y cursivas (***, **, *, __, _)
  cleanText = cleanText.replace(/(\*\*|__)(.*?)\1/g, '$2');
  cleanText = cleanText.replace(/(\*|_)(.*?)\1/g, '$2');

  // 5. Eliminar enlaces [texto](url) -> texto
  cleanText = cleanText.replace(/\[([^\]]+)\]\([^)]+\)/g, '$1');

  // 6. Eliminar imágenes ![alt](url) -> ''
  cleanText = cleanText.replace(/!\[([^\]]*)\]\([^)]+\)/g, '');

  // 7. Eliminar citas (>)
  cleanText = cleanText.replace(/^>\s+/gm, '');

  // 8. Eliminar líneas horizontales (---, ***, ___)
  cleanText = cleanText.replace(/^[*-]{3,}$/gm, '');

  // 9. Eliminar marcadores de citas [1], [2], etc.
  cleanText = cleanText.replace(/\[\d+\]/g, '');

  // 10. Limpiar espacios en blanco extra
  cleanText = cleanText.replace(/\n{3,}/g, '\n\n');

  return cleanText.trim();
};