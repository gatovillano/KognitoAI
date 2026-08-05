"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';
import apiClient from '@/lib/api';
import { Bug, Lightbulb, MessageSquare, RefreshCw, Eye, Trash2, CheckCircle, Clock, ExternalLink, Filter, ShieldAlert, Monitor, User, Mail, Calendar, FileText } from 'lucide-react';

interface FeedbackItem {
  id: string;
  account_id: string;
  user_name: string;
  user_email: string;
  feedback_type: string;
  title: string;
  description: string;
  has_attachment: boolean;
  attachment_filename?: string;
  system_metadata?: Record<string, any>;
  status: string;
  admin_notes?: string;
  created_at: string;
  updated_at: string;
}

export const BetaFeedbackAdminPanel: React.FC = () => {
  const [feedbacks, setFeedbacks] = useState<FeedbackItem[]>([]);
  const [loading, setLoading] = useState(true);

  // Filters
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Selected for Dialog
  const [selectedFeedback, setSelectedFeedback] = useState<FeedbackItem | null>(null);
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  const [adminNotes, setAdminNotes] = useState('');
  const [currentStatus, setCurrentStatus] = useState('new');
  const [savingStatus, setSavingStatus] = useState(false);

  const fetchFeedbacks = useCallback(async () => {
    try {
      setLoading(true);
      const res = await apiClient.get<FeedbackItem[]>('/api/feedback/admin/all');
      setFeedbacks(res.data);
    } catch (err: any) {
      console.error('Error fetching admin feedbacks:', err);
      toast.error('No se pudieron cargar los reportes de feedback.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchFeedbacks();
  }, [fetchFeedbacks]);

  const handleOpenDetail = (item: FeedbackItem) => {
    setSelectedFeedback(item);
    setCurrentStatus(item.status);
    setAdminNotes(item.admin_notes || '');
    setIsDetailOpen(true);
  };

  const handleSaveAdminUpdate = async () => {
    if (!selectedFeedback) return;
    setSavingStatus(true);
    try {
      await apiClient.patch(`/api/feedback/admin/${selectedFeedback.id}`, {
        status: currentStatus,
        admin_notes: adminNotes.trim()
      });
      toast.success('Estado y notas del reporte actualizados.');
      setIsDetailOpen(false);
      fetchFeedbacks();
    } catch (err: any) {
      console.error('Error actualizando feedback:', err);
      toast.error(err.response?.data?.detail || 'No se pudo actualizar el reporte.');
    } finally {
      setSavingStatus(false);
    }
  };

  const handleDeleteFeedback = async (id: string) => {
    if (!confirm('¿Estás seguro de que deseas eliminar este reporte de feedback? Esta acción no se puede deshacer.')) {
      return;
    }
    try {
      await apiClient.delete(`/api/feedback/admin/${id}`);
      toast.success('Reporte eliminado con éxito.');
      if (selectedFeedback?.id === id) {
        setIsDetailOpen(false);
      }
      fetchFeedbacks();
    } catch (err: any) {
      console.error('Error al eliminar feedback:', err);
      toast.error('No se pudo eliminar el reporte.');
    }
  };

  // KPIs
  const totalCount = feedbacks.length;
  const newBugsCount = feedbacks.filter(f => f.feedback_type === 'bug' && f.status === 'new').length;
  const suggestionsCount = feedbacks.filter(f => f.feedback_type === 'suggestion').length;
  const uxCount = feedbacks.filter(f => f.feedback_type === 'ux_experience').length;

  // Filtered List
  const filteredFeedbacks = feedbacks.filter(f => {
    if (typeFilter !== 'all' && f.feedback_type !== typeFilter) return false;
    if (statusFilter !== 'all' && f.status !== statusFilter) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchTitle = f.title.toLowerCase().includes(q);
      const matchUser = f.user_name.toLowerCase().includes(q) || f.user_email.toLowerCase().includes(q);
      const matchDesc = f.description.toLowerCase().includes(q);
      if (!matchTitle && !matchUser && !matchDesc) return false;
    }
    return true;
  });

  const getTypeBadge = (type: string) => {
    switch (type) {
      case 'bug':
        return <Badge className="bg-red-500/10 text-red-500 border-red-500/20 gap-1"><Bug className="h-3 w-3" /> Error / Bug</Badge>;
      case 'suggestion':
        return <Badge className="bg-purple-500/10 text-purple-500 border-purple-500/20 gap-1"><Lightbulb className="h-3 w-3" /> Sugerencia</Badge>;
      case 'ux_experience':
        return <Badge className="bg-cyan-500/10 text-cyan-500 border-cyan-500/20 gap-1"><MessageSquare className="h-3 w-3" /> UX</Badge>;
      default:
        return <Badge>{type}</Badge>;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'new':
        return <Badge variant="secondary" className="bg-blue-500/10 text-blue-500 border-blue-500/20">Nuevo</Badge>;
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

  return (
    <div className="space-y-6">
      {/* Targetas KPI */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className="border-l-4 border-l-primary">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Feedback</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalCount}</div>
            <p className="text-xs text-muted-foreground mt-1">Reportes acumulados</p>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-red-500">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Bugs Nuevos</CardTitle>
            <Bug className="h-4 w-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-500">{newBugsCount}</div>
            <p className="text-xs text-muted-foreground mt-1">Requieren atención rápida</p>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-purple-500">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Sugerencias</CardTitle>
            <Lightbulb className="h-4 w-4 text-purple-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-purple-500">{suggestionsCount}</div>
            <p className="text-xs text-muted-foreground mt-1">Ideas para nuevas funciones</p>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-cyan-500">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Comentarios UX</CardTitle>
            <MessageSquare className="h-4 w-4 text-cyan-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-cyan-500">{uxCount}</div>
            <p className="text-xs text-muted-foreground mt-1">Feedback de usabilidad</p>
          </CardContent>
        </Card>
      </div>

      {/* Filtros y Buscador */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <CardTitle className="text-lg font-bold">Gestión de Feedback Beta Testers</CardTitle>
              <CardDescription>Inspecciona reportes, revisa capturas de pantalla y responde a los usuarios.</CardDescription>
            </div>
            <Button variant="outline" size="sm" onClick={fetchFeedbacks} disabled={loading} className="gap-2">
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
              Recargar
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-col md:flex-row items-center gap-3">
            <div className="relative flex-1 w-full">
              <Input
                placeholder="Buscar por usuario, email o título..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full"
              />
            </div>
            <div className="flex items-center gap-2 w-full md:w-auto">
              <Select value={typeFilter} onValueChange={setTypeFilter}>
                <SelectTrigger className="w-[160px]">
                  <SelectValue placeholder="Tipo" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos los Tipos</SelectItem>
                  <SelectItem value="bug">Error / Bug</SelectItem>
                  <SelectItem value="suggestion">Sugerencia</SelectItem>
                  <SelectItem value="ux_experience">Experiencia UX</SelectItem>
                </SelectContent>
              </Select>

              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-[160px]">
                  <SelectValue placeholder="Estado" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos los Estados</SelectItem>
                  <SelectItem value="new">Nuevos</SelectItem>
                  <SelectItem value="in_review">En Revisión</SelectItem>
                  <SelectItem value="resolved">Resueltos</SelectItem>
                  <SelectItem value="archived">Archivados</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Tabla */}
          <div className="border rounded-md overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Fecha</TableHead>
                  <TableHead>Usuario</TableHead>
                  <TableHead>Tipo</TableHead>
                  <TableHead>Título / Asunto</TableHead>
                  <TableHead>Adjunto</TableHead>
                  <TableHead>Estado</TableHead>
                  <TableHead className="text-right">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                      Cargando reportes de feedback...
                    </TableCell>
                  </TableRow>
                ) : filteredFeedbacks.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                      No se encontraron reportes con los filtros seleccionados.
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredFeedbacks.map((f) => (
                    <TableRow key={f.id} className="hover:bg-muted/50 cursor-pointer" onClick={() => handleOpenDetail(f)}>
                      <TableCell className="text-xs text-muted-foreground whitespace-nowrap">
                        {new Date(f.created_at).toLocaleDateString()} {new Date(f.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </TableCell>
                      <TableCell>
                        <div className="font-medium text-xs">{f.user_name}</div>
                        <div className="text-[10px] text-muted-foreground">{f.user_email}</div>
                      </TableCell>
                      <TableCell>{getTypeBadge(f.feedback_type)}</TableCell>
                      <TableCell className="font-semibold text-xs max-w-[250px] truncate">{f.title}</TableCell>
                      <TableCell>
                        {f.has_attachment ? (
                          <Badge variant="outline" className="text-[10px] bg-primary/5 text-primary border-primary/20">Sí</Badge>
                        ) : (
                          <span className="text-[10px] text-muted-foreground">-</span>
                        )}
                      </TableCell>
                      <TableCell>{getStatusBadge(f.status)}</TableCell>
                      <TableCell className="text-right" onClick={(e) => e.stopPropagation()}>
                        <div className="flex justify-end gap-1">
                          <Button variant="ghost" size="sm" onClick={() => handleOpenDetail(f)}>
                            <Eye className="h-4 w-4" />
                          </Button>
                          <Button variant="ghost" size="sm" className="text-destructive hover:bg-destructive/10" onClick={() => handleDeleteFeedback(f.id)}>
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      {/* Modal de Detalle de Feedback */}
      <Dialog open={isDetailOpen} onOpenChange={setIsDetailOpen}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          {selectedFeedback && (
            <>
              <DialogHeader>
                <div className="flex items-center justify-between gap-2 mr-4">
                  {getTypeBadge(selectedFeedback.feedback_type)}
                  <span className="text-xs text-muted-foreground">
                    {new Date(selectedFeedback.created_at).toLocaleString()}
                  </span>
                </div>
                <DialogTitle className="text-xl font-bold mt-2">
                  {selectedFeedback.title}
                </DialogTitle>
                <DialogDescription className="flex items-center gap-3 pt-1 text-xs">
                  <span className="flex items-center gap-1"><User className="h-3.5 w-3.5 text-primary" /> {selectedFeedback.user_name}</span>
                  <span className="flex items-center gap-1"><Mail className="h-3.5 w-3.5 text-primary" /> {selectedFeedback.user_email}</span>
                </DialogDescription>
              </DialogHeader>

              <div className="space-y-6 py-4">
                {/* Descripción del Feedback */}
                <div className="space-y-2">
                  <Label className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Detalles del Reporte</Label>
                  <div className="p-4 rounded-xl bg-muted/30 border text-sm leading-relaxed whitespace-pre-wrap">
                    {selectedFeedback.description}
                  </div>
                </div>

                {/* Captura Adjunta */}
                {selectedFeedback.has_attachment && (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <Label className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Captura de Pantalla Adjunta</Label>
                      <a
                        href={`/api/feedback/attachment/${selectedFeedback.id}`}
                        target="_blank"
                        rel="noreferrer"
                        className="text-xs text-primary font-semibold flex items-center gap-1 hover:underline"
                      >
                        Abrir en tamaño completo <ExternalLink className="h-3 w-3" />
                      </a>
                    </div>
                    <div className="rounded-xl border overflow-hidden bg-black/5 p-2 flex justify-center max-h-[350px]">
                      <img
                        src={`/api/feedback/attachment/${selectedFeedback.id}`}
                        alt="Captura adjunta"
                        className="max-h-[330px] object-contain rounded-lg shadow-sm"
                      />
                    </div>
                  </div>
                )}

                {/* Metadatos del Sistema */}
                {selectedFeedback.system_metadata && (
                  <div className="space-y-2">
                    <Label className="text-xs font-bold text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
                      <Monitor className="h-3.5 w-3.5 text-primary" /> Metadatos del Entorno
                    </Label>
                    <div className="p-3 rounded-xl border bg-muted/20 text-xs font-mono grid grid-cols-1 md:grid-cols-2 gap-2">
                      <div><span className="font-bold text-muted-foreground">Ruta / URL:</span> {selectedFeedback.system_metadata.url || 'N/A'}</div>
                      <div><span className="font-bold text-muted-foreground">Resolución:</span> {selectedFeedback.system_metadata.screenResolution || 'N/A'}</div>
                      <div className="col-span-2 truncate"><span className="font-bold text-muted-foreground">Navegador:</span> {selectedFeedback.system_metadata.userAgent || 'N/A'}</div>
                    </div>
                  </div>
                )}

                {/* Actualización de Estado y Notas de Admin */}
                <div className="space-y-4 pt-4 border-t">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="admin-status" className="text-xs font-bold">Cambiar Estado del Reporte</Label>
                      <Select value={currentStatus} onValueChange={setCurrentStatus}>
                        <SelectTrigger id="admin-status">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="new">Nuevo (Sin revisar)</SelectItem>
                          <SelectItem value="in_review">En Revisión</SelectItem>
                          <SelectItem value="resolved">Resuelto / Solucionado</SelectItem>
                          <SelectItem value="archived">Archivado</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="admin-notes" className="text-xs font-bold">Respuesta o Notas del Administrador (Visible para el usuario)</Label>
                    <Textarea
                      id="admin-notes"
                      placeholder="Escribe comentarios internos o una respuesta para que el usuario Beta la vea en su portal..."
                      rows={3}
                      value={adminNotes}
                      onChange={(e) => setAdminNotes(e.target.value)}
                    />
                  </div>
                </div>
              </div>

              <DialogFooter className="gap-2">
                <Button variant="outline" onClick={() => setIsDetailOpen(false)}>
                  Cancelar
                </Button>
                <Button onClick={handleSaveAdminUpdate} disabled={savingStatus} className="font-bold gap-2">
                  {savingStatus ? 'Guardando...' : 'Guardar Cambios'}
                </Button>
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};
