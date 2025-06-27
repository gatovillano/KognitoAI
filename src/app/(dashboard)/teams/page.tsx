"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Plus } from "lucide-react";
import { DataTable } from "../rag/data-table";
import { columns } from "./columns";
import { TeamDialog } from "./team-dialog";

export default function TeamsPage() {
  const [open, setOpen] = useState(false);
  const [teams, setTeams] = useState<any[]>([]); // Replace with actual data fetching

  const handleTeamCreated = (newTeam: any) => {
    setTeams([...teams, newTeam]);
    setOpen(false);
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Equipos</h1>
        <Button onClick={() => setOpen(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Crear Equipo
        </Button>
      </div>

      <DataTable data={teams} columns={columns} />

      <TeamDialog open={open} onOpenChange={setOpen} onTeamCreated={handleTeamCreated} />
    </div>
  );
}
