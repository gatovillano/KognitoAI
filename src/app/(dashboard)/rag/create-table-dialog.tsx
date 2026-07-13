"use client";

import React, { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Plus, Trash2, Loader2 } from "lucide-react";
import apiClient from "@/lib/api";
import { toast } from "sonner";

interface CreateTableDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: (newTable: any) => void;
}

export function CreateTableDialog({
  open,
  onOpenChange,
  onSuccess,
}: CreateTableDialogProps) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const [columns, setColumns] = useState([
    { name: "Nombre", type: "string" },
  ]);

  const addColumn = () => {
    setColumns([...columns, { name: "", type: "string" }]);
  };

  const removeColumn = (index: number) => {
    setColumns(columns.filter((_, i) => i !== index));
  };

  const updateColumn = (index: number, field: string, value: string) => {
    const newColumns = [...columns];
    newColumns[index] = { ...newColumns[index], [field]: value };
    setColumns(newColumns);
  };

  const handleCreate = async () => {
    if (!name.trim()) return;
    
    setIsCreating(true);
    try {
      const payload = {
        name,
        description,
        columns: columns.filter(c => c.name.trim() !== "").map(c => ({
            name: c.name,
            type: c.type,
            required: false
        }))
      };
      
      const response = await apiClient.post("/api/tables/", payload);
      toast.success("Tabla creada exitosamente 🚀");
      onSuccess(response.data);
      setName("");
      setDescription("");
      setColumns([{ name: "Nombre", type: "string" }]);
      onOpenChange(false);
    } catch (error) {
      console.error("Error creating table:", error);
      toast.error("Error al crear la tabla.");
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Crear Nueva Tabla 📊</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="name">Nombre de la Tabla</Label>
            <Input
              id="name"
              placeholder="Ej: Inventario de Equipos"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="description">Descripción</Label>
            <Input
              id="description"
              placeholder="Opcional..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label>Columnas Iniciales</Label>
              <Button variant="outline" size="sm" onClick={addColumn}>
                <Plus className="h-4 w-4 mr-1" /> Agregar
              </Button>
            </div>
            <div className="max-h-60 overflow-y-auto space-y-2 pr-2">
              {columns.map((col, index) => (
                <div key={index} className="flex gap-2 items-center">
                  <Input
                    placeholder="Nombre col"
                    value={col.name}
                    onChange={(e) => updateColumn(index, "name", e.target.value)}
                    className="flex-1"
                  />
                  <Select
                    value={col.type}
                    onValueChange={(value) => updateColumn(index, "type", value)}
                  >
                    <SelectTrigger className="w-24">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="string">Texto</SelectItem>
                      <SelectItem value="number">Nº</SelectItem>
                      <SelectItem value="date">Fecha</SelectItem>
                      <SelectItem value="boolean">Check</SelectItem>
                      <SelectItem value="object">Objeto Vinculado</SelectItem>
                    </SelectContent>
                  </Select>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => removeColumn(index)}
                    disabled={columns.length <= 1}
                  >
                    <Trash2 className="h-4 w-4 text-destructive" />
                  </Button>
                </div>
              ))}
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isCreating}>
            Cancelar
          </Button>
          <Button onClick={handleCreate} disabled={!name.trim() || isCreating}>
            {isCreating ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
            Crear Tabla
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}