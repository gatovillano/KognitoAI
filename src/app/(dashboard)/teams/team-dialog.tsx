"use client";

import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { useForm } from "react-hook-form";
import apiClient from "@/lib/api";

interface TeamDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onTeamCreated: (team: any) => void;
  onTeamUpdated?: (team: any) => void; // Optional callback for when a team is updated
  team?: any; // Optional team object for editing
}

export function TeamDialog({ open, onOpenChange, onTeamCreated, onTeamUpdated, team }: TeamDialogProps) {
  const form = useForm({
    defaultValues: {
      name: team?.name || "",
    },
  });

  const handleSubmit = async (data: any) => {
    try {
      let response;
      if (team) {
        // Update existing team
        response = await apiClient.put(`/api/teams/${team.id}`, { name: data.name });
        if (onTeamUpdated) {
          onTeamUpdated(response.data);
        }
      } else {
        // Create new team
        response = await apiClient.post('/api/teams', { name: data.name });
        onTeamCreated(response.data);
      }
    } catch (error) {
      console.error("Error saving team:", error);
      // Optionally, show an error message to the user
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{team ? "Editar Equipo" : "Crear Nuevo Equipo"}</DialogTitle>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Nombre del Equipo</FormLabel>
                  <FormControl>
                    <Input placeholder="Nombre del equipo" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <div className="flex justify-end gap-2">
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                Cancelar
              </Button>
              <Button type="submit">
                {team ? "Guardar Cambios" : "Crear Equipo"}
              </Button>
            </div>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
