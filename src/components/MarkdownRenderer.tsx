// En: src/components/MarkdownRenderer.tsx

'use client';

import { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
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
import 'prismjs/components/prism-php';
import 'prismjs/components/prism-ruby';
import 'prismjs/components/prism-rust';
import 'prismjs/components/prism-swift';
import 'prismjs/components/prism-yaml';

interface MarkdownRendererProps {
  content: string;
}

// --- NUEVA INTERFAZ PARA TIPAR LAS PROPS DEL COMPONENTE 'code' ---
// Heredamos de las props HTML estándar y añadimos 'inline'.
interface CustomCodeProps extends React.HTMLAttributes<HTMLElement> {
    inline?: boolean;
    node?: any; // El tipo 'node' es complejo, lo dejamos como 'any' por simplicidad
}


export function MarkdownRenderer({ content }: MarkdownRendererProps) {
  const [copiedStates, setCopiedStates] = useState<Record<number, boolean>>({});

  useEffect(() => {
    // Ensure Prism highlights code on content change
    try {
      Prism.highlightAll();
    } catch (error) {
      console.error("Error highlighting syntax in content:", error);
      console.error("Problematic content snippet:", content.length > 200 ? content.substring(0, 200) + "..." : content);
    }
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

  return (
    <div className="prose prose-invert prose-sm max-w-none">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeRaw]}
        components={{
          pre: ({ node, children, ...props }) => (
            <div className="relative my-4">{children}</div>
          ),
          // --- APLICAMOS NUESTRO TIPO PERSONALIZADO AQUÍ ---
          code: ({ node, inline, className, children, ...rest }: CustomCodeProps) => {
            const match = /language-(\w+)/.exec(className || '');
            const codeText = String(children).replace(/\n$/, '');
            const codeBlockIndex = Math.random();

            if (!inline && match) {
              const isCopied = copiedStates[codeBlockIndex];
              const language = match[1];
              return (
                <div className="bg-zinc-900 rounded-md border">
                  <div className="flex items-center justify-between px-4 py-1.5 border-b">
                    <span className="text-xs text-muted-foreground">{language}</span>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7"
                      onClick={() => handleCopy(codeText, codeBlockIndex)}
                    >
                      {isCopied ? <Check className="h-4 w-4 text-green-500" /> : <Copy className="h-4 w-4 text-muted-foreground" />}
                    </Button>
                  </div>
                  <pre className="p-4 text-sm overflow-x-auto">
                    <code {...rest} className={`language-${language}`}>{children}</code>
                  </pre>
                </div>
              );
            }
            
            return (
              <code className="bg-zinc-700/50 rounded-sm px-1 py-0.5 text-sm font-mono" {...rest}>
                {children}
              </code>
            );
          }
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
