'use client';

import { useState, useEffect, useCallback } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Loader2, MessageSquare, Download, Settings2 } from 'lucide-react';
import apiClient from '@/lib/api';
import { toast } from 'sonner';
import { ContextualChat } from '@/components/ContextualChat';
import { EditableDataGrid } from './editable-data-grid';
import { ColumnManagerDialog } from './column-manager-dialog';

interface TableDetailDialogProps {
    isOpen: boolean;
    onOpenChange: (open: boolean) => void;
    tableId: string | null;
    tableName: string;
}

export function TableDetailDialog({ isOpen, onOpenChange, tableId, tableName }: TableDetailDialogProps) {
    const [table, setTable] = useState<any>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [isChatOpen, setIsChatOpen] = useState(false);
    const [isColumnManagerOpen, setIsColumnManagerOpen] = useState(false);

    const fetchTableDetails = useCallback(async () => {
        if (!tableId) return;
        setIsLoading(true);
        try {
            const response = await apiClient.get(`/api/tables/${tableId}`);
            setTable(response.data);
        } catch (error) {
            console.error('Error fetching table details:', error);
            toast.error('Error al cargar los detalles de la tabla.');
        } finally {
            setIsLoading(false);
        }
    }, [tableId]);

    useEffect(() => {
        if (isOpen && tableId) {
            fetchTableDetails();
        }
    }, [isOpen, tableId, fetchTableDetails]);

    return (
        <Dialog open={isOpen} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-6xl max-h-[90vh] overflow-hidden flex flex-col">
                <DialogHeader className="flex flex-row items-center justify-between">
                    <div>
                        <DialogTitle>{table?.name || tableName}</DialogTitle>
                    </div>
                    <div className="flex gap-2 mr-8">
                        <Button variant="outline" size="sm" className="gap-2" onClick={() => setIsColumnManagerOpen(true)}>
                            <Settings2 className="h-4 w-4" />
                            Columnas
                        </Button>
                        <Button variant="outline" size="sm" className="gap-2">
                            <Download className="h-4 w-4" />
                            Exportar
                        </Button>
                        <Button size="sm" className="gap-2" onClick={() => setIsChatOpen(true)}>
                            <MessageSquare className="h-4 w-4" />
                            Chat IA
                        </Button>
                    </div>
                </DialogHeader>

                <div className="flex-1 overflow-hidden mt-4">
                    {isLoading ? (
                        <div className="flex flex-col items-center justify-center py-20">
                            <Loader2 className="h-8 w-8 animate-spin text-primary mb-2" />
                            <p className="text-sm text-muted-foreground">Cargando tabla...</p>
                        </div>
                    ) : table ? (
                        <EditableDataGrid
                            tableId={table.id}
                            columns={table.columns}
                        />
                    ) : (
                        <div className="py-20 text-center text-muted-foreground">
                            No se pudo cargar la tabla.
                        </div>
                    )}
                </div>

                <ContextualChat
                    isOpen={isChatOpen}
                    onClose={() => setIsChatOpen(false)}
                    title={table?.name || tableName}
                    context={{
                        type: 'table',
                        id: tableId || '',
                        snapshot: {
                            name: table?.name || tableName,
                            columns: table?.columns || [],
                        }
                    }}
                />

                {table && (
                    <ColumnManagerDialog
                        isOpen={isColumnManagerOpen}
                        onOpenChange={setIsColumnManagerOpen}
                        tableId={table.id}
                        initialColumns={table.columns}
                        onSuccess={(updatedColumns) => setTable({ ...table, columns: updatedColumns })}
                    />
                )}
            </DialogContent>
        </Dialog>
    );
}
