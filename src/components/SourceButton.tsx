import React from 'react';
import { ExternalLink, File as FileIcon, Share2, NotebookText } from 'lucide-react';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';

export interface Source {
  id: number | string;
  title: string;
  url: string;
  snippet: string;
  type: 'web' | 'document' | 'memory' | 'code' | 'database';
  metadata?: Record<string, any>;
  name?: string;
}

export interface ContentPart {
  type: 'text' | 'citation';
  content?: string;
  source?: Source;
  citationNumber?: number;
}

export const SourceButton: React.FC<{ source: Source; citationNumber: number }> = ({ source, citationNumber }) => {
  const getIcon = () => {
    switch (source.type) {
      case 'web':
        return <ExternalLink className="h-3 w-3 mr-1" />;
      case 'document':
        return <FileIcon className="h-3 w-3 mr-1" />;
      case 'memory':
        return <svg className="h-3 w-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
          <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>;
      case 'code':
        return <svg className="h-3 w-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M12.316 3.051a1 1 0 01.633 1.265l-4 12a1 1 0 11-1.898-.632l4-12a1 1 0 011.265-.633zM5.707 6.293a1 1 0 010 1.414L3.414 10l2.293 2.293a1 1 0 11-1.414 1.414l-3-3a1 1 0 010-1.414l3-3a1 1 0 011.414 0zm8.586 0a1 1 0 011.414 0l3 3a1 1 0 010 1.414l-3 3a1 1 0 11-1.414-1.414L16.586 10l-2.293-2.293a1 1 0 010-1.414z" clipRule="evenodd" />
        </svg>;
      case 'database':
        return <svg className="h-3 w-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
          <path d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zM3 10a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H4a1 1 0 01-1-1v-6zM14 9a1 1 0 00-1 1v6a1 1 0 001 1h2a1 1 0 001-1v-6a1 1 0 00-1-1h-2z" />
        </svg>;
      case 'graph':
        return <Share2 className="h-3 w-3 mr-1" />;
      case 'note':
        return <NotebookText className="h-3 w-3 mr-1" />;
      default:
        return <FileIcon className="h-3 w-3 mr-1" />;
    }
  };

  const getButtonContent = () => {
    if (source.type === 'web') {
      return (
        <a
          href={source.url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center text-xs bg-primary/10 text-primary font-bold rounded-full px-1.5 mx-0.5 focus:outline-none focus:ring-2 focus:ring-primary/50 leading-normal flex-shrink-0 relative top-[-0.2em] hover:bg-primary/20 transition-colors"
        >
          {getIcon()}
          {citationNumber}
        </a>
      );
    }

    return (
      <Popover>
        <PopoverTrigger asChild>
          <button className="inline-flex items-center text-xs bg-primary/10 text-primary font-bold rounded-full px-1.5 mx-0.5 focus:outline-none focus:ring-2 focus:ring-primary/50 leading-normal flex-shrink-0 relative top-[-0.2em] hover:bg-primary/20 transition-colors">
            {getIcon()}
            {citationNumber}
          </button>
        </PopoverTrigger>
        <PopoverContent className="max-w-lg text-sm">
          <div className="flex items-center gap-2 mb-2">
            {getIcon()}
            <div className="font-bold whitespace-normal break-words min-w-0">{source.title}</div>
          </div>
          <div className="text-xs text-muted-foreground mb-2 capitalize">
            Tipo: {source.type}
          </div>
          {source.metadata?.topic && (
            <div className="text-xs text-muted-foreground mb-2">
              Colección: {source.metadata.topic}
            </div>
          )}
          <p className="text-muted-foreground">
            {source.snippet}
          </p>
          {source.metadata?.similarity_score && (
            <div className="text-xs text-primary/80 mt-2">
              Relevancia: {Math.round(source.metadata.similarity_score * 100)}%
            </div>
          )}
          {source.url && (source.type === 'document' || source.type === 'memory' || source.type === 'code' || source.type === 'database' || source.type === 'note') && (
            <div className="text-xs text-muted-foreground mt-2 break-all">
              Fuente: {source.type === 'note' && source.url.startsWith('note://') ? (
                <a href={`/notes/${source.url.replace('note://', '')}`} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">
                  {source.url}
                </a>
              ) : (
                source.url
              )}
            </div>
          )}
        </PopoverContent>
      </Popover>
    );
  };

  return getButtonContent();
};