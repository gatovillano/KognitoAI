import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Filter, X, Circle, Share2 } from 'lucide-react';
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

    const handleNodeTypeToggle = (type: string) => {
        const newNodeTypes = filters.nodeTypes.includes(type)
            ? filters.nodeTypes.filter(t => t !== type)
            : [...filters.nodeTypes, type];

        onFiltersChange({ ...filters, nodeTypes: newNodeTypes });
    };

    const handleEdgeTypeToggle = (type: string) => {
        const newEdgeTypes = filters.edgeTypes.includes(type)
            ? filters.edgeTypes.filter(t => t !== type)
            : [...filters.edgeTypes, type];

        onFiltersChange({ ...filters, edgeTypes: newEdgeTypes });
    };

    const clearFilters = () => {
        onFiltersChange({ ...filters, nodeTypes: [], edgeTypes: [] });
    };

    const hasActiveFilters = filters.nodeTypes.length > 0 || filters.edgeTypes.length > 0;

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
                    <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
                        <Circle className="h-4 w-4" /> Tipos de Nodo
                    </h4>
                    <ScrollArea className="flex-1 pr-3">
                        <div className="space-y-2">
                            {metadata.nodeTypes.map((item) => (
                                <div key={item.type} className="flex items-center space-x-2">
                                    <Checkbox
                                        id={`node-${item.type}`}
                                        checked={filters.nodeTypes.includes(item.type)}
                                        onCheckedChange={() => handleNodeTypeToggle(item.type)}
                                    />
                                    <Label
                                        htmlFor={`node-${item.type}`}
                                        className="flex-1 flex items-center justify-between cursor-pointer text-sm font-normal"
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
                        </div>
                    </ScrollArea>
                </div>

                {/* Filtros de Relaciones */}
                <div className="flex-1 min-h-0 flex flex-col pt-4 border-t">
                    <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
                        <Share2 className="h-4 w-4" /> Tipos de Relación
                    </h4>
                    <ScrollArea className="flex-1 pr-3">
                        <div className="space-y-2">
                            {metadata.edgeTypes.map((item) => (
                                <div key={item.type} className="flex items-center space-x-2">
                                    <Checkbox
                                        id={`edge-${item.type}`}
                                        checked={filters.edgeTypes.includes(item.type)}
                                        onCheckedChange={() => handleEdgeTypeToggle(item.type)}
                                    />
                                    <Label
                                        htmlFor={`edge-${item.type}`}
                                        className="flex-1 flex items-center justify-between cursor-pointer text-sm font-normal"
                                    >
                                        <span>{item.type}</span>
                                        <Badge variant="secondary" className="text-xs h-5 px-1.5">
                                            {item.count}
                                        </Badge>
                                    </Label>
                                </div>
                            ))}
                        </div>
                    </ScrollArea>
                </div>

            </CardContent>
        </Card>
    );
};
