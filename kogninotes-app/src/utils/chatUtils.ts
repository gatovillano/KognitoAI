// src/utils/chatUtils.ts
export interface Source {
  id: number | string;
  title: string;
  url: string;
  snippet: string;
  type: 'web' | 'document' | 'memory' | 'code' | 'database' | 'graph' | 'note' | 'github';
  metadata?: Record<string, any>;
  name?: string;
  is_cited?: boolean;
}

// Helper function to collect and deduplicate sources from various message fields
export const collectSourcesFromMessage = (
  sources?: any[],
  ragContext?: any[]
): { additionalSources: Source[] } => {
  const additionalSourcesToDisplay: Source[] = [];
  const seenSourceIdentifiers = new Set<string>();

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
      type: detectedType as any,
      metadata: metadata,
      name: rawSource.name || rawSource.title || 'Fuente'
    };
  };

  // Helper para añadir fuentes y evitar duplicados
  const addSourceToDisplay = (source: Source) => {
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
    additionalSources: additionalSourcesToDisplay
  };
};
