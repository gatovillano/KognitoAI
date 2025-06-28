// En: src/components/MarkdownRenderer.tsx

'use client';

import { useState, useEffect, useMemo } from 'react';
import { marked } from 'marked';
import { Button } from '@/components/ui/button';
import { Check, Copy } from 'lucide-react';
import { toast } from 'sonner';
// Import Prism for syntax highlighting
import Prism from 'prismjs';
import 'prismjs/themes/prism-tomorrow.css'; // Use a theme suitable for dark mode
import 'prismjs/components/prism-python'; // Include Python language support
import 'prismjs/components/prism-javascript';
import 'prismjs/components/prism-typescript';
import 'prismjs/components/prism-jsx';
import 'prismjs/components/prism-tsx';
import 'prismjs/components/prism-json';
import 'prismjs/components/prism-bash';
import 'prismjs/components/prism-sql';
import 'prismjs/components/prism-java';
import 'prismjs/components/prism-c';
import 'prismjs/components/prism-cpp';
import 'prismjs/components/prism-csharp';
import 'prismjs/components/prism-go';
import 'prismjs/components/prism-kotlin';
import 'prismjs/components/prism-markdown';
import 'prismjs/components/prism-markup-templating';
import 'prismjs/components/prism-php';
import 'prismjs/components/prism-ruby';
import 'prismjs/components/prism-rust';
import 'prismjs/components/prism-swift';
import 'prismjs/components/prism-yaml';

interface MarkdownRendererProps {
  content: string;
}

export function MarkdownRenderer({ content }: MarkdownRendererProps) {
  const [copiedStates, setCopiedStates] = useState<Record<number, boolean>>({});

  // Parse markdown to HTML using marked
  const htmlContent = useMemo(() => {
    try {
      return marked.parse(content, {
        gfm: true, // Enable GitHub Flavored Markdown
        breaks: true, // Convert line breaks to <br>
        async: false // Use synchronous parsing for simplicity
      });
    } catch (error) {
      console.error("Error parsing markdown:", error);
      return "<p>Error rendering content.</p>";
    }
  }, [content]);

  useEffect(() => {
    // Ensure Prism highlights code on component mount and content change
    const highlight = () => {
      try {
        Prism.highlightAll();
      } catch (error) {
        console.error("Error highlighting syntax in content:", error);
        console.error("Problematic content snippet:", content.length > 200 ? content.substring(0, 200) + "..." : content);
      }
    };
    highlight();
    return () => {};
  }, [content]);

  const handleCopy = (text: string, index: number) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopiedStates((prev) => ({ ...prev, [index]: true }));
      toast.success('¡Copiado al portapapeles!');
      setTimeout(() => {
        setCopiedStates((prev) => ({ ...prev, [index]: false }));
      }, 2000);
    }).catch(err => {
      console.error('Error al copiar texto: ', err);
      toast.error('No se pudo copiar el texto.');
    });
  };

  // Function to inject copy buttons into code blocks after DOM rendering
  useEffect(() => {
    const codeBlocks = document.querySelectorAll('pre code');
    codeBlocks.forEach((block, index) => {
      const wrapper = block.parentElement;
      if (wrapper && !wrapper.dataset.copyButtonAdded) {
        const language = block.className.split('-')[1] || 'code';
        const codeText = block.textContent || '';
        const codeBlockIndex = codeText.length > 0 ? codeText.split('').reduce((a, c) => a + c.charCodeAt(0), 0) : index;
        const isCopied = copiedStates[codeBlockIndex];

        // Create header with language and copy button
        const header = document.createElement('div');
        header.className = 'flex items-center justify-between px-4 py-1.5 border-b';
        header.innerHTML = `
          <span class="text-xs text-muted-foreground">${language}</span>
          <button id="copy-btn-${codeBlockIndex}" class="h-7 w-7 inline-flex items-center justify-center bg-transparent border-none cursor-pointer">
            ${isCopied ? '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="rgb(22 101 52)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>' : '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="rgb(142 156 173)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>'}
          </button>
        `;

        wrapper.insertBefore(header, block);
        wrapper.className = 'bg-zinc-900 rounded-md border my-4';
        wrapper.style.backgroundColor = '#2d3748 !important';
        block.parentElement.dataset.copyButtonAdded = 'true';

        const copyBtn = document.getElementById(`copy-btn-${codeBlockIndex}`);
        if (copyBtn) {
          copyBtn.onclick = () => handleCopy(codeText, codeBlockIndex);
        }
      }
    });
  }, [content, copiedStates]);

  return (
    <div className="prose prose-invert prose-sm max-w-none">
      <div dangerouslySetInnerHTML={{ __html: htmlContent }} />
    </div>
  );
};
