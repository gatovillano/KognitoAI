'use client';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface InlineMarkdownRendererProps {
  content: string;
}

export function InlineMarkdownRenderer({ content }: InlineMarkdownRendererProps) {
  // Asegurarse de que el contenido sea una cadena de texto para evitar errores en ReactMarkdown
  const markdownContent = typeof content === 'string' ? content : '';

  // Función para sanitizar el contenido Markdown y eliminar enlaces anidados
  const sanitizeMarkdown = (markdown: string): string => {
    // Expresión regular para encontrar enlaces anidados
    const nestedLinkRegex = /\[([^\]]+)\]\(([^\)]+)\)\[([^\]]+)\]\(([^\)]+)\)/g;
    // Reemplazar enlaces anidados con el primer enlace
    return markdown.replace(nestedLinkRegex, '[$1]($2)');
  };

  const sanitizedContent = sanitizeMarkdown(markdownContent);

  return (
    <ReactMarkdown
      // Lista de elementos de bloque que NO queremos que se rendericen.
      // Esto fuerza a que solo se apliquen formatos como <strong>, <em>, etc.
      disallowedElements={['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'pre', 'blockquote', 'table', 'thead', 'tbody', 'tr', 'td', 'th']}
      // Esta prop es crucial: le dice a la librería que, en lugar de ocultar el contenido
      // de un elemento no permitido (como un <p>), simplemente renderice el texto sin la etiqueta.
      unwrapDisallowed={true}
      remarkPlugins={[remarkGfm]}
      components={{
        a: ({ node, ...props }) => {
          // Evitar enlaces anidados
          return <span {...props} />;
        },
      }}
    >
      {sanitizedContent}
    </ReactMarkdown>
  );
}
