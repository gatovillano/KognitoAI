"use client";
import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import apiClient from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';

interface UserSettings {
  // Campos de Módulos y Preferencias
  profiles_enabled: boolean;
  galleries_enabled: boolean;
  forms_enabled: boolean;
  theme: string;
  notifications_email: boolean;
  notifications_push: boolean;
  language: string;
  privacy_data_sharing: boolean;
  // Campos de LLM
  llm_provider: string;
  llm_model: string;
  llm_temperature: number;
  llm_api_base: string;
  fast_llm_model: string;
  vision_llm_model: string;
  use_prompt_tooling: boolean;
  // Campos de TTS
  tts_provider: string;
  tts_model: string;
  tts_voice: string;
  tts_speed: number;
  tts_region: string;
  // Campos de Embeddings
  embedding_provider: string;
  embedding_model: string;
  embedding_api_key_name: string;
  embedding_api_base: string;
  disabled_skills: string[];
  [key: string]: any; // Allow for other settings
}

interface UserSettingsContextType {
  settings: UserSettings | null;
  loading: boolean;
  error: string | null;
  updateSettings: (updates: Partial<UserSettings>) => Promise<void>;
  getSettings: () => void;
}

const UserSettingsContext = createContext<UserSettingsContextType | undefined>(undefined);

export const UserSettingsProvider = ({ children }: { children: ReactNode }) => {
  const { user, isAuthenticated } = useAuth();
  const [settings, setSettings] = useState<UserSettings | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const getSettings = async () => {
    if (!isAuthenticated || !user) {
      setSettings(null);
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.get<UserSettings>('/api/users/me/settings');
      setSettings(response.data);
    } catch (err) {
      console.error('Error fetching user settings:', err);
      setError('Failed to fetch user settings.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    getSettings();
  }, [isAuthenticated, user]);

  const updateSettings = async (updates: Partial<UserSettings>) => {
    if (!settings) return;

    const originalSettings = { ...settings };
    setSettings((prev: UserSettings | null) => prev ? { ...prev, ...updates } : null);

    try {
      await apiClient.put('/api/users/me/settings', updates);
    } catch (err) {
      console.error('Error updating settings:', err);
      setError('Failed to update settings.');
      setSettings(originalSettings);
      throw err;
    }
  };

  return (
    <UserSettingsContext.Provider value={{ settings, loading, error, updateSettings, getSettings }}>
      {children}
    </UserSettingsContext.Provider>
  );
};

export const useUserSettings = () => {
  const context = useContext(UserSettingsContext);
  if (context === undefined) {
    throw new Error('useUserSettings must be used within a UserSettingsProvider');
  }
  return context;
};