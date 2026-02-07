'use client';

import React from 'react';
import { ExternalLink, File as FileIcon, Share2, NotebookText, Database, Globe } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Source } from '@/components/SourceButton';
import { InlineMarkdownRenderer } from './InlineMarkdownRenderer';

interface SourcesTabProps {
    sources: Source[];
    onSourceClick?: (source: Source) => void;
}

export const SourcesTab: React.FC<SourcesTabProps> = ({ sources, onSourceClick }) => {
    const getTypeIcon = (type: Source['type']) => {
        switch (type) {
            case 'web':
                return <ExternalLink className="h-4 w-4" />;
            case 'document':
                return <FileIcon className="h-4 w-4" />;
            case 'memory':
                return <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20"><path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>;
            case 'code':
                return <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M12.316 3.051a1 1 0 01.633 1.265l-4 12a1 1 0 11-1.898-.632l4-12a1 1 0 011.265-.633zM5.707 6.293a1 1 0 010 1.414L3.414 10l2.293 2.293a1 1 0 11-1.414 1.414l-3-3a1 1 0 010-1.414l3-3a1 1 0 011.414 0zm8.586 0a1 1 0 011.414 0l3 3a1 1 0 010 1.414l-3 3a1 1 0 11-1.414-1.414L16.586 10l-2.293-2.293a1 1 0 010-1.414z" clipRule="evenodd" /></svg>;
            case 'database':
                return <Database className="h-4 w-4" />;
            case 'graph':
                return <Share2 className="h-4 w-4" />;
            case 'note':
                return <NotebookText className="h-4 w-4" />;
            default:
                return <FileIcon className="h-4 w-4" />;
        }
    };

    const getTypeLabel = (type: Source['type']) => {
        switch (type) {
            case 'web': return 'Web';
            case 'document': return 'Documento';
            case 'memory': return 'Memoria';
            case 'code': return 'Código';
            case 'database': return 'Base de Datos';
            case 'graph': return 'Grafo';
            case 'note': return 'Nota';
            default: return 'Fuente';
        }
    };

    const getTypeColor = (type: Source['type']) => {
        switch (type) {
            case 'web':
                return 'bg-blue-500/15 text-blue-600 dark:text-blue-400 border-blue-300/50';
            case 'document':
                return 'bg-orange-500/15 text-orange-600 dark:text-orange-400 border-orange-300/50';
            case 'memory':
                return 'bg-purple-500/15 text-purple-600 dark:text-purple-400 border-purple-300/50';
            case 'code':
                return 'bg-slate-500/15 text-slate-600 dark:text-slate-400 border-slate-300/50';
            case 'database':
                return 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-300/50';
            case 'graph':
                return 'bg-cyan-500/15 text-cyan-600 dark:text-cyan-400 border-cyan-300/50';
            case 'note':
                return 'bg-yellow-500/15 text-yellow-600 dark:text-yellow-400 border-yellow-300/50';
            default:
                return 'bg-primary/10 text-primary border-primary/20';
        }
    };

    const getLinkUrl = (source: Source): string | null => {
        if (source.type === 'web' && source.url) {
            return source.url;
        }
        if (source.type === 'note' && source.url?.startsWith('note://')) {
            return `/notes/${source.url.replace('note://', '')}`;
        }
        if (source.type === 'graph' && source.url?.startsWith('graph://')) {
            return `/graphs/${source.url.replace('graph://', '')}`;
        }
        return null;
    };

    const getLinkText = (source: Source): string => {
        if (source.type === 'web') {
            return 'Abrir en navegador';
        }
        if (source.type === 'note') {
            return 'Abrir Nota';
        }
        if (source.type === 'graph' && source.url?.startsWith('graph://')) {
            return 'Ver en Grafo';
        }
        if (source.type === 'graph' && source.url?.startsWith('analysis://')) {
            return 'Ver Insight';
        }
        return 'Ver detalles';
    };

    if (!sources || sources.length === 0) {
        return (
            <div className="text-center py-12 text-muted-foreground">
                <ExternalLink className="w-12 h-12 mx-auto mb-4 opacity-20" />
                <p>No se registraron fuentes externas para esta investigación.</p>
            </div>
        );
    }

    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between mb-4">
                <h4 className="text-lg font-bold flex items-center gap-2 text-slate-600">
                    <ExternalLink className="w-5 h-5" />
                    Bibliografía y Referencias
                </h4>
                <Badge variant="secondary" className="rounded-full">
                    {sources.length} {sources.length === 1 ? 'fuente' : 'fuentes'}
                </Badge>
            </div>

            <div className="grid gap-4">
                {sources.map((source, idx) => {
                    const icon = getTypeIcon(source.type);
                    const label = getTypeLabel(source.type);
                    const color = getTypeColor(source.type);
                    const linkUrl = getLinkUrl(source);
                    const linkText = getLinkText(source);

                    return (
                        <Card key={idx} className="overflow-hidden hover:shadow-lg transition-shadow duration-300">
                            <CardContent className="p-0">
                                <div className={`p-4 border-b border-border/10 ${color.split(' ')[0]}`}>
                                    <div className="flex items-start justify-between gap-3">
                                        <div className="flex items-start gap-3 flex-1 min-w-0">
                                            <div className="p-2 rounded-xl bg-background/50 shadow-sm border border-white/10 flex-shrink-0">
                                                {icon}
                                            </div>
                                            <div className="flex flex-col min-w-0 flex-1">
                                                <div className="font-bold text-base leading-tight break-words tracking-tight">
                                                    {source.title}
                                                </div>
                                                <div className="flex items-center gap-2 mt-1 flex-wrap">
                                                    <Badge className={`text-[10px] uppercase tracking-widest font-bold border ${color}`}>
                                                        {label}
                                                    </Badge>
                                                    {source.id && (
                                                        <span className="text-[10px] font-mono opacity-40">#{source.id}</span>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                <div className="p-4 space-y-3">
                                    {source.metadata?.topic && (
                                        <div className="text-[10px] font-bold bg-muted px-2 py-0.5 rounded-md w-fit text-muted-foreground">
                                            COLECCIÓN: {source.metadata.topic}
                                        </div>
                                    )}

                                    <div className="text-sm text-muted-foreground leading-relaxed">
                                        <InlineMarkdownRenderer content={source.snippet} />
                                    </div>

                                    {source.metadata?.similarity_score && (
                                        <div className="flex items-center gap-2 pt-2">
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
                                        <div className="pt-3 border-t border-border/10">
                                            <div className="text-[9px] font-black text-muted-foreground uppercase tracking-widest mb-2">
                                                Origen
                                            </div>
                                            <div className="flex items-center gap-2">
                                                {linkUrl ? (
                                                    <a
                                                        href={linkUrl}
                                                        target="_blank"
                                                        rel="noopener noreferrer"
                                                        className="inline-flex items-center gap-1.5 text-sm text-primary hover:underline font-bold transition-colors"
                                                    >
                                                        <Globe className="h-3.5 w-3.5" />
                                                        {linkText}
                                                    </a>
                                                ) : source.type === 'graph' && source.url?.startsWith('analysis://') ? (
                                                    <button
                                                        onClick={() => onSourceClick && onSourceClick(source)}
                                                        className="inline-flex items-center gap-1.5 text-sm text-primary hover:underline font-bold transition-colors"
                                                    >
                                                        <Share2 className="h-3.5 w-3.5" />
                                                        {linkText}
                                                    </button>
                                                ) : (
                                                    <span className="text-xs font-mono opacity-80 break-all">
                                                        {source.url}
                                                    </span>
                                                )}
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </CardContent>
                        </Card>
                    );
                })}
            </div>
        </div>
    );
};
