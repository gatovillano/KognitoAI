'use client';

import React, { useState, useCallback } from 'react';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Loader2, Copy, Check, Link2, Calendar, Lock, AlertCircle } from 'lucide-react';
import { toast } from 'sonner';
import apiClient from '@/lib/api';

interface ShareAnalysisDialogProps {
    isOpen: boolean;
    onOpenChange: (open: boolean) => void;
    analysisId: string;
    analysisTitle: string;
}

export function ShareAnalysisDialog({
    isOpen,
    onOpenChange,
    analysisId,
    analysisTitle
}: ShareAnalysisDialogProps) {
    const [loading, setLoading] = useState(false);
    const [password, setPassword] = useState('');
    const [expiryDays, setExpiryDays] = useState<number | null>(null);
    const [allowDownload, setAllowDownload] = useState(true);
    const [shareUrl, setShareUrl] = useState<string | null>(null);
    const [copied, setCopied] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const resetState = useCallback(() => {
        setPassword('');
        setExpiryDays(null);
        setAllowDownload(true);
        setShareUrl(null);
        setCopied(false);
        setError(null);
    }, []);

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
            const response = await apiClient.post('/api/analysis/share/create', {
                analysis_id: analysisId,
                password: password || undefined,
                expiry_days: expiryDays || undefined,
                allow_download: allowDownload
            });

            const data = response.data;
            const fullUrl = `${window.location.origin}/share/analysis/${data.token}`;
            setShareUrl(fullUrl);
            toast.success('Enlace de compartir creado correctamente');
        } catch (e: any) {
            console.error('Error creating share link:', e);
            const errorMessage = e.response?.data?.detail || 'Error al crear el enlace de compartir';
            setError(errorMessage);
            toast.error(errorMessage);
        } finally {
            setLoading(false);
        }
    };

    const copyToClipboard = () => {
        if (shareUrl) {
            navigator.clipboard.writeText(shareUrl);
            setCopied(true);
            toast.success('Enlace copiado al portapapeles');
            setTimeout(() => setCopied(false), 2000);
        }
    };

    return (
        <Dialog open={isOpen} onOpenChange={handleOpenChange}>
            <DialogContent className="sm:max-w-[500px]">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <Link2 className="h-5 w-5" />
                        Compartir Análisis
                    </DialogTitle>
                    <DialogDescription>
                        Genera un enlace para compartir "{analysisTitle}" con otras personas.
                        El enlace permitirá ver el análisis sin necesidad de iniciar sesión.
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
                                    <Input
                                        value={shareUrl}
                                        readOnly
                                        className="flex-1"
                                    />
                                    <Button
                                        variant="outline"
                                        size="icon"
                                        onClick={copyToClipboard}
                                        disabled={copied}
                                    >
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
                                <Label htmlFor="password">Contraseña (opcional)</Label>
                                <Input
                                    id="password"
                                    type="password"
                                    placeholder="Sin contraseña"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                />
                                <p className="text-xs text-muted-foreground">
                                    Si estableces una contraseña, los usuarios deberán proporcionarla para ver el análisis.
                                </p>
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="expiry">Fecha de expiración (opcional)</Label>
                                <select
                                    id="expiry"
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
                                        Permitir descarga
                                    </Label>
                                    <p className="text-xs text-muted-foreground">
                                        Permitir que los visitantes descarguen el análisis como PDF
                                    </p>
                                </div>
                                <Switch
                                    checked={allowDownload}
                                    onCheckedChange={setAllowDownload}
                                />
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
