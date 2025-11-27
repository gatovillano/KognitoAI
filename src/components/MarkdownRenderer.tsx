'use client';

import { useState, useEffect, useRef, useCallback, useMemo, memo } from 'react';
import { marked } from 'marked';
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
import mermaid from 'mermaid'; // Importar mermaid
import { createRoot } from 'react-dom/client';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import MermaidViewer from '@/components/MermaidViewer'; // Importar el nuevo componente
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

    try {
      const renderer = new marked.Renderer();
      renderer.html = function ({ text }) { return text; };
      renderer.code = function ({ text, lang }) {
        if (lang === 'mermaid') {
          return `<div class="mermaid-code-block" data-mermaid-code="${encodeURIComponent(text)}"></div>`;
        }
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
          console.warn(`Language '${language}' not found in Prism, falling back to markup.`);
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
        return `<pre data-language="${language}"><code class="language-${language}">${highlightedCode}</code></pre>`;
      };
      marked.setOptions({ gfm: true, breaks: true, renderer: renderer });

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



  useEffect(() => {

    if (isStreaming) return;



    const hydrateSourceButtons = () => {

      if (!containerRef.current || !contentParts) return;



      const citationMap = new Map(contentParts

        .filter(p => p.type === 'citation' && p.source && p.citationNumber !== undefined)

        .map(p => [p.citationNumber, p.source]));



      const placeholders = Array.from(containerRef.current.querySelectorAll('.source-button-placeholder'));



      placeholders.forEach((placeholder) => {



        // Defer each hydration to a separate macrotask to prevent



        // one component's render (and its side-effects like portals)



        // from interfering with the iteration of the next one.



        setTimeout(() => {



          // Avoid re-hydrating if a root is already attached



          if (placeholder.hasAttribute('data-hydrated')) return;







          const citationNumber = parseInt(placeholder.getAttribute('data-citation-number') || '0', 10);



          const source = citationMap.get(citationNumber);







          if (source) {



            const root = createRoot(placeholder);



            root.render(<SourceButton source={source} citationNumber={citationNumber} />);



            placeholder.setAttribute('data-hydrated', 'true');



          }



        }, 0);



      });

    };



    const setupCodeBlocks = () => {
      if (!containerRef.current) return;
      const codeBlocks = containerRef.current.querySelectorAll('pre code:not([data-buttons-added="true"])');
      codeBlocks.forEach((block, index) => {
        const wrapper = block.parentNode as HTMLPreElement;
        if (!wrapper) return;
        const language = (block.className.split('-')[1] || 'code').toLowerCase();
        const codeText = block.textContent || '';
        const codeBlockIndex = `codeblock-${index}`;

        const footer = document.createElement('div');
        footer.className = 'flex items-center justify-between px-4 py-2 bg-white/5 border-t border-white/10 rounded-b-2xl';
        const languageLabel = document.createElement('span');
        languageLabel.className = 'text-xs font-medium text-muted-foreground uppercase tracking-wide';
        languageLabel.textContent = language;
        const buttonsWrapper = document.createElement('div');
        buttonsWrapper.className = 'flex items-center gap-2';

        if (language === 'html') {
          const previewBtn = document.createElement('button');
          previewBtn.className = 'inline-flex items-center justify-center text-xs font-medium transition-colors hover:bg-white/10 hover:text-white h-7 px-3 rounded-md border border-white/10 bg-transparent mr-2 text-gray-300';
          previewBtn.innerHTML = '👁️ Previsualizar';
          previewBtn.onclick = () => handlePreview(codeText);
          buttonsWrapper.appendChild(previewBtn);
        }

        const copyBtn = document.createElement('button');
        copyBtn.id = `copy-btn-${codeBlockIndex}`;
        copyBtn.className = 'inline-flex items-center justify-center text-xs font-medium transition-colors hover:bg-white/10 hover:text-white h-7 px-3 rounded-md border border-white/10 bg-transparent text-gray-300';
        copyBtn.innerHTML = copiedStates[codeBlockIndex] ? '✓ Copiado' : '📋 Copiar';
        copyBtn.onclick = () => handleCopy(codeText, codeBlockIndex);
        buttonsWrapper.appendChild(copyBtn);

        footer.appendChild(languageLabel);
        footer.appendChild(buttonsWrapper);
        wrapper.appendChild(footer);
        wrapper.className = 'backdrop-blur-md rounded-2xl border border-border/20 bg-[#1e1e1e] my-4 overflow-hidden';
        wrapper.style.backgroundColor = '';
        (block as HTMLElement).style.color = '';
        block.setAttribute('data-buttons-added', 'true');
      });
    };

    const setupMermaidBlocks = () => {
      if (!containerRef.current) return;
      const mermaidCodeBlocks = containerRef.current.querySelectorAll('.mermaid-code-block');
      mermaidCodeBlocks?.forEach(async (block) => {
        const encodedMermaidCode = block.getAttribute('data-mermaid-code');
        if (encodedMermaidCode) {
          const mermaidCode = decodeURIComponent(encodedMermaidCode);
          let staticMermaidSvg = '';
          try {
            const renderId = `mermaid-static-${Math.random().toString(36).substr(2, 9)}`;
            const { svg } = await mermaid.render(renderId, mermaidCode);
            staticMermaidSvg = svg;
          } catch (e) {
            console.error('Error rendering static mermaid diagram:', e);
            staticMermaidSvg = '<div class="text-red-500">Error al renderizar el diagrama.</div>';
          }
          const triggerContainer = document.createElement('div');
          block.parentNode?.insertBefore(triggerContainer, block);
          block.remove();
          const root = createRoot(triggerContainer);
          root.render(
            <MermaidViewer mermaidCode={mermaidCode} trigger={
              <div
                className="mermaid-diagram-trigger cursor-pointer p-4 border rounded-lg bg-muted hover:bg-muted/50 transition-colors"
                dangerouslySetInnerHTML={{ __html: staticMermaidSvg }}
                title="Haz clic para ver el diagrama interactivo"
              />
            } />
          );
        }
      });
    };

    setupCodeBlocks();
    setupMermaidBlocks();
    hydrateSourceButtons();
  }, [contentParts, renderedContent, copiedStates, handleCopy, handlePreview, isStreaming]);

  useEffect(() => {
    mermaid.initialize({
      startOnLoad: false,
      theme: 'dark',
      flowchart: { curve: 'basis' },
      securityLevel: 'loose',
      maxTextSize: 50000,
    });
  }, []);

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
    ? `${fontSize} text-foreground`
    : `${proseSizeClass} max-w-none text-foreground`;

  const ContainerElement = inline ? 'span' : 'div';

  return (
    <ContainerElement className={containerClass} style={{ overflowWrap: 'break-word', margin: 0, padding: 0, ...style }} ref={containerRef} dangerouslySetInnerHTML={{ __html: renderedContent }} />
  );
};

export const MarkdownRenderer = memo(MarkdownRendererComponent);
