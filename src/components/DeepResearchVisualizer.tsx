'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { BrainCircuit, Search, Globe, Database, Cpu, CheckCircle2, Loader2 } from 'lucide-react';
import { Progress } from '@/components/ui/progress';
import { useEffect, useState } from 'react';

interface DeepResearchVisualizerProps {
    progress: number;
    statusText: string;
    currentStep?: string;
}

export default function DeepResearchVisualizer({ progress, statusText, currentStep }: DeepResearchVisualizerProps) {
    const [logs, setLogs] = useState<string[]>([]);

    // Mantener un historial de los últimos 3 estados para mostrar como "logs"
    useEffect(() => {
        if (statusText && !logs.includes(statusText)) {
            setLogs(prev => [statusText, ...prev].slice(0, 3));
        }
    }, [statusText]);

    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="w-full max-w-2xl mx-auto p-6 rounded-2xl bg-gradient-to-br from-background/80 to-muted/50 border border-primary/20 backdrop-blur-xl shadow-2xl overflow-hidden relative"
        >
            {/* Fondo decorativo con partículas */}
            <div className="absolute inset-0 overflow-hidden pointer-events-none opacity-20">
                <div className="absolute top-[-10%] left-[-10%] w-40 h-40 bg-primary rounded-full blur-[80px] animate-pulse" />
                <div className="absolute bottom-[-10%] right-[-10%] w-40 h-40 bg-blue-500 rounded-full blur-[80px] animate-pulse delay-700" />
            </div>

            <div className="relative z-10">
                <div className="flex items-center justify-between mb-6">
                    <div className="flex items-center gap-3">
                        <div className="p-2 rounded-xl bg-primary/10 border border-primary/20">
                            <BrainCircuit className="h-6 w-6 text-primary animate-pulse" />
                        </div>
                        <div>
                            <h3 className="text-lg font-semibold bg-clip-text text-transparent bg-gradient-to-r from-primary to-blue-400">
                                Investigación Profunda en Curso
                            </h3>
                            <p className="text-xs text-muted-foreground">Kognito AI está analizando múltiples fuentes</p>
                        </div>
                    </div>
                    <div className="text-right">
                        <span className="text-2xl font-bold text-primary">{Math.round(progress)}%</span>
                    </div>
                </div>

                {/* Visualización de pasos */}
                <div className="grid grid-cols-4 gap-4 mb-8">
                    <StepIcon icon={Search} label="Búsqueda" active={progress > 10} completed={progress > 30} />
                    <StepIcon icon={Globe} label="Web" active={progress > 30} completed={progress > 60} />
                    <StepIcon icon={Database} label="Grafo" active={progress > 60} completed={progress > 85} />
                    <StepIcon icon={Cpu} label="Síntesis" active={progress > 85} completed={progress >= 100} />
                </div>

                {/* Barra de progreso principal */}
                <div className="space-y-2 mb-6">
                    <div className="flex justify-between text-xs font-medium px-1">
                        <span className="text-primary animate-pulse">{statusText}</span>
                        <span className="text-muted-foreground">Procesando...</span>
                    </div>
                    <div className="relative h-3 w-full bg-muted rounded-full overflow-hidden border border-primary/10">
                        <motion.div
                            className="absolute top-0 left-0 h-full bg-gradient-to-r from-primary via-blue-500 to-primary bg-[length:200%_100%]"
                            initial={{ width: 0 }}
                            animate={{
                                width: `${progress}%`,
                                backgroundPosition: ["0% 0%", "100% 0%"]
                            }}
                            transition={{
                                width: { type: "spring", stiffness: 50, damping: 20 },
                                backgroundPosition: { duration: 2, repeat: Infinity, ease: "linear" }
                            }}
                        />
                    </div>
                </div>

                {/* Log de actividades */}
                <div className="space-y-2">
                    <AnimatePresence mode="popLayout">
                        {logs.map((log, i) => (
                            <motion.div
                                key={log}
                                initial={{ opacity: 0, x: -10 }}
                                animate={{ opacity: 1 - i * 0.3, x: 0 }}
                                exit={{ opacity: 0, x: 10 }}
                                className="flex items-center gap-2 text-sm text-muted-foreground"
                            >
                                {i === 0 ? (
                                    <Loader2 className="h-3 w-3 animate-spin text-primary" />
                                ) : (
                                    <CheckCircle2 className="h-3 w-3 text-green-500" />
                                )}
                                <span className={i === 0 ? "text-foreground font-medium" : ""}>{log}</span>
                            </motion.div>
                        ))}
                    </AnimatePresence>
                </div>
            </div>
        </motion.div>
    );
}

function StepIcon({ icon: Icon, label, active, completed }: { icon: any, label: string, active: boolean, completed: boolean }) {
    return (
        <div className="flex flex-col items-center gap-2">
            <div className={`
        p-3 rounded-full border transition-all duration-500
        ${completed ? 'bg-green-500/20 border-green-500 text-green-500' :
                    active ? 'bg-primary/20 border-primary text-primary shadow-[0_0_15px_rgba(var(--primary),0.3)]' :
                        'bg-muted border-transparent text-muted-foreground'}
      `}>
                {completed ? <CheckCircle2 className="h-5 w-5" /> : <Icon className="h-5 w-5" />}
            </div>
            <span className={`text-[10px] font-medium uppercase tracking-wider ${active ? 'text-primary' : 'text-muted-foreground'}`}>
                {label}
            </span>
        </div>
    );
}
