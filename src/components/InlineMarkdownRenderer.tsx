'use client';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface InlineMarkdownRendererProps {
  content: string;
}

export function InlineMarkdownRenderer({ content }: InlineMarkdownRendererProps) {
  return (
    <ReactMarkdown
      // Lista de elementos de bloque que NO queremos que se rendericen.
      // Esto fuerza a que solo se apliquen formatos como <strong>, <em>, etc.
      disallowedElements={['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'pre', 'blockquote']}
      // Esta prop es crucial: le dice a la librería que, en lugar de ocultar el contenido
      // de un elemento no permitido (como un <p>), simplemente renderice el texto sin la etiqueta.
      unwrapDisallowed={true}
      remarkPlugins={[remarkGfm]}
    >
      {content}
    </ReactMarkdown>
  );
}
