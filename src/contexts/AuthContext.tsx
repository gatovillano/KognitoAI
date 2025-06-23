// En: src/contexts/AuthContext.tsx
'use client';

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import apiClient from '@/lib/api';

interface User {
  id: string;
  name: string | null;
  email: string | null;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  login: (token: string) => Promise<void>;
  logout: () => void;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const initializeAuth = async () => {
      const storedToken = localStorage.getItem('authToken');
      if (storedToken) {
        await login(storedToken);
      }
      setIsLoading(false);
    };
    initializeAuth();
  }, []);

  const login = async (newToken: string) => {
    localStorage.setItem('authToken', newToken);
    setToken(newToken);
    try {
      const response = await apiClient.get('/api/users/me', {
        headers: { Authorization: `Bearer ${newToken}` },
      });
      setUser(response.data);
    } catch (error) {
      console.error('Failed to fetch user', error);
      logout();
    }
  };

  const logout = () => {
    localStorage.removeItem('authToken');
    setToken(null);
    setUser(null);
    // Opcional: Redirigir a la página de login
    window.location.href = '/login';
  };

  const value = { user, token, login, logout, isLoading };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}