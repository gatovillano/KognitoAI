"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Plus, Users, Info } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { MoreVertical } from "lucide-react";
import { TeamDialog } from "./team-dialog";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import apiClient from "@/lib/api";
import { useToast } from "@/hooks/use-toast";

export default function TeamsPage() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [teams, setTeams] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [shareDocumentsOpen, setShareDocumentsOpen] = useState(false);
  const [shareEventsOpen, setShareEventsOpen] = useState(false);
  const [shareNotesOpen, setShareNotesOpen] = useState(false);
  const [selectedTeam, setSelectedTeam] = useState<any>(null);
  const [documents, setDocuments] = useState<any[]>([]);
  const [events, setEvents] = useState<any[]>([]);
  const [notes, setNotes] = useState<any[]>([]);
  const [loadingDocuments, setLoadingDocuments] = useState(false);
  const [loadingEvents, setLoadingEvents] = useState(false);
  const [loadingNotes, setLoadingNotes] = useState(false);
  const [selectedDocuments, setSelectedDocuments] = useState<string[]>([]);
  const [selectedEvents, setSelectedEvents] = useState<number[]>([]);
  const [selectedNotes, setSelectedNotes] = useState<number[]>([]);

  useEffect(() => {
    const fetchTeams = async () => {
      try {
        const response = await apiClient.get('/api/teams');
        setTeams(response.data);
      } catch (error) {
        console.error("Error fetching teams:", error);
      } finally {
        setLoading(false);
      }
    };
    fetchTeams();
  }, []);

  useEffect(() => {
    const fetchDocuments = async () => {
      setLoadingDocuments(true);
      try {
        const response = await apiClient.post('/api/list-documents');
        setDocuments(response.data);
      } catch (error) {
        console.error("Error fetching documents:", error);
      } finally {
        setLoadingDocuments(false);
      }
    };
    if (shareDocumentsOpen) {
      fetchDocuments();
    }
  }, [shareDocumentsOpen]);

  useEffect(() => {
    const fetchEvents = async () => {
      setLoadingEvents(true);
      try {
        const response = await apiClient.post('/api/list-events');
        setEvents(response.data);
      } catch (error) {
        console.error("Error fetching events:", error);
      } finally {
        setLoadingEvents(false);
      }
    };
    if (shareEventsOpen) {
      fetchEvents();
    }
  }, [shareEventsOpen]);

  useEffect(() => {
    const fetchNotes = async () => {
      setLoadingNotes(true);
      try {
        const response = await apiClient.post('/api/notes/list-notes', { search_term: '' });
        setNotes(response.data);
      } catch (error) {
        console.error("Error fetching notes:", error);
      } finally {
        setLoadingNotes(false);
      }
    };
    if (shareNotesOpen) {
      fetchNotes();
    }
  }, [shareNotesOpen]);

  const handleDocumentSelection = (fileName: string) => {
    setSelectedDocuments(prev => 
      prev.includes(fileName) ? prev.filter(f => f !== fileName) : [...prev, fileName]
    );
  };

  const handleEventSelection = (eventId: number) => {
    setSelectedEvents(prev => 
      prev.includes(eventId) ? prev.filter(id => id !== eventId) : [...prev, eventId]
    );
  };

  const handleNoteSelection = (noteId: number) => {
    setSelectedNotes(prev => 
      prev.includes(noteId) ? prev.filter(id => id !== noteId) : [...prev, noteId]
    );
  };

  const { toast } = useToast();

  const handleTeamCreated = async (newTeam: any) => {
    try {
      const response = await apiClient.get('/api/teams');
      setTeams(response.data);
      toast({
        title: "Éxito",
        description: "Equipo creado correctamente.",
      });
    } catch (error) {
      console.error("Error refreshing teams:", error);
      toast({
        title: "Error",
        description: "Error al actualizar la lista de equipos. Se ha añadido localmente.",
        variant: "destructive",
      });
    }
    setOpen(false);
  };

  const handleTeamUpdated = async (updatedTeam: any) => {
    try {
      const response = await apiClient.get('/api/teams');
      setTeams(response.data);
      toast({
        title: "Éxito",
        description: "Equipo actualizado correctamente.",
      });
    } catch (error) {
      console.error("Error refreshing teams:", error);
      toast({
        title: "Error",
        description: "Error al actualizar la lista de equipos. Se ha actualizado localmente.",
        variant: "destructive",
      });
    }
    setOpen(false);
  };

  const handleShareDocuments = (team: any) => {
    setSelectedTeam(team);
    setShareDocumentsOpen(true);
  };

  const handleShareEvents = (team: any) => {
    setSelectedTeam(team);
    setShareEventsOpen(true);
  };

  const handleShareNotes = (team: any) => {
    setSelectedTeam(team);
    setShareNotesOpen(true);
  };

  const handleEditTeam = (team: any) => {
    setSelectedTeam(team);
    setOpen(true);
  };

  const handleDeleteTeam = async (team: any) => {
    try {
      await apiClient.delete(`/api/teams/${team.id}`);
      setTeams(teams.filter(t => t.id !== team.id));
      toast({
        title: "Éxito",
        description: "Equipo eliminado correctamente.",
      });
    } catch (error) {
      console.error("Error deleting team:", error);
      toast({
        title: "Error",
        description: "No se pudo eliminar el equipo. Inténtalo de nuevo.",
        variant: "destructive",
      });
    }
  };

  const handleManageMembers = (team: any) => {
    setSelectedTeam(team);
    router.push(`/teams/${team.id}`);
  };

  // Removed reference to getColumns as it's no longer used with card layout

  return (
    <div className="p-4 sm:p-8 max-w-7xl mx-auto overflow-x-hidden">
      <div className="flex items-center justify-between mb-8">
        <div>
            <h1 className="text-3xl font-bold flex items-center">
                <Users className="mr-2 h-8 w-8 text-primary" />
                Equipos
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button variant="ghost" size="icon" className="ml-2 h-6 w-6 text-muted-foreground">
                        <Info className="h-4 w-4" />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>Gestiona tus equipos y colaboradores.</p>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
            </h1>
        </div>
        <Button onClick={() => setOpen(true)} className="mt-4">
          <Plus className="mr-2 h-4 w-4" />
          Crear Equipo
        </Button>
      </div>

      {teams.length === 0 ? (
        <div className="rounded-md border mt-6 p-8 text-center">
          <p className="text-muted-foreground">No hay equipos creados. Crea tu primer equipo para comenzar.</p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {teams.map((team) => (
            <Card key={team.id} className="flex flex-col hover:border-primary/50 transition-colors relative group cursor-pointer" onClick={() => router.push(`/teams/${team.id}/dashboard`)}>
              <CardHeader className="flex flex-row items-start justify-between pb-0">
                <div>
                  <CardTitle className="flex items-center break-words">
                    {team.name}
                    <span title="Equipo">
                      <Users className="ml-2 h-4 w-4 text-blue-500" />
                    </span>
                  </CardTitle>
                </div>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" size="icon" className="h-8 w-8 -mt-2 -mr-2 z-30 flex-shrink-0" onClick={(e) => e.stopPropagation()}>
                      <MoreVertical className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem onClick={(e) => { e.stopPropagation(); handleEditTeam(team); }}>
                      Editar
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={(e) => { e.stopPropagation(); handleDeleteTeam(team); }}>
                      Eliminar
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={(e) => { e.stopPropagation(); handleShareDocuments(team); }}>
                      Compartir Documentos
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={(e) => { e.stopPropagation(); handleShareEvents(team); }}>
                      Compartir Eventos
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={(e) => { e.stopPropagation(); handleShareNotes(team); }}>
                      Compartir Notas
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={(e) => { e.stopPropagation(); handleManageMembers(team); }}>
                      Gestionar Miembros
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </CardHeader>
                <CardContent className="p-4 pt-2">
                  <p className="text-sm text-muted-foreground">{team.members_count || 0} miembro(s)</p>
                </CardContent>
            </Card>
          ))}
        </div>
      )}

      <TeamDialog open={open} onOpenChange={setOpen} onTeamCreated={handleTeamCreated} onTeamUpdated={handleTeamUpdated} team={selectedTeam} />

      {/* Share Documents Dialog */}
      <Dialog open={shareDocumentsOpen} onOpenChange={setShareDocumentsOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Compartir Documentos con {selectedTeam?.name}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <p>Selecciona los documentos que deseas compartir con este equipo.</p>
            <div className="border rounded-md p-4 max-h-60 overflow-y-auto">
              {loadingDocuments ? (
                <p className="text-muted-foreground">Cargando documentos...</p>
              ) : documents.length > 0 ? (
                documents.map((doc: any) => (
                  <div key={doc.file_name} className="flex items-center space-x-2 mb-2">
                    <input
                      type="checkbox"
                      id={`doc-${doc.file_name}`}
                      checked={selectedDocuments.includes(doc.file_name)}
                      onChange={() => handleDocumentSelection(doc.file_name)}
                    />
                    <label htmlFor={`doc-${doc.file_name}`} className="flex-1">
                      {doc.title || doc.file_name}
                    </label>
                  </div>
                ))
              ) : (
                <p className="text-muted-foreground">No hay documentos disponibles.</p>
              )}
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setShareDocumentsOpen(false)}>Cancelar</Button>
              <Button onClick={async () => {
                try {
                  const response = await apiClient.post(`/api/teams/${selectedTeam?.id}/share/documents`, { documentIds: selectedDocuments });
                  toast({
                    title: "Éxito",
                    description: `${selectedDocuments.length} documento(s) compartido(s) con ${selectedTeam?.name}.`,
                  });
                  setShareDocumentsOpen(false);
                  setSelectedDocuments([]);
                  console.log("Documents shared successfully:", response.data);
                } catch (error: any) {
                  console.error("Error sharing documents:", error.response?.data || error.message || error);
                  toast({
                    title: "Error",
                    description: "No se pudieron compartir los documentos. Revisa la consola para más detalles.",
                    variant: "destructive",
                  });
                }
              }}>Compartir</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Share Events Dialog */}
      <Dialog open={shareEventsOpen} onOpenChange={setShareEventsOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Compartir Eventos con {selectedTeam?.name}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <p>Selecciona los eventos que deseas compartir con este equipo.</p>
            <div className="border rounded-md p-4 max-h-60 overflow-y-auto">
              {loadingEvents ? (
                <p className="text-muted-foreground">Cargando eventos...</p>
              ) : events.length > 0 ? (
                events.map((event: any) => (
                  <div key={event.id} className="flex items-center space-x-2 mb-2">
                    <input
                      type="checkbox"
                      id={`event-${event.id}`}
                      checked={selectedEvents.includes(event.id)}
                      onChange={() => handleEventSelection(event.id)}
                    />
                    <label htmlFor={`event-${event.id}`} className="flex-1">
                      {event.description} - {new Date(event.event_datetime_local).toLocaleString()}
                    </label>
                  </div>
                ))
              ) : (
                <p className="text-muted-foreground">No hay eventos disponibles.</p>
              )}
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setShareEventsOpen(false)}>Cancelar</Button>
              <Button onClick={async () => {
                try {
                  const response = await apiClient.post(`/api/teams/${selectedTeam?.id}/share/events`, { eventIds: selectedEvents });
                  toast({
                    title: "Éxito",
                    description: `${selectedEvents.length} evento(s) compartido(s) con ${selectedTeam?.name}.`,
                  });
                  setShareEventsOpen(false);
                  setSelectedEvents([]);
                  console.log("Events shared successfully:", response.data);
                } catch (error: any) {
                  console.error("Error sharing events:", error.response?.data || error.message || error);
                  toast({
                    title: "Error",
                    description: "No se pudieron compartir los eventos. Revisa la consola para más detalles.",
                    variant: "destructive",
                  });
                }
              }}>Compartir</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Share Notes Dialog */}
      <Dialog open={shareNotesOpen} onOpenChange={setShareNotesOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Compartir Notas con {selectedTeam?.name}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <p>Selecciona las notas que deseas compartir con este equipo.</p>
            <div className="border rounded-md p-4 max-h-60 overflow-y-auto">
              {loadingNotes ? (
                <p className="text-muted-foreground">Cargando notas...</p>
              ) : notes.length > 0 ? (
                notes.map((note: any) => (
                  <div key={note.id} className="flex items-center space-x-2 mb-2">
                    <input
                      type="checkbox"
                      id={`note-${note.id}`}
                      checked={selectedNotes.includes(note.id)}
                      onChange={() => handleNoteSelection(note.id)}
                    />
                    <label htmlFor={`note-${note.id}`} className="flex-1">
                      {note.title || "Sin título"} - {new Date(note.updated_at).toLocaleDateString()}
                    </label>
                  </div>
                ))
              ) : (
                <p className="text-muted-foreground">No hay notas disponibles.</p>
              )}
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setShareNotesOpen(false)}>Cancelar</Button>
              <Button onClick={async () => {
                try {
                  const response = await apiClient.post(`/api/teams/${selectedTeam?.id}/share/notes`, { noteIds: selectedNotes });
                  toast({
                    title: "Éxito",
                    description: `${selectedNotes.length} nota(s) compartida(s) con ${selectedTeam?.name}.`,
                  });
                  setShareNotesOpen(false);
                  setSelectedNotes([]);
                  console.log("Notes shared successfully:", response.data);
                } catch (error: any) {
                  console.error("Error sharing notes:", error.response?.data || error.message || error);
                  toast({
                    title: "Error",
                    description: "No se pudieron compartir las notas. Revisa la consola para más detalles.",
                    variant: "destructive",
                  });
                }
              }}>Compartir</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
