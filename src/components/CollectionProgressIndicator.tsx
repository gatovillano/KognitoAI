'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Loader2, CheckCircle, XCircle, X, Search, FileText } from 'lucide-react';
import { Button } from '@/components/ui/button';

export interface CollectionTask {
    task_id: string;
    phase: string;
    message: string;
    progress_percent: number;
    is_complete: boolean;
    has_error: boolean;
    error?: string;
    topic?: string;
}

const getStatusIcon = (task: CollectionTask) => {
    if (task.has_error) return <XCircle className="h-4 w-4 text-red-500" />;
    if (task.is_complete) return <CheckCircle className="h-4 w-4 text-emerald-500" />;
    return <Loader2 className="h-4 w-4 text-emerald-500 animate-spin" />;
};

const getPhaseLabel = (phase: string) => {
    const phases: Record<string, string> = {
        'initializing': 'Iniciando',
        'analyzing_structure': 'Analizando estructura',
        'extracting_key_themes': 'Extrayendo temas clave',
        'summarizing_content': 'Resumiendo contenido',
        'tagging_documents': 'Etiquetando documentos',
        'completed': 'Completado',
        'error': 'Error'
    };
    return phases[phase] || phase;
};

export default function CollectionProgressIndicator({ tasks, onDismiss }: { tasks: CollectionTask[], onDismiss: (taskId: string) => void }) {
    const [isVisible, setIsVisible] = useState(false);

    useEffect(() => {
        if (tasks.length > 0) {
            setIsVisible(true);
        } else {
            const timer = setTimeout(() => setIsVisible(false), 500) as any;
            return () => clearTimeout(timer);
        }
    }, [tasks]);

    if (!isVisible) return null;

    return (
        <motion.div
            layout
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.95 }}
            transition={{ duration: 0.4, ease: [0.4, 0, 0.2, 1] }}
            className="space-y-3"
        >
            <Card className="relative overflow-hidden border-2 bg-gradient-to-br from-emerald-50/80 via-white to-teal-50/80 dark:from-emerald-950/30 dark:via-gray-900 dark:to-teal-950/30 shadow-xl backdrop-blur-sm">
                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-emerald-500/5 to-transparent animate-shimmer" />

                <CardHeader className="pb-4 relative">
                    <div className="flex items-center justify-between">
                        <CardTitle className="flex items-center gap-3 text-lg font-semibold text-emerald-900 dark:text-emerald-100">
                            <div className="p-2 rounded-lg bg-gradient-to-br from-emerald-600 to-teal-600 shadow-md">
                                <Search className="h-5 w-5 text-white" />
                            </div>
                            <div>
                                <div className="flex items-center gap-2">
                                    Análisis de Colecciones
                                </div>
                                <p className="text-xs font-normal text-emerald-700/70 dark:text-emerald-300/70 mt-0.5">
                                    {tasks.length} {tasks.length === 1 ? 'colección procesándose' : 'colecciones procesándose'}
                                </p>
                            </div>
                        </CardTitle>
                    </div>
                </CardHeader>

                <CardContent className="space-y-3 relative">
                    <AnimatePresence mode="popLayout">
                        {tasks.map((task) => (
                            <motion.div
                                key={task.task_id}
                                layout
                                initial={{ opacity: 0, y: -10, scale: 0.95 }}
                                animate={{ opacity: 1, y: 0, scale: 1 }}
                                exit={{ opacity: 0, x: -20, scale: 0.95 }}
                                className={`relative p-4 rounded-xl border-2 transition-all duration-300 ${task.has_error
                                    ? 'bg-red-50/50 border-red-200 dark:bg-red-950/20 dark:border-red-800'
                                    : task.is_complete
                                        ? 'bg-emerald-50/50 border-emerald-200 dark:bg-emerald-950/20 dark:border-emerald-800'
                                        : 'bg-white/50 border-emerald-100 dark:bg-gray-800/50 dark:border-emerald-900/30'
                                    }`}
                            >
                                <div className="space-y-3">
                                    <div className="flex items-start justify-between gap-3">
                                        <div className="flex items-start gap-3 flex-1 min-w-0">
                                            <div className="mt-1">
                                                {getStatusIcon(task)}
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-center gap-2 mb-1">
                                                    <p className="font-bold text-sm truncate flex items-center gap-1.5">
                                                        <FileText className="h-3.5 w-3.5 text-emerald-600" />
                                                        {task.topic || 'Colección sin nombre'}
                                                    </p>
                                                </div>
                                                <p className="text-xs text-emerald-800/60 dark:text-emerald-300/60 font-medium flex items-center gap-1.5">
                                                    {getPhaseLabel(task.phase)}
                                                </p>
                                            </div>
                                        </div>
                                        {(task.is_complete || task.has_error) && (
                                            <Button
                                                variant="ghost"
                                                size="icon"
                                                className="h-6 w-6 -mr-1 -mt-1"
                                                onClick={() => onDismiss(task.task_id)}
                                            >
                                                <X className="h-3 w-3" />
                                            </Button>
                                        )}
                                    </div>

                                    {!task.is_complete && !task.has_error && (
                                        <div className="space-y-2">
                                            <div className="relative h-2 w-full bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
                                                <motion.div
                                                    className="absolute inset-y-0 left-0 bg-gradient-to-r from-emerald-500 to-teal-500"
                                                    initial={{ width: 0 }}
                                                    animate={{ width: `${task.progress_percent}%` }}
                                                    transition={{ duration: 0.5 }}
                                                />
                                            </div>
                                            <div className="flex justify-between items-center text-[10px]">
                                                <span className="text-emerald-800/50 italic truncate max-w-[70%]">
                                                    {task.message}
                                                </span>
                                                <span className="font-bold text-emerald-600 dark:text-emerald-400">
                                                    {Math.round(task.progress_percent)}%
                                                </span>
                                            </div>
                                        </div>
                                    )}

                                    {task.has_error && (
                                        <div className="p-2 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-100 dark:border-red-800/30">
                                            <p className="text-[11px] text-red-600 dark:text-red-400 leading-relaxed">
                                                {task.error}
                                            </p>
                                        </div>
                                    )}
                                </div>
                            </motion.div>
                        ))}
                    </AnimatePresence>
                </CardContent>
            </Card>
        </motion.div>
    );
}
