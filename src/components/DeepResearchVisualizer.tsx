'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { BrainCircuit, Search, Globe, Database, Cpu, CheckCircle2, Loader2, Sparkles } from 'lucide-react';
import { useEffect, useState, useMemo } from 'react';

interface DeepResearchVisualizerProps {
    progress: number;
    statusText: string;
    currentStep?: string;
}

/**
 * Simplifica textos largos de investigación para mostrar solo lo esencial.
 * Prioriza contenido entre negritas o trunca si es excesivamente largo.
 */
const simplifyText = (text: string): string => {
    if (!text) return '';

    // Extraer contenido en negrita si existe (ej: **Título**)
    const boldMatch = text.match(/\*\*(.*?)\*\*/);
    if (boldMatch && boldMatch[1]) {
        return boldMatch[1].trim();
    }

    // Si empieza con "Investigando:", limpiar ese prefijo para brevedad
    const cleanText = text.replace(/^Investigando:\s*/i, '');

    // Truncar si sigue siendo muy largo
    if (cleanText.length > 80) {
        return cleanText.substring(0, 77) + '...';
    }

    return cleanText;
};

export default function DeepResearchVisualizer({ progress, statusText, currentStep }: DeepResearchVisualizerProps) {
    const [logs, setLogs] = useState<{ original: string, simplified: string }[]>([]);

    // Mantener un historial de los últimos 3 estados simplificados
    useEffect(() => {
        if (statusText) {
            const simplified = simplifyText(statusText);
            setLogs(prev => {
                // Evitar duplicados consecutivos de la versión simplificada
                if (prev.length > 0 && prev[0].simplified === simplified) return prev;
                return [{ original: statusText, simplified }, ...prev].slice(0, 3);
            });
        }
    }, [statusText]);

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
                <div className="flex items-center justify-between mb-8">
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

                {/* Stepper Premium */}
                <div className="grid grid-cols-4 gap-2 mb-10 p-1 bg-muted/20 rounded-3xl border border-white/5 shadow-inner">
                    <StepIcon icon={Search} label="Index" active={progress > 5} completed={progress > 25} />
                    <StepIcon icon={Globe} label="Web" active={progress > 25} completed={progress > 65} />
                    <StepIcon icon={Database} label="Graph" active={progress > 65} completed={progress > 90} />
                    <StepIcon icon={Cpu} label="Core" active={progress > 90} completed={progress >= 100} />
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

                {/* Feed de Actividades Simplificado */}
                <div className="space-y-3 min-h-[100px] flex flex-col justify-end">
                    <AnimatePresence mode="popLayout">
                        {logs.map((log, i) => (
                            <motion.div
                                key={`${log.simplified}-${i}`}
                                initial={{ opacity: 0, y: 10, filter: "blur(10px)" }}
                                animate={{
                                    opacity: i === 0 ? 1 : (1 - i * 0.35),
                                    y: 0,
                                    filter: "blur(0px)",
                                    scale: i === 0 ? 1 : 0.98 - i * 0.02
                                }}
                                exit={{ opacity: 0, x: 20, filter: "blur(5px)" }}
                                transition={{ duration: 0.4, ease: "easeOut" }}
                                className={`flex items-center gap-3 p-3 rounded-2xl transition-all duration-300 ${i === 0 ? 'bg-primary/5 border border-primary/10 shadow-sm' : 'bg-transparent'
                                    }`}
                            >
                                <div className="flex-shrink-0">
                                    {i === 0 ? (
                                        <div className="relative">
                                            <Loader2 className="h-4 w-4 animate-spin text-primary" />
                                            <div className="absolute inset-0 animate-ping bg-primary/20 rounded-full" />
                                        </div>
                                    ) : (
                                        <CheckCircle2 className="h-4 w-4 text-emerald-500/80" />
                                    )}
                                </div>
                                <span className={`text-sm tracking-tight leading-snug ${i === 0 ? "text-foreground font-semibold" : "text-muted-foreground font-medium"
                                    }`}>
                                    {log.simplified}
                                </span>
                            </motion.div>
                        ))}
                    </AnimatePresence>
                </div>
            </div>

            {/* Decoración tech */}
            <div className="absolute top-0 right-0 p-4 opacity-5 pointer-events-none">
                <div className="flex gap-1">
                    {[1, 2, 3].map(j => (
                        <div key={j} className="w-1 h-3 bg-primary rounded-full" />
                    ))}
                </div>
            </div>
        </motion.div>
    );
}

function StepIcon({ icon: Icon, label, active, completed }: { icon: any, label: string, active: boolean, completed: boolean }) {
    return (
        <div className="flex flex-col items-center gap-2 flex-1 py-3 px-1 rounded-2xl transition-colors">
            <motion.div
                initial={false}
                animate={{
                    scale: active ? [1, 1.05, 1] : 1,
                }}
                transition={{ duration: 2, repeat: active && !completed ? Infinity : 0 }}
                className={`
                    p-2.5 rounded-xl border transition-all duration-500 relative
                    ${completed ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-500 shadow-inner' :
                        active ? 'bg-primary/20 border-primary/40 text-primary shadow-lg ring-1 ring-primary/20' :
                            'bg-background/20 border-transparent text-muted-foreground/40'}
                `}
            >
                {completed ? <CheckCircle2 className="h-4 w-4" /> : <Icon className="h-4 w-4" />}
                {active && !completed && (
                    <span className="absolute -top-1 -right-1 flex h-2 w-2">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-2 w-2 bg-primary"></span>
                    </span>
                )}
            </motion.div>
            <span className={`text-[9px] font-black uppercase tracking-[0.1em] ${completed ? 'text-emerald-500/70' :
                    active ? 'text-primary' :
                        'text-muted-foreground/30'
                }`}>
                {label}
            </span>
        </div>
    );
}
