# Android LLM Settings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a complete LLM and API Key configuration screen in the Android app (`kogninotes-app`) that allows users to change their LLM providers/models dynamically fetched from the backend API, set custom API bases, adjust temperature, and manage API secrets.

**Architecture:** A dedicated `settingsService.ts` module will encapsulate API interaction with backend `/api/users/me/settings`, `/api/llm/models/{provider}`, and `/api/users/me/secrets`. A new React Native screen `SettingsScreen.tsx` will present styled controls and modal pickers integrated into navigation and dropdown menus across the app.

**Tech Stack:** React Native, Expo, TypeScript, Axios, Lucide React Native icons, LinearGradient.

## Global Constraints
- Target workspace: `/home/gato/Proyectos/KognitoAI/kognito-ai/kogninotes-app`
- Do not break existing authentication interceptors or navigation.
- Follow existing color token patterns from `src/theme/colors.ts`.

---

### Task 1: Create Settings Service API (`kogninotes-app/src/api/settingsService.ts`)

**Files:**
- Create: `kogninotes-app/src/api/settingsService.ts`

**Interfaces:**
- Consumes: `api` from `src/api/config.ts`
- Produces: `settingsService.getUserSettings()`, `settingsService.updateUserSettings()`, `settingsService.getProviderModels()`, `settingsService.getUserSecrets()`, `settingsService.setUserSecret()`, `settingsService.deleteUserSecret()`

- [ ] **Step 1: Write `kogninotes-app/src/api/settingsService.ts`**

```typescript
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
```

- [ ] **Step 2: Commit**

```bash
git add kogninotes-app/src/api/settingsService.ts
git commit -m "feat(mobile): add settingsService API client"
```

---

### Task 2: Create `SettingsScreen.tsx` (`kogninotes-app/src/screens/SettingsScreen.tsx`)

**Files:**
- Create: `kogninotes-app/src/screens/SettingsScreen.tsx`

**Interfaces:**
- Consumes: `settingsService` from `src/api/settingsService.ts`, `useAuth` from `src/context/AuthContext.tsx`
- Produces: `SettingsScreen` React component for screen stack

- [ ] **Step 1: Write `SettingsScreen.tsx` implementation**

Build `SettingsScreen.tsx` supporting provider selection (Gemini, OpenAI, Anthropic, OpenRouter, Ollama, Ollama Cloud, OpenAI-compatible, Mistral, Kilocode, NVIDIA), dynamic API model loading with a Refresh button, fallback to default lists, API base URL, temperature slider, prompt tooling toggle, and API Key management (listing masked keys, adding, and deleting).

- [ ] **Step 2: Commit**

```bash
git add kogninotes-app/src/screens/SettingsScreen.tsx
git commit -m "feat(mobile): add SettingsScreen for LLM provider, models and API keys"
```

---

### Task 3: Integrate Navigation & Menu Access (`kogninotes-app/src/navigation/index.tsx`, `HomeScreen.tsx`, `ChatScreen.tsx`)

**Files:**
- Modify: `kogninotes-app/src/navigation/index.tsx`
- Modify: `kogninotes-app/src/screens/HomeScreen.tsx`
- Modify: `kogninotes-app/src/screens/ChatScreen.tsx`

- [ ] **Step 1: Add Settings to Stack Navigator in `src/navigation/index.tsx`**
- [ ] **Step 2: Add Configuración option to Dropdown Menu in `HomeScreen.tsx`**
- [ ] **Step 3: Add Configuración option to Dropdown Menu in `ChatScreen.tsx`**
- [ ] **Step 4: Commit**

```bash
git add kogninotes-app/src/navigation/index.tsx kogninotes-app/src/screens/HomeScreen.tsx kogninotes-app/src/screens/ChatScreen.tsx
git commit -m "feat(mobile): register Settings screen in navigation and dropdown menus"
```
