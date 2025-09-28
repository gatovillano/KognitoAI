'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { toast } from 'sonner';
import apiClient from '@/lib/api';
import { Copy, Trash2 } from 'lucide-react';

interface ShareAlbumModalProps {
  isOpen: boolean;
  onClose: () => void;
  albumId: string;
}

interface SharedLinkResponse {
  id: string;
  album_id: string;
  token: string;
  has_password: boolean;
  expiry_date: string | null;
  created_at: string;
}

const ShareAlbumModal: React.FC<ShareAlbumModalProps> = ({ isOpen, onClose, albumId }) => {
  const [password, setPassword] = useState('');
  const [expiryDays, setExpiryDays] = useState<number | ''>(0);
  const [generatedLink, setGeneratedLink] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [existingLinks, setExistingLinks] = useState<SharedLinkResponse[]>([]);
  const [showPassword, setShowPassword] = useState(false); // State to toggle password visibility
  const [allowDownload, setAllowDownload] = useState(true); // NEW STATE for download permission

interface SharedLinkResponse {
  id: string;
  album_id: string;
  token: string;
  has_password: boolean;
  expiry_date: string | null;
  created_at: string;
  allow_download: boolean; // NEW FIELD
}

  const fetchExistingLinks = useCallback(async () => {
    if (!albumId) return;
    try {
      const response = await apiClient.get<SharedLinkResponse[]>(`${process.env.NEXT_PUBLIC_API_URL}/api/galleries/albums/${albumId}/share-links`);
      setExistingLinks(response.data);
    } catch (e: any) {
      console.error('Error fetching existing share links:', e);
      toast.error('Error al cargar los enlaces compartidos existentes.');
    }
  }, [albumId]); // Add albumId to the dependency array

  useEffect(() => {
    if (isOpen && albumId) {
      fetchExistingLinks();
      setGeneratedLink(null); // Clear generated link on open
      setPassword('');
      setExpiryDays(0);
      setError(null);
    }
  }, [isOpen, albumId, fetchExistingLinks]);

  const handleGenerateLink = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setGeneratedLink(null);

    try {
      const payload: { password?: string; expiry_days?: number; allow_download?: boolean } = {};
      if (password) payload.password = password;
      if (expiryDays !== 0) payload.expiry_days = Number(expiryDays);
      payload.allow_download = allowDownload; // Include allowDownload in the payload

      const response = await apiClient.post<SharedLinkResponse>(`${process.env.NEXT_PUBLIC_API_URL}/api/galleries/albums/${albumId}/share-link`, payload);
      const fullLink = `${window.location.origin}/share/${response.data.token}`;
      setGeneratedLink(fullLink);
      toast.success('Enlace generado exitosamente!');
      fetchExistingLinks(); // Refresh list of existing links
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message || 'Error al generar el enlace.');
      toast.error('Error al generar el enlace.');
    } finally {
      setLoading(false);
    }
  };

  const handleRevokeLink = async (token: string) => {
    if (!confirm('¿Estás seguro de que quieres revocar este enlace? Ya no será accesible.')) return;
    try {
      await apiClient.delete(`${process.env.NEXT_PUBLIC_API_URL}/api/galleries/share/${token}`);
      toast.success('Enlace revocado exitosamente.');
      fetchExistingLinks(); // Refresh list
    } catch (e: any) {
      console.error('Error revoking link:', e);
      toast.error('Error al revocar el enlace.');
    }
  };

  const handleCopyLink = (link: string) => {
    navigator.clipboard.writeText(link);
    toast.info('Enlace copiado al portapapeles.');
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Compartir Álbum</DialogTitle>
          <DialogDescription>
            Genera enlaces compartibles para tu álbum o gestiona los existentes.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Generate New Link Section */}
          <section>
            <h3 className="text-lg font-semibold mb-3">Generar Nuevo Enlace</h3>
            <form onSubmit={handleGenerateLink} className="space-y-4">
              <div>
                <Label htmlFor="password">Contraseña (Opcional)</Label>
                <div className="relative">
                  <Input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Deja vacío para no proteger"
                    disabled={loading}
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="absolute right-0 top-0 h-full px-3 py-0"
                    onClick={() => setShowPassword(!showPassword)}
                  >
                    {showPassword ? 'Ocultar' : 'Mostrar'}
                  </Button>
                </div>
              </div>
              <div>
                <Label htmlFor="expiryDays">Caducidad (Días, Opcional)</Label>
                <Input
                  id="expiryDays"
                  type="number"
                  value={expiryDays}
                  onChange={(e) => setExpiryDays(e.target.value === '' ? '' : Number(e.target.value))}
                  placeholder="Deja vacío para no caducar"
                  min="0"
                  disabled={loading}
                />
              </div>
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="allowDownload"
                  checked={allowDownload}
                  onCheckedChange={(checked) => setAllowDownload(checked as boolean)}
                  disabled={loading}
                />
                <Label htmlFor="allowDownload">Permitir descarga de fotos</Label>
              </div>
              {error && <p className="text-red-500 text-sm">Error: {error}</p>}
              <Button type="submit" disabled={loading} className="w-full">
                {loading ? 'Generando...' : 'Generar Enlace'}
              </Button>
            </form>
            {generatedLink && (
              <div className="mt-4 p-3 bg-gray-100 dark:bg-gray-700 rounded-md flex items-center justify-between gap-2">
                <span className="text-sm truncate">{generatedLink}</span>
                <Button size="sm" variant="ghost" onClick={() => handleCopyLink(generatedLink)} title="Copiar enlace">
                  <Copy className="h-4 w-4" />
                </Button>
              </div>
            )}
          </section>

          <hr className="border-t border-gray-200 dark:border-gray-700" />

          {/* Existing Links Section */}
          <section>
            <h3 className="text-lg font-semibold mb-3">Enlaces Existentes</h3>
            {existingLinks.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center">No hay enlaces compartidos para este álbum.</p>
            ) : (
              <div className="space-y-3">
                {existingLinks.map((link) => (
                  <div key={link.id} className="p-3 bg-gray-50 dark:bg-gray-700 rounded-md flex items-center justify-between gap-2">
                    <div className="flex flex-col text-sm truncate">
                      <span className="font-medium truncate">
                        {`${window.location.origin}/share/${link.token}`}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {link.has_password && 'Protegido con contraseña | '}
                        {link.expiry_date ? `Caduca: ${new Date(link.expiry_date).toLocaleDateString()}` : 'No caduca'}
                        {!link.allow_download && ' | Descarga deshabilitada'}
                      </span>
                    </div>
                    <div className="flex items-center gap-1">
                      <Button size="sm" variant="ghost" onClick={() => handleCopyLink(`${window.location.origin}/share/${link.token}`)} title="Copiar enlace">
                        <Copy className="h-4 w-4" />
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => handleRevokeLink(link.token)} title="Revocar enlace">
                        <Trash2 className="h-4 w-4 text-red-500" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>

        <div className="flex justify-end">
          <Button onClick={onClose}>Cerrar</Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default ShareAlbumModal;
