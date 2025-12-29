'use client';

import { useState } from 'react';
import { Search, X, Filter, Loader2, Notebook } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { toast } from 'sonner';
import apiClient from '@/lib/api';

interface NoteSearchResult {
    note_id: string;
    title?: string;
    content: string;
    score?: number;
    rank_score?: number;
    rerank_score?: number;
    created_at?: string;
    workspace_id?: string;
}

interface NoteSearchProps {
    accountId: string;
    workspaceId?: string;
    onResultClick?: (result: NoteSearchResult) => void;
}

export function NoteSearch({ accountId, workspaceId, onResultClick }: NoteSearchProps) {
    const [query, setQuery] = useState('');
    const [searchType, setSearchType] = useState<'hybrid' | 'vector' | 'text'>('hybrid');
    const [results, setResults] = useState<NoteSearchResult[]>([]);
    const [isSearching, setIsSearching] = useState(false);
    const [showResults, setShowResults] = useState(false);

    const handleSearch = async () => {
        if (!query.trim()) {
            toast.error('Por favor ingresa un término de búsqueda');
            return;
        }

        setIsSearching(true);
        try {
            const response = await apiClient.get('/api/notes/search', {
                params: {
                    query: query.trim(),
                    account_id: accountId,
                    workspace_id: workspaceId || undefined,
                    search_type: searchType,
                    k: 20,
                },
            });

            setResults(response.data.results || []);
            setShowResults(true);

            if (response.data.results.length === 0) {
                toast.info('No se encontraron notas para tu búsqueda');
            } else {
                toast.success(`Se encontraron ${response.data.results.length} notas`);
            }
        } catch (error) {
            console.error('Error en búsqueda de notas:', error);
            toast.error('Error al realizar la búsqueda de notas');
        } finally {
            setIsSearching(false);
        }
    };

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter') {
            handleSearch();
        }
    };

    const clearSearch = () => {
        setQuery('');
        setResults([]);
        setShowResults(false);
    };

    const highlightText = (text: string, query: string) => {
        if (!query.trim()) return text;

        const parts = text.split(new RegExp(`(${query})`, 'gi'));
        return parts.map((part, index) =>
            part.toLowerCase() === query.toLowerCase() ? (
                <mark key={index} className="bg-yellow-200 dark:bg-yellow-800 px-0.5 rounded">
                    {part}
                </mark>
            ) : (
                part
            )
        );
    };

    const getScoreDisplay = (result: NoteSearchResult) => {
        if (searchType === 'vector' && result.score) {
            return `Similitud: ${(result.score * 100).toFixed(1)}%`;
        } else if (searchType === 'text' && result.rank_score) {
            return `Relevancia: ${result.rank_score.toFixed(2)}`;
        } else if (searchType === 'hybrid') {
            const score = (result.score || 0) + (result.rank_score || 0);
            return `Score: ${score.toFixed(2)}`;
        }
        return '';
    };

    return (
        <div className="space-y-4">
            {/* Barra de búsqueda */}
            <Card className="border-primary/20 shadow-sm">
                <CardHeader className="pb-3">
                    <CardTitle className="text-lg flex items-center gap-2">
                        <Search className="h-5 w-5 text-primary" />
                        Buscar en mis Notas
                    </CardTitle>
                    <CardDescription>
                        Búsqueda inteligente en el contenido de tus notas
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                    <div className="flex flex-col sm:flex-row gap-2">
                        <div className="relative flex-1">
                            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                            <Input
                                type="text"
                                placeholder="¿Qué estás buscando en tus notas?"
                                value={query}
                                onChange={(e) => setQuery(e.target.value)}
                                onKeyPress={handleKeyPress}
                                className="pl-10 pr-10"
                            />
                            {query && (
                                <Button
                                    variant="ghost"
                                    size="icon"
                                    className="absolute right-1 top-1/2 transform -translate-y-1/2 h-7 w-7"
                                    onClick={clearSearch}
                                >
                                    <X className="h-4 w-4" />
                                </Button>
                            )}
                        </div>
                        <div className="flex gap-2">
                            <Select value={searchType} onValueChange={(value: any) => setSearchType(value)}>
                                <SelectTrigger className="w-[140px]">
                                    <Filter className="h-4 w-4 mr-2" />
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="hybrid">🔀 Híbrida</SelectItem>
                                    <SelectItem value="vector">🧠 Vectorial</SelectItem>
                                    <SelectItem value="text">📝 Textual</SelectItem>
                                </SelectContent>
                            </Select>
                            <Button onClick={handleSearch} disabled={isSearching || !query.trim()} className="shrink-0">
                                {isSearching ? (
                                    <Loader2 className="h-4 w-4 animate-spin" />
                                ) : (
                                    <>
                                        <Search className="mr-2 h-4 w-4" />
                                        Buscar
                                    </>
                                )}
                            </Button>
                        </div>
                    </div>

                    <div className="text-xs text-muted-foreground flex items-center gap-2">
                        <span className="inline-block w-2 h-2 rounded-full bg-primary/40"></span>
                        {searchType === 'hybrid' && 'Combina significado y palabras exactas para mayor precisión'}
                        {searchType === 'vector' && 'Encuentra notas por concepto, incluso si no usan las mismas palabras'}
                        {searchType === 'text' && 'Busca coincidencias exactas de texto en tus notas'}
                    </div>
                </CardContent>
            </Card>

            {/* Resultados */}
            {showResults && (
                <Card className="border-primary/10">
                    <CardHeader className="py-4">
                        <CardTitle className="text-md flex items-center justify-between">
                            <span>Resultados de Búsqueda</span>
                            {results.length > 0 && (
                                <Badge variant="secondary">
                                    {results.length} notas encontradas
                                </Badge>
                            )}
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="pb-4">
                        {results.length === 0 ? (
                            <div className="text-center py-10 text-muted-foreground">
                                <Notebook className="h-12 w-12 mx-auto mb-3 opacity-20" />
                                <p>No se encontraron notas que coincidan</p>
                                <p className="text-sm mt-1">Prueba con términos más generales</p>
                            </div>
                        ) : (
                            <div className="grid gap-3 sm:grid-cols-1 md:grid-cols-2">
                                {results.map((result, index) => (
                                    <Card
                                        key={`${result.note_id}-${index}`}
                                        className="cursor-pointer hover:border-primary/50 hover:bg-accent/5 transition-all group"
                                        onClick={() => onResultClick?.(result)}
                                    >
                                        <CardContent className="p-4">
                                            <div className="flex items-start justify-between gap-2 mb-2">
                                                <div className="flex-1 min-w-0">
                                                    <h4 className="font-semibold text-sm truncate group-hover:text-primary transition-colors">
                                                        {result.title || 'Nota sin título'}
                                                    </h4>
                                                    <div className="flex items-center gap-2 mt-1">
                                                        {result.created_at && (
                                                            <span className="text-[10px] text-muted-foreground">
                                                                {new Date(result.created_at).toLocaleDateString()}
                                                            </span>
                                                        )}
                                                    </div>
                                                </div>
                                                {getScoreDisplay(result) && (
                                                    <Badge variant="outline" className="text-[10px] shrink-0 font-normal">
                                                        {getScoreDisplay(result)}
                                                    </Badge>
                                                )}
                                            </div>
                                            <div className="text-xs text-muted-foreground line-clamp-3 leading-relaxed">
                                                {highlightText(result.content, query)}
                                            </div>
                                        </CardContent>
                                    </Card>
                                ))}
                            </div>
                        )}
                    </CardContent>
                </Card>
            )}
        </div>
    );
}
