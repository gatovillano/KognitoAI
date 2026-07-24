'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { toast } from 'sonner';
import apiClient from '@/lib/api';
import { Copy, Trash2, Link as LinkIcon, CheckCircle2, MessageSquare, Shield } from 'lucide-react';

interface ShareModalProps {
  isOpen: boolean;
  onClose: () => void;
  albumId: string;
}

interface SelectionLink {
  id: string;
  album_id: string;
  token: string;
  has_password: boolean;
  expiry_date: string | null;
  allow_comments: boolean;
  max_selections: number | null;
  created_at: string;
}

interface StandardLink {
  id: string;
  album_id: string;
  token: string;
  has_password: boolean;
  expiry_date: string | null;
  created_at: string;
  allow_download: boolean;
}

export const ExtensionShareModal: React.FC<ShareModalProps> = ({ isOpen, onClose, albumId }) => {
  const [activeTab, setActiveTab] = useState<'standard' | 'selection'>('selection');
  
  // Standard link state
  const [stdPassword, setStdPassword] = useState('');
  const [stdExpiryDays, setStdExpiryDays] = useState<number | ''>(0);
  const [stdAllowDownload, setStdAllowDownload] = useState(true);
  const [stdGeneratedLink, setStdGeneratedLink] = useState<string | null>(null);
  const [stdExistingLinks, setStdExistingLinks] = useState<StandardLink[]>([]);

  // Selection link state
  const [selPassword, setSelPassword] = useState('');
  const [selExpiryDays, setSelExpiryDays] = useState<number | ''>(0);
  const [selAllowComments, setSelAllowComments] = useState(true);
  const [selMaxSelections, setSelMaxSelections] = useState<number | ''>('');
  const [selGeneratedLink, setSelGeneratedLink] = useState<string | null>(null);
  const [selExistingLinks, setSelExistingLinks] = useState<SelectionLink[]>([]);

  const [loading, setLoading] = useState(false);

  const fetchStandardLinks = useCallback(async () => {
    if (!albumId) return;
    try {
      const res = await apiClient.get<StandardLink[]>(`/api/galleries/albums/${albumId}/share-links`);
      setStdExistingLinks(res.data);
    } catch (e) {
      console.error(e);
    }
  }, [albumId]);

  const fetchSelectionLinks = useCallback(async () => {
    if (!albumId) return;
    try {
      const res = await apiClient.get<SelectionLink[]>(`/api/galleries/extension/selection/albums/${albumId}/share-links`);
      setSelExistingLinks(res.data);
    } catch (e) {
      console.error(e);
    }
  }, [albumId]);

  useEffect(() => {
    if (isOpen && albumId) {
      fetchStandardLinks();
      fetchSelectionLinks();
      setStdGeneratedLink(null);
      setSelGeneratedLink(null);
    }
  }, [isOpen, albumId, fetchStandardLinks, fetchSelectionLinks]);

  const handleGenerateStandard = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const payload: any = { allow_download: stdAllowDownload };
      if (stdPassword) payload.password = stdPassword;
      if (stdExpiryDays !== 0) payload.expiry_days = Number(stdExpiryDays);

      const res = await apiClient.post<StandardLink>(`/api/galleries/albums/${albumId}/share-link`, payload);
      const full = `${window.location.origin}/share/${res.data.token}`;
      setStdGeneratedLink(full);
      toast.success('Enlace de galería estándar generado.');
      fetchStandardLinks();
    } catch (e: any) {
      toast.error('Error al generar enlace.');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateSelection = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const payload: any = { allow_comments: selAllowComments };
      if (selPassword) payload.password = selPassword;
      if (selExpiryDays !== 0) payload.expiry_days = Number(selExpiryDays);
      if (selMaxSelections !== '') payload.max_selections = Number(selMaxSelections);

      const res = await apiClient.post<SelectionLink>(`/api/galleries/extension/selection/albums/${albumId}/share-link`, payload);
      const full = `${window.location.origin}/share/selection/${res.data.token}`;
      setSelGeneratedLink(full);
      toast.success('Enlace de Panel de Selección generado.');
      fetchSelectionLinks();
    } catch (e: any) {
      toast.error('Error al generar Panel de Selección.');
    } finally {
      setLoading(false);
    }
  };

  const handleRevokeStandard = async (token: string) => {
    if (!confirm('¿Revocar este enlace estándar?')) return;
    try {
      await apiClient.delete(`/api/galleries/share/${token}`);
      toast.success('Enlace revocado.');
      fetchStandardLinks();
    } catch (e) {
      toast.error('Error al revocar enlace.');
    }
  };

  const handleRevokeSelection = async (token: string) => {
    if (!confirm('¿Revocar este Panel de Selección?')) return;
    try {
      await apiClient.delete(`/api/galleries/extension/selection/share-link/${token}`);
      toast.success('Panel de selección revocado.');
      fetchSelectionLinks();
    } catch (e) {
      toast.error('Error al revocar panel.');
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast.info('Copiado al portapapeles.');
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[650px] max-h-[90vh] overflow-y-auto bg-background/95 backdrop-blur-md border-border">
        <DialogHeader>
          <DialogTitle className="text-2xl font-bold flex items-center gap-2">
            <LinkIcon className="h-6 w-6 text-primary" />
            Compartir Álbum
          </DialogTitle>
          <DialogDescription>
            Elige la forma de compartición: Vista normal de galería o Panel interactivo de selección para destinatarios.
          </DialogDescription>
        </DialogHeader>

        <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as any)} className="w-full mt-4">
          <TabsList className="grid w-full grid-cols-2 p-1 bg-muted rounded-xl">
            <TabsTrigger value="selection" className="rounded-lg font-medium py-2 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground transition-all">
              🎯 Panel de Selección
            </TabsTrigger>
            <TabsTrigger value="standard" className="rounded-lg font-medium py-2 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground transition-all">
              🖼️ Galería Estándar
            </TabsTrigger>
          </TabsList>

          {/* SELECTION PANEL TAB */}
          <TabsContent value="selection" className="space-y-6 pt-4">
            <div className="p-4 rounded-xl bg-primary/5 border border-primary/20">
              <h4 className="font-semibold text-primary mb-1 flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4" /> ¿Cómo funciona el Panel de Selección?
              </h4>
              <p className="text-xs text-muted-foreground">
                Los destinatarios abren el enlace, ingresan su nombre, marcan sus fotos favoritas y te envían sus comentarios o notas sobre las imágenes elegidas.
              </p>
            </div>

            <form onSubmit={handleGenerateSelection} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="selPass">Contraseña (Opcional)</Label>
                  <Input
                    id="selPass"
                    type="password"
                    value={selPassword}
                    onChange={(e) => setSelPassword(e.target.value)}
                    placeholder="Protección opcional"
                  />
                </div>
                <div>
                  <Label htmlFor="selExp">Caducidad (Días)</Label>
                  <Input
                    id="selExp"
                    type="number"
                    value={selExpiryDays}
                    onChange={(e) => setSelExpiryDays(e.target.value === '' ? '' : Number(e.target.value))}
                    placeholder="Sin caducidad"
                    min="0"
                  />
                </div>
              </div>

              <div>
                <Label htmlFor="selMax">Límite Máximo de Selecciones (Opcional)</Label>
                <Input
                  id="selMax"
                  type="number"
                  value={selMaxSelections}
                  onChange={(e) => setSelMaxSelections(e.target.value === '' ? '' : Number(e.target.value))}
                  placeholder="Ej: 10 fotos (Vacío = sin límite)"
                  min="1"
                />
              </div>

              <div className="flex items-center space-x-2 pt-1">
                <Checkbox
                  id="selComm"
                  checked={selAllowComments}
                  onCheckedChange={(c) => setSelAllowComments(c as boolean)}
                />
                <Label htmlFor="selComm" className="cursor-pointer text-sm">Permitir que el destinatario deje comentarios en cada foto</Label>
              </div>

              <Button type="submit" disabled={loading} className="w-full">
                {loading ? 'Generando...' : 'Generar Enlace de Selección'}
              </Button>
            </form>

            {selGeneratedLink && (
              <div className="p-3 bg-primary/10 rounded-xl border border-primary/30 flex items-center justify-between gap-2">
                <span className="text-xs font-mono truncate text-primary">{selGeneratedLink}</span>
                <Button size="sm" onClick={() => copyToClipboard(selGeneratedLink)}>
                  <Copy className="h-4 w-4 mr-1" /> Copiar
                </Button>
              </div>
            )}

            <div className="space-y-3 pt-2">
              <h4 className="text-sm font-semibold text-muted-foreground">Paneles Activos</h4>
              {selExistingLinks.length === 0 ? (
                <p className="text-xs text-muted-foreground">No hay paneles de selección activos.</p>
              ) : (
                selExistingLinks.map((link) => (
                  <div key={link.id} className="p-3 rounded-lg border border-border bg-card flex items-center justify-between text-xs">
                    <div>
                      <p className="font-mono truncate max-w-[260px] sm:max-w-[340px]">
                        {`${window.location.origin}/share/selection/${link.token}`}
                      </p>
                      <p className="text-muted-foreground text-[11px] mt-0.5">
                        {link.has_password && '🔒 Protegido | '}
                        {link.allow_comments && '💬 Comentarios enabled | '}
                        {link.max_selections ? `Máx: ${link.max_selections} fotos` : 'Sin límite'}
                      </p>
                    </div>
                    <div className="flex gap-1">
                      <Button size="icon" variant="ghost" className="h-7 w-7" onClick={() => copyToClipboard(`${window.location.origin}/share/selection/${link.token}`)}>
                        <Copy className="h-3.5 w-3.5" />
                      </Button>
                      <Button size="icon" variant="ghost" className="h-7 w-7 text-destructive" onClick={() => handleRevokeSelection(link.token)}>
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </TabsContent>

          {/* STANDARD GALLERY TAB */}
          <TabsContent value="standard" className="space-y-6 pt-4">
            <form onSubmit={handleGenerateStandard} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="stdPass">Contraseña (Opcional)</Label>
                  <Input
                    id="stdPass"
                    type="password"
                    value={stdPassword}
                    onChange={(e) => setStdPassword(e.target.value)}
                    placeholder="Sin protección"
                  />
                </div>
                <div>
                  <Label htmlFor="stdExp">Caducidad (Días)</Label>
                  <Input
                    id="stdExp"
                    type="number"
                    value={stdExpiryDays}
                    onChange={(e) => setStdExpiryDays(e.target.value === '' ? '' : Number(e.target.value))}
                    placeholder="Sin caducidad"
                    min="0"
                  />
                </div>
              </div>

              <div className="flex items-center space-x-2 pt-1">
                <Checkbox
                  id="stdDown"
                  checked={stdAllowDownload}
                  onCheckedChange={(c) => setStdAllowDownload(c as boolean)}
                />
                <Label htmlFor="stdDown" className="cursor-pointer text-sm">Permitir descarga de imágenes</Label>
              </div>

              <Button type="submit" disabled={loading} className="w-full">
                {loading ? 'Generando...' : 'Generar Enlace de Galería'}
              </Button>
            </form>

            {stdGeneratedLink && (
              <div className="p-3 bg-muted rounded-xl border border-border flex items-center justify-between gap-2">
                <span className="text-xs font-mono truncate">{stdGeneratedLink}</span>
                <Button size="sm" onClick={() => copyToClipboard(stdGeneratedLink)}>
                  <Copy className="h-4 w-4 mr-1" /> Copiar
                </Button>
              </div>
            )}

            <div className="space-y-3 pt-2">
              <h4 className="text-sm font-semibold text-muted-foreground">Enlaces Estándar Activos</h4>
              {stdExistingLinks.length === 0 ? (
                <p className="text-xs text-muted-foreground">No hay enlaces estándar creados.</p>
              ) : (
                stdExistingLinks.map((link) => (
                  <div key={link.id} className="p-3 rounded-lg border border-border bg-card flex items-center justify-between text-xs">
                    <div>
                      <p className="font-mono truncate max-w-[260px] sm:max-w-[340px]">
                        {`${window.location.origin}/share/${link.token}`}
                      </p>
                      <p className="text-muted-foreground text-[11px] mt-0.5">
                        {link.has_password && '🔒 Protegido | '}
                        {link.allow_download ? 'Descarga activa' : 'Descarga bloqueada'}
                      </p>
                    </div>
                    <div className="flex gap-1">
                      <Button size="icon" variant="ghost" className="h-7 w-7" onClick={() => copyToClipboard(`${window.location.origin}/share/${link.token}`)}>
                        <Copy className="h-3.5 w-3.5" />
                      </Button>
                      <Button size="icon" variant="ghost" className="h-7 w-7 text-destructive" onClick={() => handleRevokeStandard(link.token)}>
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </TabsContent>
        </Tabs>

        <div className="flex justify-end pt-4 border-t border-border">
          <Button variant="outline" onClick={onClose}>Cerrar</Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};
