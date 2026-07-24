'use client';

import { useState, useEffect, useCallback } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Loader2, MessageSquare, Download, Settings2, BarChart3, FileSpreadsheet, FileText } from 'lucide-react';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import apiClient from '@/lib/api';
import { toast } from 'sonner';
import { ContextualChat } from '@/components/ContextualChat';
import { EditableDataGrid } from './editable-data-grid';
import { ColumnManagerDialog } from './column-manager-dialog';
import { TableAnalysisDialog } from './table-analysis-dialog';

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
    const [isAnalysisOpen, setIsAnalysisOpen] = useState(false);
    const [isExporting, setIsExporting] = useState(false);

    const handleExport = async (format: 'xlsx' | 'csv') => {
        if (!tableId) return;
        setIsExporting(true);
        const toastId = toast.loading(`Exportando datos a ${format.toUpperCase()}...`);
        try {
            const response = await apiClient.get(`/api/tables/${tableId}/export`, {
                params: { format },
                responseType: 'blob',
            });

            const blob = new Blob([response.data], {
                type: format === 'xlsx'
                    ? 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                    : 'text/csv;charset=utf-8;'
            });

            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            const filename = `${table?.name || tableName || 'tabla'}.${format}`;
            link.setAttribute('download', filename);
            document.body.appendChild(link);
            link.click();
            link.remove();
            window.URL.revokeObjectURL(url);

            toast.success(`Tabla exportada exitosamente a ${format.toUpperCase()}`, { id: toastId });
        } catch (error) {
            console.error('Error exportando tabla:', error);
            toast.error('Error al exportar la tabla.', { id: toastId });
        } finally {
            setIsExporting(false);
        }
    };

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
                        <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                                <Button variant="outline" size="sm" className="gap-2" disabled={isExporting}>
                                    {isExporting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
                                    Exportar
                                </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                                <DropdownMenuItem onClick={() => handleExport('xlsx')} className="gap-2 cursor-pointer">
                                    <FileSpreadsheet className="h-4 w-4 text-emerald-600" />
                                    Excel (.xlsx)
                                </DropdownMenuItem>
                                <DropdownMenuItem onClick={() => handleExport('csv')} className="gap-2 cursor-pointer">
                                    <FileText className="h-4 w-4 text-blue-600" />
                                    CSV (.csv)
                                </DropdownMenuItem>
                            </DropdownMenuContent>
                        </DropdownMenu>
                        <Button variant="outline" size="sm" className="gap-2" onClick={() => setIsAnalysisOpen(true)}>
                            <BarChart3 className="h-4 w-4" />
                            Analizar
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

                {table && (
                    <TableAnalysisDialog
                        isOpen={isAnalysisOpen}
                        onOpenChange={setIsAnalysisOpen}
                        tableId={table.id}
                        tableName={table.name}
                    />
                )}
            </DialogContent>
        </Dialog>
    );
}
