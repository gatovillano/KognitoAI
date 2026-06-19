'use client';

import React, { useState, useEffect, useRef, useCallback, useMemo, memo } from 'react';
import { marked } from 'marked';
import { motion } from 'framer-motion';
import { sentImage } from '@/lib/imageUtils';
import { toast } from 'sonner';
import Prism from 'prismjs';
import 'prismjs/themes/prism-okaidia.css';

// Importar lenguajes de programación comunes
import 'prismjs/components/prism-docker';
import 'prismjs/components/prism-javascript';
import 'prismjs/components/prism-typescript';
import 'prismjs/components/prism-python';
import 'prismjs/components/prism-java';
import 'prismjs/components/prism-csharp';
import 'prismjs/components/prism-c';
import 'prismjs/components/prism-cpp';
import 'prismjs/components/prism-php';
import 'prismjs/components/prism-ruby';
import 'prismjs/components/prism-go';
import 'prismjs/components/prism-rust';
import 'prismjs/components/prism-swift';
import 'prismjs/components/prism-kotlin';
import 'prismjs/components/prism-scala';
import 'prismjs/components/prism-sql';
import 'prismjs/components/prism-bash';
import 'prismjs/components/prism-powershell';
import 'prismjs/components/prism-json';
import 'prismjs/components/prism-yaml';
import 'prismjs/components/prism-xml-doc';
import 'prismjs/components/prism-markdown';
import 'prismjs/components/prism-css';
import 'prismjs/components/prism-scss';
import 'prismjs/components/prism-less';
import 'prismjs/components/prism-jsx';
import 'prismjs/components/prism-tsx';
import 'prismjs/components/prism-lua';
import 'prismjs/components/prism-r';
import 'prismjs/components/prism-matlab';
import 'prismjs/components/prism-dart';
import 'prismjs/components/prism-elixir';
import 'prismjs/components/prism-haskell';
import { createRoot } from 'react-dom/client';
import { useAuth } from '@/contexts/AuthContext';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import dynamic from 'next/dynamic';
const MermaidViewer = dynamic(() => import('@/components/MermaidViewer'), {
  ssr: false,
}); // Importar el nuevo componente dinámicamente
const PtyTerminalDynamic = dynamic(() => import('@/components/terminal/PtyTerminalEmbedded'), {
  ssr: false,
});
import { SourceButton, Source, ContentPart } from './SourceButton'; // Importar SourceButton, Source, ContentPart



interface MarkdownRendererProps {
  content?: string; // Hacer opcional, ya que usaremos contentParts
  contentParts?: ContentPart[]; // Nueva prop para las partes del contenido
  fontSize?: string;
  isStreaming?: boolean;
  inline?: boolean;
  style?: React.CSSProperties;
}

const Citation: React.FC<{ source: Source }> = ({ source }) => {
  return (
    <Popover>
      <PopoverTrigger asChild>
        <button className="inline-block align-super text-xs bg-primary/10 text-primary font-bold rounded-full w-4 h-4 mx-0.5 focus:outline-none focus:ring-2 focus:ring-primary/50">
          {source.id}
        </button>
      </PopoverTrigger>
      <PopoverContent className="w-80 text-sm">
        <div className="font-bold mb-2">{source.title}</div>
        <p className="text-muted-foreground">
          {source.snippet}
        </p>
        {source.metadata?.similarity_score && (
          <div className="text-xs text-primary/80 mt-2">
            Relevancia: {Math.round(source.metadata.similarity_score * 100)}%
          </div>
        )}
      </PopoverContent>
    </Popover>
  );
};

