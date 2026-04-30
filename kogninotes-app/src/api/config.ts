// src/api/config.ts
import axios from 'axios';
import * as SecureStore from 'expo-secure-store';

// Cambia esta URL por la IP de tu servidor o dominio
export const API_URL = 'https://apibase.cuerpolibre.cl/api';

const api = axios.create({
    baseURL: API_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Interceptor para añadir el token a las peticiones
api.interceptors.request.use(async (config) => {
    const token = await SecureStore.getItemAsync('userToken');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

// Interceptor de respuesta: refresca el token automáticamente si expira (401)
let isRefreshing = false;
let refreshSubscribers: ((token: string) => void)[] = [];

const onTokenRefreshed = (newToken: string) => {
    refreshSubscribers.forEach((callback) => callback(newToken));
    refreshSubscribers = [];
};

const addRefreshSubscriber = (callback: (token: string) => void) => {
    refreshSubscribers.push(callback);
};

api.interceptors.response.use(
    (response) => response,
    async (error) => {
        const originalRequest = error.config;

        // Si el error es 401 y no es el propio endpoint de refresh (evitar bucle)
        if (
            error.response?.status === 401 &&
            !originalRequest._retry &&
            !originalRequest.url?.includes('/auth/refresh-token') &&
            !originalRequest.url?.includes('/auth/login') &&
            !originalRequest.url?.includes('/auth/verify-code')
        ) {
            originalRequest._retry = true;

            if (isRefreshing) {
                // Si ya hay un refresh en curso, esperar a que termine
                return new Promise((resolve) => {
                    addRefreshSubscriber((newToken: string) => {
                        originalRequest.headers.Authorization = `Bearer ${newToken}`;
                        resolve(api(originalRequest));
                    });
                });
            }

            isRefreshing = true;

            try {
                const currentToken = await SecureStore.getItemAsync('userToken');
                if (!currentToken) throw new Error('No hay token almacenado');

                // Llamar al endpoint de refresh con el token actual
                const refreshResponse = await axios.post(
                    `${API_URL}/auth/refresh-token`,
                    {},
                    { headers: { Authorization: `Bearer ${currentToken}` } }
                );

                const newToken = refreshResponse.data.access_token;
                await SecureStore.setItemAsync('userToken', newToken);

                isRefreshing = false;
                onTokenRefreshed(newToken);

                // Reintentar la petición original con el nuevo token
                originalRequest.headers.Authorization = `Bearer ${newToken}`;
                return api(originalRequest);
            } catch (refreshError) {
                // Si el refresh falla, limpiar token y forzar logout
                isRefreshing = false;
                refreshSubscribers = [];
                await SecureStore.deleteItemAsync('userToken');
                return Promise.reject(refreshError);
            }
        }

        return Promise.reject(error);
    }
);

export default api;
