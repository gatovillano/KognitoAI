// En: src/lib/api.ts
import axios from 'axios';

// Creamos una instancia de Axios con la configuración base
const apiClient = axios.create({
  // process.env.NEXT_PUBLIC_API_URL es cómo Next.js lee la variable
  // de entorno que definimos en docker-compose.yml
  baseURL: process.env.NEXT_PUBLIC_API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor para añadir el token JWT a todas las peticiones
apiClient.interceptors.request.use(
  (config) => {
    // Obtenemos el token de localStorage (lo guardaremos al hacer login)
    const token = localStorage.getItem('authToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

export default apiClient;