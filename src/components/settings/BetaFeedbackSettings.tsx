"use client";

import React, { useState, useEffect, useRef } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { toast } from 'sonner';
import apiClient from '@/lib/api';
import { Bug, Lightbulb, MessageSquare, Upload, CheckCircle2, Image as ImageIcon, X, Send, History, Clock, ShieldAlert } from 'lucide-react';

interface FeedbackItem {
  id: string;
  feedback_type: string;
  title: string;
  description: string;
  has_attachment: boolean;
  attachment_filename?: string;
  status: string;
  admin_notes?: string;
  created_at: string;
  updated_at: string;
}

export const BetaFeedbackSettings: React.FC = () => {
  const [feedbackType, setFeedbackType] = useState<'bug' | 'suggestion' | 'ux_experience'>('bug');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [includeMetadata, setIncludeMetadata] = useState(true);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const [myFeedbacks, setMyFeedbacks] = useState<FeedbackItem[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(true);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchHistory = async () => {
    try {
      setLoadingHistory(true);
      const res = await apiClient.get<FeedbackItem[]>('/api/feedback/me');
      setMyFeedbacks(res.data);
    } catch (err) {
      console.error('Error al cargar historial de feedback:', err);
    } finally {
      setLoadingHistory(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      if (file.size > 10 * 1024 * 1024) {
        toast.error('El archivo excede el tamaño máximo permitido de 10 MB.');
        return;
      }
      setSelectedFile(file);
      setPreviewUrl(URL.createObjectURL(file));
    }
  };

  const clearFile = () => {
    setSelectedFile(null);
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
      setPreviewUrl(null);
    }
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) {
      toast.error('Por favor ingresa un título para el reporte.');
      return;
    }
    if (!description.trim()) {
      toast.error('Por favor detalla tu experiencia o el error encontrado.');
      return;
    }

    setSubmitting(true);
    try {
      const formData = new FormData();
      formData.append('feedback_type', feedbackType);
      formData.append('title', title.trim());
      formData.append('description', description.trim());

      if (includeMetadata) {
        const metadata = {
          url: window.location.href,
          userAgent: navigator.userAgent,
          screenResolution: `${window.screen.width}x${window.screen.height}`,
          viewportSize: `${window.innerWidth}x${window.innerHeight}`,
          language: navigator.language,
          timestamp: new Date().toISOString()
        };
        formData.append('system_metadata', JSON.stringify(metadata));
      }

      if (selectedFile) {
        formData.append('file', selectedFile);
      }

      const res = await apiClient.post('/api/feedback', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      toast.success(res.data.message || 'Feedback enviado correctamente.');
      setTitle('');
      setDescription('');
      clearFile();
      fetchHistory();
    } catch (err: any) {
      console.error('Error al enviar feedback:', err);
      toast.error(err.response?.data?.detail || 'No se pudo enviar el feedback.');
    } finally {
      setSubmitting(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'new':
        return <Badge variant="secondary" className="bg-blue-500/10 text-blue-500 border-blue-500/20">Enviado</Badge>;
      case 'in_review':
        return <Badge variant="secondary" className="bg-amber-500/10 text-amber-500 border-amber-500/20">En Revisión</Badge>;
      case 'resolved':
        return <Badge variant="secondary" className="bg-green-500/10 text-green-500 border-green-500/20">Resuelto</Badge>;
      case 'archived':
        return <Badge variant="outline" className="text-muted-foreground">Archivado</Badge>;
      default:
        return <Badge variant="secondary">{status}</Badge>;
    }
  };

  const getTypeBadge = (type: string) => {
    switch (type) {
      case 'bug':
        return <Badge className="bg-red-500/10 text-red-500 border-red-500/20 gap-1"><Bug className="h-3 w-3" /> Error / Bug</Badge>;
      case 'suggestion':
        return <Badge className="bg-purple-500/10 text-purple-500 border-purple-500/20 gap-1"><Lightbulb className="h-3 w-3" /> Sugerencia</Badge>;
      case 'ux_experience':
        return <Badge className="bg-cyan-500/10 text-cyan-500 border-cyan-500/20 gap-1"><MessageSquare className="h-3 w-3" /> Experiencia UX</Badge>;
      default:
        return <Badge>{type}</Badge>;
    }
  };

  return (
    <div className="space-y-8">
      {/* Banner del programa Beta Tester */}
      <Card className="border-primary/20 bg-gradient-to-r from-primary/10 via-primary/5 to-transparent">
        <CardHeader className="pb-3">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-primary/20 text-primary">
              <Bug className="h-6 w-6" />
            </div>
            <div>
              <CardTitle className="text-xl">Programa Beta Tester de KognitoAI</CardTitle>
              <CardDescription className="text-sm">
                Tus opiniones y reportes directos ayudan a moldear el futuro de la plataforma. ¡Gracias por participar!
              </CardDescription>
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* Formulario de Envió */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg font-bold">Enviar Nuevo Comentario o Reporte</CardTitle>
          <CardDescription>
            Selecciona la categoría adecuada y describe tu experiencia o el error encontrado.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Categorías */}
            <div className="space-y-2">
              <Label className="text-sm font-semibold">Tipo de Feedback</Label>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <button
                  type="button"
                  onClick={() => setFeedbackType('bug')}
                  className={`p-4 rounded-xl border-2 text-left transition-all flex flex-col gap-2 ${
                    feedbackType === 'bug'
                      ? 'border-red-500 bg-red-500/5 shadow-sm'
                      : 'border-muted hover:border-muted-foreground/30 bg-card'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="p-2 rounded-lg bg-red-500/10 text-red-500">
                      <Bug className="h-5 w-5" />
                    </span>
                    {feedbackType === 'bug' && <CheckCircle2 className="h-5 w-5 text-red-500" />}
                  </div>
                  <div>
                    <h4 className="font-bold text-sm">Reporte de Error (Bug)</h4>
                    <p className="text-xs text-muted-foreground mt-1">Fallo inesperado, pantalla en blanco o comportamiento anómalo.</p>
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() => setFeedbackType('suggestion')}
                  className={`p-4 rounded-xl border-2 text-left transition-all flex flex-col gap-2 ${
                    feedbackType === 'suggestion'
                      ? 'border-purple-500 bg-purple-500/5 shadow-sm'
                      : 'border-muted hover:border-muted-foreground/30 bg-card'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="p-2 rounded-lg bg-purple-500/10 text-purple-500">
                      <Lightbulb className="h-5 w-5" />
                    </span>
                    {feedbackType === 'suggestion' && <CheckCircle2 className="h-5 w-5 text-purple-500" />}
                  </div>
                  <div>
                    <h4 className="font-bold text-sm">Sugerencia o Idea</h4>
                    <p className="text-xs text-muted-foreground mt-1">Propuesta de nueva funcionalidad o mejora de un módulo existente.</p>
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() => setFeedbackType('ux_experience')}
                  className={`p-4 rounded-xl border-2 text-left transition-all flex flex-col gap-2 ${
                    feedbackType === 'ux_experience'
                      ? 'border-cyan-500 bg-cyan-500/5 shadow-sm'
                      : 'border-muted hover:border-muted-foreground/30 bg-card'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="p-2 rounded-lg bg-cyan-500/10 text-cyan-500">
                      <MessageSquare className="h-5 w-5" />
                    </span>
                    {feedbackType === 'ux_experience' && <CheckCircle2 className="h-5 w-5 text-cyan-500" />}
                  </div>
                  <div>
                    <h4 className="font-bold text-sm">Experiencia de Uso (UX)</h4>
                    <p className="text-xs text-muted-foreground mt-1">Comentarios sobre la fluidez, diseño visual o diseño general.</p>
                  </div>
                </button>
              </div>
            </div>

            {/* Asunto y Detalles */}
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="feedback-title">Título o Asunto breve *</Label>
                <Input
                  id="feedback-title"
                  placeholder={
                    feedbackType === 'bug' ? 'Ej: Error al conectar el proveedor OpenAI en la configuración' :
                    feedbackType === 'suggestion' ? 'Ej: Añadir filtro por etiquetas en la barra lateral' :
                    'Ej: La navegación entre chats se siente muy fluida'
                  }
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="feedback-desc">Detalles explicativos *</Label>
                <Textarea
                  id="feedback-desc"
                  placeholder="Describe los pasos para reproducir el problema o los detalles de tu experiencia..."
                  rows={4}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  required
                />
              </div>
            </div>

            {/* Subida de Imagen/Captura */}
            <div className="space-y-2">
              <Label>Captura de Pantalla / Archivo Adjunto (Opcional)</Label>
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileChange}
                accept="image/png,image/jpeg,image/webp,image/gif"
                className="hidden"
              />

              {!previewUrl ? (
                <div
                  onClick={() => fileInputRef.current?.click()}
                  className="border-2 border-dashed border-muted-foreground/25 hover:border-primary/50 rounded-xl p-6 text-center cursor-pointer transition-colors bg-muted/20 hover:bg-muted/40 flex flex-col items-center justify-center gap-2"
                >
                  <div className="p-3 rounded-full bg-primary/10 text-primary">
                    <Upload className="h-5 w-5" />
                  </div>
                  <div className="text-xs font-semibold">Haz clic para subir una captura de pantalla</div>
                  <p className="text-[11px] text-muted-foreground">Soporta PNG, JPG, WEBP o GIF (máx 10 MB)</p>
                </div>
              ) : (
                <div className="relative rounded-xl border p-3 bg-card flex items-center justify-between gap-4">
                  <div className="flex items-center gap-3 overflow-hidden">
                    <img src={previewUrl} alt="Vista previa" className="h-16 w-16 object-cover rounded-lg border" />
                    <div className="truncate">
                      <p className="text-xs font-bold truncate">{selectedFile?.name}</p>
                      <p className="text-[10px] text-muted-foreground">
                        {((selectedFile?.size || 0) / 1024 / 1024).toFixed(2)} MB
                      </p>
                    </div>
                  </div>
                  <Button type="button" variant="ghost" size="icon" onClick={clearFile} className="text-destructive hover:bg-destructive/10">
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              )}
            </div>

            {/* Toggle de Metadatos de Sistema */}
            <div className="flex items-center justify-between p-3.5 rounded-xl border bg-muted/20">
              <div className="space-y-0.5">
                <Label className="text-xs font-semibold flex items-center gap-1.5">
                  <ImageIcon className="h-3.5 w-3.5 text-primary" />
                  Incluir metadatos del navegador y la ruta actual
                </Label>
                <p className="text-[11px] text-muted-foreground">
                  Ayuda a los desarrolladores adjuntando automáticamente la URL, resolución de pantalla y tipo de navegador.
                </p>
              </div>
              <Switch
                checked={includeMetadata}
                onCheckedChange={setIncludeMetadata}
              />
            </div>

            <Button type="submit" disabled={submitting} className="w-full font-bold gap-2">
              {submitting ? (
                <>Enviando...</>
              ) : (
                <><Send className="h-4 w-4" /> Enviar Feedback</>
              )}
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Historial de Feedback del Usuario */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-lg font-bold flex items-center gap-2">
                <History className="h-5 w-5 text-primary" />
                Tus Reportes y Comentarios Enviados
              </CardTitle>
              <CardDescription>
                Seguimiento del estado de los comentarios que has aportado a la comunidad Beta.
              </CardDescription>
            </div>
            <Button variant="outline" size="sm" onClick={fetchHistory} disabled={loadingHistory}>
              Actualizar
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {loadingHistory ? (
            <div className="text-center py-6 text-xs text-muted-foreground">Cargando tus reportes...</div>
          ) : myFeedbacks.length === 0 ? (
            <div className="text-center py-8 text-xs text-muted-foreground italic border border-dashed rounded-xl">
              Aún no has enviado ningún reporte de feedback. ¡Sé el primero en compartir tu experiencia!
            </div>
          ) : (
            <div className="space-y-4">
              {myFeedbacks.map((fb) => (
                <div key={fb.id} className="p-4 rounded-xl border bg-card/50 hover:bg-card transition-colors space-y-2">
                  <div className="flex items-center justify-between flex-wrap gap-2">
                    <div className="flex items-center gap-2">
                      {getTypeBadge(fb.feedback_type)}
                      <h4 className="font-bold text-sm">{fb.title}</h4>
                    </div>
                    <div className="flex items-center gap-2">
                      {getStatusBadge(fb.status)}
                      <span className="text-[10px] text-muted-foreground flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {new Date(fb.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  </div>

                  <p className="text-xs text-muted-foreground leading-relaxed whitespace-pre-wrap">
                    {fb.description}
                  </p>

                  {fb.admin_notes && (
                    <div className="mt-3 p-3 rounded-lg bg-primary/5 border border-primary/20 text-xs">
                      <span className="font-bold text-primary block mb-1">Respuesta del Equipo de Administradores:</span>
                      <p className="text-muted-foreground">{fb.admin_notes}</p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};
