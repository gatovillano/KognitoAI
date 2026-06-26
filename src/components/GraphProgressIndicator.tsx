'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Network, Loader2, CheckCircle, XCircle, Clock, X, Brain, Sparkles, Database, Share2 } from 'lucide-react';
import { Button } from '@/components/ui/button';

import { AnalysisTask } from '@/contexts/TaskContext';

export type GraphTask = AnalysisTask;

const getStatusIcon = (task: GraphTask) => {
    if (task.has_error) return <XCircle className="h-4 w-4 text-red-500" />;
    if (task.is_complete) return <CheckCircle className="h-4 w-4 text-emerald-500" />;
    return <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />;
};

const getPhaseLabel = (phase: string) => {
    const phases: Record<string, string> = {
        'initializing': 'Inicializando',
        'fetching_documents': 'Obteniendo documentos',
        'reconstructing_content': 'Reconstruyendo contenido',
        'hybrid_extracting_entities': 'Extrayendo entidades',
        'hybrid_deduplicating': 'Deduplicando',
        'hybrid_semantic_relationships': 'Creando relaciones semánticas',
        'hybrid_cooccurrence': 'Analizando co-ocurrencias',
        'hybrid_llm_enrichment': 'Enriqueciendo con IA',
        'conceptual_creating_documents': 'Preparando documentos',
        'conceptual_extracting_quotes': 'Extrayendo citas clave',
        'conceptual_thematic_relationships': 'Vinculando temas',
        'conceptual_idea_profiles': 'Perfilando ideas',
        'searching': 'Buscando información',
        'reading': 'Leyendo contenido',
        'analyzing': 'Analizando datos',
        'summarizing': 'Sintetizando resultados',
        'saving_to_neo4j': 'Guardando en base de datos',
        'completed': 'Completado',
        'error': 'Error'
    };
    return phases[phase] || phase;
};

const getGroupTitle = (tasks: GraphTask[]) => {
    if (tasks.some(t => t.type === 'document' || t.analysis_type === 'document' || t.analysis_type === 'document_summary' || t.file_name)) {
        return 'Análisis de Documento';
    }
    if (tasks.some(t => t.type === 'collection' || t.topic)) {
        return 'Análisis de Colección';
    }
    if (tasks.some(t => t.type === 'graph')) {
        return 'Grafo de Conocimiento';
    }
    return 'Procesamiento de IA';
};

const getTaskTitle = (task: GraphTask) => {
    if (task.file_name) {
        return `Documento: ${task.file_name}`;
    }
    if (task.topic) {
        return `Colección: ${task.topic}`;
    }
    return 'Proceso en ejecución';
};

export default function GraphProgressIndicator({ tasks, onDismiss }: { tasks: GraphTask[], onDismiss: (taskId: string) => void }) {
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
            <Card className="relative overflow-hidden border-2 bg-gradient-to-br from-purple-50/80 via-white to-indigo-50/80 dark:from-purple-950/30 dark:via-gray-900 dark:to-indigo-950/30 shadow-xl backdrop-blur-sm">
                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-purple-500/5 to-transparent animate-shimmer" />

                <CardHeader className="pb-4 relative">
                    <div className="flex items-center justify-between">
                        <CardTitle className="flex items-center gap-3 text-lg font-semibold">
                            <div className="p-2 rounded-lg bg-gradient-to-br from-purple-600 to-indigo-600 shadow-md">
                                <Brain className="h-5 w-5 text-white" />
                            </div>
                                    <div>
                                        <div className="flex items-center gap-2">
                                            {getGroupTitle(tasks)}
                                            <Sparkles className="h-4 w-4 text-purple-500 animate-pulse" />
                                        </div>
                                <p className="text-xs font-normal text-muted-foreground mt-0.5">
                                    {tasks.length} {tasks.length === 1 ? 'proceso activo' : 'procesos activos'}
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
                                        : 'bg-white/50 border-purple-100 dark:bg-gray-800/50 dark:border-purple-900/30'
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
                                                    <p className="font-bold text-sm truncate">
                                                        {getTaskTitle(task)}
                                                    </p>
                                                    {task.processing_mode && (
                                                        <span className="text-[10px] px-1.5 py-0.5 rounded-md bg-purple-100 text-purple-700 dark:bg-purple-900/50 dark:text-purple-300 font-medium uppercase tracking-wider">
                                                            {task.processing_mode}
                                                        </span>
                                                    )}
                                                </div>
                                                <p className="text-xs text-muted-foreground font-medium flex items-center gap-1.5">
                                                    {getPhaseLabel(task.phase)}
                                                </p>
                                            </div>
                                        </div>
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            className="h-6 w-6 -mr-1 -mt-1"
                                            onClick={() => onDismiss(task.task_id)}
                                        >
                                            <X className="h-3 w-3" />
                                        </Button>
                                    </div>

                                    {!task.is_complete && !task.has_error && (
                                        <div className="space-y-2">
                                            <div className="relative h-2 w-full bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
                                                <motion.div
                                                    className="absolute inset-y-0 left-0 bg-gradient-to-r from-purple-500 to-indigo-500"
                                                    initial={{ width: 0 }}
                                                    animate={{ width: `${task.progress_percent}%` }}
                                                    transition={{ duration: 0.5 }}
                                                />
                                            </div>
                                            <div className="flex justify-between items-center text-[10px]">
                                                <span className="text-muted-foreground italic truncate max-w-[70%]">
                                                    {task.message}
                                                </span>
                                                <span className="font-bold text-purple-600 dark:text-purple-400">
                                                    {Math.round(task.progress_percent)}%
                                                </span>
                                            </div>
                                        </div>
                                    )}

                                    {task.metrics && (
                                        <div className="grid grid-cols-2 gap-2 pt-1">
                                            <div className="flex items-center gap-2 px-2 py-1.5 rounded-lg bg-white/50 dark:bg-gray-900/50 border border-border/50">
                                                <Database className="h-3 w-3 text-purple-500" />
                                                <div className="flex flex-col">
                                                    <span className="text-[9px] text-muted-foreground uppercase font-bold">Entidades</span>
                                                    <span className="text-xs font-bold">{task.metrics.entities_count}</span>
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-2 px-2 py-1.5 rounded-lg bg-white/50 dark:bg-gray-900/50 border border-border/50">
                                                <Share2 className="h-3 w-3 text-indigo-500" />
                                                <div className="flex flex-col">
                                                    <span className="text-[9px] text-muted-foreground uppercase font-bold">Relaciones</span>
                                                    <span className="text-xs font-bold">{task.metrics.relationships_count}</span>
                                                </div>
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
