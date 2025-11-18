export interface ThemeQuote {
  document_title: string;
  quote: string;
}

export interface ThemeReference {
  theme: string;
  related_quotes: ThemeQuote[];
}

export interface CollectionConnection {
  document_titles: string[];
  insight: string;
}

export interface CollectionAnalysis {
  collection_summary: string;
  cross_cutting_themes: ThemeReference[];
  central_concepts: string[];
  concept_relationships: string[];
  identified_connections: CollectionConnection[];
  emergent_knowledge_gaps: string[];
  exploration_questions: string[];
  problematic_areas: string[];
  final_reflections: string[];
  collection_insights: string[];
  methodological_notes: string[];
  patrones_semanticos?: {
    total_documentos?: number;
    total_chunks_analizados?: number;
    temas_identificados?: number;
  };
}

export interface Insight {
  id: string;
  type: string;
  title?: string;
  description?: string;
  summary: string;
  severity?: string;
  priority?: string;
  status?: string;
  recommendations?: string[];
  created_at: string;
  related_items?: any[];
  action_suggestion?: string;
  questions?: (Question | string)[];
}

export interface Question {
  issue?: string;
  description?: string;
}

export interface AnalysisResponse {
  analysis: Analysis[];
  has_more?: boolean;
}

export interface AnalysisStats {
  type: string;
  total: number;
  completed: number;
  pending: number;
  failed: number;
  last_used: string | null;
}

export interface KeyTopic {
  topic: string;
  mentions: number;
  cluster_id?: number;
  description?: string;
  topics?: string[];
  quotes?: { document_title: string; quote: string; }[];
}

export interface DashboardInsightsResponse {
  total_analysis_tasks: number;
  analysis_stats_by_type: AnalysisStats[];
  total_proactive_insights: number;
  recent_proactive_insights: Insight[];
  key_topics: KeyTopic[];
  emergent_knowledge_gaps: string[];
  exploration_questions: string[];
}

export interface DocumentAnalysisResult {
  tool_used?: string;
  executive_summary?: string;
  general_analysis?: string;
  key_themes?: ThemeReference[];
  central_concepts?: string[];
  discipline?: string[];
  authorial_tone?: string;
  knowledge_gaps?: string[];
  exploration_questions?: string[];
  problematic_areas?: string[];
  final_reflections?: string[];
  sentiment_analysis?: {
    overall_sentiment: string;
    score: number;
  };
  key_entities?: Array<{
    entity: string;
    type: string;
    mentions: number;
  }>;
  document_structure?: Array<{
    section: string;
    summary: string;
  }>;
  key_topics?: string[];
  summary_sections?: string[];
  main_points?: string[];
  action_items?: string[];
  generated_questions?: string[];
  keywords?: string[];
  relevance_score?: number;
}

export interface CodeAnalysisResultFrontend {
  executive_summary?: string;
  code_structure?: Array<{
    component: string;
    description: string;
  }>;
  design_patterns?: Array<{
    pattern: string;
    description: string;
  }>;
  dependencies?: Array<{
    library: string;
    description: string;
  }>;
  potential_issues?: Array<{
    issue: string;
    description: string;
  }>;
  recommendations?: Array<{
    recommendation: string;
    rationale: string;
    application: string;
    implementation: string;
  }>;
}

export interface Analysis {
  id: string;
  type: AnalysisType;
  title: string;
  summary?: string;
  rawContent?: string;
  sources?: Array<{ id: string; link?: string; title?: string } | string>;
  insights?: Insight[];
  questions?: (Question | string)[];
  workflow_steps?: Array<{ title: string; description: string }>;
  confidence_score?: number;
  action_suggestion?: string;
  related_items?: Array<any>;
  tool_used?: string;
  created_at?: string;
  updated_at?: string;
  file_name?: string;
  topic?: string;
  author?: string;
  result?: DocumentAnalysisResult | CodeAnalysisResultFrontend | CollectionAnalysis | any;
  full_data?: any; // Añadido para que coincida con la implementación existente
}

export type AnalysisType =
  | 'insight'
  | 'workflow_suggestion'
  | 'document_summary'
  | 'announcement_draft'
  | 'strategic_objective'
  | 'market_trend'
  | 'experiment_proposal'
  | 'problem_statement'
  | 'goal_setting'
  | 'knowledge_retrieval'
  | 'agent_response_improvement'
  | 'verification'
  | 'information'
  | 'suggestion'
  | 'error'
  | 'warning'
  | 'question'
  | 'document'
  | 'collection'
  | 'code'
  | 'semantic'
  | 'semantic_summary'
  | 'code'
  | 'topic_analysis'
  | 'proactive_insight_manual';
