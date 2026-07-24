'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { toast } from 'sonner';
import apiClient from '@/lib/api';
import { Check, Send, Sparkles, Lock, MessageSquare, Image as ImageIcon, CheckCircle, ZoomIn } from 'lucide-react';
import Lightbox from 'yet-another-react-lightbox';
import 'yet-another-react-lightbox/styles.css';

interface PhotoResponse {
  id: string;
  album_id: string;
  file_path: string;
  thumbnail_path?: string;
}

interface AlbumResponse {
  id: string;
  name: string;
  description?: string;
  photos: PhotoResponse[];
}

interface PublicData {
  album: AlbumResponse;
  allow_comments: boolean;
  max_selections?: number;
  token: string;
}

interface PhotoThumbnailProps {
  photo: PhotoResponse;
}

const PhotoThumbnail: React.FC<PhotoThumbnailProps> = ({ photo }) => {
  const [failed, setFailed] = useState(false);
  const src = (photo.thumbnail_path && !failed)
    ? `/thumbnails/${photo.thumbnail_path}`
    : `/media/${photo.file_path}`;

  return (
    <img
      src={src}
      alt="Foto"
      className="w-full h-auto object-cover transition-transform duration-300 group-hover:scale-[1.03]"
      loading="lazy"
      onError={() => setFailed(true)}
    />
  );
};

