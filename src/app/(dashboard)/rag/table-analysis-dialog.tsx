'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { 
    Loader2, BarChart3, Brain, TrendingUp, Sparkles, 
    Calculator, Info, AlertCircle 
} from 'lucide-react';
import apiClient from '@/lib/api';
import { toast } from 'sonner';
import { MarkdownRenderer } from '@/components/MarkdownRenderer';
import { 
    ComposedChart, Scatter, Line, XAxis, YAxis, 
    CartesianGrid, Tooltip as ChartTooltip, ResponsiveContainer, Legend 
} from 'recharts';

// CSS colors for correlation heatmap cells
function getCorrelationColor(value: number) {
    const abs = Math.abs(value);
    // Standard sleek colors: positive correlations get a vibrant blue shade, negative get an orange/red shade
    if (value > 0) {
        return `rgba(59, 130, 246, ${abs * 0.8})`; // Blue
    } else if (value < 0) {
        return `rgba(249, 115, 22, ${abs * 0.8})`; // Orange
    }
    return 'transparent';
}

function getCorrelationTextColor(value: number) {
    return Math.abs(value) > 0.4 ? 'text-white' : 'text-foreground';
}

interface TableAnalysisDialogProps {
    isOpen: boolean;
    onOpenChange: (open: boolean) => void;
    tableId: string | null;
    tableName: string;
}

