// En: src/components/MarkdownRenderer.tsx

'use client';

import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { marked } from 'marked';
import { sentImage } from '@/lib/imageUtils';
import { toast } from 'sonner';
import Prism from 'prismjs';
import 'prismjs/themes/prism-tomorrow.css';
import 'prismjs/components/prism-docker'; // Importar el lenguaje Docker

interface MarkdownRendererProps {
  content: string;
  fontSize?: string;
}

export function MarkdownRenderer({ content, fontSize = 'text-base' }: MarkdownRendererProps) {
  const [copiedStates, setCopiedStates] = useState<Record<string, boolean>>({});
  const containerRef = useRef<HTMLDivElement>(null);

  // Memoize the HTML content generation
  const htmlContent = useMemo(() => {
    try {
      // Configure marked with a custom highlighter
      const renderer = new marked.Renderer();
      renderer.code = function({ text, lang }) {
        let language = lang || 'markup';
        // Mapear 'dockerfile' a 'docker' para Prism.js
        if (language === 'dockerfile') {
          language = 'docker';
        }
        const highlightedCode = Prism.highlight(text, Prism.languages[language] || Prism.languages.markup, language);
        return `<pre><code class="language-${language}">${highlightedCode}</code></pre>`;
      };
      marked.setOptions({
        gfm: true,
        breaks: true,
        renderer: renderer
      });

      // Custom processing to handle base64 image strings
      const processedContent = content.replace(
        /!\[([^\]]*)\]\((data:image\/[a-zA-Z]+;base64,[^\)]+)\)/g,
        (match, altText, src) => {
          return `![${altText}](${src})`;
        }
      ).replace(
        /!\[([^\]]*)\]\(([^)]+)\)/g,
        (match, altText, src) => {
          if (src.startsWith('data:image') || src.startsWith('http')) {
            return match;
          }
          return `![${altText}](${sentImage(src)})`;
        }
      );

      return marked.parse(processedContent, { async: false });
    } catch (error) {
      console.error("Error parsing markdown:", error);
      return "<p>Error rendering content.</p>";
    }
  }, [content]);

  // Handle copy functionality using useCallback
  const handleCopy = useCallback((text: string, index: string) => {
    navigator.clipboard.writeText(text)
      .then(() => {
        setCopiedStates(prev => ({ ...prev, [index]: true }));
        toast.success('¡Copiado al portapapeles!');
        setTimeout(() => {
          setCopiedStates(prev => ({ ...prev, [index]: false }));
        }, 2000);
      })
      .catch(err => {
        console.error('Error al copiar texto: ', err);
        toast.error('No se pudo copiar el texto.');
      });
  }, []);

  // Effect to add copy buttons
  useEffect(() => {
    const addCopyButtons = () => {
      if (!containerRef.current) return;

      const codeBlocks = containerRef.current.querySelectorAll('pre code:not([data-copy-button-added="true"])');

      codeBlocks.forEach((block, index) => {
        const wrapper = block.parentNode as HTMLPreElement;
        if (!wrapper) return;

        const language = block.className.split('-')[1] || 'code';
        const codeText = block.textContent || '';
        const codeBlockIndex = `codeblock-${index}`; // Unique index for each code block

        // Create header with language and copy button
        const header = document.createElement('div');
        header.className = 'flex items-center justify-between px-4 py-1.5 border-b';
        header.innerHTML = `
          <span class="text-xs text-muted-foreground">${language}</span>
          <button id="copy-btn-${codeBlockIndex}" class="h-7 w-7 inline-flex items-center justify-center bg-transparent border-none cursor-pointer">
            ${copiedStates[codeBlockIndex] ? '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="rgb(22 101 52)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>' : '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="rgb(142 156 173)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>'}
          </button>
        `;

        wrapper.insertBefore(header, block);
        wrapper.className = 'bg-zinc-900 rounded-md border my-4';
        wrapper.style.backgroundColor = '#2d3748 !important';
        block.setAttribute('data-copy-button-added', 'true');

        const copyBtn = header.querySelector('button');
        if (copyBtn) {
          copyBtn.onclick = () => handleCopy(codeText, codeBlockIndex);
        }
      });
    };

    addCopyButtons();
  }, [htmlContent, copiedStates, handleCopy]);

  return (
    <div className={`prose prose-sm max-w-none ${fontSize} text-foreground`} style={{ overflowWrap: 'break-word', margin: 0, padding: 0 }} ref={containerRef}>
      <div dangerouslySetInnerHTML={{ __html: htmlContent }} style={{ overflowWrap: 'break-word', margin: 0, padding: 0 }} />
    </div>
  );
}
