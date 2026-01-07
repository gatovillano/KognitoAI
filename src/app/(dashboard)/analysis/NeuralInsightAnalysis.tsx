import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Brain, Network, Sparkles, MessageSquare } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Analysis } from '@/lib/models';

interface NeuralInsightResult {
    summary: string;
    neural_data: any[];
    user_query: string;
    concepts: string[];
    analysis_metadata: {
        analysis_type: string;
        created_at: string;
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
        return <div>No hay datos disponibles para este insight.</div>;
    }

    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            {/* Header Section with User Query */}
            <div className="bg-gradient-to-r from-purple-500/10 to-blue-500/10 p-6 rounded-xl border border-purple-200/20">
                <div className="flex items-start gap-3">
                    <MessageSquare className="h-6 w-6 text-purple-500 mt-1" />
                    <div>
                        <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wider mb-1">Consulta Original</h3>
                        <p className="text-lg font-medium text-foreground italic">"{data.user_query}"</p>
                    </div>
                </div>
            </div>

            {/* Main Insight Content */}
            <Card className="border-none shadow-md bg-card/50">
                <CardHeader className="pb-2">
                    <div className="flex items-center gap-2">
                        <Sparkles className="h-5 w-5 text-yellow-500" />
                        <CardTitle className="text-xl">Insight Generado</CardTitle>
                    </div>
                </CardHeader>
                <CardContent>
                    <div className="prose prose-sm dark:prose-invert max-w-none">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {data.summary}
                        </ReactMarkdown>
                    </div>
                </CardContent>
            </Card>

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
                                    <Badge key={index} variant="secondary" className="px-3 py-1 text-sm bg-pink-500/10 text-pink-700 hover:bg-pink-500/20 border-pink-200">
                                        {concept}
                                    </Badge>
                                ))}
                            </div>
                        </CardContent>
                    </Card>
                )}

                {/* Neural Data / Connections (Simplified View) */}
                {data.neural_data && data.neural_data.length > 0 && (
                    <Card className="border-none shadow-sm h-full">
                        <CardHeader>
                            <div className="flex items-center gap-2">
                                <Network className="h-5 w-5 text-blue-500" />
                                <CardTitle className="text-lg">Conexiones Latentes</CardTitle>
                            </div>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-3 max-h-[300px] overflow-y-auto pr-2 custom-scrollbar">
                                {data.neural_data.map((item, index) => (
                                    <div key={index} className="p-3 rounded-lg bg-muted/50 text-sm border border-border/50">
                                        {/* Render based on what neural_data actually contains. 
                                            Assuming it might be a dictionary or string representation of a node/relationship */}
                                        <pre className="whitespace-pre-wrap font-mono text-xs text-muted-foreground">
                                            {typeof item === 'string' ? item : JSON.stringify(item, null, 2)}
                                        </pre>
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
