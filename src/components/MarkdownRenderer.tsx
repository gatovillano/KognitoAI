'use client';

import { useState, useEffect, useRef, useCallback, useMemo, memo } from 'react';
import { marked } from 'marked';
import { sentImage } from '@/lib/imageUtils';
import { toast } from 'sonner';
import Prism from 'prismjs';
import 'prismjs/themes/prism-tomorrow.css';

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
        let language = lang ? lang.toLowerCase() : 'markup';
        
        // Mapeo de alias de lenguajes para mayor compatibilidad
        const languageMap: Record<string, string> = {
          'dockerfile': 'docker',
          'js': 'javascript',
          'ts': 'typescript',
          'py': 'python',
          'cs': 'csharp',
          'c++': 'cpp',
          'sh': 'bash',
          'shell': 'bash',
          'ps1': 'powershell',
          'yml': 'yaml',
          'xml': 'xml-doc',
          'html': 'markup',
          'md': 'markdown',
          'rs': 'rust',
          'rb': 'ruby',
          'kt': 'kotlin',
          'jl': 'julia',
          'vim': 'vim',
          'tex': 'latex',
          'r': 'r',
          'm': 'matlab',
          'markup-templating': 'markup'
        };
        
        // Aplicar mapeo si existe, con especial atención a markup-templating
        if (language === 'markup-templating') {
          language = 'markup';
        } else if (languageMap[language]) {
          language = languageMap[language];
        }
        
        // Verificar si el lenguaje está disponible en Prism
        let prismLanguage = Prism.languages[language];
        if (!prismLanguage) {
          console.warn(`Language '${language}' not found in Prism, falling back to markup.`);
          prismLanguage = Prism.languages.markup;
          language = 'markup'; // Actualizar el lenguaje para la clase CSS
        }
        // Asegurarse de que siempre se use un lenguaje válido
        const finalLanguage = prismLanguage || Prism.languages.markup;
        
        // Evitar cualquier error al resaltar el código
        let highlightedCode = text;
        try {
          if (finalLanguage) {
            highlightedCode = Prism.highlight(text, finalLanguage, language);
          }
        } catch (e) {
          // No mostrar errores en la consola para evitar molestar al usuario
        }
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
        copyBtn.className = 'inline-flex items-center justify-center text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-ring focus-visible:ring-offset-4 disabled:pointer-events-none disabled:opacity-50 border border-input bg-background hover:bg-accent hover:text-accent-foreground h-7 px-5 rounded-md';
        copyBtn.innerHTML = copiedStates[codeBlockIndex] ? 'Copiado' : 'Copiar';
        copyBtn.onclick = () => handleCopy(codeText, codeBlockIndex);
        buttonsWrapper.appendChild(copyBtn);

        footer.appendChild(buttonsWrapper);
        wrapper.appendChild(footer);

        wrapper.className = 'backdrop-blur-md rounded-3xl'; // Bordes más curvos con rounded-3xl
        wrapper.style.backgroundColor = '#111213 !important';
        (block as HTMLElement).style.color = '#ffffff !important'; // Asegura que el texto sea blanco para contrastar con el fondo negro
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
