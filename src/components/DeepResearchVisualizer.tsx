'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { BrainCircuit, Search, Globe, Database, Cpu, CheckCircle2, Loader2, Sparkles } from 'lucide-react';
import { useEffect, useState, useMemo } from 'react';

interface DeepResearchVisualizerProps {
    progress: number;
    statusText: string;
    currentStep?: string;
}

const mapStatusToFirstPerson = (status: string): string => {
    if (!status) return 'Iniciando investigación...';
    
    // 1. Verificando claridad de la consulta...
    if (status.includes('Verificando claridad')) {
        return 'Estoy analizando tu consulta para estructurar los objetivos de la investigación.';
    }
    // 2. Generando el resumen de investigación...
    if (status.includes('Generando el resumen de investigación')) {
        return 'Estoy trazando el mapa de ruta y definiendo el plan de investigación...';
    }
    // 3. Resumen de investigación generado. Iniciando investigación...
    if (status.includes('Resumen de investigación generado')) {
        return 'He establecido el plan. Estoy creando agentes investigadores especializados para comenzar.';
    }
    // 4. Supervisor: Planificando iteración...
    if (status.includes('Supervisor: Planificando iteración')) {
        const match = status.match(/iteración de investigación (\d+)\/(\d+)/i);
        if (match) {
            return `Como supervisor, estoy planificando y organizando la iteración de investigación ${match[1]} de ${match[2]}...`;
        }
        return 'Como supervisor, estoy coordinando el trabajo y planificando los siguientes pasos de los agentes.';
    }
    // 5. Supervisor: Preparando herramientas...
    if (status.includes('Supervisor: Preparando herramientas')) {
        return 'Estoy preparando y calibrando las herramientas de búsqueda y análisis.';
    }
    // 6. Investigando: topic (Paso X/Y)
    if (status.includes('Investigando:')) {
        const match = status.match(/Investigando:\s*(.*?)(?:\s*\(Paso\s*(\d+)\/(\d+)\))?$/i);
        if (match) {
            const topic = match[1];
            const step = match[2] ? ` (Paso ${match[2]}/${match[3]})` : '';
            return `Estoy explorando y recolectando fuentes sobre: "${topic}"${step}.`;
        }
        return 'Estoy investigando y recolectando información de las fuentes seleccionadas...';
    }
    // 7. Ejecutando herramientas para: topic
    if (status.includes('Ejecutando herramientas para:')) {
        const topic = status.replace('Ejecutando herramientas para:', '').trim();
        return `Buscando información detallada y consultando bases de datos para: "${topic}"...`;
    }
    // 8. Herramientas ejecutadas para: topic
    if (status.includes('Herramientas ejecutadas para:')) {
        const topic = status.replace('Herramientas ejecutadas para:', '').trim();
        return `He recopilado información relevante para: "${topic}".`;
    }
    // 9. Sintetizando hallazgos para: topic
    if (status.includes('Sintetizando hallazgos para:')) {
        const topic = status.replace('Sintetizando hallazgos para:', '').trim();
        return `Estoy analizando, filtrando y consolidando las fuentes recopiladas para: "${topic}".`;
    }
    // 10. Experto name: topic (Paso X/Y)
    if (status.includes('Experto ')) {
        const match = status.match(/Experto\s+(.*?):\s*(.*?)(?:\s*\(Paso\s*(\d+)\/(\d+)\))?$/i);
        if (match) {
            const expert = match[1];
            const topic = match[2];
            const step = match[3] ? ` (Paso ${match[3]}/${match[4]})` : '';
            return `Mi especialista en ${expert} está buscando información y analizando en profundidad: "${topic}"${step}.`;
        }
        return 'El especialista asignado está analizando la información...';
    }
    // 11. Ejecutando herramientas para experto name: topic
    if (status.includes('Ejecutando herramientas para experto')) {
        const match = status.match(/Ejecutando herramientas para experto\s+(.*?):\s*(.*)/i);
        if (match) {
            return `El especialista en ${match[1]} está extrayendo datos clave para: "${match[2]}"...`;
        }
        return 'El especialista está ejecutando herramientas de consulta especializada...';
    }
    // 12. Sintetizando hallazgos del experto name: topic
    if (status.includes('Sintetizando hallazgos del experto')) {
        const match = status.match(/Sintetizando hallazgos del experto\s+(.*?):\s*(.*)/i);
        if (match) {
            return `El especialista en ${match[1]} está redactando sus conclusiones para: "${match[2]}".`;
        }
        return 'El especialista está sintetizando sus hallazgos...';
    }
    // 13. Generando el informe final...
    if (status.includes('Generando el informe final')) {
        return 'Estoy redactando y estructurando el informe final con todos los hallazgos y recomendaciones.';
    }

    return status;
};

