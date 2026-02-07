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

    // Buscar la fuente por índice (citationNumber es 1-based, el array es 0-based)
    // Opcionalmente también por ID si el ID coincide con el número
    const source = allSources[citationNumber - 1] || allSources.find(s => s.id == citationNumber);

    if (source) {
      // Añadir el texto antes de la cita
      if (index > lastIndex) {
        contentParts.push({ type: 'text', content: text.substring(lastIndex, index) });
      }

      // Añadir la cita como un componente
      contentParts.push({ type: 'citation', source: source, citationNumber: citationNumber });
      citedSourceIds.add(String(source.id));

      lastIndex = index + fullMatch.length;
    }
  }

  // Añadir cualquier texto restante después de la última cita
  if (lastIndex < text.length) {
    contentParts.push({ type: 'text', content: text.substring(lastIndex) });
  }

  const uncitedSources = allSources.filter(s => !citedSourceIds.has(String(s.id)));

  return { contentParts, uncitedSources };
};

// Helper function to collect and deduplicate sources from various message fields
export const collectSourcesFromMessage = (
  sources?: Source[],
  ragContext?: any[]
): { additionalSources: Source[], processedRagContext: any[] } => {
  const additionalSourcesToDisplay: Source[] = [];
  const seenSourceIdentifiers = new Set<string | number>();

  // Debug log para ver qué llega
  // console.log('collectSourcesFromMessage input:', { sources, ragContext });

  // Función interna para normalizar y detectar tipos de fuentes
  const normalizeSource = (rawSource: any): Source => {
    const url = rawSource.url || rawSource.metadata?.document_id || '';
    const metadata = rawSource.metadata || {};

    // Identificar el tipo base
    let detectedType: Source['type'] = rawSource.type || metadata.type || 'document';

    // Refuerzo de detección por URL
    if (url.includes('github.com')) {
      detectedType = 'github';
    } else if (url.startsWith('graph://') || url.startsWith('analysis://')) {
      detectedType = 'graph';
    } else if (url.startsWith('note://')) {
      detectedType = 'note';
    }

    return {
      id: rawSource.id || (rawSource.metadata?.document_id) || `src-${Math.random().toString(36).substr(2, 9)}`,
      title: rawSource.name || rawSource.title || (detectedType === 'github' ? 'GitHub Repository' : 'Fuente'),
      url: url,
      snippet: rawSource.snippet || rawSource.content || rawSource.page_content || '',
      type: detectedType,
      metadata: metadata,
      name: rawSource.name || rawSource.title || 'Fuente'
    };
  };

  // Helper para añadir fuentes y evitar duplicados
  const addSourceToDisplay = (source: Source) => {
    // Usar tipo + URL/ID como identificador para evitar colisiones entre diferentes tipos de fuentes
    const identifier = `${source.type}-${source.url || source.id}`;
    if (!seenSourceIdentifiers.has(identifier)) {
      additionalSourcesToDisplay.push(source);
      seenSourceIdentifiers.add(identifier);
    }
  };

  // 1. Process explicit sources
  if (sources && Array.isArray(sources)) {
    sources.forEach(s => addSourceToDisplay(normalizeSource(s)));
  }

  // 2. Process ragContext
  if (ragContext && Array.isArray(ragContext)) {
    ragContext.forEach(s => addSourceToDisplay(normalizeSource(s)));
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