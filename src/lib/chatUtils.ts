// src/lib/chatUtils.ts
// Utility functions for chat components to handle citations and sources processing.
// Triggering a rebuild to solve a potential cache issue.

import { Source, ContentPart } from '@/components/SourceButton';

const getNormalizedSourceId = (rawSource: any, fallbackIndex: number): string | number => {
  if (rawSource.id !== undefined && rawSource.id !== null && rawSource.id !== '') {
    return rawSource.id;
  }

  if (rawSource.metadata?.document_id) {
    return rawSource.metadata.document_id;
  }

  return `source-${fallbackIndex}`;
};

export const getSourceIdentityKey = (source: Source): string => {
  // Use url+title for dedup, but always include snippet prefix to distinguish different chunks/excerpts
  const urlKey = source.url || '';
  const titleKey = (source.title || source.name || '').toLowerCase().trim();
  const snippetKey = (source.snippet || '').slice(0, 80).replace(/\s+/g, ' ');
  return [source.type || 'document', urlKey, titleKey, snippetKey].join('::');
};

const detectSourceType = (url: string, rawType: string | undefined, metadata: Record<string, any>): Source['type'] => {
  // Explicit type from backend takes priority if it's a known value
  const knownTypes = ['web', 'document', 'memory', 'code', 'database', 'graph', 'note', 'github'];
  if (rawType && knownTypes.includes(rawType)) return rawType as Source['type'];

  // Infer from URL scheme / domain
  if (!url) return (metadata.type as Source['type']) || 'document';
  if (url.startsWith('http://') || url.startsWith('https://')) {
    if (url.includes('github.com')) return 'github';
    return 'web';
  }
  if (url.startsWith('note://')) return 'note';
  if (url.startsWith('graph://') || url.startsWith('analysis://')) return 'graph';
  if (url.startsWith('memory://')) return 'memory';
  if (url.startsWith('db://') || url.startsWith('database://')) return 'database';
  if (url.startsWith('code://') || metadata.language) return 'code';

  // Infer from metadata hints
  if (metadata.file_id || metadata.page !== undefined) return 'document';
  if (metadata.node_id || metadata.graph_id) return 'graph';
  if (metadata.note_id) return 'note';

  return 'document';
};

const normalizeSource = (rawSource: any, fallbackIndex: number): Source => {
  const url = rawSource.url || rawSource.metadata?.document_id || '';
  const metadata = rawSource.metadata || {};
  const detectedType = detectSourceType(url, rawSource.type || metadata.type, metadata);

  const title =
    rawSource.name ||
    rawSource.title ||
    metadata.title ||
    (detectedType === 'github' ? 'GitHub Repository' :
     detectedType === 'web' ? new URL(url).hostname.replace(/^www\./, '') :
     'Fuente');

  const snippet =
    rawSource.snippet ||
    rawSource.content ||
    rawSource.page_content ||
    metadata.excerpt ||
    '';

  // Enrich metadata with page/score info if present at top level
  const enrichedMetadata = {
    ...metadata,
    ...(rawSource.score != null && metadata.similarity_score == null ? { similarity_score: rawSource.score } : {}),
    ...(rawSource.distance != null && metadata.similarity_score == null ? { similarity_score: 1 - rawSource.distance } : {}),
    ...(rawSource.page != null && metadata.page == null ? { page: rawSource.page } : {}),
  };

  return {
    id: getNormalizedSourceId(rawSource, fallbackIndex),
    title,
    url,
    snippet,
    type: detectedType,
    metadata: enrichedMetadata,
    name: title,
    is_cited: rawSource.is_cited,
  };
};

const dedupeSources = (sources: Source[]): Source[] => {
  const seenKeys = new Set<string>();
  const uniqueSources: Source[] = [];

  sources.forEach((source) => {
    const key = getSourceIdentityKey(source);
    if (!seenKeys.has(key)) {
      seenKeys.add(key);
      uniqueSources.push(source);
    }
  });

  return uniqueSources;
};

