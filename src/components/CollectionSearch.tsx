'use client';

import { useState } from 'react';
import { Search, X, Filter, Loader2 } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { toast } from 'sonner';
import apiClient from '@/lib/api';

interface SearchResult {
    document_id: string;
    file_name: string;
    title?: string;
    content: string;
    topic?: string;
    chunk_index?: number;
    score?: number;
    rank_score?: number;
    rerank_score?: number;
}

interface CollectionSearchProps {
    topic: string;
    accountId: string;
    workspaceId?: string;
    onResultClick?: (result: SearchResult) => void;
}

export function CollectionSearch({ topic, accountId, workspaceId, onResultClick }: CollectionSearchProps) {
    const [query, setQuery] = useState('');
    const [searchType, setSearchType] = useState<'hybrid' | 'vector' | 'text'>('hybrid');
    const [results, setResults] = useState<SearchResult[]>([]);
    const [isSearching, setIsSearching] = useState(false);
    const [showResults, setShowResults] = useState(false);

    const handleSearch = async () => {
        if (!query.trim()) {
            toast.error('Por favor ingresa un término de búsqueda');
            return;
        }

        setIsSearching(true);
        try {
            const response = await apiClient.get('/api/collections/search', {
                params: {
                    query: query.trim(),
                    topic,
                    account_id: accountId,
                    workspace_id: workspaceId,
                    search_type: searchType,
                    k: 20,
                },
            });

            setResults(response.data.results || []);
            setShowResults(true);

            if (response.data.results.length === 0) {
                toast.info('No se encontraron resultados para tu búsqueda');
            } else {
                toast.success(`Se encontraron ${response.data.results.length} resultados`);
            }
        } catch (error) {
            console.error('Error en búsqueda:', error);
            toast.error('Error al realizar la búsqueda');
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

    const getScoreDisplay = (result: SearchResult) => {
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
            <Card>
                <CardHeader className="pb-3">
                    <CardTitle className="text-lg flex items-center gap-2">
                        <Search className="h-5 w-5" />
                        Buscar en la Colección
                    </CardTitle>
                    <CardDescription>
                        Busca documentos usando búsqueda vectorial, textual o híbrida
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                    <div className="flex gap-2">
                        <div className="relative flex-1">
                            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                            <Input
                                type="text"
                                placeholder="Escribe tu búsqueda..."
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
                        <Select value={searchType} onValueChange={(value: any) => setSearchType(value)}>
                            <SelectTrigger className="w-[160px]">
                                <Filter className="h-4 w-4 mr-2" />
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="hybrid">🔀 Híbrida</SelectItem>
                                <SelectItem value="vector">🧠 Vectorial</SelectItem>
                                <SelectItem value="text">📝 Textual</SelectItem>
                            </SelectContent>
                        </Select>
                        <Button onClick={handleSearch} disabled={isSearching || !query.trim()}>
                            {isSearching ? (
                                <>
                                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                    Buscando...
                                </>
                            ) : (
                                <>
                                    <Search className="mr-2 h-4 w-4" />
                                    Buscar
                                </>
                            )}
                        </Button>
                    </div>

                    {/* Descripción del tipo de búsqueda */}
                    <div className="text-xs text-muted-foreground">
                        {searchType === 'hybrid' && '🔀 Combina búsqueda semántica y textual para mejores resultados'}
                        {searchType === 'vector' && '🧠 Búsqueda semántica basada en el significado del texto'}
                        {searchType === 'text' && '📝 Búsqueda exacta de palabras y frases'}
                    </div>
                </CardContent>
            </Card>

            {/* Resultados */}
            {showResults && (
                <Card>
                    <CardHeader>
                        <CardTitle className="text-lg">
                            Resultados de Búsqueda
                            {results.length > 0 && (
                                <Badge variant="secondary" className="ml-2">
                                    {results.length}
                                </Badge>
                            )}
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        {results.length === 0 ? (
                            <div className="text-center py-8 text-muted-foreground">
                                <Search className="h-12 w-12 mx-auto mb-3 opacity-50" />
                                <p>No se encontraron resultados</p>
                                <p className="text-sm mt-1">Intenta con otros términos de búsqueda</p>
                            </div>
                        ) : (
                            <div className="space-y-3">
                                {results.map((result, index) => (
                                    <Card
                                        key={`${result.document_id}-${index}`}
                                        className="cursor-pointer hover:bg-accent/50 transition-colors"
                                        onClick={() => onResultClick?.(result)}
                                    >
                                        <CardContent className="p-4">
                                            <div className="flex items-start justify-between gap-2 mb-2">
                                                <div className="flex-1 min-w-0">
                                                    <h4 className="font-medium text-sm truncate">
                                                        {result.title || result.file_name}
                                                    </h4>
                                                    <div className="flex items-center gap-2 mt-1">
                                                        <Badge variant="outline" className="text-xs">
                                                            {result.file_name}
                                                        </Badge>
                                                        {result.chunk_index !== undefined && (
                                                            <Badge variant="secondary" className="text-xs">
                                                                Fragmento #{result.chunk_index + 1}
                                                            </Badge>
                                                        )}
                                                    </div>
                                                </div>
                                                {getScoreDisplay(result) && (
                                                    <Badge variant="default" className="text-xs shrink-0">
                                                        {getScoreDisplay(result)}
                                                    </Badge>
                                                )}
                                            </div>
                                            <p className="text-sm text-muted-foreground line-clamp-3">
                                                {highlightText(result.content, query)}
                                            </p>
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
