import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Brain, Network, Sparkles, MessageSquare, GitFork } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Analysis } from '@/lib/models';
import MermaidViewer from '@/components/MermaidViewer';

interface NeuralInsightResult {
    summary?: string;
    neural_data?: any[];
    neural_data_sample?: any[];
    user_query?: string;
    concepts?: string[];
    mermaid_diagram?: string;
    analysis_metadata?: {
        analysis_type?: string;
        created_at?: string;
        workspace_id?: string;
    };
}

interface NeuralInsightAnalysisProps {
    analysis: Analysis;
    play?: (text: string) => void;
    isLoading?: boolean;
    isPlaying?: boolean;
    activeText?: string;
}

const NeuralInsightAnalysis: React.FC<NeuralInsightAnalysisProps> = ({ analysis }) => {
    // Extract data from result_payload or full_data
    const data = (analysis.full_data || analysis.result_payload) as NeuralInsightResult;

    if (!data) {
        return <div className="p-6 text-muted-foreground">No hay datos disponibles para este insight.</div>;
    }

    const connections = data.neural_data_sample || data.neural_data || [];

    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            {/* Header Section with User Query */}
            {data.user_query && (
                <div className="bg-gradient-to-r from-purple-500/10 to-blue-500/10 p-6 rounded-xl border border-purple-200/20">
                    <div className="flex items-start gap-3">
                        <MessageSquare className="h-6 w-6 text-purple-500 mt-1 shrink-0" />
                        <div>
                            <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">Consulta Evaluada</h3>
                            <p className="text-base font-medium text-foreground italic">"{data.user_query}"</p>
                        </div>
                    </div>
                </div>
            )}

            {/* Main Insight Content */}
            {data.summary && (
                <Card className="border-none shadow-md bg-card/50">
                    <CardHeader className="pb-2">
                        <div className="flex items-center gap-2">
                            <Sparkles className="h-5 w-5 text-yellow-500" />
                            <CardTitle className="text-xl">Síntesis Neuronal</CardTitle>
                        </div>
                    </CardHeader>
                    <CardContent>
                        <div className="prose prose-sm dark:prose-invert max-w-none leading-relaxed">
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                {data.summary}
                            </ReactMarkdown>
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* Mermaid Graph Diagram Section */}
            {data.mermaid_diagram && (
                <Card className="border-none shadow-md bg-card/50 overflow-hidden">
                    <CardHeader className="pb-2">
                        <div className="flex items-center gap-2">
                            <GitFork className="h-5 w-5 text-purple-500" />
                            <CardTitle className="text-lg">Grafo de Relaciones Latentes (Mermaid)</CardTitle>
                        </div>
                    </CardHeader>
                    <CardContent>
                        <div className="p-4 rounded-xl bg-background/80 border border-border/40 overflow-x-auto min-h-[200px] flex justify-center items-center">
                            <MermaidViewer mermaidCode={data.mermaid_diagram} />
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* Concepts and Connections */}
            <div className="grid gap-6 md:grid-cols-2">
                {/* Concepts */}
                {data.concepts && data.concepts.length > 0 && (
                    <Card className="border-none shadow-sm h-full">
                        <CardHeader>
                            <div className="flex items-center gap-2">
                                <Brain className="h-5 w-5 text-pink-500" />
                                <CardTitle className="text-lg">Conceptos Clave</CardTitle>
                            </div>
                        </CardHeader>
                        <CardContent>
                            <div className="flex flex-wrap gap-2">
                                {data.concepts.map((concept, index) => (
                                    <Badge key={index} variant="secondary" className="px-3 py-1 text-sm bg-pink-500/10 text-pink-700 dark:text-pink-300 hover:bg-pink-500/20 border-pink-200/50">
                                        {concept}
                                    </Badge>
                                ))}
                            </div>
                        </CardContent>
                    </Card>
                )}

                {/* Neural Data / Connections (Simplified View) */}
                {connections.length > 0 && (
                    <Card className="border-none shadow-sm h-full">
                        <CardHeader>
                            <div className="flex items-center gap-2">
                                <Network className="h-5 w-5 text-blue-500" />
                                <CardTitle className="text-lg">Caminos Relacionales</CardTitle>
                            </div>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-3 max-h-[300px] overflow-y-auto pr-2 custom-scrollbar">
                                {connections.map((item, index) => (
                                    <div key={index} className="p-3 rounded-lg bg-muted/50 text-xs border border-border/50 font-mono">
                                        {typeof item === 'string' ? item : item.camino || JSON.stringify(item, null, 2)}
                                    </div>
                                ))}
                            </div>
                        </CardContent>
                    </Card>
                )}
            </div>
        </div>
    );
};

export default NeuralInsightAnalysis;