export const processMessageWithCitations = (text: string | any[], allSources: Source[] | undefined): {
  contentParts: ContentPart[];
  citedSources: Source[];
  uncitedSources: Source[];
  resolvedSources: Source[];
} => {
  // Normalizar el texto a string
  const textString = Array.isArray(text)
    ? text.join('\n\n')
    : (typeof text === 'string' ? text : JSON.stringify(text));

  if (!allSources || allSources.length === 0) {
    return {
      contentParts: [{ type: 'text', content: textString }],
      citedSources: [],
      uncitedSources: [],
      resolvedSources: [],
    };
  }

  const contentParts: ContentPart[] = [];
  let lastIndex = 0;
  const citedSourceIndexes = new Set<number>();
  const numericIdToIndex = new Map<number, number>();

  allSources.forEach((source, index) => {
    const numericId = Number(source.id);
    if (!Number.isNaN(numericId) && !numericIdToIndex.has(numericId)) {
      numericIdToIndex.set(numericId, index);
    }
  });

  // Soporta citas individuales [1], agrupadas [1,2,3] y con espacios [1, 2]
  const citationRegex = /\[(\d+(?:\s*,\s*\d+)*)\]/g;
  let match: RegExpExecArray | null;

  while ((match = citationRegex.exec(textString)) !== null) {
    const fullMatch = match[0];
    const index = match.index!;
    const nums = match[1].split(',').map(s => parseInt(s.trim(), 10)).filter(n => !isNaN(n));

    // Resolver todas las fuentes del grupo
    const resolvedGroup: Array<{ source: Source; citationNumber: number; sourceIndex: number }> = [];
    for (const citationNumber of nums) {
      // Priorizar búsqueda por ID numérico exacto para evitar colisiones/desplazamientos de índice, y usar fallback de posición
      const sourceIndex = numericIdToIndex.has(citationNumber)
        ? numericIdToIndex.get(citationNumber)
        : (citationNumber - 1 < allSources.length ? citationNumber - 1 : undefined);
      const source = sourceIndex !== undefined ? allSources[sourceIndex] : undefined;
      if (source && sourceIndex !== undefined) {
        resolvedGroup.push({ source, citationNumber, sourceIndex });
      }
    }

    if (resolvedGroup.length > 0) {
      if (index > lastIndex) {
        contentParts.push({ type: 'text', content: textString.substring(lastIndex, index) });
      }
      // Emitir cada cita del grupo como su propio ContentPart
      for (const { source, citationNumber, sourceIndex } of resolvedGroup) {
        contentParts.push({ type: 'citation', source, citationNumber });
        citedSourceIndexes.add(sourceIndex);
      }
      lastIndex = index + fullMatch.length;
    }
  }

  // Añadir cualquier texto restante después de la última cita
  if (lastIndex < textString.length) {
    contentParts.push({ type: 'text', content: textString.substring(lastIndex) });
  }

  const resolvedSources = allSources.map((source, index) => ({
    ...source,
    is_cited: citedSourceIndexes.has(index),
  }));

  const citedSources = resolvedSources.filter((source) => source.is_cited);
  const uncitedSources = resolvedSources.filter((source) => !source.is_cited);

  return { contentParts, citedSources, uncitedSources, resolvedSources };
};

// Helper function to collect and deduplicate sources from various message fields
export const collectSourcesFromMessage = (
  sources?: Source[],
  ragContext?: any[]
): { citationSources: Source[], additionalSources: Source[], processedRagContext: any[] } => {
  const normalizedExplicitSources = Array.isArray(sources)
    ? dedupeSources(sources.map((source, index) => normalizeSource(source, index + 1)))
    : [];

  const normalizedRagSources = Array.isArray(ragContext)
    ? dedupeSources(ragContext.map((source, index) => normalizeSource(source, normalizedExplicitSources.length + index + 1)))
    : [];

  // Las citas deben resolverse contra una secuencia estable. Preferimos la lista explícita
  // enviada por el backend y solo usamos ragContext como fallback si no existe.
  const citationSources = normalizedExplicitSources.length > 0
    ? normalizedExplicitSources
    : normalizedRagSources;

  const additionalSources = dedupeSources([
    ...citationSources,
    ...normalizedRagSources,
  ]);

  return {
    citationSources,
    additionalSources,
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

  // 11. Eliminar Emojis (para evitar que el TTS los mencione)
  cleanText = cleanText.replace(/[\p{Emoji_Presentation}\p{Extended_Pictographic}]/gu, '');

  return cleanText.trim();
};
