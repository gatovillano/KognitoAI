'use client';

import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
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
    topic: string;
    document_count: number;
}

export function MoveToCollectionDialog({ isOpen, onOpenChange, document, onSuccess, workspaceId }: MoveToCollectionDialogProps) {
    const [collections, setCollections] = useState<Collection[]>([]);
    const [isLoadingCollections, setIsLoadingCollections] = useState(false);
    const [isMoving, setIsMoving] = useState(false);
    const [selectedTopic, setSelectedTopic] = useState<string>('');
    const [newTopic, setNewTopic] = useState<string>('');
    const [showNewTopicInput, setShowNewTopicInput] = useState(false);

    useEffect(() => {
        if (isOpen) {
            fetchCollections();
            if (document) {
                setSelectedTopic(document.topic);
            }
        } else {
            setNewTopic('');
            setShowNewTopicInput(false);
        }
    }, [isOpen, document]);

    const fetchCollections = async () => {
        setIsLoadingCollections(true);
        try {
            const response = await apiClient.get('/api/collections');
            setCollections(response.data);
        } catch (error) {
            console.error('Error fetching collections:', error);
            toast.error('Error al cargar las colecciones.');
        } finally {
            setIsLoadingCollections(false);
        }
    };

    const handleMove = async () => {
        const targetTopic = showNewTopicInput ? newTopic : selectedTopic;

        if (!targetTopic) {
            toast.error('Por favor, selecciona o crea una colección.');
            return;
        }

        if (document && targetTopic === document.topic) {
            toast.info('El documento ya está en esta colección.');
            onOpenChange(false);
            return;
        }

        setIsMoving(true);
        const toastId = toast.loading('Moviendo documento...');

        try {
            await apiClient.post('/api/documents/update-document-metadata', null, {
                params: {
                    file_name: document?.file_name,
                    new_topic: targetTopic,
                    workspace_id: workspaceId
                }
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

    return (
        <Dialog open={isOpen} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[425px]">
                <DialogHeader>
                    <DialogTitle>Mover a Colección</DialogTitle>
                    <DialogDescription>
                        Selecciona la colección de destino para el documento <strong>{document?.title || document?.file_name}</strong>.
                    </DialogDescription>
                </DialogHeader>

                <div className="grid gap-4 py-4">
                    {!showNewTopicInput ? (
                        <div className="grid gap-2">
                            <Label htmlFor="collection-select">Colección Existente</Label>
                            <div className="flex gap-2">
                                <Select value={selectedTopic} onValueChange={setSelectedTopic} disabled={isLoadingCollections}>
                                    <SelectTrigger id="collection-select" className="flex-1">
                                        <SelectValue placeholder={isLoadingCollections ? "Cargando..." : "Seleccionar colección"} />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {collections.map((col) => (
                                            <SelectItem key={col.topic} value={col.topic}>
                                                {col.topic} ({col.document_count} docs)
                                            </SelectItem>
                                        ))}
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
                                <Button
                                    variant="ghost"
                                    onClick={() => setShowNewTopicInput(false)}
                                >
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
                    <Button onClick={handleMove} disabled={isMoving || (!selectedTopic && !newTopic)}>
                        {isMoving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        Mover Documento
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
