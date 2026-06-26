import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { FileText, Layout, List, Zap } from 'lucide-react';

import { DocumentSummaryResult } from '@/lib/models';
import { SectionTTSButton } from './analysis-detail-dialog';

interface DocumentSummaryProps {
  summary: DocumentSummaryResult;
  docColors: any;
  play: (text: string) => void;
  isLoading: boolean;
  isPlaying: boolean;
  activeText: string | null;
  documentTitle?: string;
}

const normalizeStructureItem = (
  item: NonNullable<DocumentSummaryResult['document_structure']>[number]
) => {
  if (typeof item === 'string') {
    const [section, ...rest] = item.split(':');
    return {
      section: section?.trim() || 'Sección',
      summary: rest.join(':').trim() || item,
    };
  }

  return {
    section: item?.section || 'Sección',
    summary: item?.summary || '',
  };
};

const DocumentSummary: React.FC<DocumentSummaryProps> = ({
  summary,
  docColors,
  play,
  isLoading,
  isPlaying,
  activeText,
  documentTitle,
}) => {
  if (!summary) return null;

  const normalizedStructure = Array.isArray(summary.document_structure)
    ? summary.document_structure.map(normalizeStructureItem)
    : [];

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 mb-2">
        <FileText className={`w-6 h-6 ${docColors.icon}`} />
        <h3 className="text-2xl font-bold">{documentTitle || 'Resumen del Documento'}</h3>
      </div>

      <Tabs defaultValue="summary" className="w-full">
        <TabsList className="grid w-full grid-cols-4 mb-8">
          <TabsTrigger value="summary" className="gap-2">
            <FileText className="w-4 h-4" />
            <span className="hidden sm:inline">Resumen</span>
          </TabsTrigger>
          <TabsTrigger value="structure" className="gap-2">
            <Layout className="w-4 h-4" />
            <span className="hidden sm:inline">Estructura</span>
          </TabsTrigger>
          <TabsTrigger value="ideas" className="gap-2">
            <List className="w-4 h-4" />
            <span className="hidden sm:inline">Ideas</span>
          </TabsTrigger>
          <TabsTrigger value="synthesis" className="gap-2">
            <Zap className="w-4 h-4" />
            <span className="hidden sm:inline">Síntesis</span>
          </TabsTrigger>
        </TabsList>

        <TabsContent value="summary" className="space-y-4 animate-in fade-in-50 duration-500">
          {summary.executive_summary && (
            <Card className={`${docColors.cardBg} border-none shadow-md`}>
              <CardHeader className="pb-2 flex flex-row items-center justify-between">
                <CardTitle className={`text-lg font-bold ${docColors.cardTitle}`}>Resumen Ejecutivo</CardTitle>
                <SectionTTSButton
                  text={summary.executive_summary}
                  play={play}
                  isLoading={isLoading}
                  isPlaying={isPlaying}
                  activeText={activeText}
                />
              </CardHeader>
              <CardContent>
                <div className="prose prose-sm max-w-none dark:prose-invert text-muted-foreground leading-relaxed">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{summary.executive_summary}</ReactMarkdown>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="structure" className="space-y-6 animate-in fade-in-50 duration-500">
          {normalizedStructure.length > 0 ? (
            <div className="relative border-l-2 border-muted ml-3 pl-6 space-y-6">
              {normalizedStructure.map((section, index) => (
                <div key={index} className="relative">
                  <div className="absolute -left-[31px] top-1 w-4 h-4 rounded-full bg-indigo-500 border-4 border-background" />
                  <h5 className="font-bold text-foreground">{section.section}</h5>
                  <p className="text-sm text-muted-foreground mt-1">{section.summary}</p>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-12 text-muted-foreground">
              No se detectó una estructura resumida para este documento.
            </div>
          )}
        </TabsContent>

        <TabsContent value="ideas" className="space-y-4 animate-in fade-in-50 duration-500">
          {Array.isArray(summary.main_ideas) && summary.main_ideas.length > 0 ? (
            <div className="space-y-3">
              {summary.main_ideas.map((idea, index) => (
                <div key={index} className="p-4 rounded-xl bg-muted/30 border border-muted hover:bg-muted/50 transition-colors flex gap-3">
                  <div className="mt-0.5 flex-shrink-0 w-6 h-6 rounded-full bg-primary/10 text-primary flex items-center justify-center text-xs font-bold">
                    {index + 1}
                  </div>
                  <p className="text-sm leading-relaxed">{idea}</p>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-12 text-muted-foreground">
              No se extrajeron ideas principales para este resumen.
            </div>
          )}
        </TabsContent>

        <TabsContent value="synthesis" className="space-y-4 animate-in fade-in-50 duration-500">
          {summary.kai_synthesis ? (
            <div className="p-4 rounded-xl bg-gradient-to-br from-primary/10 to-secondary/10 border border-primary/20 relative group">
              <div className="absolute top-4 right-4 opacity-0 group-hover:opacity-100 transition-opacity">
                <SectionTTSButton
                  text={summary.kai_synthesis}
                  play={play}
                  isLoading={isLoading}
                  isPlaying={isPlaying}
                  activeText={activeText}
                />
              </div>
              <h4 className="text-sm font-bold uppercase tracking-wider text-primary mb-2 flex items-center gap-2">
                <Zap className="w-4 h-4" />
                Síntesis de KAI
              </h4>
              <p className="text-sm italic text-foreground/80 leading-relaxed">
                {summary.kai_synthesis}
              </p>
            </div>
          ) : (
            <div className="text-center py-12 text-muted-foreground">
              No se generó una síntesis estratégica para este resumen.
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default DocumentSummary;
