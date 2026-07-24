'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import NextImage from 'next/image';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import apiClient from '@/lib/api';
import { User, Calendar, MessageSquare, Trash2, CheckCircle2, Image as ImageIcon, Sparkles } from 'lucide-react';

interface PhotoItem {
  id: string;
  photo_id: string;
  comment?: string;
  photo?: {
    id: string;
    file_path: string;
    thumbnail_path?: string;
  };
}

interface Submission {
  id: string;
  share_link_id: string;
  album_id: string;
  client_name: string;
  client_email?: string;
  general_comment?: string;
  created_at: string;
  items: PhotoItem[];
}

export const ReceivedSelectionsView: React.FC<{ albumId: string }> = ({ albumId }) => {
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchSubmissions = useCallback(async () => {
    try {
      const res = await apiClient.get<Submission[]>(`/api/galleries/extension/selection/albums/${albumId}/submissions`);
      setSubmissions(res.data);
    } catch (e) {
      console.error(e);
      toast.error('Error al cargar selecciones recibidas.');
    } finally {
      setLoading(false);
    }
  }, [albumId]);

  useEffect(() => {
    fetchSubmissions();
  }, [fetchSubmissions]);

  const handleDelete = async (id: string) => {
    if (!confirm('¿Eliminar esta recepción de selección?')) return;
    try {
      await apiClient.delete(`/api/galleries/extension/selection/submissions/${id}`);
      toast.success('Selección eliminada.');
      fetchSubmissions();
    } catch (e) {
      toast.error('Error al eliminar.');
    }
  };

  if (loading) {
    return <div className="text-center py-8 text-muted-foreground text-sm">Cargando selecciones recibidas...</div>;
  }

  if (submissions.length === 0) {
    return (
      <div className="text-center py-12 p-6 rounded-2xl bg-card border border-border/60 shadow-sm">
        <Sparkles className="mx-auto h-12 w-12 text-primary/40 mb-3 animate-pulse" />
        <h3 className="text-lg font-semibold mb-1">Sin selecciones recibidas aún</h3>
        <p className="text-sm text-muted-foreground max-w-md mx-auto">
          Comparte este álbum usando el <strong>Panel de Selección</strong> para que tus clientes o destinatarios elijan y comenten sus fotos favoritas.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-xl font-bold flex items-center gap-2">
          <CheckCircle2 className="h-5 w-5 text-primary" />
          Selecciones Recibidas ({submissions.length})
        </h3>
      </div>

      <AnimatePresence>
        {submissions.map((sub) => (
          <motion.div
            key={sub.id}
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="rounded-2xl border border-border bg-card/60 backdrop-blur-md p-5 shadow-sm space-y-4"
          >
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-border/40">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center text-primary font-bold text-lg">
                  {sub.client_name.charAt(0).toUpperCase()}
                </div>
                <div>
                  <h4 className="font-bold text-base flex items-center gap-2">
                    {sub.client_name}
                    {sub.client_email && <span className="text-xs text-muted-foreground font-normal">({sub.client_email})</span>}
                  </h4>
                  <p className="text-xs text-muted-foreground flex items-center gap-1 mt-0.5">
                    <Calendar className="h-3.5 w-3.5" />
                    {new Date(sub.created_at).toLocaleString()}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant="secondary" className="bg-primary/10 text-primary border-primary/20 text-xs">
                  {sub.items.length} foto(s) elegida(s)
                </Badge>
                <Button size="icon" variant="ghost" className="h-8 w-8 text-destructive" onClick={() => handleDelete(sub.id)}>
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </div>

            {sub.general_comment && (
              <div className="p-3 rounded-xl bg-muted/50 text-sm text-foreground flex items-start gap-2.5">
                <MessageSquare className="h-4 w-4 text-primary mt-0.5 flex-shrink-0" />
                <div>
                  <span className="font-semibold text-xs text-muted-foreground block">Comentario General:</span>
                  <p className="italic text-xs sm:text-sm">{sub.general_comment}</p>
                </div>
              </div>
            )}

            <div>
              <h5 className="text-xs font-semibold text-muted-foreground mb-3 uppercase tracking-wider">Fotos Seleccionadas:</h5>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
                {sub.items.map((item) => (
                  <div key={item.id} className="relative group rounded-xl overflow-hidden border border-border bg-black/5 aspect-square flex flex-col">
                    {item.photo ? (
                      <NextImage
                        src={`/media/${item.photo.file_path}`}
                        alt="Foto seleccionada"
                        fill
                        className="object-cover group-hover:scale-105 transition-transform duration-300"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center bg-muted">
                        <ImageIcon className="h-6 w-6 text-muted-foreground" />
                      </div>
                    )}
                    {item.comment && (
                      <div className="absolute inset-x-0 bottom-0 bg-black/80 text-white p-2 text-[11px] backdrop-blur-xs line-clamp-2">
                        💬 {item.comment}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
};
