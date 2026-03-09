'use client';

import React, { useState } from 'react';
import {
    ExternalLink,
    File as FileIcon,
    Share2,
    NotebookText,
    Database,
    Globe,
    Search,
    Copy,
    Check,
    ArrowUpRight,
    Github
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Card, CardContent, CardFooter, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { Source } from '@/components/SourceButton';
import { InlineMarkdownRenderer } from './InlineMarkdownRenderer';
import { cn } from '@/lib/utils';
import { ScrollArea } from '@/components/ui/scroll-area';

interface SourcesTabProps {
    sources: Source[];
    onSourceClick?: (source: Source) => void;
}

export const SourcesTab: React.FC<SourcesTabProps> = ({ sources, onSourceClick }) => {
    const [searchQuery, setSearchQuery] = useState('');
    const [activeTab, setActiveTab] = useState<'all' | 'cited' | 'uncited' | string>('all');
    // Para filtro por tipo (puede ser 'all' o tipo específico)
    const [selectedTypeFilter, setSelectedTypeFilter] = useState<string>('all');
    const [copiedId, setCopiedId] = useState<string | number | null>(null);

    const handleCopyUrl = (url: string, id: string | number) => {
        navigator.clipboard.writeText(url);
        setCopiedId(id);
        setTimeout(() => setCopiedId(null), 2000);
    };

    const getTypeIcon = (type: Source['type']) => {
        switch (type) {
            case 'web': return <Globe className="h-4 w-4" />;
            case 'document': return <FileIcon className="h-4 w-4" />;
            case 'memory': return <BrainIcon className="h-4 w-4" />;
            case 'code': return <CodeIcon className="h-4 w-4" />;
            case 'database': return <Database className="h-4 w-4" />;
            case 'graph': return <Share2 className="h-4 w-4" />;
            case 'note': return <NotebookText className="h-4 w-4" />;
            case 'github': return <Github className="h-4 w-4" />;
            default: return <FileIcon className="h-4 w-4" />;
        }
    };

    const BrainIcon = (props: React.SVGProps<SVGSVGElement>) => (
        <svg {...props} fill="currentColor" viewBox="0 0 20 20"><path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
    );

    const CodeIcon = (props: React.SVGProps<SVGSVGElement>) => (
        <svg {...props} fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M12.316 3.051a1 1 0 01.633 1.265l-4 12a1 1 0 11-1.898-.632l4-12a1 1 0 011.265-.633zM5.707 6.293a1 1 0 010 1.414L3.414 10l2.293 2.293a1 1 0 11-1.414 1.414l-3-3a1 1 0 010-1.414l3-3a1 1 0 011.414 0zm8.586 0a1 1 0 011.414 0l3 3a1 1 0 010 1.414l-3 3a1 1 0 11-1.414-1.414L16.586 10l-2.293-2.293a1 1 0 010-1.414z" clipRule="evenodd" /></svg>
    );

    const getTypeLabel = (type: Source['type']) => {
        const labels: Record<string, string> = {
            web: 'Web', document: 'Documento', memory: 'Memoria',
            code: 'Código', database: 'Base de Datos', graph: 'Grafo',
            note: 'Nota', github: 'GitHub'
        };
        return labels[type] || 'Fuente';
    };

    const getTypeStyles = (type: Source['type']) => {
        switch (type) {
            case 'web':
                return 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-200 dark:border-blue-800';
            case 'document':
                return 'bg-orange-500/10 text-orange-600 dark:text-orange-400 border-orange-200 dark:border-orange-800';
            case 'memory':
                return 'bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-200 dark:border-purple-800';
            case 'code':
            case 'github':
                return 'bg-slate-500/10 text-slate-600 dark:text-slate-400 border-slate-200 dark:border-slate-800';
            case 'database':
                return 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-200 dark:border-emerald-800';
            case 'graph':
                return 'bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 border-cyan-200 dark:border-cyan-800';
            case 'note':
                return 'bg-yellow-500/10 text-yellow-600 dark:text-yellow-400 border-yellow-200 dark:border-yellow-800';
            default:
                return 'bg-primary/5 text-primary border-primary/20';
        }
    };

    const filteredSources = sources.filter(source => {
        const query = searchQuery.toLowerCase();
        const matchesSearch =
            (source.title?.toLowerCase() ?? '').includes(query) ||
            (source.snippet?.toLowerCase() ?? '').includes(query) ||
            (source.url?.toLowerCase() ?? '').includes(query);
        const matchesType = selectedTypeFilter === 'all' || source.type === selectedTypeFilter;
        const matchesCitation =
            activeTab === 'all' ||
            (activeTab === 'cited' && source.is_cited) ||
            (activeTab === 'uncited' && !source.is_cited);
        return matchesSearch && matchesType && matchesCitation;
    });

    const uniqueTypes = ['all', ...Array.from(new Set(sources.map(s => s.type)))];
  // Para pestañas de citación, siempre incluimos todas las opciones
  const citationTabs = [
    { value: 'all', label: 'Todas' },
    { value: 'cited', label: 'Citadas' },
    { value: 'uncited', label: 'No Citadas' }
  ];
  const [showCitationTabs, setShowCitationTabs] = useState(true); // Siempre mostrar por ahora

    if (!sources || sources.length === 0) {
        return (
            <div className="flex flex-col items-center justify-center py-16 text-muted-foreground bg-muted/30 rounded-3xl border border-dashed border-border/50">
                <div className="bg-background p-4 rounded-full shadow-sm mb-4">
                    <ExternalLink className="w-8 h-8 opacity-20" />
                </div>
                <p className="font-medium text-lg">No se registraron fuentes externas</p>
                <p className="text-sm opacity-60">Esta investigación se generó sin referencias explícitas.</p>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header / Controls */}
            <div className="flex flex-col sm:flex-row gap-4 items-center justify-between bg-card/50 p-4 rounded-2xl border border-border/40 backdrop-blur-sm">
                <div className="flex items-center gap-2 w-full sm:w-auto">
                    <div className="relative w-full sm:w-64">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                        <Input
                            placeholder="Buscar en fuentes..."
                            className="pl-9 h-10 bg-background/50 border-input/50 focus:bg-background transition-all rounded-xl"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                        />
                    </div>
                </div>

                <div className="flex gap-2 w-full sm:w-auto">
                    {/* Pestañas de Citación */}
                    <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as any)} className="w-auto">
                        <TabsList className="bg-muted/50 p-1 h-10 rounded-xl flex overflow-x-auto no-scrollbar">
                            {citationTabs.map(tab => (
                                <TabsTrigger
                                    key={tab.value}
                                    value={tab.value}
                                    className="rounded-lg text-xs px-3 data-[state=active]:bg-background data-[state=active]:shadow-sm"
                                >
                                    {tab.label}
                                </TabsTrigger>
                            ))}
                        </TabsList>
                    </Tabs>

                    {/* Separador */}
                    <div className="w-px bg-border/50 mx-1 self-center" />

                    {/* Pestañas de Tipo */}
                    <Tabs value={selectedTypeFilter} onValueChange={setSelectedTypeFilter} className="w-auto flex-1 sm:flex-initial">
                        <TabsList className="bg-muted/50 p-1 h-10 rounded-xl flex overflow-x-auto no-scrollbar">
                            {uniqueTypes.map(type => (
                                <TabsTrigger
                                    key={type}
                                    value={type}
                                    className="rounded-lg capitalize text-xs px-3 data-[state=active]:bg-background data-[state=active]:shadow-sm"
                                >
                                    {type === 'all' ? 'Todas' : getTypeLabel(type as Source['type'])}
                                </TabsTrigger>
                            ))}
                        </TabsList>
                    </Tabs>
                </div>
            </div>

            {/* Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 xl:grid-cols-3 gap-4">
                <AnimatePresence mode="popLayout">
                    {filteredSources.map((source, idx) => (
                        <motion.div
                            key={`${source.id}-${idx}`}
                            layout
                            initial={{ opacity: 0, scale: 0.95, y: 10 }}
                            animate={{ opacity: 1, scale: 1, y: 0 }}
                            exit={{ opacity: 0, scale: 0.95, transition: { duration: 0.2 } }}
                            transition={{ duration: 0.3, delay: idx * 0.05 }}
                        >
                            <SourceCard
                                source={source}
                                typeStyles={getTypeStyles(source.type)}
                                typeIcon={getTypeIcon(source.type)}
                                typeLabel={getTypeLabel(source.type)}
                                onCopy={handleCopyUrl}
                                copiedId={copiedId}
                                onClick={onSourceClick}
                            />
                        </motion.div>
                    ))}
                </AnimatePresence>
            </div>

            {filteredSources.length === 0 && (
                <div className="text-center py-12 text-muted-foreground opacity-60">
                    <p>No se encontraron fuentes que coincidan con tu búsqueda.</p>
                </div>
            )}
        </div>
    );
};

interface SourceCardProps {
    source: Source;
    typeStyles: string;
    typeIcon: React.ReactNode;
    typeLabel: string;
    onCopy: (url: string, id: string | number) => void;
    copiedId: string | number | null;
    onClick?: (source: Source) => void;
}

const SourceCard: React.FC<SourceCardProps> = ({
    source,
    typeStyles,
    typeIcon,
    typeLabel,
    onCopy,
    copiedId,
    onClick
}) => {
    return (
        <Card className="group h-full flex flex-col overflow-hidden border-border/40 hover:border-primary/30 hover:shadow-lg hover:shadow-primary/5 transition-all duration-300 bg-card/60 backdrop-blur-sm rounded-2xl">
            <CardHeader className="p-4 pb-2 space-y-3">
                <div className="flex items-start justify-between gap-3">
                    <Badge variant="outline" className={cn("rounded-lg px-2 py-1 flex items-center gap-1.5 font-bold text-[10px] tracking-wider uppercase backdrop-blur-md", typeStyles)}>
                        {typeIcon}
                        {typeLabel}
                    </Badge>

                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                        {source.url && (
                            <TooltipProvider>
                                <Tooltip>
                                    <TooltipTrigger asChild>
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            className="h-7 w-7 rounded-lg hover:bg-primary/10 hover:text-primary"
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                onCopy(source.url, source.id);
                                            }}
                                        >
                                            {copiedId === source.id ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
                                        </Button>
                                    </TooltipTrigger>
                                    <TooltipContent><p>Copiar URL</p></TooltipContent>
                                </Tooltip>
                            </TooltipProvider>
                        )}
                    </div>
                </div>

                <h4 className="font-bold text-sm leading-tight line-clamp-2 group-hover:text-primary transition-colors">
                    {source.title}
                </h4>
            </CardHeader>

            <CardContent className="p-4 pt-0 flex-grow">
                {source.metadata?.topic && (
                    <div className="mb-2">
                        <span className="text-[9px] font-bold bg-muted/80 text-muted-foreground px-1.5 py-0.5 rounded uppercase tracking-wider">
                            {source.metadata.topic}
                        </span>
                    </div>
                )}

                <ScrollArea className="h-[100px] pr-2">
                    <div className="text-xs text-muted-foreground/80 leading-relaxed">
                        <InlineMarkdownRenderer content={source.snippet} />
                    </div>
                </ScrollArea>
            </CardContent>

            <CardFooter className="p-3 bg-muted/30 border-t border-border/30 flex items-center justify-between text-xs mt-auto">
                <div className="flex items-center gap-3">
                    {source.metadata?.similarity_score && (
                        <div className="flex items-center gap-1.5" title="Relevancia">
                            <div className="relative h-5 w-5 flex items-center justify-center">
                                <svg className="h-full w-full -rotate-90 text-muted/50" viewBox="0 0 24 24">
                                    <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" fill="none" />
                                    <circle
                                        cx="12" cy="12" r="10"
                                        stroke="currentColor"
                                        strokeWidth="3"
                                        fill="none"
                                        className="text-primary transition-all duration-1000"
                                        strokeDasharray="62.8"
                                        strokeDashoffset={62.8 - (62.8 * source.metadata.similarity_score)}
                                        strokeLinecap="round"
                                    />
                                </svg>
                                <span className="absolute text-[8px] font-bold">{Math.round(source.metadata.similarity_score * 100)}</span>
                            </div>
                        </div>
                    )}
                </div>

                {(source.url || (source.type === 'graph' && source.url?.startsWith('analysis://'))) ? (
                    <Button
                        variant="ghost"
                        size="sm"
                        className="h-7 px-3 text-[10px] font-bold uppercase tracking-wider hover:bg-primary/10 hover:text-primary gap-1.5 rounded-lg"
                        onClick={() => {
                            if (source.type === 'graph' && source.url?.startsWith('analysis://') && onClick) {
                                onClick(source);
                            } else if (source.url) {
                                window.open(source.url, '_blank', 'noopener,noreferrer');
                            }
                        }}
                    >
                        Abrir
                        <ArrowUpRight className="h-3 w-3" />
                    </Button>
                ) : (
                    <span className="text-[10px] text-muted-foreground italic px-2">Sin enlace</span>
                )}
            </CardFooter>
        </Card>
    );
};
