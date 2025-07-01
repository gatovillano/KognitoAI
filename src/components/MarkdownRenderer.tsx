// En: src/components/MarkdownRenderer.tsx

'use client';

import { useState, useEffect, useRef, useCallback, useMemo, memo } from 'react';
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

const _MarkdownRenderer = ({ content, fontSize = 'text-base' }: MarkdownRendererProps) => {
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

  const handlePreview = useCallback((htmlContent: string) => {
    if (!htmlContent.trim()) {
      toast.error('El contenido HTML está vacío. No hay nada que previsualizar.');
      return;
    }
    const previewWindow = window.open('', '_blank');
    if (previewWindow) {
      previewWindow.document.open();
      previewWindow.document.write('<!DOCTYPE html><html><head><title>Previsualización HTML</title></head><body>');
      previewWindow.document.write(htmlContent);
      previewWindow.document.write('</body></html>');
      previewWindow.document.close();
    } else {
      toast.error('No se pudo abrir la ventana de previsualización. Por favor, habilite las ventanas emergentes en su navegador.');
    }
  }, []);

  // Effect to add copy and preview buttons
  useEffect(() => {
    const addButtons = () => {
      if (!containerRef.current) return;

      const codeBlocks = containerRef.current.querySelectorAll('pre code:not([data-buttons-added="true"])');

      codeBlocks.forEach((block, index) => {
        const wrapper = block.parentNode as HTMLPreElement;
        if (!wrapper) return;

        const language = (block.className.split('-')[1] || 'code').toLowerCase();
        const codeText = block.textContent || '';
        const codeBlockIndex = `codeblock-${index}`;

        // Create footer with buttons
        const footer = document.createElement('div');
        footer.className = 'flex items-center justify-end px-4 py-1.5 border-t';
        
        const buttonsWrapper = document.createElement('div');
        buttonsWrapper.className = 'flex items-center gap-2';

        // Preview Button
        if (language === 'html') {
          const previewBtn = document.createElement('button');
          previewBtn.className = 'inline-flex items-center justify-center text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 border border-input bg-background hover:bg-accent hover:text-accent-foreground h-7 px-3 rounded-md';
          previewBtn.innerHTML = 'Previsualizar';
          previewBtn.onclick = () => handlePreview(codeText);
          buttonsWrapper.appendChild(previewBtn);
        }

        // Copy Button
        const copyBtn = document.createElement('button');
        copyBtn.id = `copy-btn-${codeBlockIndex}`;
        copyBtn.className = 'inline-flex items-center justify-center text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 border border-input bg-background hover:bg-accent hover:text-accent-foreground h-7 px-3 rounded-md';
        copyBtn.innerHTML = copiedStates[codeBlockIndex] ? 'Copiado' : 'Copiar';
        copyBtn.onclick = () => handleCopy(codeText, codeBlockIndex);
        buttonsWrapper.appendChild(copyBtn);

        footer.appendChild(buttonsWrapper);
        wrapper.appendChild(footer);
        
        wrapper.className = 'bg-zinc-900 rounded-md border my-4';
        wrapper.style.backgroundColor = '#2d3748 !important';
        block.setAttribute('data-buttons-added', 'true');
      });
    };

    addButtons();
  }, [htmlContent, copiedStates, handleCopy, handlePreview]);

  return (
    <div className={`prose prose-sm max-w-none ${fontSize} text-foreground`} style={{ overflowWrap: 'break-word', margin: 0, padding: 0 }} ref={containerRef}>
      <div dangerouslySetInnerHTML={{ __html: htmlContent }} style={{ overflowWrap: 'break-word', margin: 0, padding: 0 }} />
    </div>
  );
};

export const MarkdownRenderer = memo(_MarkdownRenderer);
