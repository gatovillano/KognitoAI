// En: src/lib/api.ts (Versión para API Externa)
import axios from 'axios';

const apiClient = axios.create({
  // Usar variable de entorno o fallback a desarrollo local
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8889',
  headers: {
    'Content-Type': 'application/json',
  },
  // Timeout aumentado para operaciones largas del LLM (15 minutos)
  timeout: 900000, // 15 minutos en milisegundos
});

// El interceptor para el token no cambia
apiClient.interceptors.request.use(
  (config) => {
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('authToken');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      // Log the full URL of the request to verify the base URL
      console.log('Request URL:', `${config.baseURL || ''}${config.url || ''}`);
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

export default apiClient;
