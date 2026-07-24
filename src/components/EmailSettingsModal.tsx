'use client';
import React, { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import apiClient from '@/lib/api';
import { toast } from 'sonner';

interface SettingsProps {
  isOpen: boolean;
  onClose: () => void;
}

export function EmailSettingsModal({ isOpen, onClose }: SettingsProps) {
  const [provider, setProvider] = useState('custom');
  const [imapServer, setImapServer] = useState('');
  const [imapPort, setImapPort] = useState(993);
  const [imapSsl, setImapSsl] = useState(true);
  const [imapUser, setImapUser] = useState('');
  const [imapPass, setImapPass] = useState('');
  const [smtpServer, setSmtpServer] = useState('');
  const [smtpPort, setSmtpPort] = useState(465);
  const [smtpSsl, setSmtpSsl] = useState(true);
  const [smtpUser, setSmtpUser] = useState('');
  const [smtpPass, setSmtpPass] = useState('');
  const [clientId, setClientId] = useState('');
  const [clientSecret, setClientSecret] = useState('');
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (isOpen) {
      apiClient.get('/api/email/config')
        .then(res => {
          const data = res.data;
          setProvider(data.provider || 'custom');
          setImapServer(data.imap_server || '');
          setImapPort(data.imap_port || 993);
          setImapSsl(data.imap_ssl !== false);
          setImapUser(data.imap_user || '');
          setSmtpServer(data.smtp_server || '');
          setSmtpPort(data.smtp_port || 465);
          setSmtpSsl(data.smtp_ssl !== false);
          setSmtpUser(data.smtp_user || '');
          setClientId(data.google_client_id || '');
        }).catch(err => {
          console.error(err);
          toast.error('Error al cargar la configuración de correo');
        });
    }
  }, [isOpen]);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      const payload: any = {
        provider,
        imap_server: imapServer,
        imap_port: imapPort,
        imap_ssl: imapSsl,
        imap_user: imapUser,
        smtp_server: smtpServer,
        smtp_port: smtpPort,
        smtp_ssl: smtpSsl,
        smtp_user: smtpUser,
      };
      if (imapPass) payload.imap_password = imapPass;
      if (smtpPass) payload.smtp_password = smtpPass;
      if (clientId) payload.google_client_id = clientId;
      if (clientSecret) payload.google_client_secret = clientSecret;

      await apiClient.put('/api/email/config', payload);
      toast.success('Configuración de correo guardada con éxito.');
      onClose();
    } catch (err) {
      console.error(err);
      toast.error('Error al guardar configuración.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleGoogleAuth = async () => {
    try {
      if (clientId) {
        await apiClient.put('/api/email/config', { 
          provider, 
          google_client_id: clientId, 
          google_client_secret: clientSecret || undefined 
        });
      }
      const res = await apiClient.get('/api/email/oauth/url');
      window.location.href = res.data.url;
    } catch (err) {
      console.error(err);
      toast.error('Error al generar URL de conexión de Google OAuth. Configura Client ID.');
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Configuración de Correo Electrónico</DialogTitle>
          <DialogDescription>Configura tus servidores SMTP/IMAP tradicionales o conecta tu cuenta de Gmail de forma segura.</DialogDescription>
        </DialogHeader>
        
        <div className="space-y-4 py-2">
          <div className="flex flex-col gap-2">
            <Label>Proveedor</Label>
            <Select value={provider} onValueChange={setProvider}>
              <SelectTrigger>
                <SelectValue placeholder="Selecciona proveedor" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="custom">Servidor Personalizado (IMAP/SMTP)</SelectItem>
                <SelectItem value="google">Gmail (Google OAuth)</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {provider === 'custom' ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* IMAP */}
              <div className="space-y-3 p-4 border border-border/40 bg-muted/20 rounded-2xl">
                <h3 className="font-bold text-sm">Servidor de Entrada (IMAP)</h3>
                <div>
                  <Label htmlFor="imap_server">Servidor IMAP</Label>
                  <Input id="imap_server" value={imapServer} onChange={e => setImapServer(e.target.value)} placeholder="imap.ejemplo.com" />
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <Label htmlFor="imap_port">Puerto</Label>
                    <Input id="imap_port" type="number" value={imapPort} onChange={e => setImapPort(parseInt(e.target.value))} />
                  </div>
                  <div className="flex items-center justify-center pt-5">
                    <Label className="mr-2">SSL/TLS</Label>
                    <Switch checked={imapSsl} onCheckedChange={setImapSsl} />
                  </div>
                </div>
                <div>
                  <Label htmlFor="imap_user">Usuario / Email</Label>
                  <Input id="imap_user" value={imapUser} onChange={e => setImapUser(e.target.value)} />
                </div>
                <div>
                  <Label htmlFor="imap_pass">Contraseña / Token</Label>
                  <Input id="imap_pass" type="password" value={imapPass} onChange={e => setImapPass(e.target.value)} placeholder="••••••••••••" />
                </div>
              </div>

              {/* SMTP */}
              <div className="space-y-3 p-4 border border-border/40 bg-muted/20 rounded-2xl">
                <h3 className="font-bold text-sm">Servidor de Salida (SMTP)</h3>
                <div>
                  <Label htmlFor="smtp_server">Servidor SMTP</Label>
                  <Input id="smtp_server" value={smtpServer} onChange={e => setSmtpServer(e.target.value)} placeholder="smtp.ejemplo.com" />
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <Label htmlFor="smtp_port">Puerto</Label>
                    <Input id="smtp_port" type="number" value={smtpPort} onChange={e => setSmtpPort(parseInt(e.target.value))} />
                  </div>
                  <div className="flex items-center justify-center pt-5">
                    <Label className="mr-2">SSL/TLS</Label>
                    <Switch checked={smtpSsl} onCheckedChange={smtpSsl => setSmtpSsl(smtpSsl)} />
                  </div>
                </div>
                <div>
                  <Label htmlFor="smtp_user">Usuario / Email</Label>
                  <Input id="smtp_user" value={smtpUser} onChange={e => setSmtpUser(e.target.value)} />
                </div>
                <div>
                  <Label htmlFor="smtp_pass">Contraseña</Label>
                  <Input id="smtp_pass" type="password" value={smtpPass} onChange={e => setSmtpPass(e.target.value)} placeholder="••••••••••••" />
                </div>
              </div>
            </div>
          ) : (
            <div className="space-y-4 p-4 border border-border/40 bg-muted/20 rounded-2xl">
              <h3 className="font-bold text-sm">Configuración de Google Developer Console</h3>
              <p className="text-xs text-muted-foreground">Si no existe un cliente global configurado, puedes proveer el tuyo aquí:</p>
              <div>
                <Label htmlFor="client_id">Client ID de Google</Label>
                <Input id="client_id" value={clientId} onChange={e => setClientId(e.target.value)} />
              </div>
              <div>
                <Label htmlFor="client_secret">Client Secret de Google</Label>
                <Input id="client_secret" type="password" value={clientSecret} onChange={e => setClientSecret(e.target.value)} placeholder="••••••••••••" />
              </div>
              <div className="pt-2">
                <Button type="button" onClick={handleGoogleAuth} className="w-full bg-red-600 hover:bg-red-700 text-white rounded-full">
                  Conectarse con Google
                </Button>
              </div>
            </div>
          )}
        </div>
        
        <DialogFooter>
          <Button variant="ghost" onClick={onClose}>Cancelar</Button>
          <Button onClick={handleSave} disabled={isSaving} className="rounded-full">
            {isSaving ? 'Guardando...' : 'Guardar Cambios'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
