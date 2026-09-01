// src/api/settingsService.ts
import api from './config';

export interface UserSettings {
  llm_provider?: string;
  llm_model?: string;
  llm_temperature?: number;
  llm_api_base?: string;
  fast_llm_model?: string;
  fast_llm_provider?: string;
  vision_llm_model?: string;
  vision_llm_provider?: string;
  use_prompt_tooling?: boolean;
}

export interface UserSecret {
  key_name: string;
  description?: string;
  masked_value: string;
  created_at?: string;
  updated_at?: string;
}

export interface LLMModelItem {
  id: string;
  name?: string;
  context_length?: number;
  pricing?: any;
}

export const settingsService = {
  async getUserSettings(): Promise<UserSettings> {
    const response = await api.get('/users/me/settings');
    return response.data;
  },

  async updateUserSettings(settings: Partial<UserSettings>): Promise<UserSettings> {
    const response = await api.put('/users/me/settings', settings);
    return response.data;
  },

  async getProviderModels(provider: string, apiBase?: string, refresh: boolean = false): Promise<LLMModelItem[]> {
    let url = `/llm/models/${provider}`;
    const params = new URLSearchParams();
    if (apiBase) params.append('api_base', apiBase);
    if (refresh) params.append('refresh', 'true');
    const queryString = params.toString();
    if (queryString) url += `?${queryString}`;

    const response = await api.get(url);
    return response.data || [];
  },

  async getUserSecrets(): Promise<UserSecret[]> {
    const response = await api.get('/users/me/secrets');
    return response.data || [];
  },

  async setUserSecret(keyName: string, value: string, description?: string): Promise<UserSecret> {
    const response = await api.post('/users/me/secrets', {
      key_name: keyName,
      value: value,
      description: description,
    });
    return response.data;
  },

  async deleteUserSecret(keyName: string): Promise<void> {
    await api.delete(`/users/me/secrets/${keyName}`);
  },
};
