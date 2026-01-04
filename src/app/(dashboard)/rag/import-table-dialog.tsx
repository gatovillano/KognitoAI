'use client';

import { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Upload, FileSpreadsheet, Loader2, CheckCircle2, PlusCircle } from 'lucide-react';
import apiClient from '@/lib/api';
import { toast } from 'sonner';

interface ImportTableDialogProps {
    isOpen: boolean;
    onOpenChange: (open: boolean) => void;
    onSuccess: () => void;
}

export function ImportTableDialog({ isOpen, onOpenChange, onSuccess }: ImportTableDialogProps) {
    const [file, setFile] = useState<File | null>(null);
    const [name, setName] = useState('');
    const [description, setDescription] = useState('');
    const [isProcessing, setIsProcessing] = useState(false);
    const [activeTab, setActiveTab] = useState('import');

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            const selectedFile = e.target.files[0];
            setFile(selectedFile);
            if (!name) {
                setName(selectedFile.name.replace(/\.[^/.]+$/, ""));
            }
        }
    };

    const handleCreate = async () => {
        if (!name) {
            toast.error('Por favor, asigna un nombre a la tabla.');
            return;
        }

        setIsProcessing(true);
        try {
            if (activeTab === 'import' && file) {
                const formData = new FormData();
                formData.append('file', file);
                formData.append('name', name);
                formData.append('description', description);
                await apiClient.post('/api/tables/import', formData, {
                    headers: { 'Content-Type': 'multipart/form-data' },
                });
                toast.success('Tabla importada con éxito.');
            } else {
                // Crear tabla vacía con una columna por defecto
                await apiClient.post('/api/tables/', {
                    name,
                    description,
                    columns: [{ name: 'ID', type: 'number', required: true }]
                });
                toast.success('Tabla creada con éxito.');
            }
            onSuccess();
            onOpenChange(false);
            resetForm();
        } catch (error) {
            console.error('Error creating table:', error);
            toast.error('Error al crear la tabla.');
        } finally {
            setIsProcessing(false);
        }
    };

    const resetForm = () => {
        setFile(null);
        setName('');
        setDescription('');
        setActiveTab('import');
    };

    return (
        <Dialog open={isOpen} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[450px]">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <FileSpreadsheet className="h-5 w-5 text-primary" />
                        Nueva Tabla de Datos
                    </DialogTitle>
                    <DialogDescription>
                        Crea una tabla importando un archivo o empezando desde cero.
                    </DialogDescription>
                </DialogHeader>

                <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
                    <TabsList className="grid w-full grid-cols-2 mb-4">
                        <TabsTrigger value="import" className="gap-2">
                            <Upload className="h-4 w-4" />
                            Importar
                        </TabsTrigger>
                        <TabsTrigger value="empty" className="gap-2">
                            <PlusCircle className="h-4 w-4" />
                            Vacía
                        </TabsTrigger>
                    </TabsList>

                    <div className="grid gap-4 py-2">
                        <div className="grid gap-2">
                            <Label htmlFor="name">Nombre de la Tabla</Label>
                            <Input
                                id="name"
                                placeholder="Ej: Ventas 2023"
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                            />
                        </div>

                        <div className="grid gap-2">
                            <Label htmlFor="description">Descripción (Opcional)</Label>
                            <Textarea
                                id="description"
                                placeholder="Describe el contenido de los datos..."
                                value={description}
                                className="h-20"
                                onChange={(e) => setDescription(e.target.value)}
                            />
                        </div>

                        <TabsContent value="import" className="mt-0">
                            <div className="grid gap-2">
                                <Label htmlFor="file">Archivo (CSV, XLSX, XLS)</Label>
                                <div className="flex items-center justify-center w-full">
                                    <label
                                        htmlFor="file-upload"
                                        className={`flex flex-col items-center justify-center w-full h-32 border-2 border-dashed rounded-lg cursor-pointer transition-colors ${file ? 'border-primary bg-primary/5' : 'border-muted-foreground/25 hover:bg-muted/50'}`}
                                    >
                                        <div className="flex flex-col items-center justify-center pt-5 pb-6">
                                            {file ? (
                                                <>
                                                    <CheckCircle2 className="w-8 h-8 mb-2 text-primary" />
                                                    <p className="text-xs font-medium text-primary truncate max-w-[200px]">{file.name}</p>
                                                </>
                                            ) : (
                                                <>
                                                    <Upload className="w-8 h-8 mb-2 text-muted-foreground" />
                                                    <p className="text-xs text-muted-foreground">Haz clic para subir o arrastra y suelta</p>
                                                </>
                                            )}
                                        </div>
                                        <input id="file-upload" type="file" className="hidden" accept=".csv,.xlsx,.xls" onChange={handleFileChange} />
                                    </label>
                                </div>
                            </div>
                        </TabsContent>

                        <TabsContent value="empty" className="mt-0">
                            <div className="p-4 bg-muted/30 rounded-lg border border-dashed text-center">
                                <p className="text-xs text-muted-foreground">
                                    Se creará una tabla vacía con una columna de ID por defecto. Podrás añadir más columnas después.
                                </p>
                            </div>
                        </TabsContent>
                    </div>
                </Tabs>

                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isProcessing}>
                        Cancelar
                    </Button>
                    <Button onClick={handleCreate} disabled={isProcessing || (activeTab === 'import' && !file) || !name}>
                        {isProcessing ? (
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        ) : activeTab === 'import' ? 'Importar' : 'Crear Tabla'}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
