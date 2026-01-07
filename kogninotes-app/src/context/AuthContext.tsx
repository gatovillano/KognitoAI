// src/context/AuthContext.tsx
import React, { createContext, useState, useContext, useEffect } from 'react';
import * as SecureStore from 'expo-secure-store';
import api from '../api/config';

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

    useEffect(() => {
        async function loadStorageData() {
            try {
                const [storagedToken, storagedTheme] = await Promise.all([
                    SecureStore.getItemAsync('userToken'),
                    SecureStore.getItemAsync('theme')
                ]);

                if (storagedToken) {
                    setUser({ token: storagedToken });
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

    const toggleTheme = async () => {
        const newMode = !isDarkMode;
        setIsDarkMode(newMode);
        await SecureStore.setItemAsync('theme', newMode ? 'dark' : 'light');
    };

    async function signIn(email: string, password: string) {
        const response = await api.post('/auth/login', { email, password });
        const { access_token } = response.data;
        setUser({ token: access_token });
        await SecureStore.setItemAsync('userToken', access_token);
    }

    async function requestCode(identifier: string) {
        await api.post('/auth/request-code', { identifier });
    }

    async function verifyCode(identifier: string, code: string) {
        const response = await api.post('/auth/verify-code', { identifier, code });
        const { access_token } = response.data;
        setUser({ token: access_token });
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
