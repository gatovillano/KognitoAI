// En: src/lib/api.ts (Versión para API Externa)
import axios from 'axios';

const apiClient = axios.create({
  // Hardcoding the base URL to ensure it's used correctly
  baseURL: 'https://apibase.gatoslibres.art', 
  headers: {
    'Content-Type': 'application/json',
  },
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
