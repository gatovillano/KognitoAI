'use client';

import React, { useState, useCallback, useEffect } from 'react';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Loader2, Copy, Check, Link2, Calendar, Lock, AlertCircle, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import apiClient from '@/lib/api';

interface ShareChatDialogProps {
    isOpen: boolean;
    onOpenChange: (open: boolean) => void;
    threadId: string;
    threadTitle: string;
}

interface ShareChatResponse {
    id: string;
    thread_id: string;
    token: string;
    has_password: boolean;
    expiry_date: string | null;
    created_at: string;
    allow_reply: boolean;
    share_url: string;
}

export function ShareChatDialog({
    isOpen,
    onOpenChange,
    threadId,
    threadTitle
}: ShareChatDialogProps) {
    const [loading, setLoading] = useState(false);
    const [password, setPassword] = useState('');
    const [expiryDays, setExpiryDays] = useState<number | null>(null);
    const [allowReply, setAllowReply] = useState(false);
    const [shareUrl, setShareUrl] = useState<string | null>(null);
    const [copied, setCopied] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [existingLinks, setExistingLinks] = useState<ShareChatResponse[]>([]);

    const resetState = useCallback(() => {
        setPassword('');
        setExpiryDays(null);
        setAllowReply(false);
        setShareUrl(null);
        setCopied(false);
        setError(null);
    }, []);

    const fetchExistingLinks = useCallback(async () => {
        if (!threadId) return;
        try {
            const response = await apiClient.get<ShareChatResponse[]>('/api/chat/share/list', {
                params: { thread_id: threadId }
            });
            setExistingLinks(response.data);
        } catch (e) {
            console.error('Error fetching existing share links:', e);
        }
    }, [threadId]);

    useEffect(() => {
        if (isOpen && threadId) {
            fetchExistingLinks();
            setShareUrl(null);
            setPassword('');
            setExpiryDays(null);
            setError(null);
        }
    }, [isOpen, threadId, fetchExistingLinks]);

    const handleOpenChange = (open: boolean) => {
        if (!open) {
            resetState();
        }
        onOpenChange(open);
    };

    const createShareLink = async () => {
        setLoading(true);
        setError(null);

        try {
            const payload: { thread_id: string; password?: string; expiry_days?: number; allow_reply: boolean } = {
                thread_id: threadId,
                allow_reply: allowReply,
            };
            if (password) payload.password = password;
            if (expiryDays) payload.expiry_days = expiryDays;

            const response = await apiClient.post<ShareChatResponse>('/api/chat/share/create', payload);
            const data = response.data;
            const fullUrl = `${window.location.origin}/share/chat/${data.token}`;
            setShareUrl(fullUrl);
            toast.success('Enlace de compartir creado correctamente');
            fetchExistingLinks();
        } catch (e: any) {
            const errorMessage = e.response?.data?.detail || 'Error al crear el enlace de compartir';
            setError(errorMessage);
            toast.error(errorMessage);
        } finally {
            setLoading(false);
        }
    };

    const revokeLink = async (token: string) => {
        if (!confirm('¿Estás seguro de que quieres revocar este enlace?')) return;
        try {
            await apiClient.delete(`/api/chat/share/${token}`);
            toast.success('Enlace revocado exitosamente');
            fetchExistingLinks();
        } catch (e: any) {
            toast.error('Error al revocar el enlace');
        }
    };

    const copyToClipboard = (url?: string) => {
        const target = url || shareUrl;
        if (target) {
            navigator.clipboard.writeText(target);
            setCopied(true);
            toast.success('Enlace copiado al portapapeles');
            setTimeout(() => setCopied(false), 2000);
        }
    };

    return (
        <Dialog open={isOpen} onOpenChange={handleOpenChange}>
            <DialogContent className="sm:max-w-[550px] max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <Link2 className="h-5 w-5" />
                        Compartir Conversación
                    </DialogTitle>
                    <DialogDescription>
                        Genera un enlace para compartir "{threadTitle}" con otras personas.
                        El enlace permitirá ver la conversación sin necesidad de iniciar sesión.
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-6 py-4">
                    {error && (
                        <div className="flex items-center gap-2 p-3 rounded-md bg-destructive/10 text-destructive">
                            <AlertCircle className="h-4 w-4" />
                            <p className="text-sm">{error}</p>
                        </div>
                    )}

                    {shareUrl ? (
                        <div className="space-y-4">
                            <div className="p-4 rounded-md bg-muted space-y-3">
                                <Label>Enlace de compartir</Label>
                                <div className="flex gap-2">
                                    <Input value={shareUrl} readOnly className="flex-1" />
                                    <Button variant="outline" size="icon" onClick={() => copyToClipboard()} disabled={copied}>
                                        {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                                    </Button>
                                </div>
                            </div>
                            <div className="flex flex-wrap gap-2 text-sm text-muted-foreground">
                                {password && (
                                    <div className="flex items-center gap-1">
                                        <Lock className="h-3 w-3" />
                                        <span>Protegido con contraseña</span>
                                    </div>
                                )}
                                {expiryDays && (
                                    <div className="flex items-center gap-1">
                                        <Calendar className="h-3 w-3" />
                                        <span>Expira en {expiryDays} días</span>
                                    </div>
                                )}
                            </div>
                        </div>
                    ) : (
                        <div className="space-y-4">
                            <div className="space-y-2">
                                <Label htmlFor="chat-password">Contraseña (opcional)</Label>
                                <Input
                                    id="chat-password"
                                    type="password"
                                    placeholder="Sin contraseña"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                />
                                <p className="text-xs text-muted-foreground">
                                    Si estableces una contraseña, los visitantes deberán proporcionarla para ver la conversación.
                                </p>
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="chat-expiry">Fecha de expiración (opcional)</Label>
                                <select
                                    id="chat-expiry"
                                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                                    value={expiryDays || ''}
                                    onChange={(e) => setExpiryDays(e.target.value ? Number(e.target.value) : null)}
                                >
                                    <option value="">Sin fecha de expiración</option>
                                    <option value="1">1 día</option>
                                    <option value="7">7 días</option>
                                    <option value="30">30 días</option>
                                    <option value="90">90 días</option>
                                    <option value="365">365 días</option>
                                </select>
                            </div>

                            <div className="flex items-center justify-between rounded-md border p-4">
                                <div className="space-y-0.5">
                                    <Label className="flex items-center gap-2">
                                        Permitir respuesta
                                    </Label>
                                    <p className="text-xs text-muted-foreground">
                                        Permitir que los visitantes respondan a la conversación compartida
                                    </p>
                                </div>
                                <Switch checked={allowReply} onCheckedChange={setAllowReply} />
                            </div>
                        </div>
                    )}

                    {/* Existing share links */}
                    {existingLinks.length > 0 && (
                        <div className="space-y-3">
                            <Label className="text-sm font-medium">Enlaces existentes</Label>
                            <div className="space-y-2">
                                {existingLinks.map((link) => (
                                    <div key={link.id} className="p-3 rounded-md bg-muted/50 flex items-center justify-between gap-2">
                                        <div className="flex flex-col text-sm truncate flex-1 min-w-0">
                                            <span className="font-medium truncate">
                                                {`${window.location.origin}/share/chat/${link.token}`}
                                            </span>
                                            <span className="text-xs text-muted-foreground">
                                                {link.has_password && 'Protegido | '}
                                                {link.expiry_date ? `Expira: ${new Date(link.expiry_date).toLocaleDateString()}` : 'Sin expiración'}
                                            </span>
                                        </div>
                                        <div className="flex items-center gap-1 shrink-0">
                                            <Button size="sm" variant="ghost" onClick={() => copyToClipboard(`${window.location.origin}/share/chat/${link.token}`)} title="Copiar enlace">
                                                <Copy className="h-4 w-4" />
                                            </Button>
                                            <Button size="sm" variant="ghost" onClick={() => revokeLink(link.token)} title="Revocar enlace">
                                                <Trash2 className="h-4 w-4 text-red-500" />
                                            </Button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>

                <DialogFooter>
                    {!shareUrl ? (
                        <Button onClick={createShareLink} disabled={loading}>
                            {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                            Generar Enlace
                        </Button>
                    ) : (
                        <Button onClick={() => handleOpenChange(false)}>
                            Cerrar
                        </Button>
                    )}
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