export const SelectionPublicPage: React.FC<{ token: string }> = ({ token }) => {
  const [data, setData] = useState<PublicData | null>(null);
  const [loading, setLoading] = useState(true);
  const [password, setPassword] = useState('');
  const [needPassword, setNeedPassword] = useState(false);

  // Client submission state
  const [clientName, setClientName] = useState('');
  const [clientEmail, setClientEmail] = useState('');
  const [generalComment, setGeneralComment] = useState('');
  const [selectedPhotos, setSelectedPhotos] = useState<Map<string, string>>(new Map()); // photo_id -> comment
  const [activeCommentPhoto, setActiveCommentPhoto] = useState<PhotoResponse | null>(null);
  const [tempComment, setTempComment] = useState('');

  const [submitting, setSubmitting] = useState(false);
  const [submittedSuccess, setSubmittedSuccess] = useState(false);
  const [lightboxOpen, setLightboxOpen] = useState(false);
  const [lightboxIndex, setLightboxIndex] = useState(0);

  const fetchPanelData = useCallback(async (pwd?: string) => {
    setLoading(true);
    try {
      const res = await apiClient.post<PublicData>(`/api/galleries/extension/selection/public/${token}`, pwd ? { password: pwd } : {});
      setData(res.data);
      setNeedPassword(false);
    } catch (e: any) {
      if (e.response?.status === 401) {
        setNeedPassword(true);
      } else {
        toast.error(e.response?.data?.detail || 'Error al cargar el panel de selección.');
      }
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    fetchPanelData();
  }, [fetchPanelData]);

  const toggleSelectPhoto = (photoId: string) => {
    setSelectedPhotos((prev) => {
      const next = new Map(prev);
      if (next.has(photoId)) {
        next.delete(photoId);
      } else {
        if (data?.max_selections && next.size >= data.max_selections) {
          toast.warning(`Has alcanzado el límite máximo de ${data.max_selections} fotos.`);
          return prev;
        }
        next.set(photoId, '');
      }
      return next;
    });
  };

  const handleSavePhotoComment = () => {
    if (activeCommentPhoto) {
      setSelectedPhotos((prev) => {
        const next = new Map(prev);
        if (!next.has(activeCommentPhoto.id)) {
          next.set(activeCommentPhoto.id, tempComment);
        } else {
          next.set(activeCommentPhoto.id, tempComment);
        }
        return next;
      });
      setActiveCommentPhoto(null);
      setTempComment('');
    }
  };

  const handleSubmitSelection = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!clientName.trim()) {
      toast.error('Por favor, ingresa tu nombre.');
      return;
    }
    if (selectedPhotos.size === 0) {
      toast.error('Selecciona al menos una foto para enviar.');
      return;
    }

    setSubmitting(true);
    try {
      const items = Array.from(selectedPhotos.entries()).map(([photo_id, comment]) => ({
        photo_id,
        comment: comment || undefined
      }));

      await apiClient.post(`/api/galleries/extension/selection/public/${token}/submit`, {
        client_name: clientName,
        client_email: clientEmail || undefined,
        general_comment: generalComment || undefined,
        items
      });

      setSubmittedSuccess(true);
      toast.success('¡Selección enviada exitosamente!');
    } catch (e: any) {
      toast.error(e.response?.data?.detail || 'Error al enviar la selección.');
    } finally {
      setSubmitting(false);
    }
  };

  if (needPassword) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background p-4">
        <div className="w-full max-w-md p-6 rounded-2xl bg-card border border-border shadow-2xl space-y-4">
          <div className="text-center">
            <Lock className="mx-auto h-10 w-10 text-primary mb-2" />
            <h2 className="text-xl font-bold">Panel Protegido</h2>
            <p className="text-xs text-muted-foreground">Introduce la contraseña proporcionada por el emisor para ver el álbum.</p>
          </div>
          <form onSubmit={(e) => { e.preventDefault(); fetchPanelData(password); }} className="space-y-4">
            <Input
              type="password"
              placeholder="Contraseña"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? 'Verificando...' : 'Acceder'}
            </Button>
          </form>
        </div>
      </div>
    );
  }

  if (loading || !data) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (submittedSuccess) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background p-4">
        <motion.div initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} className="max-w-md w-full text-center p-8 rounded-3xl bg-card border border-border shadow-2xl space-y-4">
          <div className="h-16 w-16 bg-primary/10 text-primary rounded-full flex items-center justify-center mx-auto">
            <CheckCircle className="h-10 w-10" />
          </div>
          <h2 className="text-2xl font-bold">¡Gracias, {clientName}!</h2>
          <p className="text-sm text-muted-foreground">
            Hemos recibido tu selección de <strong>{selectedPhotos.size} foto(s)</strong> para el álbum &quot;{data.album.name}&quot;. El creador del álbum ha sido notificado.
          </p>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background text-foreground pb-24">
      {/* Header banner */}
      <header className="sticky top-0 z-40 bg-background/80 backdrop-blur-md border-b border-border/60 px-4 py-4 sm:px-8">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <span className="text-xs uppercase font-bold tracking-wider text-primary flex items-center gap-1">
              <Sparkles className="h-3.5 w-3.5" /> Panel de Selección Interactivo
            </span>
            <h1 className="text-2xl font-bold">{data.album.name}</h1>
            {data.album.description && <p className="text-xs text-muted-foreground mt-0.5">{data.album.description}</p>}
          </div>
          <div className="flex items-center gap-3">
            <Badge variant="outline" className="text-xs py-1.5 px-3 bg-primary/5 border-primary/20">
              {selectedPhotos.size} {data.max_selections ? `/ ${data.max_selections}` : ''} seleccionadas
            </Badge>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-8 pt-6 space-y-8">
        {/* Client form inputs */}
        <section className="p-6 rounded-3xl bg-card border border-border/80 shadow-sm space-y-4">
          <h3 className="text-base font-bold flex items-center gap-2 text-primary">
            1. Tus Datos de Envío
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="cName">Tu Nombre (Requerido)</Label>
              <Input id="cName" placeholder="Ej: Maria Lopez" value={clientName} onChange={(e) => setClientName(e.target.value)} />
            </div>
            <div>
              <Label htmlFor="cEmail">Tu Email (Opcional)</Label>
              <Input id="cEmail" placeholder="maria@ejemplo.com" value={clientEmail} onChange={(e) => setClientEmail(e.target.value)} />
            </div>
          </div>
          <div>
            <Label htmlFor="cComm">Notas o Comentarios Generales para el creador</Label>
            <Textarea id="cComm" rows={2} placeholder="Ej: Me encantaron estas fotos para el álbum final..." value={generalComment} onChange={(e) => setGeneralComment(e.target.value)} />
          </div>
        </section>

        {/* Photo selection grid */}
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-bold flex items-center gap-2 text-primary">
              2. Haz clic en las fotos que deseas seleccionar
            </h3>
            <span className="text-xs text-muted-foreground">Toca una foto para marcarla</span>
          </div>

          <div className="columns-2 sm:columns-3 md:columns-4 lg:columns-5 gap-4">
            {data.album.photos.map((photo, index) => {
              const isSelected = selectedPhotos.has(photo.id);
              const photoComment = selectedPhotos.get(photo.id);
              const imageSrc = photo.thumbnail_path ? `/thumbnails/${photo.thumbnail_path}` : `/media/${photo.file_path}`;

              return (
                <div
                  key={photo.id}
                  onClick={() => toggleSelectPhoto(photo.id)}
                  className={`relative break-inside-avoid mb-4 rounded-2xl overflow-hidden cursor-pointer border-2 transition-all duration-300 hover:scale-[1.02] active:scale-[0.98] group shadow-sm will-change-transform ${
                    isSelected ? 'border-primary ring-4 ring-primary/20' : 'border-border/60 hover:border-primary/40'
                  }`}
                >
                  <PhotoThumbnail photo={photo} />

                  {/* Selection Overlay Checkmark */}
                  <div className={`absolute top-3 left-3 h-7 w-7 rounded-full flex items-center justify-center transition-all ${
                    isSelected ? 'bg-primary text-primary-foreground shadow-lg scale-110' : 'bg-black/40 text-white opacity-60 group-hover:opacity-100'
                  }`}>
                    <Check className="h-4 w-4 stroke-[3]" />
                  </div>

                  {/* Zoom button for Lightbox */}
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      setLightboxIndex(index);
                      setLightboxOpen(true);
                    }}
                    className="absolute top-3 right-3 p-1.5 rounded-full bg-black/60 backdrop-blur-md text-white hover:bg-black transition-colors opacity-0 group-hover:opacity-100 focus:opacity-100"
                    title="Ver en pantalla completa"
                  >
                    <ZoomIn className="h-4 w-4" />
                  </button>

                  {/* Comment trigger badge */}
                  {data.allow_comments && isSelected && (
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setActiveCommentPhoto(photo);
                        setTempComment(photoComment || '');
                      }}
                      className="absolute bottom-3 right-3 p-2 rounded-full bg-black/70 backdrop-blur-md text-white hover:bg-black transition-colors"
                      title="Agregar comentario a esta foto"
                    >
                      <MessageSquare className="h-3.5 w-3.5" />
                    </button>
                  )}

                  {/* Display comment tag if exists */}
                  {photoComment && (
                    <div className="absolute inset-x-0 bottom-0 bg-black/80 text-white p-2 text-[10px] truncate backdrop-blur-xs">
                      💬 {photoComment}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </section>
      </main>

      {/* Floating Submit Bar */}
      <div className="fixed bottom-0 inset-x-0 bg-background/90 backdrop-blur-md border-t border-border/80 p-4 z-50">
        <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
          <div className="text-sm">
            <span className="font-bold">{selectedPhotos.size}</span> fotos seleccionadas
          </div>
          <Button size="lg" onClick={handleSubmitSelection} disabled={submitting || selectedPhotos.size === 0} className="rounded-2xl px-8 shadow-xl">
            <Send className="mr-2 h-4 w-4" /> {submitting ? 'Enviando...' : 'Enviar Selección'}
          </Button>
        </div>
      </div>

      {/* Photo comment modal */}
      <Dialog open={!!activeCommentPhoto} onOpenChange={(o) => !o && setActiveCommentPhoto(null)}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <MessageSquare className="h-5 w-5 text-primary" /> Comentario de la Foto
            </DialogTitle>
            <DialogDescription>Añade una nota o detalle específico sobre esta imagen.</DialogDescription>
          </DialogHeader>
          <div className="py-2 space-y-4">
            <Textarea
              rows={3}
              placeholder="Ej: Prefiero esta opción recortada en formato vertical..."
              value={tempComment}
              onChange={(e) => setTempComment(e.target.value)}
            />
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setActiveCommentPhoto(null)}>Cancelar</Button>
            <Button onClick={handleSavePhotoComment}>Guardar Nota</Button>
          </div>
        </DialogContent>
      </Dialog>

      {data && (
        <Lightbox
          open={lightboxOpen}
          close={() => setLightboxOpen(false)}
          slides={data.album.photos.map(p => ({ src: `/media/${p.file_path}` }))}
          index={lightboxIndex}
        />
      )}
    </div>
  );
};
