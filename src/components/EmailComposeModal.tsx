'use client';
import React, { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Sparkles } from 'lucide-react';
import apiClient from '@/lib/api';
import { toast } from 'sonner';

interface ComposeProps {
  isOpen: boolean;
  onClose: () => void;
  replyToUid?: string;
  originalSubject?: string;
  originalBody?: string;
  originalFrom?: string;
}

export function EmailComposeModal({ isOpen, onClose, replyToUid, originalSubject, originalBody, originalFrom }: ComposeProps) {
  const [to, setTo] = useState('');
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [aiInstructions, setAiInstructions] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [isDrafting, setIsDrafting] = useState(false);

  useEffect(() => {
    if (isOpen) {
      if (replyToUid) {
        setTo(originalFrom || '');
        setSubject(originalSubject?.startsWith('Re:') ? originalSubject : `Re: ${originalSubject}`);
        setBody(`\n\n--- El ${originalFrom} escribió:\n> ${originalBody?.split('\n').join('\n> ')}`);
      } else {
        setTo('');
        setSubject('');
        setBody('');
      }
      setAiInstructions('');
    }
  }, [isOpen, replyToUid, originalSubject, originalBody, originalFrom]);

  const handleSend = async () => {
    if (!to || !subject || !body) {
      toast.error('Completa los campos obligatorios.');
      return;
    }
    setIsSending(true);
    try {
      await apiClient.post('/api/email/send', {
        to_email: to,
        subject,
        body
      });
      toast.success('Correo enviado con éxito.');
      onClose();
    } catch (err) {
      console.error(err);
      toast.error('Error al enviar el correo.');
    } finally {
      setIsSending(false);
    }
  };

  const handleAIDraft = async () => {
    if (!aiInstructions) {
      toast.error('Especifica instrucciones para K Kai.');
      return;
    }
    setIsDrafting(true);
    try {
      const res = await apiClient.post('/api/email/ai-draft', {
        original_email_uid: replyToUid || null,
        instructions: aiInstructions,
        original_subject: originalSubject || null,
        original_body: originalBody || null
      });
      setBody(prev => `${res.data.draft}\n\n${prev}`);
      toast.success('Borrador inteligente insertado.');
    } catch (err) {
      console.error(err);
      toast.error('Error al generar el borrador.');
    } finally {
      setIsDrafting(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle>{replyToUid ? 'Responder Correo' : 'Redactar Nuevo Correo'}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-2">
          <div>
            <Label htmlFor="to_email">Destinatario (Email)</Label>
            <Input id="to_email" value={to} onChange={e => setTo(e.target.value)} placeholder="destinatario@dominio.com" />
          </div>
          <div>
            <Label htmlFor="subject">Asunto</Label>
            <Input id="subject" value={subject} onChange={e => setSubject(e.target.value)} />
          </div>
          
          {/* AI Assistant Composer Widget */}
          <div className="p-3 border border-primary/20 bg-primary/5 rounded-2xl space-y-2">
            <div className="flex items-center gap-1.5 text-primary text-xs font-bold uppercase tracking-wider">
              <Sparkles className="h-4 w-4 animate-pulse" />
              Redactar con K Kai
            </div>
            <div className="flex gap-2">
              <Input value={aiInstructions} onChange={e => setAiInstructions(e.target.value)} placeholder="Ej. 'Responde amablemente que estaré ocupado e indica agendar para el miércoles'" className="flex-1 text-sm bg-card" />
              <Button size="sm" onClick={handleAIDraft} disabled={isDrafting} className="rounded-full">
                {isDrafting ? 'Pensando...' : 'Generar'}
              </Button>
            </div>
          </div>

          <div>
            <Label htmlFor="body">Mensaje</Label>
            <Textarea id="body" value={body} onChange={e => setBody(e.target.value)} className="min-h-[250px] font-sans" />
          </div>
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="ghost" onClick={onClose}>Descartar</Button>
          <Button onClick={handleSend} disabled={isSending} className="rounded-full">
            {isSending ? 'Enviando...' : 'Enviar Correo'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
