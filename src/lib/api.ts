// En: src/lib/api.ts (Versión para API Externa)
import axios from 'axios';

const apiClient = axios.create({
  // Next.js reemplazará esto con "https://apibase.gatoslibres.art"
  // gracias a la configuración en docker-compose.yml
  baseURL: process.env.NEXT_PUBLIC_API_URL, 
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
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

export default apiClient;
