"use client";

import { useState, useEffect } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { useForm } from "react-hook-form";
import apiClient from "@/lib/api";
import { toast } from "sonner";
// Assuming the select components are in a similar location or need to be created
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

interface TeamDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onTeamCreated: (team: any) => void;
  onTeamUpdated?: (team: any) => void; // Optional callback for when a team is updated
  team?: any; // Optional team object for editing
}

export function TeamDialog({ open, onOpenChange, onTeamCreated, onTeamUpdated, team }: TeamDialogProps) {
  const [users, setUsers] = useState<any[]>([]);
  const [selectedMembers, setSelectedMembers] = useState<string[]>(team?.members?.map((m: any) => m.account_id) || []);
  const form = useForm({
    defaultValues: {
      name: team?.name || "",
    },
  });

  useEffect(() => {
    const fetchUsers = async () => {
      try {
        const response = await apiClient.get('/api/users');
        setUsers(response.data);
      } catch (error) {
        toast.error("Error al cargar usuarios.");
        console.error(error);
      }
    };
    if (open) {
      fetchUsers();
    }
  }, [open]);

  const handleSubmit = async (data: any) => {
    try {
      let response;
      const teamData = { 
        name: data.name,
        members: selectedMembers
      };
      if (team) {
        // Update existing team
        response = await apiClient.put(`/api/teams/${team.id}`, teamData);
        if (onTeamUpdated) {
          onTeamUpdated({ ...response.data, members_count: selectedMembers.length });
        }
      } else {
        // Create new team
        response = await apiClient.post('/api/teams', teamData);
        onTeamCreated({ ...response.data, members_count: selectedMembers.length });
      }
    } catch (error: any) {
      toast.error("Error al guardar el equipo. Revisa la consola para más detalles.");
      console.error("Error saving team:", error.response?.data || error.message || error);
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
            <FormItem>
              <FormLabel>Miembros del Equipo</FormLabel>
              <FormControl>
                <Select onValueChange={(value: string) => {
                  if (!selectedMembers.includes(value)) {
                    setSelectedMembers([...selectedMembers, value]);
                  }
                }}>
                  <SelectTrigger>
                    <SelectValue placeholder="Seleccionar miembros" />
                  </SelectTrigger>
                  <SelectContent>
                    {users.map((user) => (
                      <SelectItem key={user.id} value={user.id}>
                        {user.name || user.username || user.email || 'Usuario sin nombre'}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </FormControl>
              <div className="mt-2 flex flex-wrap gap-2">
                {selectedMembers.map((memberId) => {
                  const member = users.find(u => u.id === memberId);
                  return (
                    <div key={memberId} className="flex items-center gap-2 bg-muted p-2 rounded-md">
                      {member?.name || member?.username || member?.email || 'Usuario desconocido'}
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => setSelectedMembers(selectedMembers.filter(id => id !== memberId))}
                      >
                        ×
                      </Button>
                    </div>
                  );
                })}
              </div>
            </FormItem>
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
