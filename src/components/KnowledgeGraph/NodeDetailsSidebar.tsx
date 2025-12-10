'use client';

import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { X, FileText, Calendar, Tag, Link, Info } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface NodeDetailsSidebarProps {
    node: any;
    onClose: () => void;
    isOpen: boolean;
}

export const NodeDetailsSidebar: React.FC<NodeDetailsSidebarProps> = ({
    node,
    onClose,
    isOpen
}) => {
    if (!isOpen || !node) return null;
    console.log("NodeDetailsSidebar received node:", node); // Added for debugging

    const truncateText = (text: string, maxLength: number = 100) => {
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    };

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

    const renderNodeDetails = () => {
        const properties = node.properties || {};

        switch (node.type) {
            case 'CONCEPTUAL_QUOTE':
                return (
                    <div className="space-y-4">
                        <div>
                            <h4 className="font-semibold text-sm mb-2 flex items-center gap-2">
                                <FileText className="h-4 w-4" />
                                Cita Conceptual
                            </h4>
                            <div className="bg-muted p-3 rounded-md">
                                <p className="text-sm leading-relaxed">
                                    {properties.description || properties.text || node.label || 'No hay cita conceptual disponible.'}
                                </p>
                            </div>
                        </div>

                        {properties.concept && (
                            <div>
                                <h4 className="font-semibold text-sm mb-2">Concepto Principal</h4>
                                <Badge variant="secondary">{properties.concept}</Badge>
                            </div>
                        )}

                        {properties.category && (
                            <div>
                                <h4 className="font-semibold text-sm mb-2">Categoría</h4>
                                <Badge variant="outline">{properties.category}</Badge>
                            </div>
                        )}

                        {properties.importance && (
                            <div>
                                <h4 className="font-semibold text-sm mb-2">Importancia</h4>
                                <Badge
                                    variant={properties.importance === 'alta' ? 'default' : 'secondary'}
                                >
                                    {properties.importance}
                                </Badge>
                            </div>
                        )}

                        {properties.source_document && (
                            <div>
                                <h4 className="font-semibold text-sm mb-2 flex items-center gap-2">
                                    <FileText className="h-4 w-4" />
                                    Documento Fuente
                                </h4>
                                <p className="text-sm text-muted-foreground">
                                    {properties.source_document}
                                </p>
                            </div>
                        )}

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
                    </div>
                );

            case 'IDEA_PROFILE':
                return (
                    <div className="space-y-4">
                        <div>
                            <h4 className="font-semibold text-sm mb-2 flex items-center gap-2">
                                <Info className="h-4 w-4" />
                                Perfil de Ideas
                            </h4>
                            <div className="bg-muted p-3 rounded-md">
                                <p className="text-sm leading-relaxed">
                                    {properties.description || node.label}
                                </p>
                            </div>
                        </div>

                        {properties.central_concept && (
                            <div>
                                <h4 className="font-semibold text-sm mb-2">Concepto Central</h4>
                                <Badge variant="secondary">{properties.central_concept}</Badge>
                            </div>
                        )}

                        {properties.categories && properties.categories.length > 0 && (
                            <div>
                                <h4 className="font-semibold text-sm mb-2">Categorías</h4>
                                <div className="flex flex-wrap gap-1">
                                    {properties.categories.map((category: string, index: number) => (
                                        <Badge key={index} variant="outline" className="text-xs">
                                            {category}
                                        </Badge>
                                    ))}
                                </div>
                            </div>
                        )}

                        {properties.quote_ids && (
                            <div>
                                <h4 className="font-semibold text-sm mb-2">Citas Relacionadas</h4>
                                <p className="text-sm text-muted-foreground">
                                    {properties.quote_ids.length} citas conceptuales
                                </p>
                            </div>
                        )}

                        {properties.importance_score && (
                            <div>
                                <h4 className="font-semibold text-sm mb-2">Puntuación de Importancia</h4>
                                <div className="flex items-center gap-2">
                                    <div className="flex-1 bg-muted rounded-full h-2">
                                        <div
                                            className="bg-primary h-2 rounded-full"
                                            style={{ width: `${properties.importance_score * 10}%` }}
                                        />
                                    </div>
                                    <span className="text-xs text-muted-foreground">
                                        {properties.importance_score}/10
                                    </span>
                                </div>
                            </div>
                        )}

                        {properties.coherence_score && (
                            <div>
                                <h4 className="font-semibold text-sm mb-2">Coherencia</h4>
                                <div className="flex items-center gap-2">
                                    <div className="flex-1 bg-muted rounded-full h-2">
                                        <div
                                            className="bg-primary h-2 rounded-full"
                                            style={{ width: `${properties.coherence_score * 100}%` }}
                                        />
                                    </div>
                                    <span className="text-xs text-muted-foreground">
                                        {Math.round(properties.coherence_score * 100)}%
                                    </span>
                                </div>
                            </div>
                        )}
                    </div>
                );

            default:
                return (
                    <div className="space-y-4">
                        <div>
                            <h4 className="font-semibold text-sm mb-2">Descripción</h4>
                            <p className="text-sm text-muted-foreground">
                                {properties.description || node.title || 'Sin descripción disponible'}
                            </p>
                        </div>

                        {properties.source_document && (
                            <div>
                                <h4 className="font-semibold text-sm mb-2 flex items-center gap-2">
                                    <FileText className="h-4 w-4" />
                                    Documento Fuente
                                </h4>
                                <p className="text-sm text-muted-foreground">
                                    {properties.source_document}
                                </p>
                            </div>
                        )}

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
                    </div>
                );
        }
    };

    return (
        <div className={`fixed right-0 top-0 h-full w-[500px] bg-background border-l shadow-lg transform transition-transform duration-300 z-50 ${isOpen ? 'translate-x-0' : 'translate-x-full'}`}>
            <Card className="h-full rounded-none border-0 border-l">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
                    <CardTitle className="text-lg flex items-center gap-2">
                        <Info className="h-5 w-5" />
                        Detalles del Nodo
                    </CardTitle>
                    <Button variant="ghost" size="icon" onClick={onClose}>
                        <X className="h-4 w-4" />
                    </Button>
                </CardHeader>
                <CardContent>
                    <ScrollArea className="h-[calc(100vh-120px)]">
                        <div className="space-y-6">
                            {/* Información básica */}
                            <div>
                                <h3 className="font-semibold text-base mb-2">{node.label}</h3>
                                <Badge variant="secondary" className="mb-4">
                                    {node.type || 'Desconocido'}
                                </Badge>
                            </div>

                            <Separator />

                            {/* Detalles específicos del tipo de nodo */}
                            {renderNodeDetails()}

                            {/* Metadata común */}
                            {node.properties && (node.properties.created_at || node.properties.extraction_method) && (
                                <>
                                    <Separator />
                                    <div className="space-y-3">
                                        {node.properties.created_at && (
                                            <div className="flex items-center gap-2 text-sm text-muted-foreground">
                                                <Calendar className="h-4 w-4" />
                                                <span>Creado: {formatDate(node.properties.created_at)}</span>
                                            </div>
                                        )}

                                        {node.properties.extraction_method && (
                                            <div className="flex items-center gap-2 text-sm text-muted-foreground">
                                                <Tag className="h-4 w-4" />
                                                <span>Método: {node.properties.extraction_method}</span>
                                            </div>
                                        )}
                                    </div>
                                </>
                            )}

                            {/* Propiedades adicionales */}
                            {node.properties && Object.keys(node.properties).length > 0 && (
                                <>
                                    <Separator />
                                    <div>
                                        <h4 className="font-semibold text-sm mb-3">Todas las Propiedades</h4>
                                        <div className="space-y-3">
                                            {Object.entries(node.properties).map(([key, value]) => {
                                                // Excluir propiedades internas que no son relevantes para el usuario
                                                if (['id', 'type', 'label', 'concept', 'importance', 'category', 'source_document', 'confidence', 'extraction_method', 'created_at', 'description', 'central_concept', 'quotes_count', 'categories', 'importance_score', 'coherence_score', 'documents_span'].includes(key)) {
                                                    return null;
                                                }
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

                            {/* ID del nodo */}
                            <div className="pt-4 border-t">
                                <p className="text-xs text-muted-foreground">
                                    ID: {node.id}
                                </p>
                            </div>
                        </div>
                    </ScrollArea>
                </CardContent>
            </Card>
        </div>
    );
};