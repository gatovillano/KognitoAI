'use client';
import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Folder, Mail, RefreshCw, Settings, Sparkles, Send, FileText, ChevronRight, ChevronLeft } from 'lucide-react';
import { EmailSettingsModal } from './EmailSettingsModal';
import { EmailComposeModal } from './EmailComposeModal';
import { SafeHtmlViewer } from './SafeHtmlViewer';
import apiClient from '@/lib/api';
import { toast } from 'sonner';

export function EmailInboxView() {
  const [folders, setFolders] = useState<string[]>(['INBOX']);
  const [activeFolder, setActiveFolder] = useState('INBOX');
  const [messages, setMessages] = useState<any[]>([]);
  const [selectedMsg, setSelectedMsg] = useState<any | null>(null);
  const [msgDetail, setMsgDetail] = useState<any | null>(null);
  const [isLoadingMails, setIsLoadingMails] = useState(false);
  const [aiSummary, setAiSummary] = useState('');
  const [isSummarizing, setIsSummarizing] = useState(false);
  
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isComposeOpen, setIsComposeOpen] = useState(false);
  const [isReplyMode, setIsReplyMode] = useState(false);
  const [activeView, setActiveView] = useState<'folders' | 'list' | 'viewer'>('folders');

  useEffect(() => {
    // Fetch folders
    apiClient.get('/api/email/folders')
      .then(res => {
        if (res.data.folders && res.data.folders.length > 0) {
          setFolders(res.data.folders);
        }
      }).catch(err => {
        console.error(err);
        // Standard fallback
      });
  }, []);

  const loadMails = async (folder: string) => {
    setIsLoadingMails(true);
    try {
      const res = await apiClient.get(`/api/email/messages?folder=${encodeURIComponent(folder)}&limit=40`);
      setMessages(res.data.messages || []);
      setSelectedMsg(null);
      setMsgDetail(null);
      setAiSummary('');
    } catch (err) {
      console.error(err);
      toast.error('Error al cargar la bandeja de entrada.');
    } finally {
      setIsLoadingMails(false);
    }
  };

  useEffect(() => {
    loadMails(activeFolder);
  }, [activeFolder]);

  const selectMessage = async (msg: any) => {
    setSelectedMsg(msg);
    setMsgDetail(null);
    setAiSummary('');
    setActiveView('viewer');
    try {
      const res = await apiClient.get(`/api/email/messages/${msg.uid}?folder=${encodeURIComponent(activeFolder)}`);
      setMsgDetail(res.data);
    } catch (err) {
      console.error(err);
      toast.error('No se pudo abrir el mensaje.');
    }
  };

  const handleSummarize = async () => {
    if (!selectedMsg) return;
    setIsSummarizing(true);
    try {
      const res = await apiClient.post(`/api/email/messages/${selectedMsg.uid}/ai-summarize?folder=${encodeURIComponent(activeFolder)}`);
      setAiSummary(res.data.summary);
    } catch (err) {
      console.error(err);
      toast.error('No se pudo generar el resumen.');
    } finally {
      setIsSummarizing(false);
    }
  };

  const handleSaveToNotes = async () => {
    if (!msgDetail) return;
    try {
      await apiClient.post('/api/notes', {
        titulo: `Email: ${msgDetail.subject}`,
        contenido: `Remitente: ${msgDetail.from}\nFecha: ${msgDetail.date}\n\n${msgDetail.text}`
      });
      toast.success('Correo guardado en Notas e indexado en el Cerebro de K Kai.');
    } catch (err) {
      console.error(err);
      toast.error('No se pudo guardar la nota.');
    }
  };

  return (
    <div className="flex h-[calc(100vh-6rem)] w-full gap-4 overflow-hidden px-4 lg:pl-0 lg:pr-4">
      {/* Panel 1: Folders */}
      <div className={`${activeView === 'folders' ? 'flex' : 'hidden'} lg:flex w-full lg:w-56 bg-card/30 backdrop-blur-xl border border-border/40 p-4 rounded-3xl flex-col gap-3 shrink-0`}>
        <Button onClick={() => { setIsReplyMode(false); setIsComposeOpen(true); }} className="w-full rounded-full bg-primary hover:bg-primary/95 text-white gap-2 h-10 shadow-lg">
          <Send className="h-4 w-4" />
          Redactar
        </Button>
        <div className="border-t border-border/50 my-2" />
        <ScrollArea className="flex-1">
          <div className="space-y-1">
            {folders.map(f => (
              <Button
                key={f}
                variant={activeFolder === f ? 'secondary' : 'ghost'}
                onClick={() => { setActiveFolder(f); setActiveView('list'); }}
                className="w-full justify-start rounded-xl gap-2 font-normal text-sm"
              >
                <Folder className="h-4 w-4 text-muted-foreground" />
                <span className="truncate">{f}</span>
              </Button>
            ))}
          </div>
        </ScrollArea>
        <Button variant="outline" onClick={() => setIsSettingsOpen(true)} className="rounded-full gap-2 mt-auto border-border/40">
          <Settings className="h-4 w-4" />
          Configuración
        </Button>
      </div>

      {/* Panel 2: Message List */}
      <div className={`${activeView === 'list' ? 'flex' : 'hidden'} lg:flex w-full lg:w-80 bg-card/30 backdrop-blur-xl border border-border/40 rounded-3xl flex-col overflow-hidden shrink-0`}>
        <div className="p-4 border-b border-border/40 flex justify-between items-center bg-card/10">
          <div className="flex items-center gap-2 min-w-0">
            <Button
              size="icon"
              variant="ghost"
              onClick={() => setActiveView('folders')}
              className="lg:hidden h-8 w-8 rounded-full shrink-0"
            >
              <ChevronLeft className="h-4 w-4 text-muted-foreground" />
            </Button>
            <h2 className="font-bold text-sm tracking-tight truncate">{activeFolder}</h2>
          </div>
          <Button size="icon" variant="ghost" onClick={() => loadMails(activeFolder)} className="h-8 w-8 rounded-full">
            <RefreshCw className="h-4 w-4 text-muted-foreground" />
          </Button>
        </div>
        <ScrollArea className="flex-1">
          {isLoadingMails ? (
            <div className="flex justify-center p-8 text-sm text-muted-foreground">Buscando correos...</div>
          ) : messages.length === 0 ? (
            <div className="flex justify-center p-8 text-sm text-muted-foreground">Bandeja vacía</div>
          ) : (
            <div className="divide-y divide-border/20">
              {messages.map(msg => (
                <div
                  key={msg.uid}
                  onClick={() => selectMessage(msg)}
                  className={`p-3 cursor-pointer transition-all hover:bg-primary/5 ${selectedMsg?.uid === msg.uid ? 'bg-primary/10 border-l-4 border-primary' : ''}`}
                >
                  <div className="flex justify-between items-start mb-1 gap-2">
                    <span className="font-bold text-xs truncate max-w-[120px]">{msg.from.split('<')[0].trim()}</span>
                    <span className="text-[10px] text-muted-foreground shrink-0">{msg.date.split(',')[1]?.split('+')[0]?.trim() || msg.date}</span>
                  </div>
                  <h4 className="font-semibold text-xs text-foreground truncate mb-1">{msg.subject}</h4>
                  <p className="text-[11px] text-muted-foreground truncate">Haz clic para leer el mensaje completo.</p>
                </div>
              ))}
            </div>
          )}
        </ScrollArea>
      </div>

      {/* Panel 3: Viewer */}
      <div className={`${activeView === 'viewer' ? 'flex' : 'hidden'} lg:flex flex-1 w-full bg-card/30 backdrop-blur-xl border border-border/40 rounded-3xl flex-col overflow-hidden`}>
        {selectedMsg ? (
          msgDetail ? (
            <div className="flex-1 flex flex-col overflow-hidden">
              {/* Header */}
              <div className="p-4 border-b border-border/40 flex justify-between items-start bg-card/10 gap-4 shrink-0">
                <div className="min-w-0 flex-1 flex gap-2 items-start">
                  <Button
                    size="icon"
                    variant="ghost"
                    onClick={() => setActiveView('list')}
                    className="lg:hidden h-8 w-8 rounded-full shrink-0"
                  >
                    <ChevronLeft className="h-4 w-4 text-muted-foreground" />
                  </Button>
                  <div className="min-w-0 flex-1">
                    <h1 className="font-bold text-base text-foreground tracking-tight line-clamp-1">{msgDetail.subject}</h1>
                    <p className="text-xs text-muted-foreground mt-0.5 truncate">De: {msgDetail.from}</p>
                    <p className="text-xs text-muted-foreground mt-0.5 truncate">Para: {msgDetail.to}</p>
                  </div>
                </div>
                <div className="flex gap-1.5 shrink-0">
                  <Button size="sm" onClick={handleSummarize} disabled={isSummarizing} className="rounded-full bg-primary/10 hover:bg-primary/20 text-primary gap-1 border border-primary/20">
                    <Sparkles className="h-4 w-4" />
                    <span className="hidden sm:inline">{isSummarizing ? 'Resumiendo...' : 'Resumir'}</span>
                  </Button>
                  <Button size="sm" onClick={handleSaveToNotes} className="rounded-full bg-secondary/10 hover:bg-secondary/20 text-secondary gap-1 border border-secondary/20">
                    <FileText className="h-4 w-4" />
                    <span className="hidden sm:inline">Cerebro</span>
                  </Button>
                  <Button size="sm" onClick={() => { setIsReplyMode(true); setIsComposeOpen(true); }} className="rounded-full bg-primary hover:bg-primary/95 text-white">
                    Responder
                  </Button>
                </div>
              </div>

              {/* AI Summary Block */}
              {aiSummary && (
                <div className="m-4 p-4 border border-primary/20 bg-primary/5 rounded-2xl space-y-1 animate-fade-in shrink-0">
                  <div className="flex items-center gap-1.5 text-primary text-xs font-bold uppercase tracking-wider mb-2">
                    <Sparkles className="h-4 w-4 animate-pulse" />
                    Resumen Inteligente de K Kai
                  </div>
                  <div className="text-xs text-foreground leading-relaxed whitespace-pre-line">{aiSummary}</div>
                </div>
              )}

              {/* Body Viewer */}
              <div className="flex-1 p-4 overflow-hidden">
                <SafeHtmlViewer htmlContent={msgDetail.html} />
              </div>
            </div>
          ) : (
            <div className="flex-1 flex justify-center items-center text-sm text-muted-foreground">Abriendo mensaje...</div>
          )
        ) : (
          <div className="flex-1 flex flex-col justify-center items-center text-sm text-muted-foreground gap-3 relative">
            <Button
              size="icon"
              variant="ghost"
              onClick={() => setActiveView('list')}
              className="lg:hidden absolute top-4 left-4 h-8 w-8 rounded-full"
            >
              <ChevronLeft className="h-4 w-4 text-muted-foreground" />
            </Button>
            <Mail className="h-10 w-10 text-muted-foreground/50 animate-bounce" />
            Selecciona un correo para comenzar a leer
          </div>
        )}
      </div>

      {/* Modals */}
      <EmailSettingsModal isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} />
      <EmailComposeModal
        isOpen={isComposeOpen}
        onClose={() => setIsComposeOpen(false)}
        replyToUid={isReplyMode ? selectedMsg?.uid : undefined}
        originalSubject={isReplyMode ? msgDetail?.subject : undefined}
        originalBody={isReplyMode ? msgDetail?.text : undefined}
        originalFrom={isReplyMode ? msgDetail?.from : undefined}
      />
    </div>
  );
}
