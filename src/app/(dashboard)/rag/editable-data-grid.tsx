'use client';

import { useState, useEffect, useCallback } from 'react';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Plus, Trash2, Save, X, Loader2, FileText, Calendar, User, CheckSquare } from 'lucide-react';
import apiClient from '@/lib/api';
import { toast } from 'sonner';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { ObjectTagSelectorDialog, TaggedObject } from './object-tag-selector-dialog';

// Import detail and edit dialogs
import { ProfileDetailDialog } from '@/app/(dashboard)/profiles/profile-detail-dialog';
import { ProfileDialog } from '@/app/(dashboard)/profiles/profile-dialog';
import { ViewNoteDialog } from '@/app/(dashboard)/notes/view-note-dialog';
import { EventDetailsDialog } from '@/app/(dashboard)/agenda/EventDetailsDialog';
import { EventEditDialog } from '@/app/(dashboard)/agenda/EventEditDialog';
import { TaskDialog } from '@/app/(dashboard)/agenda/task-dialog';

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
    const [isObjectSelectorOpen, setIsObjectSelectorOpen] = useState(false);
    const [activeObjectCell, setActiveObjectCell] = useState<{ rowId: string, colName: string } | null>(null);

    // States for viewing detailed item modals/dialogs
    const [activeNote, setActiveNote] = useState<any | null>(null);
    const [isNoteViewOpen, setIsNoteViewOpen] = useState(false);

    const [activeProfileId, setActiveProfileId] = useState<string | null>(null);
    const [isProfileViewOpen, setIsProfileViewOpen] = useState(false);
    const [editingProfile, setEditingProfile] = useState<any | null>(null);
    const [isProfileDialogOpen, setIsProfileDialogOpen] = useState(false);

    const [activeEvent, setActiveEvent] = useState<any | null>(null);
    const [isEventViewOpen, setIsEventViewOpen] = useState(false);
    const [isEventEditOpen, setIsEventEditOpen] = useState(false);

    const [activeTask, setActiveTask] = useState<any | null>(null);
    const [isTaskViewOpen, setIsTaskViewOpen] = useState(false);

    const handleBadgeClick = async (item: TaggedObject) => {
        const toastId = toast.loading('Cargando detalles...');
        try {
            if (item.type === 'profile') {
                // Profiles detail dialog fetches details internally
                setActiveProfileId(String(item.id));
                setIsProfileViewOpen(true);
                toast.dismiss(toastId);
            } else if (item.type === 'note') {
                const response = await apiClient.get(`/api/notes/${item.id}`);
                setActiveNote(response.data);
                setIsNoteViewOpen(true);
                toast.dismiss(toastId);
            } else if (item.type === 'event') {
                const response = await apiClient.get(`/api/agenda/events/${item.id}`);
                setActiveEvent(response.data);
                setIsEventViewOpen(true);
                toast.dismiss(toastId);
            } else if (item.type === 'task') {
                const response = await apiClient.get(`/api/tasks/${item.id}`);
                setActiveTask(response.data);
                setIsTaskViewOpen(true);
                toast.dismiss(toastId);
            }
        } catch (error) {
            console.error('Error fetching details for badge:', error);
            toast.error('No se pudieron cargar los detalles.');
            toast.dismiss(toastId);
        }
    };

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
        const col = columns.find(c => c.name === colName);
        if (col?.type === 'object') {
            setActiveObjectCell({ rowId, colName });
            setEditValue(value || []);
            setIsObjectSelectorOpen(true);
        } else {
            setEditingCell({ rowId, colName });
            setEditValue(value ?? '');
        }
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

    const handleSaveObjectTags = async (selectedTags: TaggedObject[]) => {
        if (!activeObjectCell) return;
        const { rowId, colName } = activeObjectCell;

        setIsSaving(true);
        const row = rows.find(r => r.id === rowId);
        if (!row) {
            setIsSaving(false);
            return;
        }

        const newData = { ...row.data, [colName]: selectedTags };

        try {
            await apiClient.patch(`/api/tables/${tableId}/rows/${rowId}`, { data: newData });
            setRows(prev => prev.map(r => r.id === rowId ? { ...r, data: newData } : r));
            if (onDataChange) onDataChange();
            toast.success('Objetos vinculados actualizados.');
        } catch (error) {
            toast.error('Error al guardar las vinculaciones.');
        } finally {
            setIsSaving(false);
            setActiveObjectCell(null);
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
                                                    ) : col.type === 'object' ? (
                                                        <div className="flex flex-wrap gap-1 max-w-[300px] overflow-hidden">
                                                            {Array.isArray(row.data[col.name]) && row.data[col.name].length > 0 ? (
                                                                row.data[col.name].map((item: any, idx: number) => {
                                                                    const Icon = item.type === 'note' ? FileText : item.type === 'event' ? Calendar : item.type === 'task' ? CheckSquare : User;
                                                                    let colorClass = "bg-blue-500/10 text-blue-500 border-blue-500/20";
                                                                    if (item.type === 'event') colorClass = "bg-emerald-500/10 text-emerald-500 border-emerald-500/20";
                                                                    if (item.type === 'profile') colorClass = "bg-purple-500/10 text-purple-500 border-purple-500/20";
                                                                    if (item.type === 'task') colorClass = "bg-orange-500/10 text-orange-500 border-orange-500/20";
                                                                    return (
                                                                        <Badge
                                                                            key={idx}
                                                                            variant="outline"
                                                                            className={cn("text-[10px] py-0 px-1.5 flex items-center gap-1 cursor-pointer hover:opacity-80 transition-opacity", colorClass)}
                                                                            onClick={(e) => {
                                                                                e.stopPropagation();
                                                                                handleBadgeClick(item);
                                                                            }}
                                                                        >
                                                                            <Icon className="h-2.5 w-2.5" />
                                                                            <span className="truncate max-w-[80px]">{item.title}</span>
                                                                        </Badge>
                                                                    );
                                                                })
                                                            ) : (
                                                                <span className="text-muted-foreground italic text-xs">Vincular...</span>
                                                            )}
                                                        </div>
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

            <ObjectTagSelectorDialog
                isOpen={isObjectSelectorOpen}
                onOpenChange={setIsObjectSelectorOpen}
                initialSelected={editValue as TaggedObject[]}
                onSave={handleSaveObjectTags}
            />

            {/* View Note Dialog */}
            {activeNote && (
                <ViewNoteDialog
                    note={activeNote}
                    isOpen={isNoteViewOpen}
                    onOpenChange={setIsNoteViewOpen}
                    onNoteUpdated={() => {
                        fetchRows();
                        apiClient.get(`/api/notes/${activeNote.id}`).then((res) => {
                            setActiveNote(res.data);
                        });
                    }}
                />
            )}

            {/* Profile Detail and Edit Dialogs */}
            {activeProfileId && (
                <ProfileDetailDialog
                    isOpen={isProfileViewOpen}
                    onOpenChange={setIsProfileViewOpen}
                    profileId={activeProfileId}
                    onEdit={(profileToEdit) => {
                        setEditingProfile(profileToEdit);
                        setIsProfileViewOpen(false);
                        setIsProfileDialogOpen(true);
                    }}
                />
            )}
            <ProfileDialog
                isOpen={isProfileDialogOpen}
                onOpenChange={setIsProfileDialogOpen}
                profile={editingProfile}
                onSaveSuccess={() => {
                    fetchRows();
                    setIsProfileDialogOpen(false);
                }}
            />

            {/* Event Detail and Edit Dialogs */}
            {activeEvent && (
                <EventDetailsDialog
                    isOpen={isEventViewOpen}
                    onOpenChange={setIsEventViewOpen}
                    onEditClick={(eventToEdit) => {
                        setActiveEvent(eventToEdit);
                        setIsEventViewOpen(false);
                        setIsEventEditOpen(true);
                    }}
                    onDeleteClick={async (eventToDelete) => {
                        if (window.confirm('¿Eliminar este evento?')) {
                            try {
                                await apiClient.delete(`/api/agenda/events/${eventToDelete.id}`);
                                toast.success('Evento eliminado.');
                                setIsEventViewOpen(false);
                                fetchRows();
                            } catch (error) {
                                toast.error('Error al eliminar el evento.');
                            }
                        }
                    }}
                    event={activeEvent}
                />
            )}
            {activeEvent && (
                <EventEditDialog
                    isOpen={isEventEditOpen}
                    onOpenChange={setIsEventEditOpen}
                    onSaveSuccess={(updatedEvent) => {
                        toast.success('Evento guardado.');
                        fetchRows();
                        setActiveEvent(updatedEvent);
                        setIsEventEditOpen(false);
                        setIsEventViewOpen(true);
                    }}
                    onCloseDetails={() => setIsEventViewOpen(false)}
                    event={activeEvent}
                />
            )}

            {/* Task Dialog */}
            <TaskDialog
                isOpen={isTaskViewOpen}
                onOpenChange={setIsTaskViewOpen}
                task={activeTask}
                onSaveSuccess={(updatedTask) => {
                    toast.success('Tarea guardada.');
                    fetchRows();
                    setIsTaskViewOpen(false);
                }}
            />
        </div>
    );
}
