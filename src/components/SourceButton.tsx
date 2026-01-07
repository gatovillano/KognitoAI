import React from 'react';
import { ExternalLink, File as FileIcon, Share2, NotebookText } from 'lucide-react';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { InlineMarkdownRenderer } from './InlineMarkdownRenderer';

export interface Source {
  id: number | string;
  title: string;
  url: string;
  snippet: string;
  type: 'web' | 'document' | 'memory' | 'code' | 'database' | 'graph' | 'note';
  metadata?: Record<string, any>;
  name?: string;
}

export interface ContentPart {
  type: 'text' | 'citation';
  content?: string;
  source?: Source;
  citationNumber?: number;
}

export const SourceButton: React.FC<{ source: Source; citationNumber: number; onSourceClick?: (source: Source) => void }> = ({ source, citationNumber, onSourceClick }) => {
  const getTypeStyles = () => {
    switch (source.type) {
      case 'web':
        return {
          icon: <ExternalLink className="h-3.5 w-3.5 mr-1" />,
          color: 'bg-blue-500/15 text-blue-600 dark:text-blue-400 border-blue-300/50 shadow-[0_0_10px_-3px_rgba(59,130,246,0.3)]',
          label: 'Web'
        };
      case 'document':
        return {
          icon: <FileIcon className="h-3.5 w-3.5 mr-1" />,
          color: 'bg-orange-500/15 text-orange-600 dark:text-orange-400 border-orange-300/50 shadow-[0_0_10px_-3px_rgba(249,115,22,0.3)]',
          label: 'Documento'
        };
      case 'memory':
        return {
          icon: <svg className="h-3.5 w-3.5 mr-1" fill="currentColor" viewBox="0 0 20 20"><path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>,
          color: 'bg-purple-500/15 text-purple-600 dark:text-purple-400 border-purple-300/50 shadow-[0_0_10px_-3px_rgba(168,85,247,0.3)]',
          label: 'Memoria'
        };
      case 'code':
        return {
          icon: <svg className="h-3.5 w-3.5 mr-1" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M12.316 3.051a1 1 0 01.633 1.265l-4 12a1 1 0 11-1.898-.632l4-12a1 1 0 011.265-.633zM5.707 6.293a1 1 0 010 1.414L3.414 10l2.293 2.293a1 1 0 11-1.414 1.414l-3-3a1 1 0 010-1.414l3-3a1 1 0 011.414 0zm8.586 0a1 1 0 011.414 0l3 3a1 1 0 010 1.414l-3 3a1 1 0 11-1.414-1.414L16.586 10l-2.293-2.293a1 1 0 010-1.414z" clipRule="evenodd" /></svg>,
          color: 'bg-slate-500/15 text-slate-600 dark:text-slate-400 border-slate-300/50 shadow-[0_0_10px_-3px_rgba(100,116,139,0.3)]',
          label: 'Código'
        };
      case 'database':
        return {
          icon: <svg className="h-3.5 w-3.5 mr-1" fill="currentColor" viewBox="0 0 20 20"><path d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zM3 10a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H4a1 1 0 01-1-1v-6zM14 9a1 1 0 00-1 1v6a1 1 0 001 1h2a1 1 0 001-1v-6a1 1 0 00-1-1h-2z" /></svg>,
          color: 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-300/50 shadow-[0_0_10px_-3px_rgba(16,185,129,0.3)]',
          label: 'Base de Datos'
        };
      case 'graph':
        return {
          icon: <Share2 className="h-3.5 w-3.5 mr-1" />,
          color: 'bg-cyan-500/15 text-cyan-600 dark:text-cyan-400 border-cyan-300/50 shadow-[0_0_10px_-3px_rgba(6,182,212,0.3)]',
          label: 'Grafo'
        };
      case 'note':
        return {
          icon: <NotebookText className="h-3.5 w-3.5 mr-1" />,
          color: 'bg-yellow-500/15 text-yellow-600 dark:text-yellow-400 border-yellow-300/50 shadow-[0_0_10px_-3px_rgba(234,179,8,0.3)]',
          label: 'Nota'
        };
      default:
        return {
          icon: <FileIcon className="h-3 w-3 mr-1" />,
          color: 'bg-primary/10 text-primary border-primary/20',
          label: 'Fuente'
        };
    }
  };

  const { icon, color, label } = getTypeStyles();

  const getButtonContent = () => {
    const commonClasses = `inline-flex items-center text-[10px] font-bold rounded-full px-2 py-0.5 mx-0.5 border transition-all hover:scale-105 active:scale-95 focus:outline-none focus:ring-2 focus:ring-primary/50 leading-none flex-shrink-0 relative top-[-0.1em] ${color}`;

    if (source.type === 'web') {
      return (
        <a
          href={source.url}
          target="_blank"
          rel="noopener noreferrer"
          className={commonClasses}
          title={`Fuente Web: ${source.title}`}
        >
          {icon}
          {citationNumber}
        </a>
      );
    }

    return (
      <Popover>
        <PopoverTrigger asChild>
          <button className={commonClasses} title={`${label}: ${source.title}`}>
            {icon}
            {citationNumber}
          </button>
        </PopoverTrigger>
        <PopoverContent className="max-w-lg p-0 overflow-hidden shadow-2xl border-border/40 backdrop-blur-xl bg-background/95 rounded-xl">
          <div className={`p-4 border-b border-border/10 ${color.split(' ')[0]}`}>
            <div className="flex items-center gap-3">
              <div className={`p-2 rounded-xl bg-background/50 shadow-sm border border-white/10`}>
                {React.isValidElement(icon) ? React.cloneElement(icon as React.ReactElement<any>, { className: "h-5 w-5" }) : icon}
              </div>
              <div className="flex flex-col">
                <div className="font-black text-base leading-tight break-words tracking-tight">{source.title}</div>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="text-[10px] uppercase tracking-widest font-black opacity-70">{label}</span>
                  {source.id && <span className="text-[10px] font-mono opacity-40">#ID-{source.id}</span>}
                </div>
              </div>
            </div>
          </div>

          <div className="p-4 space-y-4">

            {source.metadata?.topic && (
              <div className="text-[10px] font-bold bg-muted px-2 py-0.5 rounded-md w-fit mb-3 text-muted-foreground">
                COLECCIÓN: {source.metadata.topic}
              </div>
            )}

            <div className="relative group">
              <div className="absolute -left-4 top-0 bottom-0 w-1 bg-primary/30 rounded-full transition-all group-hover:bg-primary/60" />
              <div className="text-sm text-muted-foreground leading-relaxed font-medium">
                <InlineMarkdownRenderer content={source.snippet} />
              </div>
            </div>

            {source.metadata?.similarity_score && (
              <div className="flex items-center gap-2 mt-4 pt-3 border-t border-border/10">
                <div className="h-1.5 flex-1 bg-muted rounded-full overflow-hidden">
                  <div
                    className="h-full bg-primary transition-all duration-1000"
                    style={{ width: `${Math.round(source.metadata.similarity_score * 100)}%` }}
                  />
                </div>
                <span className="text-[10px] font-bold text-primary whitespace-nowrap">
                  {Math.round(source.metadata.similarity_score * 100)}% Relevancia
                </span>
              </div>
            )}

            {source.url && (
              <div className="mt-4 pt-3 border-t border-border/10">
                <div className="text-[9px] font-black text-muted-foreground uppercase tracking-widest mb-1">Origen</div>
                <div className="text-[10px] break-all opacity-80">
                  {source.type === 'note' && source.url.startsWith('note://') ? (
                    <a href={`/notes/${source.url.replace('note://', '')}`} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline font-bold">
                      Abrir Nota: {source.title}
                    </a>
                  ) : source.type === 'graph' && source.url.startsWith('graph://') ? (
                    <a href={`/graphs/${source.url.replace('graph://', '')}`} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline font-bold">
                      Ver en Grafo: {source.title}
                    </a>
                  ) : source.type === 'graph' && source.url.startsWith('analysis://') ? (
                    <button
                      onClick={() => onSourceClick && onSourceClick(source)}
                      className="text-primary hover:underline font-bold text-left"
                    >
                      Ver Insight: {source.title}
                    </button>
                  ) : (
                    <span className="font-mono">{source.url}</span>
                  )}
                </div>
              </div>
            )}
          </div>
        </PopoverContent>
      </Popover >
    );
  };

  return getButtonContent();
};