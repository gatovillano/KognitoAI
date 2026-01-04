'use client';

import { useState, useEffect, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Plus, FileSpreadsheet, Trash2, BarChart3, MoreVertical, ExternalLink } from 'lucide-react';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import apiClient from '@/lib/api';
import { toast } from 'sonner';
import { motion, AnimatePresence } from 'framer-motion';
import { ImportTableDialog } from './import-table-dialog';
import { TableDetailDialog } from './table-detail-dialog';
import { CreateTableDialog } from './create-table-dialog';

interface UserTable {
    id: string;
    name: string;
    description?: string;
    columns: any;
    created_at: string;
}

export function TablesView() {
    const [tables, setTables] = useState<UserTable[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isImportOpen, setIsImportOpen] = useState(false);
    const [isCreateOpen, setIsCreateOpen] = useState(false);
    const [selectedTable, setSelectedTable] = useState<UserTable | null>(null);
    const [isDetailOpen, setIsDetailOpen] = useState(false);

    const fetchTables = useCallback(async () => {
        setIsLoading(true);
        try {
            const response = await apiClient.get('/api/tables/');
            setTables(response.data);
        } catch (error) {
            console.error('Error fetching tables:', error);
            toast.error('Error al cargar las tablas.');
        } finally {
            setIsLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchTables();
    }, [fetchTables]);

    const handleDeleteTable = async (id: string) => {
        if (!window.confirm('¿Estás seguro de que quieres eliminar esta tabla?')) return;

        try {
            await apiClient.delete(`/api/tables/${id}`);
            toast.success('Tabla eliminada correctamente.');
            setTables(prev => prev.filter(t => t.id !== id));
        } catch (error) {
            toast.error('Error al eliminar la tabla.');
        }
    };

    if (isLoading) {
        return <div className="flex justify-center py-20">Cargando tablas...</div>;
    }

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center">
                <h2 className="text-xl font-semibold">Tus Tablas de Datos</h2>
                <div className="flex gap-2">
                    <Button variant="outline" onClick={() => setIsCreateOpen(true)} className="gap-2">
                        <Plus className="h-4 w-4" />
                        Crear Tabla
                    </Button>
                    <Button onClick={() => setIsImportOpen(true)} className="gap-2">
                        <Plus className="h-4 w-4" />
                        Importar Tabla
                    </Button>
                </div>
            </div>

            {tables.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-20 text-center border-2 border-dashed rounded-xl bg-muted/30">
                    <FileSpreadsheet className="h-16 w-16 text-muted-foreground/50 mb-6" />
                    <h3 className="text-xl font-semibold mb-2">No hay tablas aún</h3>
                    <p className="text-muted-foreground mb-8 max-w-md">
                        Importa archivos CSV o Excel para empezar a analizar tus datos con IA.
                    </p>
                    <Button onClick={() => setIsImportOpen(true)}>
                        <Plus className="mr-2 h-4 w-4" />
                        Importar mi primera Tabla
                    </Button>
                </div>
            ) : (
                <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                    <AnimatePresence>
                        {tables.map((table) => (
                            <motion.div
                                key={table.id}
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, scale: 0.95 }}
                            >
                                <Card className="group hover:shadow-md transition-all duration-200 border-primary/10">
                                    <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-2">
                                        <div className="space-y-1">
                                            <CardTitle className="text-lg font-bold group-hover:text-primary transition-colors">
                                                {table.name}
                                            </CardTitle>
                                            <p className="text-xs text-muted-foreground line-clamp-1">
                                                {table.description || 'Sin descripción'}
                                            </p>
                                        </div>
                                        <DropdownMenu>
                                            <DropdownMenuTrigger asChild>
                                                <Button variant="ghost" size="icon" className="h-8 w-8">
                                                    <MoreVertical className="h-4 w-4" />
                                                </Button>
                                            </DropdownMenuTrigger>
                                            <DropdownMenuContent align="end">
                                                <DropdownMenuItem onClick={() => handleDeleteTable(table.id)} className="text-destructive">
                                                    <Trash2 className="mr-2 h-4 w-4" />
                                                    Eliminar
                                                </DropdownMenuItem>
                                            </DropdownMenuContent>
                                        </DropdownMenu>
                                    </CardHeader>
                                    <CardContent>
                                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                            <FileSpreadsheet className="h-3 w-3" />
                                            <span>{Object.keys(table.columns || {}).length} columnas</span>
                                            <span>•</span>
                                            <span>{new Date(table.created_at).toLocaleDateString()}</span>
                                        </div>
                                    </CardContent>
                                    <CardFooter className="pt-0 flex gap-2">
                                        <Button
                                            variant="outline"
                                            size="sm"
                                            className="w-full gap-2"
                                            onClick={() => {
                                                setSelectedTable(table);
                                                setIsDetailOpen(true);
                                            }}
                                        >
                                            <ExternalLink className="h-3 w-3" />
                                            Ver Datos
                                        </Button>
                                        <Button variant="secondary" size="sm" className="w-full gap-2" onClick={() => toast.info('Análisis en desarrollo')}>
                                            <BarChart3 className="h-3 w-3" />
                                            Analizar
                                        </Button>
                                    </CardFooter>
                                </Card>
                            </motion.div>
                        ))}
                    </AnimatePresence>
                </div>
            )}

            <ImportTableDialog
                isOpen={isImportOpen}
                onOpenChange={setIsImportOpen}
                onSuccess={fetchTables}
            />

            <CreateTableDialog
                open={isCreateOpen}
                onOpenChange={setIsCreateOpen}
                onSuccess={(newTable) => {
                    setTables(prev => [newTable, ...prev]);
                    setSelectedTable(newTable);
                    setIsDetailOpen(true);
                }}
            />

            <TableDetailDialog
                isOpen={isDetailOpen}
                onOpenChange={setIsDetailOpen}
                tableId={selectedTable?.id || null}
                tableName={selectedTable?.name || ''}
            />
        </div>
    );
}