export function TableAnalysisDialog({ isOpen, onOpenChange, tableId, tableName }: TableAnalysisDialogProps) {
    const [stats, setStats] = useState<any>(null);
    const [isLoadingStats, setIsLoadingStats] = useState(false);
    
    // Prediccion / Regresion
    const [xCol, setXCol] = useState<string>('');
    const [yCol, setYCol] = useState<string>('');
    const [predictResult, setPredictResult] = useState<any>(null);
    const [isLoadingPredict, setIsLoadingPredict] = useState(false);
    
    // Filas para el grafico de dispersion
    const [rows, setRows] = useState<any[]>([]);
    const [isLoadingRows, setIsLoadingRows] = useState(false);

    // AI
    const [aiPrompt, setAiPrompt] = useState<string>('');
    const [aiAnalysis, setAiAnalysis] = useState<string>('');
    const [isLoadingAI, setIsLoadingAI] = useState(false);

    const [activeTab, setActiveTab] = useState('stats');

    // Fetch general statistics and correlation
    const fetchStats = useCallback(async () => {
        if (!tableId) return;
        setIsLoadingStats(true);
        try {
            const response = await apiClient.get(`/api/tables/${tableId}/analysis/stats`);
            setStats(response.data);
            
            // Auto-select first columns for regression if available
            if (response.data.numeric_columns && response.data.numeric_columns.length > 0) {
                setXCol(response.data.numeric_columns[0]);
                if (response.data.numeric_columns.length > 1) {
                    setYCol(response.data.numeric_columns[1]);
                } else {
                    setYCol(response.data.numeric_columns[0]);
                }
            }
        } catch (error) {
            console.error('Error fetching statistics:', error);
            toast.error('Error al calcular las estadísticas de la tabla.');
        } finally {
            setIsLoadingStats(false);
        }
    }, [tableId]);

    // Fetch row data for scatter plot
    const fetchRows = useCallback(async () => {
        if (!tableId) return;
        setIsLoadingRows(true);
        try {
            // Fetch up to 300 rows to keep UI responsive and render a nice scatter plot
            const response = await apiClient.get(`/api/tables/${tableId}/rows?limit=300`);
            setRows(response.data);
        } catch (error) {
            console.error('Error fetching rows:', error);
        } finally {
            setIsLoadingRows(false);
        }
    }, [tableId]);

    useEffect(() => {
        if (isOpen && tableId) {
            fetchStats();
            fetchRows();
            // Reset AI state
            setAiAnalysis('');
            setAiPrompt('');
            setPredictResult(null);
            setActiveTab('stats');
        }
    }, [isOpen, tableId, fetchStats, fetchRows]);

    // Run regression analysis
    const handleCalculateRegression = async () => {
        if (!tableId || !xCol || !yCol) {
            toast.error('Por favor selecciona ambas columnas.');
            return;
        }
        setIsLoadingPredict(true);
        try {
            const response = await apiClient.get(`/api/tables/${tableId}/analysis/predict`, {
                params: { x_col: xCol, y_col: yCol }
            });
            setPredictResult(response.data);
        } catch (error) {
            console.error('Error computing regression:', error);
            toast.error('Error al calcular la regresión lineal.');
        } finally {
            setIsLoadingPredict(false);
        }
    };

    // Run AI Insights analysis
    const handleRunAIAnalysis = async () => {
        if (!tableId) return;
        setIsLoadingAI(true);
        setAiAnalysis('');
        try {
            const response = await apiClient.post(`/api/tables/${tableId}/analysis/ai`, {
                prompt: aiPrompt || undefined
            });
            setAiAnalysis(response.data.analysis);
            toast.success('Análisis de IA generado correctamente.');
        } catch (error) {
            console.error('Error generating AI analysis:', error);
            toast.error('Error al generar el análisis con IA.');
        } finally {
            setIsLoadingAI(false);
        }
    };

    // Parse data points for Recharts Scatter plot & best-fit line
    const scatterChartData = useMemo(() => {
        if (!xCol || !yCol || rows.length === 0) return [];
        return rows.map((r: any) => {
            const xVal = Number(r.data[xCol]);
            const yVal = Number(r.data[yCol]);
            return { x: xVal, y: yVal };
        }).filter(d => !isNaN(d.x) && !isNaN(d.y));
    }, [rows, xCol, yCol]);

    const regressionLineData = useMemo(() => {
        if (scatterChartData.length === 0 || !predictResult || predictResult.slope === undefined) return [];
        const xValues = scatterChartData.map(d => d.x);
        const minX = Math.min(...xValues);
        const maxX = Math.max(...xValues);
        
        return [
            { x: minX, y: predictResult.slope * minX + predictResult.intercept },
            { x: maxX, y: predictResult.slope * maxX + predictResult.intercept }
        ];
    }, [scatterChartData, predictResult]);

    const isNumericDataAvailable = stats && stats.numeric_columns && stats.numeric_columns.length > 0;

    return (
        <Dialog open={isOpen} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-5xl max-h-[90vh] overflow-hidden flex flex-col p-6">
                <DialogHeader className="pb-2 border-b">
                    <div className="flex items-center gap-2">
                        <BarChart3 className="h-5 w-5 text-primary" />
                        <DialogTitle className="text-xl font-bold">Análisis de Datos: {tableName}</DialogTitle>
                    </div>
                    <DialogDescription>
                        Visualiza estadísticas descriptivas, calcula regresiones y genera insights con IA sobre tus datos.
                    </DialogDescription>
                </DialogHeader>

                <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col overflow-hidden mt-4">
                    <TabsList className="grid grid-cols-4 w-full max-w-md bg-muted/60 p-1 rounded-lg self-start mb-4">
                        <TabsTrigger value="stats" className="gap-2">
                            <BarChart3 className="h-4 w-4" />
                            Estadísticas
                        </TabsTrigger>
                        <TabsTrigger value="correlation" className="gap-2">
                            <Info className="h-4 w-4" />
                            Correlación
                        </TabsTrigger>
                        <TabsTrigger value="prediction" className="gap-2">
                            <TrendingUp className="h-4 w-4" />
                            Predicción
                        </TabsTrigger>
                        <TabsTrigger value="ai" className="gap-2">
                            <Sparkles className="h-4 w-4" />
                            Insights IA
                        </TabsTrigger>
                    </TabsList>

                    <div className="flex-1 overflow-y-auto pr-2 pb-4">
                        {isLoadingStats ? (
                            <div className="flex flex-col items-center justify-center py-20">
                                <Loader2 className="h-8 w-8 animate-spin text-primary mb-2" />
                                <p className="text-sm text-muted-foreground">Analizando datos y calculando estadísticas...</p>
                            </div>
                        ) : (
                            <>
                                {/* TAB 1: ESTADISTICAS */}
                                <TabsContent value="stats" className="space-y-4 outline-none">
                                    {!isNumericDataAvailable ? (
                                        <Card className="border-dashed flex flex-col items-center justify-center p-8 text-center bg-muted/20">
                                            <AlertCircle className="h-10 w-10 text-muted-foreground/60 mb-3" />
                                            <p className="font-medium text-muted-foreground">
                                                No se encontraron columnas numéricas en esta tabla para análisis estadístico.
                                            </p>
                                        </Card>
                                    ) : (
                                        <Card className="border-primary/10 overflow-hidden">
                                            <CardHeader className="bg-muted/30 pb-3">
                                                <CardTitle className="text-md font-semibold">Resumen Estadístico</CardTitle>
                                                <CardDescription>Métricas descriptivas básicas calculadas para cada columna numérica.</CardDescription>
                                            </CardHeader>
                                            <CardContent className="p-0 overflow-x-auto">
                                                <table className="w-full text-sm text-left border-collapse">
                                                    <thead>
                                                        <tr className="border-b bg-muted/20">
                                                            <th className="p-3 font-semibold text-muted-foreground">Columna</th>
                                                            <th className="p-3 font-semibold text-muted-foreground text-right">Recuento (N)</th>
                                                            <th className="p-3 font-semibold text-muted-foreground text-right">Promedio (Media)</th>
                                                            <th className="p-3 font-semibold text-muted-foreground text-right">Desv. Estándar</th>
                                                            <th className="p-3 font-semibold text-muted-foreground text-right">Mínimo</th>
                                                            <th className="p-3 font-semibold text-muted-foreground text-right">25%</th>
                                                            <th className="p-3 font-semibold text-muted-foreground text-right">Mediana (50%)</th>
                                                            <th className="p-3 font-semibold text-muted-foreground text-right">75%</th>
                                                            <th className="p-3 font-semibold text-muted-foreground text-right">Máximo</th>
                                                        </tr>
                                                    </thead>
                                                    <tbody className="divide-y">
                                                        {stats?.statistics && Object.keys(stats.statistics).map((colName) => {
                                                            const colStats = stats.statistics[colName];
                                                            return (
                                                                <tr key={colName} className="hover:bg-muted/10">
                                                                    <td className="p-3 font-medium border-r">{colName}</td>
                                                                    <td className="p-3 text-right">{colStats.count}</td>
                                                                    <td className="p-3 text-right">{colStats.mean !== undefined ? colStats.mean.toFixed(2) : '-'}</td>
                                                                    <td className="p-3 text-right">{colStats.std !== undefined ? colStats.std.toFixed(2) : '-'}</td>
                                                                    <td className="p-3 text-right">{colStats.min !== undefined ? colStats.min.toFixed(2) : '-'}</td>
                                                                    <td className="p-3 text-right">{colStats['25%'] !== undefined ? colStats['25%'].toFixed(2) : '-'}</td>
                                                                    <td className="p-3 text-right">{colStats['50%'] !== undefined ? colStats['50%'].toFixed(2) : '-'}</td>
                                                                    <td className="p-3 text-right">{colStats['75%'] !== undefined ? colStats['75%'].toFixed(2) : '-'}</td>
                                                                    <td className="p-3 text-right">{colStats.max !== undefined ? colStats.max.toFixed(2) : '-'}</td>
                                                                </tr>
                                                            );
                                                        })}
                                                    </tbody>
                                                </table>
                                            </CardContent>
                                        </Card>
                                    )}
                                </TabsContent>

                                {/* TAB 2: CORRELACION */}
                                <TabsContent value="correlation" className="space-y-4 outline-none">
                                    {!isNumericDataAvailable ? (
                                        <Card className="border-dashed flex flex-col items-center justify-center p-8 text-center bg-muted/20">
                                            <AlertCircle className="h-10 w-10 text-muted-foreground/60 mb-3" />
                                            <p className="font-medium text-muted-foreground">
                                                No hay columnas numéricas suficientes para una matriz de correlación.
                                            </p>
                                        </Card>
                                    ) : (
                                        <Card className="border-primary/10 overflow-hidden">
                                            <CardHeader className="bg-muted/30 pb-3">
                                                <CardTitle className="text-md font-semibold">Matriz de Correlación de Pearson</CardTitle>
                                                <CardDescription>
                                                    Mide la relación lineal entre variables. Valores cercanos a +1 indican una fuerte correlación positiva; cercanos a -1 indican fuerte negativa.
                                                </CardDescription>
                                            </CardHeader>
                                            <CardContent className="p-6 overflow-x-auto">
                                                {stats?.correlations && Object.keys(stats.correlations).length > 0 ? (
                                                    <div className="inline-block min-w-full align-middle">
                                                        <table className="min-w-full border border-collapse rounded-lg overflow-hidden font-sans">
                                                            <thead>
                                                                <tr className="bg-muted/20 border-b">
                                                                    <th className="p-3 text-left font-semibold text-muted-foreground border-r bg-muted/10">Variable</th>
                                                                    {Object.keys(stats.correlations).map(colName => (
                                                                        <th key={colName} className="p-3 text-center font-semibold text-muted-foreground border-r">{colName}</th>
                                                                    ))}
                                                                </tr>
                                                            </thead>
                                                            <tbody className="divide-y">
                                                                {Object.keys(stats.correlations).map(rowName => {
                                                                    const rowData = stats.correlations[rowName];
                                                                    return (
                                                                        <tr key={rowName} className="hover:bg-muted/5">
                                                                            <td className="p-3 font-medium text-left border-r bg-muted/5">{rowName}</td>
                                                                            {Object.keys(stats.correlations).map(colName => {
                                                                                const correlationValue = rowData[colName];
                                                                                const displayVal = correlationValue !== undefined ? correlationValue.toFixed(2) : '-';
                                                                                return (
                                                                                    <td 
                                                                                        key={colName} 
                                                                                        className="p-3 text-center border-r font-semibold transition-colors duration-150"
                                                                                        style={{ 
                                                                                            backgroundColor: correlationValue !== undefined ? getCorrelationColor(correlationValue) : 'transparent',
                                                                                        }}
                                                                                    >
                                                                                        <span className={getCorrelationTextColor(correlationValue)}>
                                                                                            {displayVal}
                                                                                        </span>
                                                                                    </td>
                                                                                );
                                                                            })}
                                                                        </tr>
                                                                    );
                                                                })}
                                                            </tbody>
                                                        </table>
                                                    </div>
                                                ) : (
                                                    <p className="text-sm text-muted-foreground text-center py-8">
                                                        Se necesita más de una columna numérica para construir la matriz de correlación.
                                                    </p>
                                                )}
                                            </CardContent>
                                        </Card>
                                    )}
                                </TabsContent>

                                {/* TAB 3: PREDICCION / REGRESION */}
                                <TabsContent value="prediction" className="space-y-4 outline-none">
                                    {!isNumericDataAvailable ? (
                                        <Card className="border-dashed flex flex-col items-center justify-center p-8 text-center bg-muted/20">
                                            <AlertCircle className="h-10 w-10 text-muted-foreground/60 mb-3" />
                                            <p className="font-medium text-muted-foreground">
                                                No hay variables numéricas para realizar análisis predictivo.
                                            </p>
                                        </Card>
                                    ) : (
                                        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                                            <Card className="border-primary/10 h-fit lg:col-span-1">
                                                <CardHeader className="bg-muted/30 pb-3">
                                                    <CardTitle className="text-md font-semibold">Configuración de Regresión</CardTitle>
                                                </CardHeader>
                                                <CardContent className="space-y-4 pt-4">
                                                    <div className="space-y-2">
                                                        <Label>Variable Independiente (X)</Label>
                                                        <Select value={xCol} onValueChange={setXCol}>
                                                            <SelectTrigger>
                                                                <SelectValue placeholder="Selecciona X..." />
                                                            </SelectTrigger>
                                                            <SelectContent>
                                                                {stats?.numeric_columns?.map((col: string) => (
                                                                    <SelectItem key={col} value={col}>{col}</SelectItem>
                                                                ))}
                                                            </SelectContent>
                                                        </Select>
                                                    </div>
                                                    
                                                    <div className="space-y-2">
                                                        <Label>Variable Dependiente (Y)</Label>
                                                        <Select value={yCol} onValueChange={setYCol}>
                                                            <SelectTrigger>
                                                                <SelectValue placeholder="Selecciona Y..." />
                                                            </SelectTrigger>
                                                            <SelectContent>
                                                                {stats?.numeric_columns?.map((col: string) => (
                                                                    <SelectItem key={col} value={col}>{col}</SelectItem>
                                                                ))}
                                                            </SelectContent>
                                                        </Select>
                                                    </div>

                                                    <Button 
                                                        onClick={handleCalculateRegression} 
                                                        className="w-full gap-2 mt-2" 
                                                        disabled={isLoadingPredict || !xCol || !yCol}
                                                    >
                                                        {isLoadingPredict ? (
                                                            <Loader2 className="h-4 w-4 animate-spin" />
                                                        ) : (
                                                            <Calculator className="h-4 w-4" />
                                                        )}
                                                        Calcular Relación
                                                    </Button>
                                                </CardContent>
                                            </Card>

                                            <div className="lg:col-span-2 space-y-6">
                                                {predictResult && predictResult.equation && (
                                                    <Card className="border-primary/10">
                                                        <CardHeader className="bg-muted/30 pb-3">
                                                            <CardTitle className="text-md font-semibold">Resultados del Modelo</CardTitle>
                                                        </CardHeader>
                                                        <CardContent className="p-4 grid grid-cols-2 gap-4">
                                                            <div className="space-y-1">
                                                                <span className="text-xs text-muted-foreground font-medium uppercase tracking-wider">Ecuación de la Recta</span>
                                                                <p className="text-lg font-mono font-bold text-primary">{predictResult.equation}</p>
                                                            </div>
                                                            <div className="space-y-1">
                                                                <span className="text-xs text-muted-foreground font-medium uppercase tracking-wider">Coeficiente R²</span>
                                                                <p className="text-lg font-mono font-bold">{predictResult.r_squared !== undefined ? predictResult.r_squared.toFixed(4) : '-'}</p>
                                                            </div>
                                                            <div className="space-y-1">
                                                                <span className="text-xs text-muted-foreground font-medium uppercase tracking-wider">Pendiente (Slope)</span>
                                                                <p className="text-base font-mono">{predictResult.slope !== undefined ? predictResult.slope.toFixed(4) : '-'}</p>
                                                            </div>
                                                            <div className="space-y-1">
                                                                <span className="text-xs text-muted-foreground font-medium uppercase tracking-wider">P-Valor</span>
                                                                <p className="text-base font-mono">{predictResult.p_value !== undefined ? predictResult.p_value.toExponential(4) : '-'}</p>
                                                            </div>
                                                        </CardContent>
                                                    </Card>
                                                )}

                                                <Card className="border-primary/10 p-4 min-h-[300px]">
                                                    {isLoadingRows ? (
                                                        <div className="flex flex-col items-center justify-center py-20 h-full">
                                                            <Loader2 className="h-6 w-6 animate-spin text-primary mb-2" />
                                                            <p className="text-xs text-muted-foreground">Cargando puntos de datos...</p>
                                                        </div>
                                                    ) : scatterChartData.length > 0 ? (
                                                        <div className="w-full h-[320px]">
                                                            <ResponsiveContainer width="100%" height="100%">
                                                                <ComposedChart margin={{ top: 20, right: 20, bottom: 20, left: 10 }}>
                                                                    <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                                                                    <XAxis 
                                                                        type="number" 
                                                                        dataKey="x" 
                                                                        name={xCol} 
                                                                        label={{ value: xCol, position: 'bottom', offset: -5 }} 
                                                                        stroke="currentColor" 
                                                                        className="text-xs fill-muted-foreground"
                                                                    />
                                                                    <YAxis 
                                                                        type="number" 
                                                                        dataKey="y" 
                                                                        name={yCol} 
                                                                        label={{ value: yCol, angle: -90, position: 'insideLeft', offset: 0 }}
                                                                        stroke="currentColor"
                                                                        className="text-xs fill-muted-foreground"
                                                                    />
                                                                    <ChartTooltip cursor={{ strokeDasharray: '3 3' }} />
                                                                    <Legend verticalAlign="top" height={36}/>
                                                                    <Scatter name="Registros" data={scatterChartData} fill="#3b82f6" opacity={0.7} />
                                                                    {predictResult && regressionLineData.length > 0 && (
                                                                        <Line 
                                                                            name="Ajuste Lineal" 
                                                                            data={regressionLineData} 
                                                                            type="monotone" 
                                                                            dataKey="y" 
                                                                            stroke="#10b981" 
                                                                            strokeWidth={2}
                                                                            dot={false} 
                                                                            activeDot={false} 
                                                                        />
                                                                    )}
                                                                </ComposedChart>
                                                            </ResponsiveContainer>
                                                        </div>
                                                    ) : (
                                                        <div className="flex flex-col items-center justify-center py-20 text-center text-muted-foreground">
                                                            <Info className="h-8 w-8 text-muted-foreground/40 mb-2" />
                                                            <p className="text-sm">Configura la regresión y presiona Calcular para visualizar el gráfico.</p>
                                                        </div>
                                                    )}
                                                </Card>
                                            </div>
                                        </div>
                                    )}
                                </TabsContent>

                                {/* TAB 4: INSIGHTS DE IA */}
                                <TabsContent value="ai" className="space-y-4 outline-none">
                                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                                        <Card className="border-primary/10 h-fit lg:col-span-1">
                                            <CardHeader className="bg-muted/30 pb-3">
                                                <CardTitle className="text-md font-semibold">Generar Insights con IA</CardTitle>
                                            </CardHeader>
                                            <CardContent className="space-y-4 pt-4">
                                                <div className="space-y-2">
                                                    <Label htmlFor="aiPrompt">Instrucciones u Objetivos</Label>
                                                    <Textarea
                                                        id="aiPrompt"
                                                        placeholder="Ej: ¿Cuáles son las tres principales conclusiones que se pueden extraer de esta tabla? ¿Hay patrones inusuales?"
                                                        value={aiPrompt}
                                                        onChange={(e) => setAiPrompt(e.target.value)}
                                                        rows={4}
                                                        className="text-sm"
                                                    />
                                                    <p className="text-xs text-muted-foreground">
                                                        Si lo dejas vacío, el asistente realizará un análisis general de las variables, estadísticas descriptivas y patrones.
                                                    </p>
                                                </div>

                                                <Button 
                                                    onClick={handleRunAIAnalysis} 
                                                    className="w-full gap-2" 
                                                    disabled={isLoadingAI}
                                                >
                                                    {isLoadingAI ? (
                                                        <Loader2 className="h-4 w-4 animate-spin" />
                                                    ) : (
                                                        <Sparkles className="h-4 w-4" />
                                                    )}
                                                    Generar Análisis IA
                                                </Button>
                                            </CardContent>
                                        </Card>

                                        <Card className="lg:col-span-2 border-primary/10 flex flex-col min-h-[400px] overflow-hidden">
                                            <CardHeader className="bg-muted/30 pb-3 border-b flex-shrink-0">
                                                <CardTitle className="text-md font-semibold">Reporte de IA</CardTitle>
                                            </CardHeader>
                                            <CardContent className="flex-1 p-6 overflow-y-auto max-h-[500px]">
                                                {isLoadingAI ? (
                                                    <div className="flex flex-col items-center justify-center py-20 h-full">
                                                        <Loader2 className="h-8 w-8 animate-spin text-primary mb-2" />
                                                        <p className="text-sm text-muted-foreground">El LLM está procesando la tabla y redactando los insights...</p>
                                                    </div>
                                                ) : aiAnalysis ? (
                                                    <div className="prose prose-sm dark:prose-invert max-w-none">
                                                        <MarkdownRenderer content={aiAnalysis} />
                                                    </div>
                                                ) : (
                                                    <div className="flex flex-col items-center justify-center py-20 h-full text-center text-muted-foreground">
                                                        <Sparkles className="h-10 w-10 text-muted-foreground/30 mb-3" />
                                                        <h4 className="font-semibold text-md mb-1">Tu Asistente de Datos</h4>
                                                        <p className="text-sm max-w-md">
                                                            Escribe una instrucción específica o presiona el botón para que la IA genere un análisis descriptivo del esquema y datos de esta tabla.
                                                        </p>
                                                    </div>
                                                )}
                                            </CardContent>
                                        </Card>
                                    </div>
                                </TabsContent>
                            </>
                        )}
                    </div>
                </Tabs>
            </DialogContent>
        </Dialog>
    );
}
