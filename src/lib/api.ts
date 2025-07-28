// En: src/lib/api.ts (Versión para API Externa)
import axios from 'axios';

const apiClient = axios.create({
  // Usar variable de entorno o fallback a desarrollo local
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'https://apibase.gatoslibres.art', // Cambiado a HTTPS para depuración
  headers: {
    'Content-Type': 'application/json',
  },
  // Timeout aumentado para operaciones largas del LLM (15 minutos)
  timeout: 900000, // 15 minutos en milisegundos
});

// Interceptor para manejar tokens
apiClient.interceptors.request.use(
  (config) => {
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('authToken');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      // Log the full URL of the request to verify the base URL
      console.log('DEBUG (Frontend): Request URL:', `${config.baseURL || ''}${config.url || ''}`);
      console.log('DEBUG (Frontend): Current baseURL:', config.baseURL);
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Interceptor para manejar errores de autenticación
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && typeof window !== 'undefined') {
      // Token JWT inválido, limpiar localStorage
      console.warn('🔑 Token JWT inválido detectado, limpiando localStorage...');
      localStorage.removeItem('authToken');
      localStorage.removeItem('access_token');

      // Solo redirigir si no estamos ya en la página de login
      if (!window.location.pathname.includes('/login')) {
        console.warn('🔄 Redirigiendo al login...');
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export default apiClient;
