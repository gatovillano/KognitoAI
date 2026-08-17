'use client';

import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { X, FileText, Calendar, Tag, Link, Info, Brain, Bookmark, BookmarkCheck, Volume2, Loader2, Square } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useTextToSpeech } from '@/hooks/useTextToSpeech';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface NodeDetailsSidebarProps {
    node: any;
    onClose: () => void;
    isOpen: boolean;
    onToggleSave?: (node: any) => void;
    isSaved?: boolean;
}

export const NodeDetailsSidebar: React.FC<NodeDetailsSidebarProps> = ({
    node,
    onClose,
    isOpen,
    onToggleSave,
    isSaved = false
}) => {
    const { play, stop, isLoading: isTtsLoading, isPlaying: isTtsPlaying, activeText } = useTextToSpeech();

    if (!isOpen || !node) return null;

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
                        <div className="flex items-center justify-between mb-2">
                            <h4 className="font-semibold text-sm flex items-center gap-2">
                                <FileText className="h-4 w-4" />
                                Cita Conceptual
                            </h4>
                            {(properties.full_text || properties.description || properties.text || node.label) && (
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    className="h-8 w-8 p-0 rounded-full hover:bg-primary/10 transition-all"
                                    onClick={() => {
                                        const text = properties.full_text || properties.description || properties.text || node.label;
                                        if (isTtsPlaying && activeText === text) {
                                            stop();
                                        } else {
                                            play(text);
                                        }
                                    }}
                                >
                                    {isTtsLoading && activeText === (properties.full_text || properties.description || properties.text || node.label) ? (
                                        <Loader2 className="h-4 w-4 animate-spin text-primary" />
                                    ) : isTtsPlaying && activeText === (properties.full_text || properties.description || properties.text || node.label) ? (
                                        <Square className="h-4 w-4 text-primary fill-primary" />
                                    ) : (
                                        <Volume2 className="h-4 w-4 text-primary" />
                                    )}
                                </Button>
                            )}
                        </div>
                        <div className="bg-muted p-3 rounded-md text-sm leading-relaxed prose prose-sm dark:prose-invert max-w-none">
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                {properties.full_text || properties.description || properties.text || node.label || 'No hay cita conceptual disponible.'}
                            </ReactMarkdown>
                        </div>

                        {properties.extraction_method && (
                            <div>
                                <h4 className="font-semibold text-sm mb-2 flex items-center gap-2">
                                    <Tag className="h-4 w-4" />
                                    Método de Extracción
                                </h4>
                                <p className="text-sm text-muted-foreground">
                                    {properties.extraction_method}
                                </p>
                            </div>
                        )}

                        {properties.concept && (
                            <div>
                                <h4 className="font-semibold text-sm mb-2 flex items-center gap-2">
                                    <Brain className="h-4 w-4" /> Concepto Principal
                                </h4>
                                <Badge variant="secondary">{properties.concept}</Badge>
                            </div>
                        )}

                        {properties.category && (
                            <div>
                                <h4 className="font-semibold text-sm mb-2 flex items-center gap-2">
                                    <Tag className="h-4 w-4" /> Categoría
                                </h4>
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
                            <div className="flex items-center justify-between mb-2">
                                <h4 className="font-semibold text-sm flex items-center gap-2">
                                    <Info className="h-4 w-4" />
                                    Perfil de Ideas
                                </h4>
                                {(properties.description || node.label) && (
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        className="h-8 w-8 p-0 rounded-full hover:bg-primary/10 transition-all"
                                        onClick={() => {
                                            const text = properties.description || node.label;
                                            if (isTtsPlaying && activeText === text) {
                                                stop();
                                            } else {
                                                play(text);
                                            }
                                        }}
                                    >
                                        {isTtsLoading && activeText === (properties.description || node.label) ? (
                                            <Loader2 className="h-4 w-4 animate-spin text-primary" />
                                        ) : isTtsPlaying && activeText === (properties.description || node.label) ? (
                                            <Square className="h-4 w-4 text-primary fill-primary" />
                                        ) : (
                                            <Volume2 className="h-4 w-4 text-primary" />
                                        )}
                                    </Button>
                                )}
                            </div>
                            <div className="bg-muted p-3 rounded-md text-sm leading-relaxed prose prose-sm dark:prose-invert max-w-none">
                                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                    {properties.description || node.label}
                                </ReactMarkdown>
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

            case 'ANTHROPOLOGICAL_QUOTE':
                return (
                    <div className="space-y-4">
                        <div>
                            <h4 className="font-semibold text-sm mb-2 flex items-center gap-2 text-amber-600 dark:text-amber-400">
                                <FileText className="h-4 w-4" />
                                Cita Etnográfica (Corpus)
                            </h4>
                            <div className="bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-900/50 p-3 rounded-md text-sm italic leading-relaxed">
                                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                    {properties.full_text || properties.description || node.label}
                                </ReactMarkdown>
                            </div>
                        </div>

                        {properties.code && (
                            <div>
                                <h4 className="font-semibold text-sm mb-1 flex items-center gap-2">
                                    <Tag className="h-4 w-4 text-purple-500" />
                                    Código Asignado (1:N)
                                </h4>
                                <Badge className="bg-purple-600 text-white font-mono text-xs">{properties.code}</Badge>
                            </div>
                        )}

                        {properties.code_explanation && (
                            <div>
                                <h4 className="font-semibold text-sm mb-1">Justificación del Código</h4>
                                <p className="text-xs text-muted-foreground">{properties.code_explanation}</p>
                            </div>
                        )}

                        {properties.analytical_level && (
                            <div>
                                <h4 className="font-semibold text-sm mb-1">Nivel Analítico</h4>
                                <Badge variant="outline" className="capitalize">{properties.analytical_level}</Badge>
                            </div>
                        )}

                        {properties.source_document && (
                            <div>
                                <h4 className="font-semibold text-sm mb-1">Documento Origen</h4>
                                <p className="text-xs text-muted-foreground">{properties.source_document}</p>
                            </div>
                        )}
                    </div>
                );

            case 'ANTHROPOLOGICAL_CODE':
                return (
                    <div className="space-y-4">
                        <div>
                            <h4 className="font-semibold text-sm mb-2 flex items-center gap-2 text-purple-600 dark:text-purple-400">
                                <Brain className="h-4 w-4" />
                                Código Atómico Antropológico (Contenedor 1:N)
                            </h4>
                            <Badge className="bg-purple-700 text-white font-mono text-sm px-3 py-1 mb-2">
                                {properties.code_name || node.label}
                            </Badge>
                            <p className="text-sm text-muted-foreground bg-muted p-3 rounded-md">
                                {properties.description || 'Sin descripción'}
                            </p>
                        </div>

                        {properties.quotes_count !== undefined && (
                            <div>
                                <h4 className="font-semibold text-sm mb-1">Citas Agrupadas</h4>
                                <Badge variant="secondary">{properties.quotes_count} cita(s) contenida(s)</Badge>
                            </div>
                        )}
                    </div>
                );

            case 'ANTHROPOLOGICAL_CATEGORY':
                return (
                    <div className="space-y-4">
                        <div>
                            <h4 className="font-semibold text-sm mb-2 flex items-center gap-2 text-blue-600 dark:text-blue-400">
                                <Tag className="h-4 w-4" />
                                Categoría Analítica Superior (Perfil de Idea)
                            </h4>
                            <Badge className="bg-blue-600 text-white text-sm px-3 py-1 mb-3">
                                {properties.category_name || node.label}
                            </Badge>
                            <div className="text-sm text-foreground bg-muted p-4 rounded-md prose prose-sm dark:prose-invert max-w-none leading-relaxed">
                                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                    {properties.description || 'Sin descripción'}
                                </ReactMarkdown>
                            </div>
                        </div>

                        {properties.theoretical_connection && (
                            <div>
                                <h4 className="font-semibold text-sm mb-2 text-primary">Conexión Teórica y Respuesta a Hipótesis</h4>
                                <div className="text-sm text-foreground bg-blue-50 dark:bg-blue-950/30 p-4 rounded-md border border-blue-200 dark:border-blue-900/40 prose prose-sm dark:prose-invert max-w-none leading-relaxed">
                                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                        {properties.theoretical_connection}
                                    </ReactMarkdown>
                                </div>
                            </div>
                        )}
                    </div>
                );

            default:
                return (
                    <div className="space-y-4">
                        <div>
                            <div className="flex items-center justify-between mb-2">
                                <h4 className="font-semibold text-sm">Descripción</h4>
                                {(properties.description || node.title) && (
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        className="h-8 w-8 p-0 rounded-full hover:bg-primary/10 transition-all"
                                        onClick={() => {
                                            const text = properties.description || node.title;
                                            if (isTtsPlaying && activeText === text) {
                                                stop();
                                            } else {
                                                play(text);
                                            }
                                        }}
                                    >
                                        {isTtsLoading && activeText === (properties.description || node.title) ? (
                                            <Loader2 className="h-4 w-4 animate-spin text-primary" />
                                        ) : isTtsPlaying && activeText === (properties.description || node.title) ? (
                                            <Square className="h-4 w-4 text-primary fill-primary" />
                                        ) : (
                                            <Volume2 className="h-4 w-4 text-primary" />
                                        )}
                                    </Button>
                                )}
                            </div>
                            <div className="text-sm text-muted-foreground prose prose-sm dark:prose-invert max-w-none">
                                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                    {properties.description || node.title || 'Sin descripción disponible'}
                                </ReactMarkdown>
                            </div>
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
                    <div className="flex items-center gap-2">
                        {onToggleSave && (
                            <Button
                                variant="ghost"
                                size="icon"
                                onClick={() => onToggleSave(node)}
                                className={isSaved ? "text-primary" : "text-muted-foreground"}
                                title={isSaved ? "Quitar de la lista" : "Guardar en la lista"}
                            >
                                {isSaved ? <BookmarkCheck className="h-5 w-5 fill-current" /> : <Bookmark className="h-5 w-5" />}
                            </Button>
                        )}
                        <Button variant="ghost" size="icon" onClick={onClose}>
                            <X className="h-4 w-4" />
                        </Button>
                    </div>
                </CardHeader>
                <CardContent>
                    <ScrollArea className="h-[calc(100vh-120px)]">
                        <div className="space-y-6">
                            {/* Información básica */}
                            <div className="min-w-0"> {/* Añadido para evitar truncamiento del título */}
                                <h3 className="font-semibold text-base mb-2 max-w-full">
                                    <span style={{ wordBreak: 'break-word', whiteSpace: 'normal' }}>
                                        {node.properties?.name || node.properties?.title || node.label}
                                    </span>
                                </h3>
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
                                                // Mostrar todas las propiedades por defecto, a menos que sean propiedades internas del nodo que se manejan aparte.
                                                // Excluir propiedades internas y 'description' que ya se muestran de forma prominente.
                                                // Excluir solo las propiedades básicas que ya se muestran de forma prominente.
                                                // Esto asegura que otras propiedades como 'category' y 'categories' sean visibles.
                                                // La propiedad 'description' se mostrará aquí aunque también aparezca arriba,
                                                // para cumplir con la solicitud de mostrar "absolutamente todas" las propiedades
                                                // si no está específicamente excluida por el usuario.
                                                // Excluir solo las propiedades básicas que ya se muestran de forma prominente,
                                                // incluyendo 'description' para evitar duplicidad según el feedback del usuario.
                                                if (['id', 'type', 'label', 'description'].includes(key)) {
                                                    return null;
                                                }

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

                                                // Renderizado por defecto para otras propiedades
                                                return (
                                                    <div key={key} className="flex flex-col space-y-1">
                                                        <div className="flex items-center justify-between">
                                                            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                                                                {key.replace(/_/g, ' ')}
                                                            </span>
                                                        </div>
                                                        <div className="text-sm bg-muted/50 p-3 rounded text-foreground break-words prose prose-sm dark:prose-invert max-w-none">
                                                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                                                {typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}
                                                            </ReactMarkdown>
                                                        </div>
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    </div>
                                </>
                            )}

                            {/* ID del nodo */}
                            <div className="pt-4 border-t space-y-4">
                                <p className="text-xs text-muted-foreground">
                                    ID: {node.id}
                                </p>
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