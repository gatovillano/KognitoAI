// src/api/config.ts
import axios from 'axios';
import * as SecureStore from 'expo-secure-store';

// Cambia esta URL por la IP de tu servidor o dominio
export const API_URL = 'https://apibase.gatoslibres.art/api';

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

export default api;
