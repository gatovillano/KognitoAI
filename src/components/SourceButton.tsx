import React from 'react';
import { ExternalLink, File as FileIcon, Share2, NotebookText, Github, BookOpen } from 'lucide-react';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { InlineMarkdownRenderer } from './InlineMarkdownRenderer';

/** Genera una URL con Text Fragment (#:~:text=) para anclar al snippet exacto */
function getTextFragmentUrl(url: string, snippet: string): string {
  if (!url || !snippet) return url;
  const words = snippet.trim().replace(/\s+/g, ' ').split(' ').filter(w => w.length > 1);
  if (words.length === 0) return url;
  const clean = (w: string) => encodeURIComponent(w.replace(/[^\w]/g, ''));
  const first = clean(words[0]);
  const last = words.length > 1 ? clean(words[words.length - 1]) : '';
  const fragment = last ? `${first},${last}` : first;
  return fragment ? `${url}#:~:text=${fragment}` : url;
}

function getRelevanceStyle(score: number): { badge: string; label: string } {
  if (score >= 0.8) return { badge: 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300', label: `${Math.round(score * 100)}%` };
  if (score >= 0.6) return { badge: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-300', label: `${Math.round(score * 100)}%` };
  if (score >= 0.4) return { badge: 'bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-300', label: `${Math.round(score * 100)}%` };
  return { badge: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300', label: `${Math.round(score * 100)}%` };
}

export interface Source {
  id: number | string;
  title: string;
  url: string;
  snippet: string;
  type: 'web' | 'document' | 'memory' | 'code' | 'database' | 'graph' | 'note' | 'github';
  metadata?: Record<string, any>;
  name?: string;
  is_cited?: boolean;
}

export interface ContentPart {
  type: 'text' | 'citation';
  content?: string;
  source?: Source;
  citationNumber?: number;
}

export const SourceButton: React.FC<{
  source: Source;
  citationNumber: number;
  onSourceClick?: (source: Source) => void;
  showTitle?: boolean;
}> = ({ source, citationNumber, onSourceClick, showTitle = false }) => {
  const getTypeStyles = () => {
    switch (source.type) {
      case 'web':
        return {
          icon: <ExternalLink className="h-3 w-3 mr-1" />,
          color: 'bg-blue-500/15 text-blue-600 dark:text-blue-400 border-blue-300/50 shadow-[0_0_10px_-3px_rgba(59,130,246,0.3)]',
          label: 'Web'
        };
      case 'document':
        return {
          icon: <FileIcon className="h-3 w-3 mr-1" />,
          color: 'bg-orange-500/15 text-orange-600 dark:text-orange-400 border-orange-300/50 shadow-[0_0_10px_-3px_rgba(249,115,22,0.3)]',
          label: 'Documento'
        };
      case 'memory':
        return {
          icon: <svg className="h-3 w-3 mr-1" fill="currentColor" viewBox="0 0 20 20"><path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>,
          color: 'bg-purple-500/15 text-purple-600 dark:text-purple-400 border-purple-300/50 shadow-[0_0_10px_-3px_rgba(168,85,247,0.3)]',
          label: 'Memoria'
        };
      case 'code':
        return {
          icon: <svg className="h-3 w-3 mr-1" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M12.316 3.051a1 1 0 01.633 1.265l-4 12a1 1 0 11-1.898-.632l4-12a1 1 0 011.265-.633zM5.707 6.293a1 1 0 010 1.414L3.414 10l2.293 2.293a1 1 0 11-1.414 1.414l-3-3a1 1 0 010-1.414l3-3a1 1 0 011.414 0zm8.586 0a1 1 0 011.414 0l3 3a1 1 0 010 1.414l-3 3a1 1 0 11-1.414-1.414L16.586 10l-2.293-2.293a1 1 0 010-1.414z" clipRule="evenodd" /></svg>,
          color: 'bg-slate-500/15 text-slate-600 dark:text-slate-400 border-slate-300/50 shadow-[0_0_10px_-3px_rgba(100,116,139,0.3)]',
          label: 'Código'
        };
      case 'database':
        return {
          icon: <svg className="h-3 w-3 mr-1" fill="currentColor" viewBox="0 0 20 20"><path d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zM3 10a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H4a1 1 0 01-1-1v-6zM14 9a1 1 0 00-1 1v6a1 1 0 001 1h2a1 1 0 001-1v-6a1 1 0 00-1-1h-2z" /></svg>,
          color: 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-300/50 shadow-[0_0_10px_-3px_rgba(16,185,129,0.3)]',
          label: 'Base de Datos'
        };
      case 'graph':
        return {
          icon: <Share2 className="h-3 w-3 mr-1" />,
          color: 'bg-cyan-500/15 text-cyan-600 dark:text-cyan-400 border-cyan-300/50 shadow-[0_0_10px_-3px_rgba(6,182,212,0.3)]',
          label: 'Grafo'
        };
      case 'note':
        return {
          icon: <NotebookText className="h-3 w-3 mr-1" />,
          color: 'bg-yellow-500/15 text-yellow-600 dark:text-yellow-400 border-yellow-300/50 shadow-[0_0_10px_-3px_rgba(234,179,8,0.3)]',
          label: 'Nota'
        };
      case 'github':
        return {
          icon: <Github className="h-3 w-3 mr-1" />,
          color: 'bg-indigo-500/15 text-indigo-600 dark:text-indigo-400 border-indigo-300/50 shadow-[0_0_10px_-3px_rgba(99,102,241,0.3)]',
          label: 'GitHub'
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

  const score = source.metadata?.similarity_score as number | undefined;
  const relevance = score != null ? getRelevanceStyle(score) : null;

  const commonClasses = `inline-flex items-center text-[10px] sm:text-[11px] font-bold rounded-full px-2 py-0.5 mx-0.5 border transition-all hover:scale-105 active:scale-95 focus:outline-none focus:ring-2 focus:ring-primary/50 leading-none flex-shrink-0 relative top-[-0.1em] shadow-sm h-5 ${color}`;

  const popoverContent = (
    <PopoverContent className="max-w-lg p-0 overflow-hidden shadow-2xl border-border/40 backdrop-blur-xl bg-background/95 rounded-xl max-h-[400px] overflow-y-auto">
      <div className={`p-4 border-b border-border/10 ${color.split(' ')[0]}`}>
        <div className="flex items-center gap-3">
          {source.type === 'web' ? (
            <img
              src={`https://www.google.com/s2/favicons?sz=32&domain=${source.url}`}
              alt=""
              className="w-8 h-8 rounded-lg border border-border/20"
              onError={e => { (e.target as HTMLImageElement).style.display = 'none'; }}
            />
          ) : (
            <div className="p-2 rounded-xl bg-background/50 shadow-sm border border-white/10">
              {React.isValidElement(icon) ? React.cloneElement(icon as React.ReactElement<any>, { className: 'h-5 w-5' }) : icon}
            </div>
          )}
          <div className="flex flex-col flex-1 min-w-0">
            <div className="font-black text-base leading-tight break-words tracking-tight">{source.title}</div>
            <div className="flex items-center gap-2 mt-0.5 flex-wrap">
              <span className="text-[10px] uppercase tracking-widest font-black opacity-70">{label}</span>
              {source.metadata?.page != null && (
                <span className="inline-flex items-center gap-0.5 text-[10px] text-muted-foreground">
                  <BookOpen className="h-2.5 w-2.5" /> p.{Number(source.metadata.page) + 1}
                </span>
              )}
              {relevance && (
                <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${relevance.badge}`}>
                  {relevance.label}
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="p-4 space-y-4">
        {source.metadata?.topic && (
          <div className="text-[10px] font-bold bg-muted px-2 py-0.5 rounded-md w-fit text-muted-foreground">
            COLECCIÓN: {source.metadata.topic}
          </div>
        )}

        {source.snippet && (
          <div className="relative group">
            <div className="absolute -left-4 top-0 bottom-0 w-1 bg-primary/30 rounded-full transition-all group-hover:bg-primary/60" />
            <div className="text-sm text-muted-foreground leading-relaxed font-medium">
              <InlineMarkdownRenderer content={source.snippet} />
            </div>
          </div>
        )}

        {relevance && (
          <div className="flex items-center gap-2 pt-3 border-t border-border/10">
            <div className="h-1.5 flex-1 bg-muted rounded-full overflow-hidden">
              <div
                className="h-full bg-primary transition-all duration-700"
                style={{ width: `${Math.round(score! * 100)}%` }}
              />
            </div>
            <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${relevance.badge}`}>
              {relevance.label} relevancia
            </span>
          </div>
        )}

        {source.url && (
          <div className="pt-3 border-t border-border/10">
            <div className="text-[9px] font-black text-muted-foreground uppercase tracking-widest mb-1">Origen</div>
            <div className="text-[10px] break-all opacity-80">
              {source.type === 'web' ? (
                <a
                  href={getTextFragmentUrl(source.url, source.snippet)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary hover:underline font-bold break-all"
                >
                  {source.url}
                </a>
              ) : source.type === 'note' && source.url.startsWith('note://') ? (
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
              ) : source.type === 'github' ? (
                <a href={source.url} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline font-bold break-all">
                  {source.url}
                </a>
              ) : (
                <span className="font-mono">{source.url}</span>
              )}
            </div>
          </div>
        )}
      </div>
    </PopoverContent>
  );

  if (showTitle) {
    const badgeClasses = `inline-flex items-center text-[10px] sm:text-[11px] font-bold rounded-full px-2 py-0.5 border leading-none flex-shrink-0 shadow-sm h-5 ${color}`;
    return (
      <Popover>
        <PopoverTrigger asChild>
          <div
            role="button"
            tabIndex={0}
            className="flex items-center gap-2 text-left text-xs font-medium p-1.5 rounded-lg border border-border/40 hover:border-border/80 bg-muted/20 hover:bg-muted/50 cursor-pointer w-full max-w-full transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary/20 group/source-item animate-in fade-in-50 duration-200"
          >
            <span className={badgeClasses}>
              {source.type === 'web' ? (
                <img
                  src={`https://www.google.com/s2/favicons?sz=16&domain=${source.url}`}
                  alt=""
                  className="w-3 h-3 rounded-sm mr-1"
                  onError={e => { (e.target as HTMLImageElement).style.display = 'none'; }}
                />
              ) : (
                icon
              )}
              {citationNumber}
            </span>
            <span className="truncate text-[11px] text-muted-foreground group-hover/source-item:text-foreground transition-colors flex-1 pr-1 font-medium">
              {source.title || source.name || 'Sin título'}
            </span>
          </div>
        </PopoverTrigger>
        {popoverContent}
      </Popover>
    );
  }

  // Web sources: botón con favicon + popover (no navegar directo, mostrar snippet primero)
  if (source.type === 'web') {
    return (
      <Popover>
        <PopoverTrigger asChild>
          <span
            role="button"
            className={commonClasses}
            title={`Fuente Web: ${source.title}`}
          >
            <img
              src={`https://www.google.com/s2/favicons?sz=16&domain=${source.url}`}
              alt=""
              className="w-3 h-3 rounded-sm mr-0.5"
              onError={e => { (e.target as HTMLImageElement).style.display = 'none'; }}
            />
            {citationNumber}
          </span>
        </PopoverTrigger>
        {popoverContent}
      </Popover>
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
      {popoverContent}
    </Popover>
  );
};
