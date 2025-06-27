"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Plus } from "lucide-react";
import { DataTable } from "../rag/data-table";
import { getColumns } from "./columns";
import { TeamDialog } from "./team-dialog";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";

export default function TeamsPage() {
  const [open, setOpen] = useState(false);
  const [teams, setTeams] = useState<any[]>([]); // Replace with actual data fetching
  const [shareDocumentsOpen, setShareDocumentsOpen] = useState(false);
  const [shareEventsOpen, setShareEventsOpen] = useState(false);
  const [shareNotesOpen, setShareNotesOpen] = useState(false);
  const [selectedTeam, setSelectedTeam] = useState<any>(null);

  const handleTeamCreated = (newTeam: any) => {
    setTeams([...teams, newTeam]);
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

  // Pass sharing handlers to columns
  const columnsWithHandlers = getColumns(handleShareDocuments, handleShareEvents, handleShareNotes);

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold mb-2">Equipos</h1>
          <p className="text-muted-foreground">Gestiona tus equipos y colaboradores.</p>
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
        <DataTable data={teams} columns={columnsWithHandlers} />
      )}

      <TeamDialog open={open} onOpenChange={setOpen} onTeamCreated={handleTeamCreated} />

      {/* Share Documents Dialog */}
      <Dialog open={shareDocumentsOpen} onOpenChange={setShareDocumentsOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Compartir Documentos con {selectedTeam?.name}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <p>Selecciona los documentos que deseas compartir con este equipo.</p>
            {/* Placeholder for document selection UI */}
            <p className="text-muted-foreground">Aquí se implementará la selección de documentos.</p>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setShareDocumentsOpen(false)}>Cancelar</Button>
              <Button onClick={() => {
                // Placeholder for sharing action
                console.log(`Compartiendo documentos con equipo ${selectedTeam?.id}`);
                setShareDocumentsOpen(false);
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
            {/* Placeholder for event selection UI */}
            <p className="text-muted-foreground">Aquí se implementará la selección de eventos.</p>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setShareEventsOpen(false)}>Cancelar</Button>
              <Button onClick={() => {
                // Placeholder for sharing action
                console.log(`Compartiendo eventos con equipo ${selectedTeam?.id}`);
                setShareEventsOpen(false);
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
            {/* Placeholder for note selection UI */}
            <p className="text-muted-foreground">Aquí se implementará la selección de notas.</p>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setShareNotesOpen(false)}>Cancelar</Button>
              <Button onClick={() => {
                // Placeholder for sharing action
                console.log(`Compartiendo notas con equipo ${selectedTeam?.id}`);
                setShareNotesOpen(false);
              }}>Compartir</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
