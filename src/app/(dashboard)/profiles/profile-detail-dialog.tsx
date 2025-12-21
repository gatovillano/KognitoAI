'use client';

import { useCallback, useEffect, useState } from 'react';
import { Loader2, Mail, Phone, Tag, Calendar, ListTodo, FileText, Info, Edit, ExternalLink, Album, Image as LucideImage } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import apiClient from '@/lib/api';
import { toast } from 'sonner';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';
import Image from 'next/image';
import { useRouter } from 'next/navigation';

import { ContactProfile } from './page';
import { LinkedFormResponse } from '@/types/form';

interface LinkedNoteResponse {
    id: number;
    title: string | null;
    content: string;
    created_at: string;
}

interface LinkedAgendaEventResponse {
    id: number;
    summary: string;
    description: string;
    event_datetime_utc: string;
    event_datetime_local: string;
}

interface LinkedTaskResponse {
    id: string;
    description: string;
    is_completed: boolean;
    due_date: string | null;
}

interface LinkedUserDocumentTopicResponse {
    id: string;
    name: string;
    description: string | null;
}

interface PhotoResponseForContactProfile {
    id: string;
    file_path: string;
    thumbnail_path: string | null;
}

interface LinkedAlbumResponse {
    id: string;
    name: string;
    description: string | null;
    cover_photo_id: string | null;
    created_at: string;
    total_photos: number;
    cover_photo: PhotoResponseForContactProfile | null;
}

interface LinkedObjectsResponse {
    notes: LinkedNoteResponse[];
    agenda_events: LinkedAgendaEventResponse[];
    tasks: LinkedTaskResponse[];
    user_document_topics: LinkedUserDocumentTopicResponse[];
    albums: LinkedAlbumResponse[];
    form_responses: LinkedFormResponse[];
}

interface ProfileDetailDialogProps {
    isOpen: boolean;
    onOpenChange: (open: boolean) => void;
    profileId: string | null;
    onEdit: (profile: ContactProfile) => void;
}