export default function DeepResearchVisualizer({ progress, statusText, currentStep }: DeepResearchVisualizerProps) {
    const [logs, setLogs] = useState<string[]>([]);

    useEffect(() => {
        if (statusText) {
            const mappedMsg = mapStatusToFirstPerson(statusText);
            setLogs(prev => {
                if (prev.length > 0 && prev[0] === mappedMsg) return prev;
                return [mappedMsg, ...prev].slice(0, 3);
            });
        }
    }, [statusText]);

    const latestFirstPersonMsg = logs[0] || mapStatusToFirstPerson(statusText);

    const milestones = useMemo(() => [
        {
            id: 'plan',
            title: 'Planificación y Configuración',
            description: 'Analizando la consulta y configurando el plan de investigación.',
            minProgress: 0,
            maxProgress: 20,
            icon: BrainCircuit,
        },
        {
            id: 'search',
            title: 'Exploración de Fuentes',
            description: 'Buscando en la web y recolectando fuentes relevantes.',
            minProgress: 21,
            maxProgress: 60,
            icon: Globe,
        },
        {
            id: 'expert',
            title: 'Análisis de Expertos',
            description: 'Agentes especialistas investigando a fondo cada tema.',
            minProgress: 61,
            maxProgress: 90,
            icon: Cpu,
        },
        {
            id: 'report',
            title: 'Generación de Informe',
            description: 'Estructurando y redactando el informe y recomendaciones.',
            minProgress: 91,
            maxProgress: 100,
            icon: CheckCircle2,
        }
    ], []);

    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="w-full max-w-2xl mx-auto p-8 rounded-[2.5rem] bg-gradient-to-br from-background/40 via-background/80 to-muted/30 border border-primary/10 backdrop-blur-3xl shadow-[0_20px_50px_rgba(0,0,0,0.3)] overflow-hidden relative"
        >
            {/* Orbes de luz premium en el fondo */}
            <div className="absolute inset-0 overflow-hidden pointer-events-none">
                <motion.div
                    animate={{
                        scale: [1, 1.2, 1],
                        opacity: [0.1, 0.2, 0.1],
                        x: [0, 20, 0],
                        y: [0, -20, 0]
                    }}
                    transition={{ duration: 8, repeat: Infinity, ease: "easeInOut" }}
                    className="absolute top-[-20%] left-[-10%] w-64 h-64 bg-primary/30 rounded-full blur-[100px]"
                />
                <motion.div
                    animate={{
                        scale: [1.2, 1, 1.2],
                        opacity: [0.05, 0.15, 0.05],
                        x: [0, -30, 0],
                        y: [0, 30, 0]
                    }}
                    transition={{ duration: 10, repeat: Infinity, ease: "easeInOut", delay: 1 }}
                    className="absolute bottom-[-20%] right-[-10%] w-80 h-80 bg-blue-500/20 rounded-full blur-[120px]"
                />
            </div>

            <div className="relative z-10">
                {/* Header */}
                <div className="flex items-center justify-between mb-6">
                    <div className="flex items-center gap-4">
                        <div className="relative">
                            <div className="absolute inset-0 bg-primary/20 rounded-2xl blur-md animate-pulse" />
                            <div className="relative p-3 rounded-2xl bg-primary/10 border border-primary/20 shadow-inner">
                                <BrainCircuit className="h-7 w-7 text-primary" />
                            </div>
                        </div>
                        <div>
                            <div className="flex items-center gap-2">
                                <h3 className="text-xl font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-foreground via-primary to-blue-400">
                                    Deep Research
                                </h3>
                                <Sparkles className="h-4 w-4 text-primary/60" />
                            </div>
                            <p className="text-xs text-muted-foreground/80 font-medium tracking-wide flex items-center gap-1.5">
                                <span className="relative flex h-2 w-2">
                                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
                                    <span className="relative inline-flex rounded-full h-2 w-2 bg-primary"></span>
                                </span>
                                PROCESANDO CONOCIMIENTO GLOBAL
                            </p>
                        </div>
                    </div>
                    <div className="flex flex-col items-end">
                        <div className="flex items-baseline gap-1">
                            <span className="text-4xl font-black tabular-nums tracking-tighter text-primary">
                                {Math.round(progress)}
                            </span>
                            <span className="text-sm font-bold text-primary/60">%</span>
                        </div>
                    </div>
                </div>

                {/* Barra de progreso de alto contraste */}
                <div className="space-y-3 mb-8">
                    <div className="relative h-2.5 w-full bg-muted/30 rounded-full overflow-hidden border border-white/5 ring-1 ring-black/5">
                        <motion.div
                            className="absolute top-0 left-0 h-full bg-gradient-to-r from-primary via-blue-500 to-indigo-600 shadow-[0_0_15px_rgba(var(--primary),0.5)]"
                            initial={{ width: 0 }}
                            animate={{ width: `${progress}%` }}
                            transition={{ type: "spring", stiffness: 40, damping: 15 }}
                        />
                        <div className="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/carbon-fibre.png')] opacity-10 pointer-events-none" />
                    </div>
                </div>

                {/* Línea de Tiempo Vertical */}
                <div className="space-y-1">
                    {milestones.map((m, idx) => {
                        const isCompleted = progress > m.maxProgress;
                        const isActive = progress >= m.minProgress && progress <= m.maxProgress;
                        const isPending = progress < m.minProgress;
                        const Icon = isCompleted ? CheckCircle2 : m.icon;

                        return (
                            <div key={m.id} className="relative pl-10 pb-6 last:pb-2">
                                {/* Línea vertical conectora */}
                                {idx < milestones.length - 1 && (
                                    <div className={`absolute left-4 top-8 bottom-0 w-0.5 -translate-x-1/2 transition-colors duration-500 ${
                                        isCompleted ? 'bg-emerald-500/50' : 
                                        isActive ? 'bg-gradient-to-b from-primary/50 to-muted/30' : 'bg-muted/30'
                                    }`} />
                                )}

                                {/* Icono del hito */}
                                <div className={`absolute left-4 top-1 -translate-x-1/2 w-8 h-8 rounded-xl flex items-center justify-center border transition-all duration-500 z-10 ${
                                    isCompleted ? 'bg-emerald-500/10 border-emerald-500 text-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.15)]' :
                                    isActive ? 'bg-primary/10 border-primary text-primary shadow-[0_0_12px_rgba(var(--primary),0.25)]' :
                                    'bg-background/40 border-border/40 text-muted-foreground/30'
                                }`}>
                                    {isActive && !isCompleted ? (
                                        <div className="relative flex items-center justify-center">
                                            <Icon className="w-4 h-4 animate-pulse" />
                                            <span className="absolute -top-1 -right-1 flex h-2 w-2">
                                                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
                                                <span className="relative inline-flex rounded-full h-2 w-2 bg-primary"></span>
                                            </span>
                                        </div>
                                    ) : (
                                        <Icon className="w-4 h-4" />
                                    )}
                                </div>

                                {/* Contenido del hito */}
                                <div className={`transition-all duration-300 ${isPending ? 'opacity-30' : 'opacity-100'}`}>
                                    <h4 className={`text-sm font-bold tracking-tight ${isActive ? 'text-primary' : isCompleted ? 'text-emerald-500' : 'text-foreground/90'}`}>
                                        {m.title}
                                    </h4>
                                    <p className="text-xs text-muted-foreground/80 mt-0.5 leading-relaxed">
                                        {m.description}
                                    </p>

                                    {/* Mensaje dinámico en primera persona (solo para el hito activo) */}
                                    {isActive && latestFirstPersonMsg && (
                                        <motion.div 
                                            initial={{ opacity: 0, y: 5 }}
                                            animate={{ opacity: 1, y: 0 }}
                                            className="mt-3 p-3 rounded-2xl bg-primary/5 border border-primary/10 flex items-center gap-3"
                                        >
                                            <div className="flex-shrink-0 relative">
                                                <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
                                                <div className="absolute inset-0 animate-ping bg-primary/20 rounded-full" />
                                            </div>
                                            <span className="text-xs font-semibold text-foreground leading-normal">
                                                {latestFirstPersonMsg}
                                            </span>
                                        </motion.div>
                                    )}
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>
        </motion.div>
    );
}
