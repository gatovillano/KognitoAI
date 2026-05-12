'use client';

import { useState, useEffect, useMemo } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectGroup, SelectItem, SelectLabel, SelectSeparator, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { toast } from 'sonner';
import apiClient from '@/lib/api';
import { Loader2, FolderPlus } from 'lucide-react';
import { type Document } from './columns';

interface MoveToCollectionDialogProps {
    isOpen: boolean;
    onOpenChange: (open: boolean) => void;
    document: Document | null;
    onSuccess: () => void;
    workspaceId?: string;
}

interface Collection {
    id?: string;
    name: string;
    topic?: string;
    document_count: number;
    parent_id?: string | null;
    workspace_id?: string | null;
}

export function MoveToCollectionDialog({ isOpen, onOpenChange, document, onSuccess, workspaceId }: MoveToCollectionDialogProps) {
    const [collections, setCollections] = useState<Collection[]>([]);
    const [isLoadingCollections, setIsLoadingCollections] = useState(false);
    const [isMoving, setIsMoving] = useState(false);
    const [selectedName, setSelectedName] = useState<string>('');
    const [newTopic, setNewTopic] = useState<string>('');
    const [showNewTopicInput, setShowNewTopicInput] = useState(false);

    useEffect(() => {
        if (isOpen) {
            fetchCollections();
            if (document) {
                setSelectedName(document.topic || '');
            }
        } else {
            setNewTopic('');
            setShowNewTopicInput(false);
        }
    }, [isOpen, document]);

    const fetchCollections = async () => {
        setIsLoadingCollections(true);
        try {
            // Sin workspace_id para mostrar TODAS las colecciones del usuario
            const response = await apiClient.get('/api/collections');
            const normalised: Collection[] = (response.data as any[])
                .map((c) => ({
                    id: c.id,
                    name: c.name || c.topic || '',
                    topic: c.topic,
                    document_count: c.document_count ?? 0,
                    parent_id: c.parent_id ?? null,
                    workspace_id: c.workspace_id ?? null,
                }))
                .filter((c) => !!c.name);
            setCollections(normalised);
        } catch (error) {
            console.error('Error fetching collections:', error);
            toast.error('Error al cargar las colecciones.');
        } finally {
            setIsLoadingCollections(false);
        }
    };

    // Agrupar colecciones en tres categorías
    const grouped = useMemo(() => {
        const workspaceOnes = collections.filter(
            (c) => c.workspace_id && c.workspace_id === workspaceId && !c.parent_id
        );
        const subcollections = collections.filter((c) => !!c.parent_id);
        const others = collections.filter(
            (c) =>
                !c.parent_id &&
                !(c.workspace_id && c.workspace_id === workspaceId)
        );
        return { workspaceOnes, subcollections, others };
    }, [collections, workspaceId]);

    const handleMove = async () => {
        const targetTopic = showNewTopicInput ? newTopic : selectedName;

        if (!targetTopic) {
            toast.error('Por favor, selecciona o crea una colección.');
            return;
        }

        if (document && targetTopic === (document.topic || '')) {
            toast.info('El documento ya está en esta colección.');
            onOpenChange(false);
            return;
        }

        setIsMoving(true);
        const toastId = toast.loading('Moviendo documento...');

        try {
            await apiClient.post('/api/documents/update-document-metadata', {
                file_name: document?.file_name,
                new_topic: targetTopic,
                workspace_id: workspaceId || null,
            });

            toast.success(`Documento movido a "${targetTopic}" correctamente.`, { id: toastId });
            onSuccess();
            onOpenChange(false);
        } catch (error) {
            console.error('Error moving document:', error);
            toast.error('Error al mover el documento.', { id: toastId });
        } finally {
            setIsMoving(false);
        }
    };

    const renderCollectionItem = (col: Collection) => (
        <SelectItem key={col.id ?? col.name} value={col.name}>
            <span className="flex items-center justify-between w-full gap-3">
                <span>{col.name}</span>
                <span className="text-xs text-muted-foreground">{col.document_count} docs</span>
            </span>
        </SelectItem>
    );

    const hasAnyCollections = collections.length > 0;

    return (
        <Dialog open={isOpen} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[440px]">
                <DialogHeader>
                    <DialogTitle>Mover a Colección</DialogTitle>
                    <DialogDescription>
                        Selecciona la colección de destino para el documento{' '}
                        <strong>{document?.title || document?.file_name}</strong>.
                    </DialogDescription>
                </DialogHeader>

                <div className="grid gap-4 py-4">
                    {!showNewTopicInput ? (
                        <div className="grid gap-2">
                            <Label htmlFor="collection-select">Colección Existente</Label>
                            <div className="flex gap-2">
                                <Select
                                    value={selectedName}
                                    onValueChange={setSelectedName}
                                    disabled={isLoadingCollections}
                                >
                                    <SelectTrigger id="collection-select" className="flex-1">
                                        <SelectValue
                                            placeholder={
                                                isLoadingCollections
                                                    ? 'Cargando...'
                                                    : !hasAnyCollections
                                                    ? 'No hay colecciones disponibles'
                                                    : 'Seleccionar colección'
                                            }
                                        />
                                    </SelectTrigger>
                                    <SelectContent className="max-h-72">
                                        {/* ── Colecciones del Workspace ── */}
                                        {grouped.workspaceOnes.length > 0 && (
                                            <SelectGroup>
                                                <SelectLabel className="text-xs font-semibold text-muted-foreground uppercase tracking-wide px-2 py-1.5">
                                                    Colecciones del Workspace
                                                </SelectLabel>
                                                {grouped.workspaceOnes.map(renderCollectionItem)}
                                            </SelectGroup>
                                        )}

                                        {/* ── Subcolecciones ── */}
                                        {grouped.subcollections.length > 0 && (
                                            <>
                                                {grouped.workspaceOnes.length > 0 && <SelectSeparator />}
                                                <SelectGroup>
                                                    <SelectLabel className="text-xs font-semibold text-muted-foreground uppercase tracking-wide px-2 py-1.5">
                                                        Subcolecciones
                                                    </SelectLabel>
                                                    {grouped.subcollections.map(renderCollectionItem)}
                                                </SelectGroup>
                                            </>
                                        )}

                                        {/* ── Otras Colecciones ── */}
                                        {grouped.others.length > 0 && (
                                            <>
                                                {(grouped.workspaceOnes.length > 0 || grouped.subcollections.length > 0) && (
                                                    <SelectSeparator />
                                                )}
                                                <SelectGroup>
                                                    <SelectLabel className="text-xs font-semibold text-muted-foreground uppercase tracking-wide px-2 py-1.5">
                                                        Otras Colecciones
                                                    </SelectLabel>
                                                    {grouped.others.map(renderCollectionItem)}
                                                </SelectGroup>
                                            </>
                                        )}

                                        {/* Fallback si todo está vacío */}
                                        {!hasAnyCollections && !isLoadingCollections && (
                                            <div className="px-2 py-4 text-center text-sm text-muted-foreground">
                                                No hay colecciones disponibles
                                            </div>
                                        )}
                                    </SelectContent>
                                </Select>
                                <Button
                                    variant="outline"
                                    size="icon"
                                    onClick={() => setShowNewTopicInput(true)}
                                    title="Crear nueva colección"
                                >
                                    <FolderPlus className="h-4 w-4" />
                                </Button>
                            </div>
                        </div>
                    ) : (
                        <div className="grid gap-2">
                            <Label htmlFor="new-topic">Nueva Colección</Label>
                            <div className="flex gap-2">
                                <Input
                                    id="new-topic"
                                    placeholder="Nombre de la nueva colección"
                                    value={newTopic}
                                    onChange={(e) => setNewTopic(e.target.value)}
                                    autoFocus
                                />
                                <Button variant="ghost" onClick={() => setShowNewTopicInput(false)}>
                                    Cancelar
                                </Button>
                            </div>
                        </div>
                    )}
                </div>

                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isMoving}>
                        Cancelar
                    </Button>
                    <Button onClick={handleMove} disabled={isMoving || (!selectedName && !newTopic)}>
                        {isMoving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        Mover Documento
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
