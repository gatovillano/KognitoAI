'use client';

import { useState, useEffect, useCallback } from 'react';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Plus, Trash2, Save, X, Loader2 } from 'lucide-react';
import apiClient from '@/lib/api';
import { toast } from 'sonner';

interface EditableDataGridProps {
    tableId: string;
    columns: any[];
    onDataChange?: () => void;
}

export function EditableDataGrid({ tableId, columns, onDataChange }: EditableDataGridProps) {
    const [rows, setRows] = useState<any[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [editingCell, setEditingCell] = useState<{ rowId: string, colName: string } | null>(null);
    const [editValue, setEditValue] = useState<any>('');
    const [isSaving, setIsSaving] = useState(false);

    const fetchRows = useCallback(async () => {
        setIsLoading(true);
        try {
            const response = await apiClient.get(`/api/tables/${tableId}/rows`);
            setRows(response.data);
        } catch (error) {
            toast.error('Error al cargar los datos.');
        } finally {
            setIsLoading(false);
        }
    }, [tableId]);

    useEffect(() => {
        fetchRows();
    }, [fetchRows]);

    const handleCellClick = (rowId: string, colName: string, value: any) => {
        setEditingCell({ rowId, colName });
        setEditValue(value ?? '');
    };

    const handleSaveCell = async (rowId: string, colName: string) => {
        if (isSaving) return;
        setIsSaving(true);

        const row = rows.find(r => r.id === rowId);
        if (!row) return;

        const col = columns.find(c => c.name === colName);
        let valueToSave = editValue;
        
        if (col?.type === 'number') valueToSave = editValue === '' ? null : Number(editValue);
        if (col?.type === 'boolean') valueToSave = !!editValue;

        const newData = { ...row.data, [colName]: valueToSave };

        try {
            await apiClient.patch(`/api/tables/${tableId}/rows/${rowId}`, { data: newData });
            setRows(prev => prev.map(r => r.id === rowId ? { ...r, data: newData } : r));
            setEditingCell(null);
            if (onDataChange) onDataChange();
        } catch (error) {
            toast.error('Error al guardar el cambio.');
        } finally {
            setIsSaving(false);
        }
    };

    const handleAddRow = async () => {
        const emptyData = columns.reduce((acc, col) => ({ ...acc, [col.name]: null }), {});
        try {
            const response = await apiClient.post(`/api/tables/${tableId}/rows`, { data: emptyData });
            setRows(prev => [...prev, response.data]);
            if (onDataChange) onDataChange();
        } catch (error) {
            toast.error('Error al añadir fila.');
        }
    };

    const handleDeleteRow = async (rowId: string) => {
        if (!window.confirm('¿Eliminar esta fila?')) return;
        try {
            await apiClient.delete(`/api/tables/${tableId}/rows/${rowId}`);
            setRows(prev => prev.filter(r => r.id !== rowId));
            if (onDataChange) onDataChange();
        } catch (error) {
            toast.error('Error al eliminar fila.');
        }
    };

    if (isLoading) {
        return (
            <div className="flex justify-center py-10">
                <Loader2 className="h-6 w-6 animate-spin text-primary" />
            </div>
        );
    }

    return (
        <div className="space-y-4">
            <div className="border rounded-md overflow-hidden">
                <Table>
                    <TableHeader className="bg-muted/50">
                        <TableRow>
                            {columns.map((col) => (
                                <TableHead key={col.name} className="font-bold uppercase text-[10px] tracking-wider">
                                    {col.name}
                                </TableHead>
                            ))}
                            <TableHead className="w-[50px]"></TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {rows.map((row) => (
                            <TableRow key={row.id}>
                                {columns.map((col) => {
                                    const isEditing = editingCell?.rowId === row.id && editingCell?.colName === col.name;
                                    return (
                                        <TableCell
                                            key={col.name}
                                            className="p-1 cursor-pointer hover:bg-muted/30 transition-colors h-10"
                                            onClick={() => !isEditing && handleCellClick(row.id, col.name, row.data[col.name])}
                                        >
                                            {isEditing ? (
                                                <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                                                    {col.type === 'boolean' ? (
                                                        <Checkbox
                                                            checked={!!editValue}
                                                            onCheckedChange={(checked) => setEditValue(checked)}
                                                        />
                                                    ) : col.type === 'number' ? (
                                                        <Input
                                                            type="number"
                                                            autoFocus
                                                            className="h-8 text-sm"
                                                            value={editValue}
                                                            onChange={(e) => setEditValue(e.target.value)}
                                                            onKeyDown={(e) => {
                                                                if (e.key === 'Enter') handleSaveCell(row.id, col.name);
                                                                if (e.key === 'Escape') setEditingCell(null);
                                                            }}
                                                        />
                                                    ) : col.type === 'date' ? (
                                                        <Input
                                                            type="date"
                                                            autoFocus
                                                            className="h-8 text-sm"
                                                            value={editValue}
                                                            onChange={(e) => setEditValue(e.target.value)}
                                                            onKeyDown={(e) => {
                                                                if (e.key === 'Enter') handleSaveCell(row.id, col.name);
                                                                if (e.key === 'Escape') setEditingCell(null);
                                                            }}
                                                        />
                                                    ) : (
                                                        <Input
                                                            autoFocus
                                                            className="h-8 text-sm"
                                                            value={editValue}
                                                            onChange={(e) => setEditValue(e.target.value)}
                                                            onKeyDown={(e) => {
                                                                if (e.key === 'Enter') handleSaveCell(row.id, col.name);
                                                                if (e.key === 'Escape') setEditingCell(null);
                                                            }}
                                                        />
                                                    )}
                                                    <Button size="icon" variant="ghost" className="h-7 w-7" onClick={() => handleSaveCell(row.id, col.name)}>
                                                        <Save className="h-3 w-3" />
                                                    </Button>
                                                </div>
                                            ) : (
                                                <div className="px-2 text-sm flex items-center h-full">
                                                    {col.type === 'boolean' ? (
                                                        <Checkbox checked={!!row.data[col.name]} disabled className="opacity-70" />
                                                    ) : (
                                                        <span className="truncate max-w-[200px]">
                                                            {row.data[col.name] !== null ? String(row.data[col.name]) : <span className="text-muted-foreground italic">null</span>}
                                                        </span>
                                                    )}
                                                </div>
                                            )}
                                        </TableCell>
                                    );
                                })}
                                <TableCell className="p-1">
                                    <Button variant="ghost" size="icon" className="h-8 w-8 text-destructive" onClick={() => handleDeleteRow(row.id)}>
                                        <Trash2 className="h-3 w-3" />
                                    </Button>
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </div>
            <Button variant="outline" size="sm" className="gap-2" onClick={handleAddRow}>
                <Plus className="h-4 w-4" />
                Añadir Fila
            </Button>
        </div>
    );
}
