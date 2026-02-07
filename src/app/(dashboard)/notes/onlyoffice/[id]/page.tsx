'use client';

import { useEffect, useState, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { ArrowLeft, Loader2, AlertCircle, FileDown } from 'lucide-react';
import { Button } from '@/components/ui/button';
import apiClient from '@/lib/api';
import { toast } from 'sonner';
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

declare global {
    interface Window {
        DocsAPI: any;
    }
}

export default function OnlyOfficeEditorPage() {
    const params = useParams();
    const router = useRouter();
    const noteId = params?.id as string;
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [config, setConfig] = useState<any>(null);
    const editorRef = useRef<any>(null);
    const loadingTimeoutRef = useRef<any>(null);

    // 1. Cargar la configuración desde el backend
    useEffect(() => {
        const fetchConfig = async () => {
            console.log('🔍 [OnlyOffice] Obteniendo configuración para nota:', noteId);
            try {
                const response = await apiClient.get(`/api/notes/${noteId}/onlyoffice-config`, {
                    timeout: 10000 // Timeout de 10s para la petición de config
                });
                setConfig(response.data);
            } catch (error: any) {
                console.error('❌ [OnlyOffice] Error fetching config:', error);
                const msg = error.response?.data?.detail || 'No se pudo cargar la configuración de OnlyOffice.';
                setError(msg);
                toast.error(msg);
                setIsLoading(false);
            }
        };

        if (noteId) {
            fetchConfig();
        }
    }, [noteId]);

    // 2. Cargar el script de OnlyOffice y manejar la inicialización
    useEffect(() => {
        let script: HTMLScriptElement | null = null;

        if (config && !editorRef.current) {
            // Establecer un timeout de carga (30 segundos)
            loadingTimeoutRef.current = setTimeout(() => {
                if (isLoading) {
                    setError('El editor de OnlyOffice está tardando demasiado en responder. Por favor, verifica tu conexión o el estado del servidor.');
                    setIsLoading(false);
                }
            }, 30000);

            script = document.createElement('script');

            // Determinar la URL del script (api.js)
            const onlyOfficeUrl = config.onlyoffice_url || process.env.NEXT_PUBLIC_ONLYOFFICE_URL || 'http://localhost:8081';
            const scriptUrl = `${onlyOfficeUrl.replace(/\/$/, '')}/web-apps/apps/api/documents/api.js`;

            script.src = scriptUrl;
            script.async = true;

            script.onload = () => {
                if (loadingTimeoutRef.current) clearTimeout(loadingTimeoutRef.current);

                if (window.DocsAPI) {
                    try {
                        // Si la config viene con token, OnlyOffice prefiere inicializar solo con él
                        let finalConfig = config.token ? { token: config.token } : (config.config || config);

                        // Asegurar dimensiones
                        finalConfig.width = '100%';
                        finalConfig.height = '100%';

                        editorRef.current = new window.DocsAPI.DocEditor('onlyoffice-editor', {
                            ...finalConfig,
                            events: {
                                onAppReady: () => {
                                    console.log('✅ [OnlyOffice] Editor listo');
                                    setIsLoading(false);
                                },
                                onError: (err: any) => {
                                    console.error('❌ [OnlyOffice] Error del editor:', err);
                                    toast.error('Error en el editor de OnlyOffice.');
                                }
                            }
                        });
                    } catch (err) {
                        console.error('❌ [OnlyOffice] Error inicializando:', err);
                        setError('Error al inicializar el editor de OnlyOffice.');
                        setIsLoading(false);
                    }
                } else {
                    setError('No se pudo encontrar la API de OnlyOffice.');
                    setIsLoading(false);
                }
            };

            script.onerror = (err) => {
                if (loadingTimeoutRef.current) clearTimeout(loadingTimeoutRef.current);
                console.error('❌ [OnlyOffice] Error cargando script:', err);
                setError(`No se pudo cargar el script de OnlyOffice desde ${scriptUrl}. Verifica que el servidor de documentos sea accesible.`);
                setIsLoading(false);
            };

            document.body.appendChild(script);
        }

        return () => {
            if (loadingTimeoutRef.current) clearTimeout(loadingTimeoutRef.current);
            if (editorRef.current) {
                try {
                    editorRef.current.destroyEditor();
                    editorRef.current = null;
                } catch (err) {
                    console.error('❌ [OnlyOffice] Error destruyendo editor:', err);
                }
            }
            if (script && document.body.contains(script)) {
                document.body.removeChild(script);
            }
        };
    }, [config]);

    return (
        <div className="flex flex-col h-screen bg-background">
            <header className="flex items-center justify-between p-4 border-b bg-card">
                <div className="flex items-center gap-4">
                    <Button variant="ghost" onClick={() => router.back()} size="sm">
                        <ArrowLeft className="mr-2 h-4 w-4" /> Volver
                    </Button>
                    <div className="h-6 w-px bg-border" />
                    <h1 className="text-lg font-semibold bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent">
                        Editor de Documentos Kognito
                    </h1>
                </div>

                <div className="flex items-center gap-2">
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                            const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || '';
                            window.open(`${apiBaseUrl}/api/notes/${noteId}/download-raw`, '_blank');
                        }}
                    >
                        <FileDown className="mr-2 h-4 w-4" /> Descargar DOCX
                    </Button>
                </div>
            </header>

            <main className="flex-grow relative flex flex-col">
                {isLoading && (
                    <div className="absolute inset-0 flex flex-col items-center justify-center bg-background/80 backdrop-blur-sm z-50">
                        <div className="relative">
                            <Loader2 className="h-12 w-12 animate-spin text-primary" />
                            <div className="absolute inset-0 h-12 w-12 rounded-full border-t-2 border-primary/20" />
                        </div>
                        <p className="mt-4 text-sm font-medium animate-pulse">Iniciando entorno de edición segura...</p>
                    </div>
                )}

                {error && (
                    <div className="p-8 max-w-2xl mx-auto">
                        <Alert variant="destructive">
                            <AlertCircle className="h-4 w-4" />
                            <AlertTitle>Error de Conexión</AlertTitle>
                            <AlertDescription className="mt-2 flex flex-col gap-4">
                                <p>{error}</p>
                                <Button variant="outline" onClick={() => window.location.reload()} className="w-fit">
                                    Reintentar carga
                                </Button>
                            </AlertDescription>
                        </Alert>
                    </div>
                )}

                <div
                    id="onlyoffice-editor"
                    className={`w-full h-full flex-grow ${error ? 'hidden' : 'block'}`}
                />
            </main>
        </div>
    );
}
