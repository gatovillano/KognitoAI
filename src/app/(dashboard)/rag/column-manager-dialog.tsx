'use client';

import { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Plus, Trash2, Settings2, Loader2 } from 'lucide-react';
import apiClient from '@/lib/api';
import { toast } from 'sonner';

interface ColumnManagerDialogProps {
    isOpen: boolean;
    onOpenChange: (open: boolean) => void;
    tableId: string;
    initialColumns: any[];
    onSuccess: (updatedColumns: any[]) => void;
}

export function ColumnManagerDialog({ isOpen, onOpenChange, tableId, initialColumns, onSuccess }: ColumnManagerDialogProps) {
    const [columns, setColumns] = useState<any[]>(initialColumns);
    const [isSaving, setIsSaving] = useState(false);

    const handleAddColumn = () => {
        setColumns([...columns, { name: `Nueva Columna ${columns.length + 1}`, type: 'string', required: false }]);
    };

    const handleRemoveColumn = (index: number) => {
        setColumns(columns.filter((_, i) => i !== index));
    };

    const handleUpdateColumn = (index: number, field: string, value: any) => {
        setColumns(columns.map((col, i) => i === index ? { ...col, [field]: value } : col));
    };

    const handleSave = async () => {
        setIsSaving(true);
        try {
            const response = await apiClient.patch(`/api/tables/${tableId}/columns`, columns);
            toast.success('Esquema de columnas actualizado.');
            onSuccess(response.data.columns);
            onOpenChange(false);
        } catch (error) {
            toast.error('Error al actualizar las columnas.');
        } finally {
            setIsSaving(false);
        }
    };

    return (
        <Dialog open={isOpen} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[500px]">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <Settings2 className="h-5 w-5 text-primary" />
                        Gestionar Columnas
                    </DialogTitle>
                    <DialogDescription>
                        Añade o elimina columnas. Ten en cuenta que eliminar una columna borrará sus datos permanentemente.
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-4 py-4 max-h-[400px] overflow-y-auto pr-2">
                    {columns.map((col, index) => (
                        <div key={index} className="flex items-end gap-2 p-3 border rounded-lg bg-muted/30">
                            <div className="grid gap-2 flex-1">
                                <Label className="text-[10px] uppercase font-bold text-muted-foreground">Nombre</Label>
                                <Input
                                    value={col.name}
                                    onChange={(e) => handleUpdateColumn(index, 'name', e.target.value)}
                                    className="h-8 text-sm"
                                />
                            </div>
                            <div className="grid gap-2 w-[120px]">
                                <Label className="text-[10px] uppercase font-bold text-muted-foreground">Tipo</Label>
                                <Select
                                    value={col.type}
                                    onValueChange={(val) => handleUpdateColumn(index, 'type', val)}
                                >
                                    <SelectTrigger className="h-8 text-xs">
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="string">Texto</SelectItem>
                                        <SelectItem value="number">Nº</SelectItem>
                                        <SelectItem value="date">Fecha</SelectItem>
                                        <SelectItem value="boolean">Check</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                            <Button
                                variant="ghost"
                                size="icon"
                                className="h-8 w-8 text-destructive"
                                onClick={() => handleRemoveColumn(index)}
                            >
                                <Trash2 className="h-4 w-4" />
                            </Button>
                        </div>
                    ))}

                    <Button variant="outline" size="sm" className="w-full gap-2 border-dashed" onClick={handleAddColumn}>
                        <Plus className="h-4 w-4" />
                        Añadir Nueva Columna
                    </Button>
                </div>

                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isSaving}>
                        Cancelar
                    </Button>
                    <Button onClick={handleSave} disabled={isSaving}>
                        {isSaving ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                        Guardar Cambios
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
