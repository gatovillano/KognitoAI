'use client';

import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { X, Link, ArrowRight, Info, Calendar, Tag } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface EdgeDetailsSidebarProps {
    edge: any;
    onClose: () => void;
    isOpen: boolean;
    sourceNode?: any;
    targetNode?: any;
}

export const EdgeDetailsSidebar: React.FC<EdgeDetailsSidebarProps> = ({
    edge,
    onClose,
    isOpen,
    sourceNode,
    targetNode
}) => {
    if (!isOpen || !edge) return null;

    const formatDate = (dateString: string) => {
        try {
            return new Date(dateString).toLocaleDateString('es-ES', {
                year: 'numeric',
                month: 'long',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        } catch {
            return dateString;
        }
    };

    const renderEdgeDetails = () => {
        const properties = edge.properties || {};

        return (
            <div className="space-y-4">
                {/* Descripción de la relación */}
                <div>
                    <h4 className="font-semibold text-sm mb-2 flex items-center gap-2">
                        <Link className="h-4 w-4" />
                        Descripción de la Relación
                    </h4>
                    <div className="bg-muted p-3 rounded-md">
                        <p className="text-sm leading-relaxed">
                            {edge.label || properties.description || properties.relationship || 'No hay descripción disponible.'}
                        </p>
                    </div>
                </div>

                {/* Nodos conectados */}
                {(sourceNode || targetNode) && (
                    <div>
                        <h4 className="font-semibold text-sm mb-3">Nodos Conectados</h4>
                        <div className="space-y-3">
                            {sourceNode && (
                                <div className="bg-muted/50 p-3 rounded">
                                    <div className="flex items-center gap-2 mb-1">
                                        <span className="text-xs font-medium text-muted-foreground">DESDE:</span>
                                        <Badge variant="outline" className="text-xs">
                                            {sourceNode.type || 'Nodo'}
                                        </Badge>
                                    </div>
                                    <p className="text-sm font-medium">{sourceNode.label || sourceNode.properties?.name || `ID: ${sourceNode.id}`}</p>
                                </div>
                            )}
                            
                            <div className="flex justify-center">
                                <ArrowRight className="h-4 w-4 text-muted-foreground" />
                            </div>
                            
                            {targetNode && (
                                <div className="bg-muted/50 p-3 rounded">
                                    <div className="flex items-center gap-2 mb-1">
                                        <span className="text-xs font-medium text-muted-foreground">HACIA:</span>
                                        <Badge variant="outline" className="text-xs">
                                            {targetNode.type || 'Nodo'}
                                        </Badge>
                                    </div>
                                    <p className="text-sm font-medium">{targetNode.label || targetNode.properties?.name || `ID: ${targetNode.id}`}</p>
                                </div>
                            )}
                        </div>
                    </div>
                )}

                {/* Tipo de relación */}
                {edge.type && (
                    <div>
                        <h4 className="font-semibold text-sm mb-2 flex items-center gap-2">
                            <Tag className="h-4 w-4" />
                            Tipo de Relación
                        </h4>
                        <Badge variant="secondary">{edge.type}</Badge>
                    </div>
                )}

                {/* Documento fuente */}
                {properties.source_document && (
                    <div>
                        <h4 className="font-semibold text-sm mb-2">Documento Fuente</h4>
                        <p className="text-sm text-muted-foreground">
                            {properties.source_document}
                        </p>
                    </div>
                )}

                {/* Confianza */}
                {properties.confidence && (
                    <div>
                        <h4 className="font-semibold text-sm mb-2">Confianza</h4>
                        <div className="flex items-center gap-2">
                            <div className="flex-1 bg-muted rounded-full h-2">
                                <div
                                    className="bg-primary h-2 rounded-full"
                                    style={{ width: `${properties.confidence * 100}%` }}
                                />
                            </div>
                            <span className="text-xs text-muted-foreground">
                                {Math.round(properties.confidence * 100)}%
                            </span>
                        </div>
                    </div>
                )}

                {/* Peso de la relación */}
                {properties.weight && (
                    <div>
                        <h4 className="font-semibold text-sm mb-2">Peso de la Relación</h4>
                        <div className="flex items-center gap-2">
                            <div className="flex-1 bg-muted rounded-full h-2">
                                <div
                                    className="bg-primary h-2 rounded-full"
                                    style={{ width: `${Math.min(properties.weight * 100, 100)}%` }}
                                />
                            </div>
                            <span className="text-xs text-muted-foreground">
                                {typeof properties.weight === 'number' ? properties.weight.toFixed(2) : properties.weight}
                            </span>
                        </div>
                    </div>
                )}

                {/* Método de extracción */}
                {properties.extraction_method && (
                    <div>
                        <h4 className="font-semibold text-sm mb-2">Método de Extracción</h4>
                        <p className="text-sm text-muted-foreground">
                            {properties.extraction_method}
                        </p>
                    </div>
                )}

                {/* Contexto */}
                {properties.context && (
                    <div>
                        <h4 className="font-semibold text-sm mb-2">Contexto</h4>
                        <div className="bg-muted p-3 rounded-md">
                            <p className="text-sm leading-relaxed">
                                {properties.context}
                            </p>
                        </div>
                    </div>
                )}

                {/* Posición en el texto */}
                {properties.position && (
                    <div>
                        <h4 className="font-semibold text-sm mb-2">Posición en el Texto</h4>
                        <p className="text-sm text-muted-foreground">
                            {properties.position}
                        </p>
                    </div>
                )}
            </div>
        );
    };

    return (
        <div className={`fixed right-0 top-0 h-full w-[500px] bg-background border-l shadow-lg transform transition-transform duration-300 z-50 ${isOpen ? 'translate-x-0' : 'translate-x-full'}`}>
            <Card className="h-full rounded-none border-0 border-l">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
                    <CardTitle className="text-lg flex items-center gap-2">
                        <Link className="h-5 w-5" />
                        Detalles de la Relación
                    </CardTitle>
                    <Button variant="ghost" size="icon" onClick={onClose}>
                        <X className="h-4 w-4" />
                    </Button>
                </CardHeader>
                <CardContent>
                    <ScrollArea className="h-[calc(100vh-120px)]">
                        <div className="space-y-6">
                            {/* Información básica */}
                            <div className="min-w-0">
                                <h3 className="font-semibold text-base mb-2 max-w-full">
                                    <span style={{ wordBreak: 'break-all', whiteSpace: 'normal' }}>
                                        {edge.label || edge.properties?.description || edge.properties?.relationship || 'Relación'}
                                    </span>
                                </h3>
                                <Badge variant="secondary" className="mb-4">
                                    {edge.type || 'Relación'}
                                </Badge>
                            </div>

                            <Separator />

                            {/* Detalles específicos de la relación */}
                            {renderEdgeDetails()}

                            {/* Metadata común */}
                            {edge.properties && (edge.properties.created_at || edge.properties.extraction_method) && (
                                <>
                                    <Separator />
                                    <div className="space-y-3">
                                        {edge.properties.created_at && (
                                            <div className="flex items-center gap-2 text-sm text-muted-foreground">
                                                <Calendar className="h-4 w-4" />
                                                <span>Creado: {formatDate(edge.properties.created_at)}</span>
                                            </div>
                                        )}

                                        {edge.properties.extraction_method && (
                                            <div className="flex items-center gap-2 text-sm text-muted-foreground">
                                                <Tag className="h-4 w-4" />
                                                <span>Método: {edge.properties.extraction_method}</span>
                                            </div>
                                        )}
                                    </div>
                                </>
                            )}

                            {/* Todas las propiedades */}
                            {edge.properties && Object.keys(edge.properties).length > 0 && (
                                <>
                                    <Separator />
                                    <div>
                                        <h4 className="font-semibold text-sm mb-3">Todas las Propiedades</h4>
                                        <div className="space-y-3">
                                            {Object.entries(edge.properties).map(([key, value]) => {
                                                // Mostrar TODAS las propiedades sin exclusión

                                                // Manejo especial para 'confidence' como barra de porcentaje
                                                if (key === 'confidence' && typeof value === 'number') {
                                                    return (
                                                        <div key={key} className="flex flex-col space-y-1">
                                                            <div className="flex items-center justify-between">
                                                                <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                                                                    {key.replace(/_/g, ' ')}
                                                                </span>
                                                            </div>
                                                            <div className="flex items-center gap-2">
                                                                <div className="flex-1 bg-muted rounded-full h-2">
                                                                    <div
                                                                        className="bg-primary h-2 rounded-full"
                                                                        style={{ width: `${value * 100}%` }}
                                                                    />
                                                                </div>
                                                                <span className="text-xs text-muted-foreground">
                                                                    {Math.round(value * 100)}%
                                                                </span>
                                                            </div>
                                                        </div>
                                                    );
                                                }

                                                // Manejo especial para 'weight' como barra de porcentaje
                                                if (key === 'weight' && typeof value === 'number') {
                                                    return (
                                                        <div key={key} className="flex flex-col space-y-1">
                                                            <div className="flex items-center justify-between">
                                                                <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                                                                    {key.replace(/_/g, ' ')}
                                                                </span>
                                                            </div>
                                                            <div className="flex items-center gap-2">
                                                                <div className="flex-1 bg-muted rounded-full h-2">
                                                                    <div
                                                                        className="bg-primary h-2 rounded-full"
                                                                        style={{ width: `${Math.min(value * 100, 100)}%` }}
                                                                    />
                                                                </div>
                                                                <span className="text-xs text-muted-foreground">
                                                                    {typeof value === 'number' ? value.toFixed(2) : String(value)}
                                                                </span>
                                                            </div>
                                                        </div>
                                                    );
                                                }

                                                // Renderizado por defecto para todas las demás propiedades
                                                return (
                                                    <div key={key} className="flex flex-col space-y-1">
                                                        <div className="flex items-center justify-between">
                                                            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                                                                {key.replace(/_/g, ' ')}
                                                            </span>
                                                        </div>
                                                        <div className="text-sm bg-muted/50 p-3 rounded text-foreground break-words">
                                                            {typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}
                                                        </div>
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    </div>
                                </>
                            )}

                            {/* ID de la relación */}
                            <div className="pt-4 border-t space-y-4">
                                <div>
                                    <p className="text-xs text-muted-foreground">
                                        ID: {edge.id}
                                    </p>
                                    <p className="text-xs text-muted-foreground">
                                        Desde: {edge.from} → Hacia: {edge.to}
                                    </p>
                                </div>
                                <Button variant="outline" className="w-full" onClick={onClose}>
                                    Cerrar Detalles
                                </Button>
                            </div>
                        </div>
                    </ScrollArea>
                </CardContent>
            </Card>
        </div>
    );
};