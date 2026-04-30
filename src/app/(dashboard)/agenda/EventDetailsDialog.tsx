'use client';

import { toast } from 'sonner';
import { useState, useEffect } from 'react';
import { Pencil, Trash2, Calendar as CalendarIcon, Clock, MapPin, AlignLeft, Users, Briefcase, Activity, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';
import apiClient from '@/lib/api';

interface EventDetailsDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  onEditClick: (event: any) => void;
  onDeleteClick: (event: any) => void;
  event: any;
}

export function EventDetailsDialog({ isOpen, onOpenChange, onEditClick, onDeleteClick, event }: EventDetailsDialogProps) {
  const [workspaces, setWorkspaces] = useState<any[]>([]);
  const [loadingWorkspaces, setLoadingWorkspaces] = useState(false);
  const [linkedProfiles, setLinkedProfiles] = useState<any[]>([]);

  useEffect(() => {
    const fetchWorkspaces = async () => {
      setLoadingWorkspaces(true);
      try {
        const response = await apiClient.get('/api/workspaces?limit=100');
        if (response.data && Array.isArray(response.data.workspaces)) {
          setWorkspaces(response.data.workspaces);
        } else if (Array.isArray(response.data)) {
          setWorkspaces(response.data);
        }
      } catch (error) {
        console.error("Error fetching workspaces:", error);
      } finally {
        setLoadingWorkspaces(false);
      }
    };

    const fetchLinkedProfiles = async () => {
      if (event?.id) {
        try {
          const response = await apiClient.get(`/api/agenda/events/${event.id}/linked-profiles`);
          setLinkedProfiles(response.data);
        } catch (error) {
          console.error("Error fetching linked profiles:", error);
        }
      }
    };

    if (isOpen) {
      fetchWorkspaces();
      fetchLinkedProfiles();
    }
  }, [isOpen, event?.id]);

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[550px] bg-white/80 dark:bg-card/40 backdrop-blur-2xl border-white/20 dark:border-border/40 rounded-[2.5rem] shadow-2xl overflow-hidden p-0">
        <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-transparent pointer-events-none" />

        <DialogHeader className="p-8 pb-4 relative z-10">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-2xl bg-primary/10 text-primary shadow-inner">
                <CalendarIcon className="h-6 w-6" />
              </div>
              <DialogTitle className="text-3xl font-black tracking-tighter bg-gradient-to-r from-foreground to-foreground/70 bg-clip-text text-transparent">
                Detalles del Evento
              </DialogTitle>
            </div>
            <Badge variant="outline" className="rounded-full px-4 py-1 border-primary/20 bg-primary/5 text-primary font-bold uppercase tracking-widest text-[10px]">
              {event?.status || 'Pendiente'}
            </Badge>
          </div>
        </DialogHeader>

        <div className="p-8 pt-0 space-y-8 relative z-10 max-h-[70vh] overflow-y-auto custom-scrollbar">
          <div className="space-y-4">
            <h3 className="text-2xl font-black tracking-tight text-foreground/90 leading-tight">
              {event?.summary || 'Sin título'}
            </h3>
            {event?.description && (
              <div className="flex gap-3">
                <AlignLeft className="h-5 w-5 text-primary/50 shrink-0 mt-1" />
                <p className="text-muted-foreground leading-relaxed font-medium">
                  {event.description}
                </p>
              </div>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-6 rounded-[2rem] bg-primary/5 border border-primary/10">
            <div className="space-y-1">
              <p className="text-[10px] font-black uppercase tracking-widest text-primary/60">Inicio</p>
              <div className="flex items-center gap-2">
                <CalendarIcon className="h-4 w-4 text-primary" />
                <span className="font-bold text-sm">
                  {event?.event_datetime_local ? format(new Date(event.event_datetime_local), "PPP", { locale: es }) : 'N/A'}
                </span>
              </div>
              <div className="flex items-center gap-2 ml-6">
                <Clock className="h-3.5 w-3.5 text-primary/50" />
                <span className="font-medium text-xs text-muted-foreground">
                  {event?.event_datetime_local ? format(new Date(event.event_datetime_local), "HH:mm") : 'N/A'}
                </span>
              </div>
            </div>
            <div className="space-y-1 border-l border-primary/10 pl-4">
              <p className="text-[10px] font-black uppercase tracking-widest text-primary/60">Fin</p>
              <div className="flex items-center gap-2">
                <CalendarIcon className="h-4 w-4 text-primary" />
                <span className="font-bold text-sm">
                  {event?.end_date ? format(new Date(event.end_date), "PPP", { locale: es }) : 'N/A'}
                </span>
              </div>
              <div className="flex items-center gap-2 ml-6">
                <Clock className="h-3.5 w-3.5 text-primary/50" />
                <span className="font-medium text-xs text-muted-foreground">
                  {event?.end_date ? format(new Date(event.end_date), "HH:mm") : 'N/A'}
                </span>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {event?.location && (
              <div className="space-y-2">
                <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground/60">Ubicación</p>
                <div className="flex items-center gap-2">
                  <MapPin className="h-4 w-4 text-primary" />
                  <span className="font-bold text-sm truncate">{event.location}</span>
                </div>
              </div>
            )}
            <div className="space-y-2">
              <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground/60">Workspace</p>
              <div className="flex items-center gap-2">
                <Briefcase className="h-4 w-4 text-primary" />
                <span className="font-bold text-sm truncate">
                  {event?.workspace_id ? (workspaces.find(ws => ws.id.toString() === event.workspace_id)?.name || event.workspace_name || event.workspace_id) : 'Personal'}
                </span>
              </div>
            </div>
          </div>

          {(event?.attendees?.length > 0 || event?.external_attendees?.length > 0) && (
            <div className="space-y-4">
              <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground/60">Asistentes</p>
              <div className="flex flex-wrap gap-2">
                {event?.attendees?.map((id: string) => (
                  <Badge key={id} variant="secondary" className="rounded-xl px-3 py-1 bg-background/50 border-border/40 font-bold text-[10px]">
                    ID: {id}
                  </Badge>
                ))}
                {event?.external_attendees?.map((name: string) => (
                  <Badge key={name} variant="secondary" className="rounded-xl px-3 py-1 bg-background/50 border-border/40 font-bold text-[10px]">
                    {name}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          <div className="space-y-4">
            <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground/60">Perfiles Vinculados</p>
            <div className="flex flex-wrap gap-2 p-4 rounded-2xl bg-background/30 border border-border/40 min-h-[60px] items-center">
              {linkedProfiles.length === 0 ? (
                <span className="text-xs font-medium text-muted-foreground/60 italic">Ningún perfil vinculado...</span>
              ) : (
                linkedProfiles.map(profile => (
                  <div key={profile.id} className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-primary/10 border border-primary/20 text-primary text-[10px] font-black uppercase tracking-tighter transition-all hover:bg-primary/20">
                    {profile.name}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        <DialogFooter className="p-8 pt-4 bg-background/20 backdrop-blur-md border-t border-border/40 grid grid-cols-2 gap-4">
          <Button
            variant="destructive"
            className="h-12 rounded-2xl font-black uppercase tracking-widest text-[10px] gap-2 shadow-lg shadow-destructive/10 hover:shadow-destructive/20 transition-all"
            onClick={() => onDeleteClick(event)}
          >
            <Trash2 className="h-4 w-4" /> Eliminar
          </Button>
          <Button
            className="h-12 rounded-2xl bg-primary font-black uppercase tracking-widest text-[10px] gap-2 shadow-lg shadow-primary/10 hover:shadow-primary/20 transition-all"
            onClick={() => onEditClick(event)}
          >
            <Pencil className="h-4 w-4" /> Editar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
