// En: src/app/(dashboard)/agenda/page.tsx (VERSIÓN FINAL Y ROBUSTA)

'use client';

import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import apiClient from '@/lib/api';
import { toast } from 'sonner';
import { PlusCircle, Clock, Trash2, Users } from 'lucide-react';
import { EventDialog } from './event-dialog';
import { Calendar } from '@/components/ui/calendar';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';

export interface AgendaEvent {
  id: number;
  description: string;
  event_datetime_utc: string;
  event_datetime_local: string;
  user_timezone: string;
  team_shared?: boolean | string; // Indicates if shared with a team, can be boolean or team name/id
}

export default function AgendaPage() {
  const [allEvents, setAllEvents] = useState<AgendaEvent[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedDate, setSelectedDate] = useState<Date | undefined>(new Date());
  const [isWeekView, setIsWeekView] = useState(false);
  
  const [isEventDialogOpen, setIsEventDialogOpen] = useState(false);
  const [deletingEvent, setDeletingEvent] = useState<AgendaEvent | null>(null);

  const fetchEvents = async () => {
    setIsLoading(true);
    try {
      const response = await apiClient.post('/api/list-events');
      setAllEvents(response.data);
    } catch (error) {
      toast.error('Error al cargar los eventos.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => { fetchEvents(); }, []);

  const handleSaveSuccess = (newEvent: AgendaEvent) => {
    setAllEvents(prev => [...prev, newEvent].sort((a,b) => new Date(a.event_datetime_utc).getTime() - new Date(b.event_datetime_utc).getTime()));
  };

  const handleDeleteConfirm = async () => {
    if (!deletingEvent) return;
    const toastId = toast.loading('Cancelando evento...');
    try {
      await apiClient.post('/api/cancel-event', { event_id: deletingEvent.id });
      setAllEvents(allEvents.filter(e => e.id !== deletingEvent.id));
      toast.success('Evento cancelado', { id: toastId });
      setDeletingEvent(null);
    } catch (error) {
      toast.error('Error al cancelar el evento', { id: toastId });
    }
  };

  const eventsForSelectedPeriod = allEvents.filter(event => {
    if (!selectedDate) return false;
    const eventDate = new Date(event.event_datetime_local);
    if (isWeekView) {
      // Get start of the week for selected date (assuming week starts on Sunday)
      const startOfWeek = new Date(selectedDate);
      startOfWeek.setDate(selectedDate.getDate() - selectedDate.getDay());
      startOfWeek.setHours(0, 0, 0, 0);
      
      // Get end of the week
      const endOfWeek = new Date(startOfWeek);
      endOfWeek.setDate(startOfWeek.getDate() + 6);
      endOfWeek.setHours(23, 59, 59, 999);
      
      return eventDate >= startOfWeek && eventDate <= endOfWeek;
    } else {
      return (
        eventDate.getDate() === selectedDate.getDate() &&
        eventDate.getMonth() === selectedDate.getMonth() &&
        eventDate.getFullYear() === selectedDate.getFullYear()
      );
    }
  });

  return (
    <>
      <div className="p-6 h-full flex flex-col">
        <div className="flex items-center justify-between mb-6 shrink-0">
          <div>
            <h1 className="text-3xl font-bold">Agenda</h1>
            <p className="text-muted-foreground">Tus próximos eventos y recordatorios.</p>
          </div>
          <div className="flex gap-2">
            <Button onClick={() => setIsEventDialogOpen(true)}>
              <PlusCircle className="mr-2 h-4 w-4" />
              Agendar Evento
            </Button>
            <Button variant={isWeekView ? "default" : "outline"} onClick={() => setIsWeekView(true)}>
              Vista Semanal
            </Button>
            <Button variant={!isWeekView ? "default" : "outline"} onClick={() => setIsWeekView(false)}>
              Vista Diaria
            </Button>
          </div>
        </div>
        
        {/* ---- ESTRUCTURA DE LAYOUT CORREGIDA ---- */}
        <div className="flex-grow grid md:grid-cols-3 gap-6 min-h-0">
          <div className="md:col-span-1 flex justify-center md:justify-start">
              <Calendar
                  mode="single"
                  selected={selectedDate}
                  onSelect={setSelectedDate}
                  className="rounded-md border p-0"
                  classNames={{
                    month: "space-y-4 p-3",
                    caption_label: "text-sm font-medium",
                  }}
              />
          </div>

          <div className="md:col-span-2 flex flex-col min-h-0">
              <h2 className="text-xl font-semibold mb-4 shrink-0">
                  Eventos para {isWeekView ? "la semana del" : "el"} {selectedDate ? format(selectedDate, "PPP", { locale: es }) : "..."}
              </h2>
              <div className="flex-grow overflow-y-auto pr-2">
                {isLoading ? <p>Cargando eventos...</p> : (
                    <div className="space-y-4">
                        {eventsForSelectedPeriod.length > 0 ? (
                            eventsForSelectedPeriod.map((event) => (
                            <div key={event.id} className="p-4 border rounded-lg flex items-center justify-between hover:border-primary/50">
                                <div>
                                    <p className="font-semibold flex items-center">
                                        {event.description}
                                        {event.team_shared && (
                                            <span title="Compartido con equipo">
                                                <Users className="ml-2 h-4 w-4 text-blue-500" />
                                            </span>
                                        )}
                                    </p>
                                    <div className="text-sm text-muted-foreground flex items-center gap-1.5 mt-1">
                                        <Clock className="h-4 w-4" /> 
                                        {new Date(event.event_datetime_local).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}
                                    </div>
                                </div>
                                <div>
                                    <Button variant="ghost" size="icon" onClick={() => setDeletingEvent(event)}>
                                        <Trash2 className="h-4 w-4 text-destructive" />
                                    </Button>
                                </div>
                            </div>
                            ))
                        ) : (
                            <p className="text-center text-muted-foreground pt-10">No tienes eventos para {isWeekView ? "esta semana" : "este día"}.</p>
                        )}
                    </div>
                )}
              </div>
          </div>
        </div>
      </div>

      <EventDialog
        isOpen={isEventDialogOpen}
        onOpenChange={setIsEventDialogOpen}
        onSaveSuccess={handleSaveSuccess}
      />
      
      <AlertDialog open={!!deletingEvent} onOpenChange={(open) => !open && setDeletingEvent(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>¿Cancelar este evento?</AlertDialogTitle>
            <AlertDialogDescription>
              Esta acción es irreversible y cancelará el recordatorio para "{deletingEvent?.description}".
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction onClick={handleDeleteConfirm}>Sí, cancelar evento</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
