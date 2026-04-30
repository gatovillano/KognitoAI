// src/context/AuthContext.tsx
import React, { createContext, useState, useContext, useEffect } from 'react';
import * as SecureStore from 'expo-secure-store';
import api from '../api/config';
import { jwtDecode } from 'jwt-decode';

interface AuthContextData {
    signed: boolean;
    user: any | null;
    loading: boolean;
    isDarkMode: boolean;
    signIn(email: string, pass: string): Promise<void>;
    requestCode(identifier: string): Promise<void>;
    verifyCode(identifier: string, code: string): Promise<void>;
    signOut(): void;
    toggleTheme(): void;
}

const AuthContext = createContext<AuthContextData>({} as AuthContextData);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [user, setUser] = useState<any | null>(null);
    const [loading, setLoading] = useState(true);
    const [isDarkMode, setIsDarkMode] = useState(true);

    // Al iniciar la app, cargar el token y refrescarlo si está próximo a expirar
    useEffect(() => {
        async function loadStorageData() {
            try {
                const [storagedToken, storagedTheme] = await Promise.all([
                    SecureStore.getItemAsync('userToken'),
                    SecureStore.getItemAsync('theme')
                ]);

                if (storagedToken) {
                    try {
                        const payload: any = jwtDecode(storagedToken);
                        const expiresAt = payload.exp * 1000;
                        const hoursUntilExpiry = (expiresAt - Date.now()) / (1000 * 60 * 60);

                        if (hoursUntilExpiry <= 0) {
                            // Token ya expirado — limpiar y mostrar login
                            await SecureStore.deleteItemAsync('userToken');
                        } else if (hoursUntilExpiry < 24) {
                            // Token expira en menos de 24h — refrescar proactivamente
                            try {
                                const refreshResponse = await api.post('/auth/refresh-token');
                                const newToken = refreshResponse.data.access_token;
                                await SecureStore.setItemAsync('userToken', newToken);
                                const newPayload: any = jwtDecode(newToken);
                                setUser({ token: newToken, id: newPayload.sub });
                            } catch {
                                // Refresh falló pero el token aún es válido, usarlo
                                setUser({ token: storagedToken, id: payload.sub });
                            }
                        } else {
                            // Token válido con tiempo suficiente
                            setUser({ token: storagedToken, id: payload.sub });
                        }
                    } catch {
                        // No se pudo decodificar, intentar usar el token tal cual
                        setUser({ token: storagedToken });
                    }
                }

                if (storagedTheme) {
                    setIsDarkMode(storagedTheme === 'dark');
                }
            } catch (e) {
                console.error('Error loading storage data', e);
            } finally {
                setLoading(false);
            }
        }
        loadStorageData();
    }, []);

    // Refrescar el token cada hora para mantener la sesión indefinidamente activa
    useEffect(() => {
        if (!user) return;

        const refreshInterval = setInterval(async () => {
            try {
                const currentToken = await SecureStore.getItemAsync('userToken');
                if (!currentToken) {
                    // El interceptor eliminó el token → sesión terminada
                    setUser(null);
                    return;
                }

                const refreshResponse = await api.post('/auth/refresh-token');
                const newToken = refreshResponse.data.access_token;
                await SecureStore.setItemAsync('userToken', newToken);
                const newPayload: any = jwtDecode(newToken);
                setUser((prev: any) => ({ ...prev, token: newToken, id: newPayload.sub }));
            } catch {
                // Si el token ya no existe en SecureStore, cerrar sesión
                const tokenStillExists = await SecureStore.getItemAsync('userToken');
                if (!tokenStillExists) {
                    setUser(null);
                }
            }
        }, 60 * 60 * 1000); // cada hora

        return () => clearInterval(refreshInterval);
    }, [!!user]);

    const toggleTheme = async () => {
        const newMode = !isDarkMode;
        setIsDarkMode(newMode);
        await SecureStore.setItemAsync('theme', newMode ? 'dark' : 'light');
    };

    async function signIn(email: string, password: string) {
        const response = await api.post('/auth/login', { email, password });
        const { access_token } = response.data;
        const payload: any = jwtDecode(access_token);
        setUser({ token: access_token, id: payload.sub });
        await SecureStore.setItemAsync('userToken', access_token);
    }

    async function requestCode(identifier: string) {
        await api.post('/auth/request-code', { identifier });
    }

    async function verifyCode(identifier: string, code: string) {
        const response = await api.post('/auth/verify-code', { identifier, code });
        const { access_token } = response.data;
        const payload: any = jwtDecode(access_token);
        setUser({ token: access_token, id: payload.sub });
        await SecureStore.setItemAsync('userToken', access_token);
    }

    function signOut() {
        SecureStore.deleteItemAsync('userToken').then(() => {
            setUser(null);
        });
    }

    return (
        <AuthContext.Provider value={{
            signed: !!user,
            user,
            loading,
            isDarkMode,
            signIn,
            requestCode,
            verifyCode,
            signOut,
            toggleTheme
        }}>
            {children}
        </AuthContext.Provider>
    );
};

export function useAuth() {
    return useContext(AuthContext);
}
