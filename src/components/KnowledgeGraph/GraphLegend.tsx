import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ChevronDown, ChevronUp, Info } from 'lucide-react';
import { GraphMetadata } from '@/types/graph';

interface GraphLegendProps {
    metadata: GraphMetadata | null;
    getNodeColor: (type: string) => string;
}

export const GraphLegend: React.FC<GraphLegendProps> = ({ metadata, getNodeColor }) => {
    const [isExpanded, setIsExpanded] = useState(true);

    if (!metadata || (metadata.nodeTypes.length === 0 && metadata.edgeTypes.length === 0)) {
        return null;
    }

    return (
        <Card className="absolute top-4 right-4 w-64 shadow-lg bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 z-10">
            <CardHeader className="p-3 flex flex-row items-center justify-between space-y-0">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                    <Info className="h-4 w-4" /> Leyenda
                </CardTitle>
                <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 w-6 p-0"
                    onClick={() => setIsExpanded(!isExpanded)}
                >
                    {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                </Button>
            </CardHeader>

            {isExpanded && (
                <CardContent className="p-3 pt-0 max-h-[300px] overflow-y-auto text-xs">
                    {metadata.nodeTypes.length > 0 && (
                        <div className="mb-3">
                            <h5 className="font-semibold mb-2 text-muted-foreground">Nodos</h5>
                            <div className="space-y-1.5">
                                {metadata.nodeTypes.map((item) => (
                                    <div key={item.type} className="flex items-center gap-2">
                                        <span
                                            className="w-3 h-3 rounded-full border border-border"
                                            style={{ backgroundColor: getNodeColor(item.type) }}
                                        />
                                        <span className="truncate">{item.type}</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {metadata.edgeTypes.length > 0 && (
                        <div>
                            <h5 className="font-semibold mb-2 text-muted-foreground">Relaciones</h5>
                            <div className="space-y-1.5">
                                {metadata.edgeTypes.map((item) => (
                                    <div key={item.type} className="flex items-center gap-2">
                                        <span className="w-8 h-0.5 bg-muted-foreground/50" />
                                        <span className="truncate">{item.type}</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </CardContent>
            )}
        </Card>
    );
};
