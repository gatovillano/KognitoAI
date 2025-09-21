/**
 * Utilidades para realizar peticiones a la API
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://apibase.gatoslibres.art';

/**
 * Realiza una petición HTTP a la API
 * @param {string} endpoint - Endpoint de la API (ej: '/api/knowledge-graph/statistics')
 * @param {string} method - Método HTTP ('GET', 'POST', 'PUT', 'DELETE')
 * @param {Object} data - Datos a enviar en el body (para POST/PUT)
 * @param {Object} options - Opciones adicionales
 * @returns {Promise<Object>} Respuesta de la API
 */
export const apiRequest = async (endpoint, method = 'GET', data = null, options = {}) => {
  try {
    const config = {
      method,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    };

    // Agregar token de autenticación si está disponible
    const token = localStorage.getItem('authToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    // Agregar body para métodos que lo requieren
    if (data && ['POST', 'PUT', 'PATCH'].includes(method.toUpperCase())) {
      config.body = JSON.stringify(data);
    }

    const response = await fetch(`${API_BASE_URL}${endpoint}`, config);
    
    // Verificar si la respuesta es exitosa
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.message || `HTTP Error: ${response.status}`);
    }

    const result = await response.json();
    return result;

  } catch (error) {
    console.error('API Request Error:', error);
    throw error;
  }
};

/**
 * Métodos de conveniencia para diferentes tipos de peticiones
 */
export const api = {
  get: (endpoint, options = {}) => apiRequest(endpoint, 'GET', null, options),
  post: (endpoint, data, options = {}) => apiRequest(endpoint, 'POST', data, options),
  put: (endpoint, data, options = {}) => apiRequest(endpoint, 'PUT', data, options),
  delete: (endpoint, options = {}) => apiRequest(endpoint, 'DELETE', null, options),
};

/**
 * Endpoints específicos para el grafo de conocimiento
 */
export const knowledgeGraphAPI = {
  // Estadísticas
  getStatistics: () => api.get('/api/knowledge-graph/entity-statistics'),
  
  // Revisión de calidad
  reviewEntities: (workspaceId = null) => 
    api.post('/api/knowledge-graph/review-entities', { workspace_id: workspaceId }),
  
  // Aplicar correcciones
  applyCorrections: (corrections, autoApply = false) =>
    api.post('/api/knowledge-graph/apply-corrections', { 
      corrections, 
      auto_apply: autoApply 
    }),
  
  // Limpiar Neo4j
  clearNeo4j: () => api.post('/api/knowledge-graph/clear-neo4j', {}),
  
  // Chat enriquecido
  enhancedChat: (message, workspaceId = null, useKnowledgeGraph = true) =>
    api.post('/api/knowledge-graph/enhanced-chat', {
      message,
      workspace_id: workspaceId,
      use_knowledge_graph: useKnowledgeGraph
    }),
  
  // Procesar documentos
  processDocuments: (documents, datasetName) =>
    api.post('/api/knowledge-graph/process-documents', {
      documents,
      dataset_name: datasetName
    }),
  
  // Obtener grafo
  getGraph: (workspaceId = null, limit = 100) =>
    api.get(`/api/knowledge-graph/graph?workspace_id=${workspaceId || ''}&limit=${limit}`),
  
  // Buscar en el grafo
  searchGraph: (query, workspaceId = null) =>
    api.post('/api/knowledge-graph/search', {
      query,
      workspace_id: workspaceId
    }),
};

/**
 * Manejo de errores específicos de la API
 */
export const handleAPIError = (error) => {
  if (error.message.includes('401')) {
    // Token expirado o no válido
    localStorage.removeItem('authToken');
    window.location.href = '/login';
    return 'Sesión expirada. Por favor, inicia sesión nuevamente.';
  }
  
  if (error.message.includes('403')) {
    return 'No tienes permisos para realizar esta acción.';
  }
  
  if (error.message.includes('404')) {
    return 'Recurso no encontrado.';
  }
  
  if (error.message.includes('500')) {
    return 'Error interno del servidor. Por favor, intenta más tarde.';
  }
  
  return error.message || 'Error desconocido en la API.';
};

/**
 * Hook personalizado para manejar estados de carga y errores
 */
export const useAPICall = () => {
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState(null);

  const callAPI = async (apiFunction, ...args) => {
    setLoading(true);
    setError(null);
    
    try {
      const result = await apiFunction(...args);
      return result;
    } catch (err) {
      const errorMessage = handleAPIError(err);
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return { loading, error, callAPI, setError };
};

export default api;
