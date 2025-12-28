import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Filter, X, Circle, Share2, ChevronDown, ChevronRight } from 'lucide-react';
import { GraphMetadata, GraphFilters as GraphFiltersType } from '@/types/graph';
import { cn } from '@/lib/utils';

interface GraphFiltersProps {
    metadata: GraphMetadata | null;
    filters: GraphFiltersType;
    onFiltersChange: (filters: GraphFiltersType) => void;
    totalNodes: number;
    totalEdges: number;
    filteredNodes: number;
    filteredEdges: number;
    getNodeColor: (type: string) => string;
}

export const GraphFilters: React.FC<GraphFiltersProps> = ({
    metadata,
    filters,
    onFiltersChange,
    totalNodes,
    totalEdges,
    filteredNodes,
    filteredEdges,
    getNodeColor
}) => {
    if (!metadata) return null;

    const [isEdgeTypesExpanded, setIsEdgeTypesExpanded] = React.useState(true);
    const [isNodeTypesExpanded, setIsNodeTypesExpanded] = React.useState(true);
    const [nodeFilterMode, setNodeFilterMode] = React.useState<'include' | 'exclude'>('include');
    const [edgeFilterMode, setEdgeFilterMode] = React.useState<'include' | 'exclude'>('include');

    const handleNodeTypeToggle = (type: string) => {
        if (nodeFilterMode === 'include') {
            const newNodeTypes = filters.nodeTypes.includes(type)
                ? filters.nodeTypes.filter(t => t !== type)
                : [...filters.nodeTypes, type];
            onFiltersChange({ ...filters, nodeTypes: newNodeTypes });
        } else {
            const excluded = filters.excludedNodeTypes || [];
            const newExcluded = excluded.includes(type)
                ? excluded.filter(t => t !== type)
                : [...excluded, type];
            onFiltersChange({ ...filters, excludedNodeTypes: newExcluded });
        }
    };

    const handleEdgeTypeToggle = (type: string) => {
        if (edgeFilterMode === 'include') {
            const newEdgeTypes = filters.edgeTypes.includes(type)
                ? filters.edgeTypes.filter(t => t !== type)
                : [...filters.edgeTypes, type];
            onFiltersChange({ ...filters, edgeTypes: newEdgeTypes });
        } else {
            const excluded = filters.excludedEdgeTypes || [];
            const newExcluded = excluded.includes(type)
                ? excluded.filter(t => t !== type)
                : [...excluded, type];
            onFiltersChange({ ...filters, excludedEdgeTypes: newExcluded });
        }
    };

    const clearFilters = () => {
        onFiltersChange({
            ...filters,
            nodeTypes: [],
            edgeTypes: [],
            excludedNodeTypes: [],
            excludedEdgeTypes: []
        });
    };

    const hasActiveFilters = filters.nodeTypes.length > 0 ||
        filters.edgeTypes.length > 0 ||
        (filters.excludedNodeTypes?.length || 0) > 0 ||
        (filters.excludedEdgeTypes?.length || 0) > 0;

    return (
        <Card className="h-full flex flex-col">
            <CardHeader className="pb-3">
                <CardTitle className="flex items-center justify-between text-lg">
                    <div className="flex items-center gap-2">
                        <Filter className="h-5 w-5" />
                        Filtros
                    </div>
                    {hasActiveFilters && (
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={clearFilters}
                            className="h-8 px-2 text-muted-foreground hover:text-foreground"
                        >
                            <X className="h-4 w-4 mr-1" /> Limpiar
                        </Button>
                    )}
                </CardTitle>
            </CardHeader>
            <CardContent className="flex-1 overflow-hidden flex flex-col gap-4">

                {/* Resumen de conteos */}
                <div className="grid grid-cols-2 gap-2 text-sm mb-2">
                    <div className="bg-muted/50 p-2 rounded flex flex-col items-center justify-center">
                        <span className="font-bold text-lg">{filteredNodes}</span>
                        <span className="text-xs text-muted-foreground">Nodos ({totalNodes})</span>
                    </div>
                    <div className="bg-muted/50 p-2 rounded flex flex-col items-center justify-center">
                        <span className="font-bold text-lg">{filteredEdges}</span>
                        <span className="text-xs text-muted-foreground">Relaciones ({totalEdges})</span>
                    </div>
                </div>

                {/* Filtros de Nodos */}
                <div className="flex-1 min-h-0 flex flex-col">
                    <div
                        className="flex items-center justify-between mb-2 cursor-pointer"
                    >
                        <h4 className="text-sm font-medium flex items-center gap-2" onClick={() => setIsNodeTypesExpanded(!isNodeTypesExpanded)}>
                            <Circle className="h-4 w-4" /> Tipos de Nodo
                            {(filters.nodeTypes.length > 0 || (filters.excludedNodeTypes?.length || 0) > 0) && (
                                <Badge variant="default" className="text-xs h-4 px-1">
                                    {filters.nodeTypes.length + (filters.excludedNodeTypes?.length || 0)}
                                </Badge>
                            )}
                        </h4>
                        <div className="flex items-center gap-1">
                            <div className="flex bg-muted rounded-md p-0.5 mr-2">
                                <Button
                                    variant={nodeFilterMode === 'include' ? 'secondary' : 'ghost'}
                                    size="sm"
                                    className="h-6 px-2 text-[10px]"
                                    onClick={() => setNodeFilterMode('include')}
                                >
                                    Incluir
                                </Button>
                                <Button
                                    variant={nodeFilterMode === 'exclude' ? 'secondary' : 'ghost'}
                                    size="sm"
                                    className="h-6 px-2 text-[10px]"
                                    onClick={() => setNodeFilterMode('exclude')}
                                >
                                    Excluir
                                </Button>
                            </div>
                            <Button
                                variant="ghost"
                                size="sm"
                                className="h-6 w-6 p-0 hover:bg-muted"
                                onClick={() => setIsNodeTypesExpanded(!isNodeTypesExpanded)}
                            >
                                {isNodeTypesExpanded ? (
                                    <ChevronDown className="h-3 w-3" />
                                ) : (
                                    <ChevronRight className="h-3 w-3" />
                                )}
                            </Button>
                        </div>
                    </div>
                    {isNodeTypesExpanded && (
                        <ScrollArea className="flex-1 pr-3">
                            <div className="space-y-2">
                                {metadata.nodeTypes.map((item) => (
                                    <div key={item.type} className="flex items-center space-x-2">
                                        <Checkbox
                                            id={`node-${item.type}`}
                                            checked={nodeFilterMode === 'include'
                                                ? filters.nodeTypes.includes(item.type)
                                                : filters.excludedNodeTypes?.includes(item.type)
                                            }
                                            onCheckedChange={() => handleNodeTypeToggle(item.type)}
                                            className={nodeFilterMode === 'exclude' ? "data-[state=checked]:bg-destructive data-[state=checked]:border-destructive" : ""}
                                        />
                                        <Label
                                            htmlFor={`node-${item.type}`}
                                            className={cn(
                                                "flex-1 flex items-center justify-between cursor-pointer text-sm font-normal",
                                                nodeFilterMode === 'exclude' && filters.excludedNodeTypes?.includes(item.type) && "text-destructive line-through opacity-70"
                                            )}
                                        >
                                            <span className="flex items-center gap-2">
                                                <span
                                                    className="w-3 h-3 rounded-full inline-block"
                                                    style={{ backgroundColor: getNodeColor(item.type) }}
                                                />
                                                {item.type}
                                            </span>
                                            <Badge variant="secondary" className="text-xs h-5 px-1.5">
                                                {item.count}
                                            </Badge>
                                        </Label>
                                    </div>
                                ))}
                                {metadata.nodeTypes.length === 0 && (
                                    <div className="text-xs text-muted-foreground text-center py-4">
                                        No hay tipos de nodo disponibles
                                    </div>
                                )}
                            </div>
                        </ScrollArea>
                    )}
                    {!isNodeTypesExpanded && filters.nodeTypes.length > 0 && (
                        <div className="mt-2 text-xs text-muted-foreground">
                            {filters.nodeTypes.length} tipo{filters.nodeTypes.length !== 1 ? 's' : ''} seleccionado{filters.nodeTypes.length !== 1 ? 's' : ''}
                        </div>
                    )}
                </div>

                {/* Filtros de Relaciones */}
                <div className="flex-1 min-h-0 flex flex-col pt-4 border-t">
                    <div
                        className="flex items-center justify-between mb-2 cursor-pointer"
                    >
                        <h4 className="text-sm font-medium flex items-center gap-2" onClick={() => setIsEdgeTypesExpanded(!isEdgeTypesExpanded)}>
                            <Share2 className="h-4 w-4" /> Tipos de Relación
                            {(filters.edgeTypes.length > 0 || (filters.excludedEdgeTypes?.length || 0) > 0) && (
                                <Badge variant="default" className="text-xs h-4 px-1">
                                    {filters.edgeTypes.length + (filters.excludedEdgeTypes?.length || 0)}
                                </Badge>
                            )}
                        </h4>
                        <div className="flex items-center gap-1">
                            <div className="flex bg-muted rounded-md p-0.5 mr-2">
                                <Button
                                    variant={edgeFilterMode === 'include' ? 'secondary' : 'ghost'}
                                    size="sm"
                                    className="h-6 px-2 text-[10px]"
                                    onClick={() => setEdgeFilterMode('include')}
                                >
                                    Incluir
                                </Button>
                                <Button
                                    variant={edgeFilterMode === 'exclude' ? 'secondary' : 'ghost'}
                                    size="sm"
                                    className="h-6 px-2 text-[10px]"
                                    onClick={() => setEdgeFilterMode('exclude')}
                                >
                                    Excluir
                                </Button>
                            </div>
                            <Button
                                variant="ghost"
                                size="sm"
                                className="h-6 w-6 p-0 hover:bg-muted"
                                onClick={() => setIsEdgeTypesExpanded(!isEdgeTypesExpanded)}
                            >
                                {isEdgeTypesExpanded ? (
                                    <ChevronDown className="h-3 w-3" />
                                ) : (
                                    <ChevronRight className="h-3 w-3" />
                                )}
                            </Button>
                        </div>
                    </div>
                    {isEdgeTypesExpanded && (
                        <ScrollArea className="flex-1 pr-3">
                            <div className="space-y-2">
                                {metadata.edgeTypes.map((item) => (
                                    <div key={item.type} className="flex items-center space-x-2">
                                        <Checkbox
                                            id={`edge-${item.type}`}
                                            checked={edgeFilterMode === 'include'
                                                ? filters.edgeTypes.includes(item.type)
                                                : filters.excludedEdgeTypes?.includes(item.type)
                                            }
                                            onCheckedChange={() => handleEdgeTypeToggle(item.type)}
                                            className={edgeFilterMode === 'exclude' ? "data-[state=checked]:bg-destructive data-[state=checked]:border-destructive" : ""}
                                        />
                                        <Label
                                            htmlFor={`edge-${item.type}`}
                                            className={cn(
                                                "flex-1 flex items-center justify-between cursor-pointer text-sm font-normal",
                                                edgeFilterMode === 'exclude' && filters.excludedEdgeTypes?.includes(item.type) && "text-destructive line-through opacity-70"
                                            )}
                                        >
                                            <span>{item.type}</span>
                                            <Badge variant="secondary" className="text-xs h-5 px-1.5">
                                                {item.count}
                                            </Badge>
                                        </Label>
                                    </div>
                                ))}
                                {metadata.edgeTypes.length === 0 && (
                                    <div className="text-xs text-muted-foreground text-center py-4">
                                        No hay tipos de relación disponibles
                                    </div>
                                )}
                            </div>
                        </ScrollArea>
                    )}
                    {!isEdgeTypesExpanded && filters.edgeTypes.length > 0 && (
                        <div className="mt-2 text-xs text-muted-foreground">
                            {filters.edgeTypes.length} tipo{filters.edgeTypes.length !== 1 ? 's' : ''} seleccionado{filters.edgeTypes.length !== 1 ? 's' : ''}
                        </div>
                    )}
                </div>

            </CardContent>
        </Card>
    );
};
