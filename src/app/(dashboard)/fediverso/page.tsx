"use client";

import { FediversePanel } from "@/components/FediversePanel";

export default function FediversoPage() {
  return (
    <div className="space-y-6 container mx-auto px-4 py-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-foreground">Fediverso</h1>
        <p className="text-muted-foreground">
          Conéctate a redes sociales descentralizadas y colabora con tu Asistente de IA.
        </p>
      </div>
      <FediversePanel />
    </div>
  );
}
