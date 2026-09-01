# Design Specification: Android LLM Settings Module

## Overview
This specification details the design for adding an LLM & API Configuration module to the Android React Native application (`kogninotes-app`). The module allows users to configure their preferred LLM provider, models (Main Reasoning, Fast Summarization, Vision), API base URL, temperature, prompt tooling, and manage API secret keys securely. Model lists are fetched dynamically from the backend API corresponding to each provider, matching the functionality of the web frontend.

---

## 1. Architecture & Data Flow

### Backend Endpoint Integration
The Android application will interface with the following pre-existing backend endpoints:
1. `GET /api/users/me/settings`: Retrieves the current user settings.
2. `PUT /api/users/me/settings`: Updates the current user settings.
3. `GET /api/llm/models/{provider}?api_base={api_base}&refresh={refresh}`: Fetches real-time model list from the provider API.
4. `GET /api/users/me/secrets`: Lists masked API keys stored for the user.
5. `POST /api/users/me/secrets`: Saves or updates an encrypted API key.
6. `DELETE /api/users/me/secrets/{key_name}`: Deletes an API key.

---

## 2. API Service (`kogninotes-app/src/api/settingsService.ts`)

A dedicated service file `settingsService.ts` will provide structured methods for configuration and API key operations:

```typescript
export interface UserSettings {
  llm_provider: string;
  llm_model: string;
  llm_temperature: number;
  llm_api_base: string;
  fast_llm_model: string;
  fast_llm_provider: string;
  vision_llm_model: string;
  vision_llm_provider: string;
  use_prompt_tooling: boolean;
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
```

---

## 3. UI Screen (`kogninotes-app/src/screens/SettingsScreen.tsx`)

### UI Components & Sections
1. **Header Bar**:
   - Navigation Back button (`<ChevronLeft />`).
   - Title: "Configuración de IA".
   - Theme toggle button (`<Sun />` / `<Moon />`).
   - Save button (`<Check />` or "Guardar").

2. **LLM Configuration Section**:
   - **Main LLM (Razonamiento)**:
     - Provider picker modal/dropdown.
     - Model picker modal displaying dynamically loaded models with model badges (Google, OpenAI, Anthropic, Free, etc.).
     - Refresh button (`<RefreshCw />`) to force reload models from the backend with `refresh=true`.
     - Option to enter custom model string.
   - **Fast LLM (Sumarización)**:
     - Provider picker & dynamic model selector.
   - **Vision LLM (Imágenes)**:
     - Provider picker & dynamic model selector.
   - **API Base URL**:
     - Input field with helper text for Android emulator (`http://10.0.2.2:11434` for Ollama).
   - **Creativity (Temperature)**:
     - Slider / Stepper (0.0 - 1.0).

3. **API Keys / Secrets Management**:
   - List of active saved keys (with masked display).
   - Form to add/update API keys for selected provider (`GOOGLE_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `OPENROUTER_API_KEY`, `OLLAMA_API_KEY`, `NVIDIA_API_KEY`, `MISTRAL_API_KEY`, `KILOCODE_API_KEY`).
   - Delete button for each key.

---

## 4. Navigation & App Integration

1. **Stack Navigation**:
   - Add `<Stack.Screen name="Settings" component={SettingsScreen} />` to `src/navigation/index.tsx`.

2. **App Dropdown Menus**:
   - Update `HomeScreen.tsx` and `ChatScreen.tsx` dropdown menus to include "Configuración" link leading to `Settings`.

---

## 5. Verification Plan

1. Verify static TypeScript typing and imports.
2. Ensure `SettingsScreen` compiles clean without syntax errors.
3. Test API model fetching flow, fallback mechanisms, and user feedback states.
