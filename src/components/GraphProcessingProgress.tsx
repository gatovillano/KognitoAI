'use client';

import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Loader2, CheckCircle, XCircle, Brain, Network, Database, FileText } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface GraphProcessingProgressProps {
    isVisible: boolean;
    status: 'idle' | 'processing' | 'completed' | 'error';
    progress?: number; // 0-100
    message?: string;
    mode?: 'hybrid' | 'conceptual';
    onClose?: () => void;
}

const processingSteps = {
    hybrid: [
        { icon: FileText, label: 'Analizando documentos', duration: 20 },
        { icon: Brain, label: 'Extrayendo entidades', duration: 30 },
        { icon: Network, label: 'Generando relaciones', duration: 30 },
        { icon: Database, label: 'Guardando en base de datos', duration: 20 }
    ],
    conceptual: [
        { icon: FileText, label: 'Procesando documentos', duration: 25 },
        { icon: Brain, label: 'Extrayendo citas conceptuales', duration: 35 },
        { icon: Network, label: 'Generando perfiles de ideas', duration: 25 },
        { icon: Database, label: 'Guardando conceptos', duration: 15 }
    ]
};

export const GraphProcessingProgress: React.FC<GraphProcessingProgressProps> = ({
    isVisible,
    status,
    progress = 0,
    message = '',
    mode = 'hybrid',
    onClose
}) => {
    if (!isVisible) return null;

    const steps = processingSteps[mode];
    const currentStepIndex = Math.floor((progress / 100) * steps.length);
    const currentStep = steps[Math.min(currentStepIndex, steps.length - 1)];

    const getStatusIcon = () => {
        switch (status) {
            case 'processing':
                return <Loader2 className="h-6 w-6 animate-spin text-primary" />;
            case 'completed':
                return <CheckCircle className="h-6 w-6 text-green-500" />;
            case 'error':
                return <XCircle className="h-6 w-6 text-red-500" />;
            default:
                return <Brain className="h-6 w-6 text-muted-foreground" />;
        }
    };

    const getStatusColor = () => {
        switch (status) {
            case 'processing':
                return 'text-primary';
            case 'completed':
                return 'text-green-600';
            case 'error':
                return 'text-red-600';
            default:
                return 'text-muted-foreground';
        }
    };

    return (
        <AnimatePresence>
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                className="fixed bottom-6 right-6 z-50 w-96"
            >
                <Card className="shadow-lg border-2">
                    <CardHeader className="pb-3">
                        <CardTitle className="flex items-center justify-between text-lg">
                            <div className="flex items-center gap-2">
                                {getStatusIcon()}
                                <span>Procesando Grafo</span>
                                <span className="text-sm font-normal text-muted-foreground">
                                    ({mode === 'hybrid' ? 'Híbrido' : 'Conceptual'})
                                </span>
                            </div>
                            {onClose && (
                                <button
                                    onClick={onClose}
                                    className="text-muted-foreground hover:text-foreground transition-colors"
                                >
                                    ✕
                                </button>
                            )}
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        {/* Barra de progreso */}
                        <div className="space-y-2">
                            <div className="flex justify-between text-sm">
                                <span className={getStatusColor()}>
                                    {status === 'processing' && currentStep?.label}
                                    {status === 'completed' && 'Completado'}
                                    {status === 'error' && 'Error'}
                                    {status === 'idle' && 'Iniciando...'}
                                </span>
                                <span className="text-muted-foreground">{progress}%</span>
                            </div>
                            <Progress value={progress} className="h-2" />
                        </div>

                        {/* Pasos del proceso */}
                        {status === 'processing' && (
                            <div className="space-y-2">
                                <h4 className="text-sm font-medium">Progreso detallado:</h4>
                                <div className="space-y-1">
                                    {steps.map((step, index) => {
                                        const isCompleted = index < currentStepIndex;
                                        const isCurrent = index === currentStepIndex;
                                        const StepIcon = step.icon;

                                        return (
                                            <div
                                                key={index}
                                                className={`flex items-center gap-2 text-sm ${isCompleted
                                                        ? 'text-green-600'
                                                        : isCurrent
                                                            ? 'text-primary font-medium'
                                                            : 'text-muted-foreground'
                                                    }`}
                                            >
                                                <StepIcon className={`h-4 w-4 ${isCurrent ? 'animate-pulse' : ''}`} />
                                                <span>{step.label}</span>
                                                {isCompleted && <CheckCircle className="h-3 w-3 ml-auto" />}
                                            </div>
                                        );
                                    })}
                                </div>
                            </div>
                        )}

                        {/* Mensaje adicional */}
                        {message && (
                            <div className="text-sm text-muted-foreground bg-muted/50 p-2 rounded">
                                {message}
                            </div>
                        )}

                        {/* Mensaje de finalización */}
                        {status === 'completed' && (
                            <div className="text-sm text-green-600 bg-green-50 dark:bg-green-950/20 p-2 rounded">
                                ✅ Grafo procesado exitosamente
                            </div>
                        )}

                        {/* Mensaje de error */}
                        {status === 'error' && (
                            <div className="text-sm text-red-600 bg-red-50 dark:bg-red-950/20 p-2 rounded">
                                ❌ Error durante el procesamiento
                            </div>
                        )}
                    </CardContent>
                </Card>
            </motion.div>
        </AnimatePresence>
    );
};