const MarkdownRendererComponent = ({ content, contentParts, fontSize, isStreaming = false, inline = false, style }: MarkdownRendererProps) => {
  const [copiedStates, setCopiedStates] = useState<Record<string, boolean>>({});
  const containerRef = useRef<HTMLDivElement>(null);
  const { user, token } = useAuth();

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

  const renderedContent = useMemo(() => {
    const textToProcess = contentParts
      ? contentParts.map(part => part.type === 'text' ? part.content : `[${part.citationNumber}]`).join('')
      : content || '';

    if (!textToProcess) return '';

                try {
                const renderer = new marked.Renderer();
                // Enable raw HTML rendering
                renderer.html = function ({ text }) {
                  return text;
                };
                renderer.link = function ({ href, title, text }) {            const isPdf = href.toLowerCase().endsWith('.pdf');
            if (isPdf) {
              return `<a href="${href}" target="_blank" rel="noopener noreferrer" class="inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-full text-sm font-medium transition-all bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700 text-white shadow-md hover:shadow-lg h-9 px-4 py-2 my-2 no-underline">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-download"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/></svg>
                <span>${text || 'Descargar PDF'}</span>
              </a>`;
            }
            return `<a href="${href}" title="${title || ''}" target="_blank" rel="noopener noreferrer">${text}</a>`;
          };
    
          renderer.image = function ({ href, title, text }) {
            let src = href;
            if (href.startsWith('/tmp/') || href.startsWith('/media/')) {
              const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
              src = `${apiUrl}${href}`;
            }
            return `<img src="${src}" alt="${text || ''}" title="${title || ''}" class="rounded-xl max-w-full my-2 border border-border/20 shadow-sm inline-block" />`;
          };
    
          renderer.code = function ({ text, lang }) {
            if (lang === 'mermaid') {
              return `<div class="mermaid-code-block" data-mermaid-code="${encodeURIComponent(text)}"></div>`;
            }
    
            // --- Mejoras de Resiliencia para HTML Premium (V3) ---
            // Si el agente envía HTML envuelto en un bloque de código (error común), 
            // lo renderizamos directamente si parece contenido visual estructural.
            // Interceptamos aún sin la etiqueta de lenguaje 'html' si es muy evidente.
            const htmlTagsRegex = /<(table|div|p|span|section|h[1-6]|ul|ol|li|img|br|hr|blockquote|a|svg|button)\b/i;
            const tailwindClassesRegex = /(class|className)=["'][^"']*(bg-|text-|border-|flex|grid|p-|m-|rounded|shadow|w-full)[^"']*["']/i;
    
            const isHtmlLang = lang === 'html' || lang === 'xml' || !lang || lang === '';
            const isLikelyPremiumHtml = isHtmlLang &&
              htmlTagsRegex.test(text) &&
              (tailwindClassesRegex.test(text) || text.includes('style="') || text.includes('class="grid') || text.includes('class="flex'));
    
                    if (isLikelyPremiumHtml) {
                      // Devolver el HTML directamente. El contenedor de marked ya maneja el layout.
                      return text;
                    }            // ------------------------------------------------
        let language = lang ? lang.toLowerCase() : 'markup';
        const languageMap: Record<string, string> = {
          'dockerfile': 'docker', 'js': 'javascript', 'ts': 'typescript', 'py': 'python',
          'cs': 'csharp', 'c++': 'cpp', 'sh': 'bash', 'shell': 'bash', 'ps1': 'powershell',
          'yml': 'yaml', 'xml': 'xml-doc', 'html': 'markup', 'md': 'markdown', 'rs': 'rust',
          'rb': 'ruby', 'kt': 'kotlin', 'jl': 'julia', 'vim': 'vim', 'tex': 'latex',
          'r': 'r', 'm': 'matlab', 'markup-templating': 'markup'
        };
        if (language === 'markup-templating') language = 'markup';
        else if (languageMap[language]) language = languageMap[language];

        let prismLanguage = Prism.languages[language];
        if (!prismLanguage) {
          // console.warn(`Language '${language}' not found in Prism, falling back to markup.`);
          prismLanguage = Prism.languages.markup;
          language = 'markup';
        }
        const finalLanguage = prismLanguage || Prism.languages.markup;

        let highlightedCode = text;
        try {
          if (finalLanguage) {
            highlightedCode = Prism.highlight(text, finalLanguage, language);
          }
        } catch (e) { /* Suppress errors */ }
        return `<pre data-language="${language}" style="white-space: pre-wrap; word-break: break-all;"><code class="language-${language}">${highlightedCode}</code></pre>`;
      };

      // Use marked.use() and allow HTML
      marked.use({
        gfm: true,
        breaks: true,
        renderer: renderer,
      });

      // Configure marked to allow HTML
      const parseOptions = {
        async: false,
      };

      let html = marked.parse(textToProcess) as string;

      if (inline) {
        const match = html.match(/^<p>(.*)<\/p>$/s);
        if (match) html = match[1];
      }

      if (!contentParts) {
        return html;
      }

      const citationMap = new Map(contentParts
        .filter(p => p.type === 'citation' && p.source && p.citationNumber !== undefined)
        .map(p => [`[${p.citationNumber}]`, p]));

      const regex = /(\[\d+\])/g;

      // Replace citation markers with placeholder spans
      const finalHtml = html.replace(regex, (match) => {
        const citationPart = citationMap.get(match);
        if (citationPart && citationPart.source) {
          // Render a placeholder span that we will hydrate on the client
          return `<span class="source-button-placeholder" data-citation-number="${citationPart.citationNumber}"></span>`;
        }
        return match;
      });

      return finalHtml; // Return the raw HTML string

    } catch (error: any) {
      console.error("Error parsing markdown:", error);
      return `<p>Error rendering content: ${error.message || error}</p>`;
    }

  }, [content, contentParts, inline]);

  // ... (useEffect hooks remain the same) ...

  const proseSizeClass = useMemo(() => {
    switch (fontSize) {
      case 'text-sm': return 'prose-sm';
      case 'text-base': return 'prose';
      case 'text-lg': return 'prose-lg';
      case 'text-xl': return 'prose-xl';
      case 'text-2xl': return 'prose-2xl';
      default: return 'prose';
    }
  }, [fontSize]);

  const containerClass = inline
    ? `${fontSize} text-foreground premium-html-content`
    : `${proseSizeClass} max-w-none text-foreground dark:prose-invert premium-html-content`; // Added dark:prose-invert

  // Hidratación de placeholders (Citas y Mermaid) con componentes React
  useEffect(() => {
    if (!containerRef.current) return;

    const container = containerRef.current;

    // 1. Citas
    if (contentParts) {
      const citationPlaceholders = container.querySelectorAll('.source-button-placeholder');
      citationPlaceholders.forEach((placeholder) => {
        if (placeholder.getAttribute('data-hydrated') === 'true') return;

        const citationNumber = placeholder.getAttribute('data-citation-number');
        if (!citationNumber) return;

        const citationPart = contentParts.find(part =>
          part.type === 'citation' && part.citationNumber === parseInt(citationNumber)
        );

        if (citationPart && citationPart.source) {
          placeholder.setAttribute('data-hydrated', 'true');
          const sourceButton = React.createElement(SourceButton, {
            source: citationPart.source,
            citationNumber: citationPart.citationNumber || 0
          });
          const reactRoot = createRoot(placeholder);
          reactRoot.render(sourceButton);
        }
      });
    }

    // 2. Mermaid
    const mermaidBlocks = container.querySelectorAll('.mermaid-code-block');
    mermaidBlocks.forEach((block) => {
      if (block.getAttribute('data-hydrated') === 'true') return;

      const encodedCode = block.getAttribute('data-mermaid-code');
      if (!encodedCode) return;

      try {
        const mermaidCode = decodeURIComponent(encodedCode);
        block.setAttribute('data-hydrated', 'true');

        const mermaidViewer = React.createElement(MermaidViewer, {
          mermaidCode: mermaidCode
        });

        const reactRoot = createRoot(block);
        reactRoot.render(mermaidViewer);
      } catch (e) {
        console.error("Error hydrating mermaid block:", e);
      }
    });

    // 3. PTY placeholders
    const ptyPlaceholders = container.querySelectorAll('.pty-session-placeholder');
    ptyPlaceholders.forEach((placeholder) => {
      if (placeholder.getAttribute('data-hydrated') === 'true') return;
      const cmd = placeholder.getAttribute('data-cmd') || '';
      const sessionId = placeholder.getAttribute('data-session-id') || '';
      placeholder.setAttribute('data-hydrated', 'true');

      try {
        const ptyElement = React.createElement(PtyTerminalDynamic, {
          accountId: (user?.account_id || user?.id) as string || '',
          token: token || '',
          apiBaseUrl: process.env.NEXT_PUBLIC_API_URL || (typeof window !== 'undefined' ? window.location.origin : ''),
          sessionId: sessionId,
          initialCommand: cmd,
          className: 'h-[260px]'
        });
        const reactRoot = createRoot(placeholder);
        reactRoot.render(ptyElement);
      } catch (e) {
        console.error('Error hydrating PTY placeholder:', e);
      }
    });
  }, [contentParts, renderedContent, user?.id, user?.account_id, token]);


  const MotionContainer = inline ? (motion.span as any) : (motion.div as any);

  return (
    <MotionContainer
      className={containerClass}
      style={{ overflowWrap: 'break-word', margin: 0, padding: 0, ...style }}
      ref={containerRef}
      dangerouslySetInnerHTML={{ __html: renderedContent }}
    />
  );
};

export const MarkdownRenderer = memo(MarkdownRendererComponent);