export function ProfileDetailDialog({ isOpen, onOpenChange, profileId, onEdit }: ProfileDetailDialogProps) {
    const router = useRouter();
    const [profile, setProfile] = useState<ContactProfile | null>(null);
    const [linkedObjects, setLinkedObjects] = useState<LinkedObjectsResponse | null>(null);
    const [loading, setLoading] = useState(false);

    const fetchDetails = useCallback(async () => {
        if (!profileId) return;
        setLoading(true);
        try {
            const [profileRes, linkedObjectsRes] = await Promise.all([
                apiClient.get(`/api/contact-profiles/${profileId}`),
                apiClient.get(`/api/contact-profiles/${profileId}/linked-objects`),
            ]);
            setProfile(profileRes.data);
            setLinkedObjects(linkedObjectsRes.data);
        } catch (err) {
            toast.error('Error al cargar los detalles del perfil.');
            onOpenChange(false);
        } finally {
            setLoading(false);
        }
    }, [profileId, onOpenChange]);

    useEffect(() => {
        if (isOpen && profileId) {
            fetchDetails();
        }
    }, [isOpen, profileId, fetchDetails]);

    if (!profileId) return null;

    return (
        <Dialog open={isOpen} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-4xl max-h-[90vh] flex flex-col p-0 overflow-hidden">
                <DialogHeader className="p-6 pb-2">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4">
                            <div className="h-12 w-12 rounded-xl bg-primary/10 flex items-center justify-center shrink-0">
                                <Info className="h-6 w-6 text-primary" />
                            </div>
                            <div>
                                <DialogTitle className="text-2xl font-bold">
                                    {loading ? 'Cargando...' : (profile?.name || 'Perfil sin nombre')}
                                </DialogTitle>
                                <DialogDescription>
                                    Detalles y elementos vinculados a este contacto.
                                </DialogDescription>
                            </div>
                        </div>
                        {!loading && profile && (
                            <div className="flex gap-2">
                                <Button variant="outline" size="sm" onClick={() => onEdit(profile)}>
                                    <Edit className="h-4 w-4 mr-2" /> Editar
                                </Button>
                                <Button variant="outline" size="sm" onClick={() => router.push(`/profiles/${profile.id}`)}>
                                    <ExternalLink className="h-4 w-4 mr-2" /> Ver detalles completos
                                </Button>
                            </div>
                        )}
                    </div>
                </DialogHeader>

                <Separator />

                <ScrollArea className="flex-1 p-6">
                    {loading ? (
                        <div className="flex flex-col items-center justify-center py-20">
                            <Loader2 className="h-10 w-10 animate-spin text-primary mb-4" />
                            <p className="text-muted-foreground">Obteniendo información del perfil...</p>
                        </div>
                    ) : profile ? (
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                            {/* Información General */}
                            <div className="md:col-span-1 space-y-6">
                                <section>
                                    <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground mb-4">Información de Contacto</h3>
                                    <div className="space-y-3">
                                        {profile.email && (
                                            <div className="flex items-center gap-3 text-sm">
                                                <Mail className="h-4 w-4 text-primary shrink-0" />
                                                <span className="truncate">{profile.email}</span>
                                            </div>
                                        )}
                                        {profile.phone && (
                                            <div className="flex items-center gap-3 text-sm">
                                                <Phone className="h-4 w-4 text-primary shrink-0" />
                                                <span>{profile.phone}</span>
                                            </div>
                                        )}
                                        {profile.category && (
                                            <div className="flex items-center gap-3 text-sm">
                                                <Tag className="h-4 w-4 text-primary shrink-0" />
                                                <span>Categoría: {profile.category}</span>
                                            </div>
                                        )}
                                        {!profile.email && !profile.phone && !profile.category && (
                                            <p className="text-sm text-muted-foreground italic">Sin datos de contacto básicos.</p>
                                        )}
                                    </div>
                                </section>

                                {profile.tags && profile.tags.length > 0 && (
                                    <section>
                                        <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground mb-3">Etiquetas</h3>
                                        <div className="flex flex-wrap gap-2">
                                            {profile.tags.map((tag) => (
                                                <Badge key={tag} variant="secondary" className="px-2 py-0.5 text-xs">
                                                    {tag}
                                                </Badge>
                                            ))}
                                        </div>
                                    </section>
                                )}

                                {profile.custom_fields && Object.keys(profile.custom_fields).length > 0 && (
                                    <section>
                                        <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground mb-3">Campos Personalizados</h3>
                                        <div className="space-y-2">
                                            {Object.entries(profile.custom_fields).map(([key, value]) => (
                                                <div key={key} className="text-sm">
                                                    <span className="font-medium text-muted-foreground">{key}:</span> {String(value)}
                                                </div>
                                            ))}
                                        </div>
                                    </section>
                                )}

                                <Separator />

                                <div className="text-[10px] text-muted-foreground space-y-1">
                                    <p>Creado: {new Date(profile.created_at).toLocaleString()}</p>
                                    <p>Actualizado: {new Date(profile.updated_at).toLocaleString()}</p>
                                </div>
                            </div>

                            {/* Elementos Vinculados */}
                            <div className="md:col-span-2 space-y-6">
                                <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Elementos Vinculados</h3>

                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                    {/* Notas */}
                                    {linkedObjects?.notes.map(note => (
                                        <Card key={note.id} className="overflow-hidden hover:border-primary/50 transition-colors cursor-pointer" onClick={() => router.push(`/notes?id=${note.id}`)}>
                                            <CardHeader className="p-3 pb-0">
                                                <div className="flex items-center gap-2">
                                                    <FileText className="h-4 w-4 text-yellow-600" />
                                                    <CardTitle className="text-sm truncate">{note.title || 'Sin título'}</CardTitle>
                                                </div>
                                            </CardHeader>
                                            <CardContent className="p-3 pt-2">
                                                <p className="text-xs text-muted-foreground line-clamp-2">{note.content}</p>
                                            </CardContent>
                                        </Card>
                                    ))}

                                    {/* Eventos */}
                                    {linkedObjects?.agenda_events.map(event => (
                                        <Card key={event.id} className="overflow-hidden hover:border-primary/50 transition-colors cursor-pointer" onClick={() => router.push(`/agenda`)}>
                                            <CardHeader className="p-3 pb-0">
                                                <div className="flex items-center gap-2">
                                                    <Calendar className="h-4 w-4 text-purple-600" />
                                                    <CardTitle className="text-sm truncate">{event.summary}</CardTitle>
                                                </div>
                                            </CardHeader>
                                            <CardContent className="p-3 pt-2">
                                                <p className="text-xs text-muted-foreground">
                                                    {format(new Date(event.event_datetime_local), 'dd/MM/yyyy HH:mm', { locale: es })}
                                                </p>
                                            </CardContent>
                                        </Card>
                                    ))}

                                    {/* Tareas */}
                                    {linkedObjects?.tasks.map(task => (
                                        <Card key={task.id} className="overflow-hidden hover:border-primary/50 transition-colors cursor-pointer" onClick={() => router.push(`/agenda`)}>
                                            <CardHeader className="p-3 pb-0">
                                                <div className="flex items-center gap-2">
                                                    <ListTodo className="h-4 w-4 text-green-600" />
                                                    <CardTitle className="text-sm truncate">{task.description}</CardTitle>
                                                </div>
                                            </CardHeader>
                                            <CardContent className="p-3 pt-2">
                                                <Badge variant={task.is_completed ? "default" : "outline"} className="text-[10px] h-5">
                                                    {task.is_completed ? 'Completada' : 'Pendiente'}
                                                </Badge>
                                            </CardContent>
                                        </Card>
                                    ))}

                                    {/* Álbumes */}
                                    {linkedObjects?.albums.map(album => (
                                        <Card key={album.id} className="overflow-hidden hover:border-primary/50 transition-colors cursor-pointer" onClick={() => router.push(`/galleries/albums/${album.id}`)}>
                                            <div className="relative h-24 w-full bg-muted">
                                                {album.cover_photo?.file_path ? (
                                                    <Image
                                                        src={`${process.env.NEXT_PUBLIC_API_URL}/media/${album.cover_photo.file_path}`}
                                                        alt={album.name}
                                                        fill
                                                        className="object-cover"
                                                    />
                                                ) : (
                                                    <div className="flex items-center justify-center h-full">
                                                        <LucideImage className="h-6 w-6 text-muted-foreground opacity-20" />
                                                    </div>
                                                )}
                                                <div className="absolute inset-0 bg-black/20 flex items-end p-2">
                                                    <span className="text-white text-xs font-bold truncate">{album.name}</span>
                                                </div>
                                            </div>
                                        </Card>
                                    ))}
                                </div>

                                {(!linkedObjects || (
                                    linkedObjects.notes.length === 0 &&
                                    linkedObjects.agenda_events.length === 0 &&
                                    linkedObjects.tasks.length === 0 &&
                                    linkedObjects.albums.length === 0 &&
                                    linkedObjects.form_responses.length === 0
                                )) && (
                                        <div className="text-center py-10 border-2 border-dashed rounded-xl">
                                            <p className="text-sm text-muted-foreground">No hay elementos vinculados a este perfil.</p>
                                        </div>
                                    )}
                            </div>
                        </div>
                    ) : null}
                </ScrollArea>
            </DialogContent>
        </Dialog>
    );
}
