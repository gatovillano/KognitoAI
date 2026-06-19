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
  kai_synthesis?: string;
  general_analysis?: string;
  authorial_tone?: string;
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
  workspace_id?: string | null;
  workspace_name?: string | null;
  workspace_color?: string | null;
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
  citations?: { document_title: string; quote: string; }[];
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
  knowledge_gaps?: Array<{
    gap_title?: string;
    gap?: string;
    title?: string;
    explanation?: string;
    description?: string;
    related_context?: string;
    context?: string;
  }>;
  exploration_questions?: string[];
  problematic_areas?: string[];
  final_reflections?: string[];
  kai_synthesis?: string;
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

export interface DocumentSummaryResult {
  tool_used?: string;
  executive_summary?: string;
  document_structure?: Array<
    | string
    | {
        section?: string;
        summary?: string;
      }
  >;
  main_ideas?: string[];
  kai_synthesis?: string;
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
  security_analysis?: Array<{
    vulnerability: string;
    description: string;
    severity: string;
  }>;
  performance_analysis?: Array<{
    area: string;
    issue: string;
    suggestion: string;
  }>;
  refactoring_opportunities?: Array<{
    concept: string;
    description: string;
    benefit: string;
  }>;
  documentation_health?: Array<{
    item: string;
    status: string;
    recommendation: string;
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

export interface NoteAnalysisResult {
  executive_summary: string;
  general_analysis?: string;
  authorial_tone?: string;
  key_themes: string[];
  potential_implications: string[];
  action_suggestions: string[];
  related_concepts: string[];
  kai_insight: string;
}

export interface NoteCollectionAnalysisResult {
  collection_summary: string;
  cross_cutting_themes: Array<string | { theme: string; description: string }>;
  synthesized_insights: string[];
  strategic_recommendations: string[];
  knowledge_gaps: string[];
  kai_synthesis: string;
  general_analysis?: string;
  authorial_tone?: string;
}

export interface GroupedTopic {
  topic: string;
  mentions: number;
  cluster_id?: number;
  description?: string;
  topics?: string[];
  quotes?: Array<{ document_title: string; quote: string }>;
}

export interface DetailedCluster {
  cluster_id: number;
  representative_term: string;
  description: string;
  topics: string[];
  total_mentions: number;
  topic_count: number;
}

export interface ClusteringMetrics {
  optimal_k: number;
  silhouette_score: number;
  inertia: number;
  all_scores?: number[];
  all_inertias?: number[];
  method?: string;
  k_range_evaluated?: number[];
}

export interface SemanticAnalysisResult {
  grouped_topics: GroupedTopic[];
  detailed_clusters: DetailedCluster[];
  clustering_metrics?: ClusteringMetrics;
  tool_used?: string;
  analysis_metadata?: {
    tool_used?: string;
    analysis_type?: string;
    total_topics?: number;
    clusters_count?: number;
    max_terms_limit?: number;
    created_at?: string;
  };
}

export interface DeepResearchAnalysisResult {
  final_report: string;
  summary: string;
  findings: string;
  recommendations: string[];
  visual_schema?: string;
  sources: Array<{
    id: number;
    title: string;
    url: string;
    snippet: string;
    type: string;
  }>;
}

export interface ProactiveInsightResult {
  type: 'duplicidad' | 'sinergia' | 'evolucion' | 'contradiccion' | 'opportunity' | 'innovation' | 'synthesis' | 'follow_up' | 'deadline' | 'alert' | 'insight' | string;
  title?: string;
  insight_message: string;
  confidence_score: number;
  action_suggestion: string;
  innovation_potential?: string;
  related_items: any[];
  kai_synthesis?: string;
}

export type ComprehensiveWebAnalysisResult = string;
export type ScopedRagAnalysisResult = string;


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
  result?: DocumentAnalysisResult | DocumentSummaryResult | CodeAnalysisResultFrontend | CollectionAnalysis | NoteAnalysisResult | NoteCollectionAnalysisResult | SemanticAnalysisResult | DeepResearchAnalysisResult | ProactiveInsightResult | ComprehensiveWebAnalysisResult | ScopedRagAnalysisResult | any;
  full_data?: any; // Añadido para que coincida con la implementación existente
  status?: 'pending' | 'in_progress' | 'completed' | 'failed';
  error_message?: string;
  result_payload?: any;
  workspace_id?: string | null;
  workspace_name?: string | null;
  workspace_color?: string | null;
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
  | 'code_security'
  | 'code_performance'
  | 'code_refactoring'
  | 'code_documentation'
  | 'code_structure'
  | 'semantic'
  | 'semantic_summary'
  | 'topic_analysis'
  | 'proactive_insight_manual'
  | 'note_analysis'
  | 'note_collection_analysis'
  | 'knowledge_graph_analysis'
  | 'custom_analysis'
  | 'custom'
  | 'knowledge_graph'
  | 'repository_update'
  | 'gap_development'
  | 'comprehensive_web_analysis'
  | 'scoped_rag_analysis'
  | 'deep_research'
  | 'deep_research'
  | 'proactive_insight'
  | 'neural_insight';

export interface Note {
  id: number;
  title: string | null;
  content: string;
  category: string;
  created_at: string;
  is_starred?: boolean;
  team_shared?: boolean | string;
  team_id?: string;
  workspace_id?: string;
  workspace_name?: string;
  workspace_color?: string;
  workspace_role?: string;
}
