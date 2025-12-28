// src/types/graph.ts

export interface GraphNode {
  id: string;
  label: string;
  properties?: { // Hacer properties opcional
    name?: string;
    description?: string;
    category?: string;
    type?: string; // e.g., 'CONCEPTUAL_QUOTE'
    [key: string]: any; // Para otras propiedades dinámicas
  };
  type?: string; // Para el tipo de nodo (ej. CONCEPTUAL_QUOTE)
}

export interface GraphEdge {
  id: string;
  source: string; // ID del nodo de origen
  target: string; // ID del nodo de destino
  label: string;  // Etiqueta principal de la relación (e.g., r.type)
  properties?: { // Hacer properties opcional
    type?: string; // e.g., 'FUNDAMENTACION_TEORICA'
    description?: string;
    [key: string]: any; // Para otras propiedades dinámicas
  };
  type?: string; // Para el tipo de relación
}

export interface GraphVisualizationData {
  status: "success" | "error";
  message: string;
  dataset_name: string;
  focus_query?: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  summary?: string;
}

export interface GraphMetadata {
  nodeTypes: Array<{
    type: string;
    count: number;
    color?: string;
  }>;
  edgeTypes: Array<{
    type: string;
    count: number;
  }>;
  datasets?: Array<{
    name: string;
    nodeCount: number;
  }>;
}

export interface GraphFilters {
  nodeTypes: string[];
  edgeTypes: string[];
  excludedNodeTypes?: string[];
  excludedEdgeTypes?: string[];
  datasetName: string;
}

export interface FilteredGraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  metadata: GraphMetadata;
  appliedFilters: GraphFilters;
}