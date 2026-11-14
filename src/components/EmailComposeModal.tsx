'use client';
import React, { useState, useEffect, useRef } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Sparkles, Mic, MicOff, Loader2 } from 'lucide-react';
import apiClient from '@/lib/api';
import { toast } from 'sonner';
import { useAudioRecorder } from '@/hooks/useAudioRecorder';

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
  const [dictationTarget, setDictationTarget] = useState<'body' | 'aiInstructions'>('body');

  const dictationTargetRef = useRef<'body' | 'aiInstructions'>('body');
  useEffect(() => {
    dictationTargetRef.current = dictationTarget;
  }, [dictationTarget]);

  const {
    isRecording,
    isProcessingAudio,
    startRecording,
    stopRecording,
    clearTranscript
  } = useAudioRecorder({
    language: 'es',
    onTranscriptChunk: (chunk: string) => {
      const cleanChunk = chunk.trim();
      if (!cleanChunk) return;

      if (dictationTargetRef.current === 'body') {
        setBody(prev => {
          if (!prev) return cleanChunk + ' ';
          const separator = prev.endsWith(' ') || prev.endsWith('\n') ? '' : ' ';
          return `${prev}${separator}${cleanChunk} `;
        });
      } else {
        setAiInstructions(prev => {
          if (!prev) return cleanChunk + ' ';
          const separator = prev.endsWith(' ') ? '' : ' ';
          return `${prev}${separator}${cleanChunk} `;
        });
      }
    },
    onFinalTranscript: () => {
      toast.success('Dictado finalizado y procesado.');
    }
  });

  // Detener grabación si se cierra el modal
  useEffect(() => {
    if (!isOpen && isRecording) {
      stopRecording();
    }
  }, [isOpen, isRecording, stopRecording]);

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

  const handleToggleDictation = (target: 'body' | 'aiInstructions') => {
    if (isRecording) {
      if (dictationTarget === target) {
        stopRecording();
      } else {
        // Cambiar el objetivo sobre la marcha
        setDictationTarget(target);
      }
    } else {
      setDictationTarget(target);
      clearTranscript();
      startRecording();
    }
  };

  const handleSend = async () => {
    if (!to || !subject || !body) {
      toast.error('Completa los campos obligatorios.');
      return;
    }
    if (isRecording) {
      stopRecording();
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
    <Dialog open={isOpen} onOpenChange={(open) => {
      if (!open && isRecording) {
        stopRecording();
      }
      onClose();
    }}>
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
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5 text-primary text-xs font-bold uppercase tracking-wider">
                <Sparkles className="h-4 w-4 animate-pulse" />
                Redactar con K Kai
              </div>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => handleToggleDictation('aiInstructions')}
                disabled={isProcessingAudio}
                className={`h-7 px-2 text-xs rounded-full gap-1 transition-all ${
                  isRecording && dictationTarget === 'aiInstructions'
                    ? 'bg-red-500 text-white hover:bg-red-600 animate-pulse'
                    : 'text-primary/80 hover:text-primary hover:bg-primary/10'
                }`}
                title="Dictar instrucciones para K Kai"
              >
                {isRecording && dictationTarget === 'aiInstructions' ? (
                  <>
                    <MicOff className="h-3.5 w-3.5" />
                    <span>Detener</span>
                  </>
                ) : isProcessingAudio && dictationTarget === 'aiInstructions' ? (
                  <>
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    <span>Procesando</span>
                  </>
                ) : (
                  <>
                    <Mic className="h-3.5 w-3.5" />
                    <span>Dictar</span>
                  </>
                )}
              </Button>
            </div>
            <div className="flex gap-2">
              <Input
                value={aiInstructions}
                onChange={e => setAiInstructions(e.target.value)}
                placeholder="Ej. 'Responde amablemente que estaré ocupado e indica agendar para el miércoles'"
                className="flex-1 text-sm bg-card"
              />
              <Button size="sm" onClick={handleAIDraft} disabled={isDrafting} className="rounded-full">
                {isDrafting ? 'Pensando...' : 'Generar'}
              </Button>
            </div>
          </div>

          <div>
            <div className="flex justify-between items-center mb-1.5">
              <Label htmlFor="body" className="font-semibold text-sm">Mensaje</Label>
              <div className="flex items-center gap-2">
                {isRecording && dictationTarget === 'body' && (
                  <span className="flex items-center gap-1.5 text-xs text-red-500 font-medium animate-pulse">
                    <span className="h-2 w-2 rounded-full bg-red-500 inline-block animate-ping" />
                    Dictando con Whisper en vivo...
                  </span>
                )}
                {isProcessingAudio && dictationTarget === 'body' && (
                  <span className="flex items-center gap-1.5 text-xs text-muted-foreground font-medium">
                    <Loader2 className="h-3 w-3 animate-spin text-primary" />
                    Procesando audio final...
                  </span>
                )}
                <Button
                  type="button"
                  size="sm"
                  variant={isRecording && dictationTarget === 'body' ? 'destructive' : 'outline'}
                  onClick={() => handleToggleDictation('body')}
                  disabled={isProcessingAudio}
                  className={`h-8 rounded-full gap-1.5 px-3 text-xs transition-all ${
                    isRecording && dictationTarget === 'body'
                      ? 'shadow-md shadow-red-500/20'
                      : 'hover:bg-primary/10 hover:text-primary hover:border-primary/40'
                  }`}
                >
                  {isRecording && dictationTarget === 'body' ? (
                    <>
                      <MicOff className="h-3.5 w-3.5" />
                      <span>Detener Dictado</span>
                    </>
                  ) : isProcessingAudio && dictationTarget === 'body' ? (
                    <>
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      <span>Finalizando...</span>
                    </>
                  ) : (
                    <>
                      <Mic className="h-3.5 w-3.5 text-primary" />
                      <span>Dictar con Micrófono</span>
                    </>
                  )}
                </Button>
              </div>
            </div>
            <Textarea
              id="body"
              value={body}
              onChange={e => setBody(e.target.value)}
              className="min-h-[250px] font-sans"
              placeholder="Escribe o dicta tu mensaje aquí en tiempo real..."
            />
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
