// src/screens/SettingsScreen.tsx
import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  TextInput,
  ActivityIndicator,
  Modal,
  Alert,
  Switch,
  Platform,
  StatusBar,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useAuth } from '../context/AuthContext';
import { colors, lightColors, spacing, borderRadius } from '../theme/colors';
import {
  settingsService,
  UserSettings,
  UserSecret,
  LLMModelItem,
} from '../api/settingsService';
import {
  ChevronLeft,
  Brain,
  Zap,
  Image as ImageIcon,
  RefreshCw,
  Globe,
  Key,
  Trash2,
  Check,
  Sun,
  Moon,
  ChevronDown,
  Sparkles,
  Sliders,
  ShieldCheck,
  Plus,
  X,
  Search,
} from 'lucide-react-native';
import { LinearGradient } from 'expo-linear-gradient';

export const LLM_PROVIDERS = [
  { id: 'gemini', name: 'Google AI Studio', envKey: 'GOOGLE_API_KEY' },
  { id: 'openai', name: 'OpenAI (GPT)', envKey: 'OPENAI_API_KEY' },
  { id: 'anthropic', name: 'Anthropic (Claude)', envKey: 'ANTHROPIC_API_KEY' },
  { id: 'openrouter', name: 'OpenRouter', envKey: 'OPENROUTER_API_KEY' },
  { id: 'ollama', name: 'Ollama (Local)', envKey: null },
  { id: 'ollama-cloud', name: '☁️ Ollama Cloud', envKey: 'OLLAMA_API_KEY' },
  { id: 'openai-compatible', name: '🖥️ Local AI / OpenAI Compatible', envKey: null },
  { id: 'mistral', name: 'Mistral AI', envKey: 'MISTRAL_API_KEY' },
  { id: 'kilocode', name: '🚀 Kilocode Gateway', envKey: 'KILOCODE_API_KEY' },
  { id: 'nvidia', name: '🟢 NVIDIA AI Catalog', envKey: 'NVIDIA_API_KEY' },
  { id: 'inceptionlabs', name: '🔮 Inception Labs', envKey: 'INCEPTIONLABS_API_KEY' },
];

export const DEFAULT_MODELS_BY_PROVIDER: Record<string, string[]> = {
  gemini: ['gemini/gemini-2.0-flash', 'gemini/gemini-1.5-flash', 'gemini/gemini-1.5-pro', 'gemini/gemini-2.0-flash-exp'],
  openai: ['openai/gpt-4o', 'openai/gpt-4o-mini', 'openai/gpt-4-turbo'],
  anthropic: ['anthropic/claude-3-5-sonnet-20240620', 'anthropic/claude-3-opus-20240229', 'anthropic/claude-3-haiku-20240307'],
  openrouter: [
    'openrouter/google/gemini-2.5-flash-preview',
    'openrouter/anthropic/claude-sonnet-4',
    'openrouter/openai/gpt-4.1-mini',
    'openrouter/google/gemini-2.5-pro-preview',
    'openrouter/mistralai/mistral-small-3.1-24b-instruct:free',
  ],
  ollama: ['ollama/llama3.1', 'ollama/mistral', 'ollama/phi3', 'ollama/gemma2'],
  'ollama-cloud': ['ollama_chat/llama3.1', 'ollama_chat/mistral', 'ollama_chat/phi3', 'ollama_chat/gemma2', 'ollama_chat/qwen2.5'],
  'openai-compatible': [],
  mistral: ['mistral/mistral-large-latest', 'mistral/mistral-small-latest'],
  kilocode: [],
  nvidia: [
    'nvidia/meta/llama-3.3-70b-instruct',
    'nvidia/nvidia/llama-3.1-nemotron-70b-instruct',
    'nvidia/mistralai/mistral-large-2-instruct',
    'nvidia/deepseek-ai/deepseek-r1',
    'nvidia/qwen/qwen2.5-72b-instruct',
  ],
  inceptionlabs: [],
};

type ModelType = 'main' | 'fast' | 'vision';

export const SettingsScreen = ({ navigation }: any) => {
  const { isDarkMode, toggleTheme } = useAuth();
  const theme = isDarkMode ? colors : lightColors;

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // Settings State
  const [llmProvider, setLlmProvider] = useState('gemini');
  const [llmModel, setLlmModel] = useState('gemini/gemini-2.0-flash');
  const [llmTemperature, setLlmTemperature] = useState(0.7);
  const [llmApiBase, setLlmApiBase] = useState('');

  const [fastLlmProvider, setFastLlmProvider] = useState('gemini');
  const [fastLlmModel, setFastLlmModel] = useState('gemini/gemini-2.0-flash');

  const [visionLlmProvider, setVisionLlmProvider] = useState('gemini');
  const [visionLlmModel, setVisionLlmModel] = useState('gemini/gemini-2.0-flash');

  const [usePromptTooling, setUsePromptTooling] = useState(false);

  // Models State
  const [mainModels, setMainModels] = useState<LLMModelItem[]>([]);
  const [fastModels, setFastModels] = useState<LLMModelItem[]>([]);
  const [visionModels, setVisionModels] = useState<LLMModelItem[]>([]);
  const [loadingModels, setLoadingModels] = useState<{ [key in ModelType]: boolean }>({
    main: false,
    fast: false,
    vision: false,
  });

  // Modal State
  const [activeModal, setActiveModal] = useState<{
    type: 'provider' | 'model';
    target: ModelType;
  } | null>(null);
  const [modalSearchTerm, setModalSearchTerm] = useState('');
  const [customModelText, setCustomModelText] = useState('');

  // Secrets State
  const [secrets, setSecrets] = useState<UserSecret[]>([]);
  const [selectedKeyProvider, setSelectedKeyProvider] = useState('gemini');
  const [newKeyValue, setNewKeyValue] = useState('');
  const [savingSecret, setSavingSecret] = useState(false);

  // Load Settings & Secrets
  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [userSettings, userSecrets] = await Promise.all([
        settingsService.getUserSettings(),
        settingsService.getUserSecrets(),
      ]);

      if (userSettings) {
        setLlmProvider(userSettings.llm_provider || 'gemini');
        setLlmModel(userSettings.llm_model || 'gemini/gemini-2.0-flash');
        setLlmTemperature(userSettings.llm_temperature ?? 0.7);
        setLlmApiBase(userSettings.llm_api_base || '');

        setFastLlmProvider(userSettings.fast_llm_provider || 'gemini');
        setFastLlmModel(userSettings.fast_llm_model || 'gemini/gemini-2.0-flash');

        setVisionLlmProvider(userSettings.vision_llm_provider || 'gemini');
        setVisionLlmModel(userSettings.vision_llm_model || 'gemini/gemini-2.0-flash');

        setUsePromptTooling(!!userSettings.use_prompt_tooling);
      }

      setSecrets(userSecrets || []);
    } catch (e) {
      console.error('Error loading settings:', e);
      Alert.alert('Error', 'No se pudieron cargar las configuraciones del usuario.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Fetch models for provider
  const fetchModels = async (
    provider: string,
    target: ModelType,
    apiBase?: string,
    refresh: boolean = false
  ) => {
    setLoadingModels((prev) => ({ ...prev, [target]: true }));
    try {
      const fetched = await settingsService.getProviderModels(provider, apiBase, refresh);
      if (target === 'main') setMainModels(fetched);
      else if (target === 'fast') setFastModels(fetched);
      else if (target === 'vision') setVisionModels(fetched);
    } catch (e) {
      console.error(`Error fetching ${target} models for ${provider}:`, e);
    } finally {
      setLoadingModels((prev) => ({ ...prev, [target]: false }));
    }
  };

  // Trigger model fetch on provider / apiBase change
  useEffect(() => {
    if (llmProvider) fetchModels(llmProvider, 'main', llmApiBase);
  }, [llmProvider, llmApiBase]);

  useEffect(() => {
    if (fastLlmProvider) fetchModels(fastLlmProvider, 'fast', llmApiBase);
  }, [fastLlmProvider, llmApiBase]);

  useEffect(() => {
    if (visionLlmProvider) fetchModels(visionLlmProvider, 'vision', llmApiBase);
  }, [visionLlmProvider, llmApiBase]);

  // Save All Settings
  const handleSaveSettings = async () => {
    setSaving(true);
    try {
      await settingsService.updateUserSettings({
        llm_provider: llmProvider,
        llm_model: llmModel,
        llm_temperature: llmTemperature,
        llm_api_base: llmApiBase,
        fast_llm_provider: fastLlmProvider,
        fast_llm_model: fastLlmModel,
        vision_llm_provider: visionLlmProvider,
        vision_llm_model: visionLlmModel,
        use_prompt_tooling: usePromptTooling,
      });
      Alert.alert('¡Éxito!', 'Configuración de LLM guardada correctamente.');
    } catch (e) {
      console.error('Error saving settings:', e);
      Alert.alert('Error', 'Ocurrió un error al guardar la configuración.');
    } finally {
      setSaving(false);
    }
  };

  // Save Secret (API Key)
  const handleSaveSecret = async () => {
    if (!newKeyValue.trim()) {
      Alert.alert('Atención', 'Por favor ingresa un valor para la API Key.');
      return;
    }

    const providerObj = LLM_PROVIDERS.find((p) => p.id === selectedKeyProvider);
    if (!providerObj || !providerObj.envKey) {
      Alert.alert('Error', 'Este proveedor no requiere una API Key de entorno.');
      return;
    }

    setSavingSecret(true);
    try {
      await settingsService.setUserSecret(
        providerObj.envKey,
        newKeyValue.trim(),
        `API Key para ${providerObj.name}`
      );
      Alert.alert('¡Guardado!', `API Key de ${providerObj.name} guardada exitosamente.`);
      setNewKeyValue('');
      const updatedSecrets = await settingsService.getUserSecrets();
      setSecrets(updatedSecrets);
    } catch (e) {
      console.error('Error saving secret:', e);
      Alert.alert('Error', 'No se pudo guardar la API Key.');
    } finally {
      setSavingSecret(false);
    }
  };

  // Delete Secret
  const handleDeleteSecret = (keyName: string) => {
    Alert.alert('Eliminar API Key', `¿Estás seguro de eliminar la clave ${keyName}?`, [
      { text: 'Cancelar', style: 'cancel' },
      {
        text: 'Eliminar',
        style: 'destructive',
        onPress: async () => {
          try {
            await settingsService.deleteUserSecret(keyName);
            const updatedSecrets = await settingsService.getUserSecrets();
            setSecrets(updatedSecrets);
          } catch (e) {
            console.error('Error deleting secret:', e);
            Alert.alert('Error', 'No se pudo eliminar la API Key.');
          }
        },
      },
    ]);
  };

  // Get current models list for a target
  const getModelsForTarget = (target: ModelType) => {
    let apiModels: LLMModelItem[] = [];
    let currentProvider = llmProvider;
    if (target === 'main') {
      apiModels = mainModels;
      currentProvider = llmProvider;
    } else if (target === 'fast') {
      apiModels = fastModels;
      currentProvider = fastLlmProvider;
    } else {
      apiModels = visionModels;
      currentProvider = visionLlmProvider;
    }

    let items: { id: string; name: string; isApi?: boolean }[] = [];

    if (apiModels.length > 0) {
      items = apiModels.map((m) => ({
        id: typeof m === 'string' ? m : m.id,
        name: typeof m === 'string' ? m : m.name || m.id,
        isApi: true,
      }));
    } else {
      const defaults = DEFAULT_MODELS_BY_PROVIDER[currentProvider] || [];
      items = defaults.map((d) => ({ id: d, name: d, isApi: false }));
    }

    if (modalSearchTerm.trim()) {
      const term = modalSearchTerm.toLowerCase();
      items = items.filter(
        (i) => i.id.toLowerCase().includes(term) || i.name.toLowerCase().includes(term)
      );
    }

    return items;
  };

  // Select Model
  const selectModel = (modelId: string, target: ModelType) => {
    if (target === 'main') setLlmModel(modelId);
    else if (target === 'fast') setFastLlmModel(modelId);
    else setVisionLlmModel(modelId);
    setActiveModal(null);
    setModalSearchTerm('');
  };

  // Select Provider
  const selectProvider = (providerId: string, target: ModelType) => {
    if (target === 'main') {
      setLlmProvider(providerId);
      setLlmModel('');
    } else if (target === 'fast') {
      setFastLlmProvider(providerId);
      setFastLlmModel('');
    } else {
      setVisionLlmProvider(providerId);
      setVisionLlmModel('');
    }
    setActiveModal(null);
  };

  const getProviderName = (id: string) => {
    return LLM_PROVIDERS.find((p) => p.id === id)?.name || id;
  };

  if (loading) {
    return (
      <View style={[styles.centered, { backgroundColor: theme.background }]}>
        <ActivityIndicator size="large" color={theme.primary} />
        <Text style={[styles.loadingText, { color: theme.textMuted }]}>Cargando configuración...</Text>
      </View>
    );
  }

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: theme.background }]}>
      <StatusBar barStyle={isDarkMode ? 'light-content' : 'dark-content'} />

      {/* Header */}
      <View style={[styles.header, { borderBottomColor: theme.border + '40' }]}>
        <TouchableOpacity onPress={() => navigation.goBack()} style={styles.headerBtn}>
          <ChevronLeft color={theme.text} size={24} />
        </TouchableOpacity>
        <Text style={[styles.headerTitle, { color: theme.text }]}>Configuración de IA</Text>
        <View style={styles.headerActions}>
          <TouchableOpacity onPress={toggleTheme} style={styles.headerBtn}>
            {isDarkMode ? <Sun size={20} color={theme.text} /> : <Moon size={20} color={theme.text} />}
          </TouchableOpacity>
          <TouchableOpacity
            onPress={handleSaveSettings}
            disabled={saving}
            style={[styles.saveBtn, { backgroundColor: theme.primary }]}
          >
            {saving ? (
              <ActivityIndicator size="small" color="#fff" />
            ) : (
              <Check size={18} color="#fff" />
            )}
          </TouchableOpacity>
        </View>
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
        {/* Card: Main Model */}
        <View style={[styles.card, { backgroundColor: theme.surface, borderColor: theme.border }]}>
          <View style={styles.cardHeader}>
            <View style={[styles.iconBadge, { backgroundColor: theme.primary + '15' }]}>
              <Brain size={18} color={theme.primary} />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={[styles.cardTitle, { color: theme.text }]}>Modelo Principal (Razonamiento)</Text>
              <Text style={[styles.cardSub, { color: theme.textMuted }]}>Motor para chat y tareas complejas</Text>
            </View>
          </View>

          <View style={styles.fieldGroup}>
            <Text style={[styles.fieldLabel, { color: theme.textMuted }]}>PROVEEDOR</Text>
            <TouchableOpacity
              style={[styles.selectTrigger, { backgroundColor: theme.background, borderColor: theme.border }]}
              onPress={() => setActiveModal({ type: 'provider', target: 'main' })}
            >
              <Text style={[styles.selectValue, { color: theme.text }]}>{getProviderName(llmProvider)}</Text>
              <ChevronDown size={18} color={theme.textMuted} />
            </TouchableOpacity>
          </View>

          <View style={styles.fieldGroup}>
            <View style={styles.labelRow}>
              <Text style={[styles.fieldLabel, { color: theme.textMuted }]}>MODELO</Text>
              <TouchableOpacity
                onPress={() => fetchModels(llmProvider, 'main', llmApiBase, true)}
                style={styles.refreshBtnInline}
              >
                <RefreshCw
                  size={14}
                  color={theme.primary}
                  style={loadingModels.main ? { transform: [{ rotate: '45deg' }] } : {}}
                />
                <Text style={[styles.refreshText, { color: theme.primary }]}>Refrescar API</Text>
              </TouchableOpacity>
            </View>

            <TouchableOpacity
              style={[styles.selectTrigger, { backgroundColor: theme.background, borderColor: theme.border }]}
              onPress={() => setActiveModal({ type: 'model', target: 'main' })}
            >
              <Text style={[styles.selectValue, { color: llmModel ? theme.text : theme.textMuted }]} numberOfLines={1}>
                {llmModel || 'Seleccionar modelo...'}
              </Text>
              <ChevronDown size={18} color={theme.textMuted} />
            </TouchableOpacity>
          </View>
        </View>

        {/* Card: Fast Model */}
        <View style={[styles.card, { backgroundColor: theme.surface, borderColor: theme.border }]}>
          <View style={styles.cardHeader}>
            <View style={[styles.iconBadge, { backgroundColor: '#f9731615' }]}>
              <Zap size={18} color="#f97316" />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={[styles.cardTitle, { color: theme.text }]}>Modelo Rápido (Sumarización)</Text>
              <Text style={[styles.cardSub, { color: theme.textMuted }]}>Para tareas ligeras y resúmenes</Text>
            </View>
          </View>

          <View style={styles.fieldGroup}>
            <Text style={[styles.fieldLabel, { color: theme.textMuted }]}>PROVEEDOR</Text>
            <TouchableOpacity
              style={[styles.selectTrigger, { backgroundColor: theme.background, borderColor: theme.border }]}
              onPress={() => setActiveModal({ type: 'provider', target: 'fast' })}
            >
              <Text style={[styles.selectValue, { color: theme.text }]}>{getProviderName(fastLlmProvider)}</Text>
              <ChevronDown size={18} color={theme.textMuted} />
            </TouchableOpacity>
          </View>

          <View style={styles.fieldGroup}>
            <View style={styles.labelRow}>
              <Text style={[styles.fieldLabel, { color: theme.textMuted }]}>MODELO</Text>
              <TouchableOpacity
                onPress={() => fetchModels(fastLlmProvider, 'fast', llmApiBase, true)}
                style={styles.refreshBtnInline}
              >
                <RefreshCw size={14} color={theme.primary} />
                <Text style={[styles.refreshText, { color: theme.primary }]}>Refrescar API</Text>
              </TouchableOpacity>
            </View>

            <TouchableOpacity
              style={[styles.selectTrigger, { backgroundColor: theme.background, borderColor: theme.border }]}
              onPress={() => setActiveModal({ type: 'model', target: 'fast' })}
            >
              <Text style={[styles.selectValue, { color: fastLlmModel ? theme.text : theme.textMuted }]} numberOfLines={1}>
                {fastLlmModel || 'Seleccionar modelo...'}
              </Text>
              <ChevronDown size={18} color={theme.textMuted} />
            </TouchableOpacity>
          </View>
        </View>

        {/* Card: Vision Model */}
        <View style={[styles.card, { backgroundColor: theme.surface, borderColor: theme.border }]}>
          <View style={styles.cardHeader}>
            <View style={[styles.iconBadge, { backgroundColor: '#3b82f615' }]}>
              <ImageIcon size={18} color="#3b82f6" />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={[styles.cardTitle, { color: theme.text }]}>Modelo de Visión (Imágenes)</Text>
              <Text style={[styles.cardSub, { color: theme.textMuted }]}>Para procesamiento OCR y análisis visual</Text>
            </View>
          </View>

          <View style={styles.fieldGroup}>
            <Text style={[styles.fieldLabel, { color: theme.textMuted }]}>PROVEEDOR</Text>
            <TouchableOpacity
              style={[styles.selectTrigger, { backgroundColor: theme.background, borderColor: theme.border }]}
              onPress={() => setActiveModal({ type: 'provider', target: 'vision' })}
            >
              <Text style={[styles.selectValue, { color: theme.text }]}>{getProviderName(visionLlmProvider)}</Text>
              <ChevronDown size={18} color={theme.textMuted} />
            </TouchableOpacity>
          </View>

          <View style={styles.fieldGroup}>
            <View style={styles.labelRow}>
              <Text style={[styles.fieldLabel, { color: theme.textMuted }]}>MODELO</Text>
              <TouchableOpacity
                onPress={() => fetchModels(visionLlmProvider, 'vision', llmApiBase, true)}
                style={styles.refreshBtnInline}
              >
                <RefreshCw size={14} color={theme.primary} />
                <Text style={[styles.refreshText, { color: theme.primary }]}>Refrescar API</Text>
              </TouchableOpacity>
            </View>

            <TouchableOpacity
              style={[styles.selectTrigger, { backgroundColor: theme.background, borderColor: theme.border }]}
              onPress={() => setActiveModal({ type: 'model', target: 'vision' })}
            >
              <Text style={[styles.selectValue, { color: visionLlmModel ? theme.text : theme.textMuted }]} numberOfLines={1}>
                {visionLlmModel || 'Seleccionar modelo...'}
              </Text>
              <ChevronDown size={18} color={theme.textMuted} />
            </TouchableOpacity>
          </View>
        </View>

        {/* Card: Parameters */}
        <View style={[styles.card, { backgroundColor: theme.surface, borderColor: theme.border }]}>
          <View style={styles.cardHeader}>
            <View style={[styles.iconBadge, { backgroundColor: theme.primary + '15' }]}>
              <Sliders size={18} color={theme.primary} />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={[styles.cardTitle, { color: theme.text }]}>Parámetros Avanzados</Text>
              <Text style={[styles.cardSub, { color: theme.textMuted }]}>Ajustes de endpoint y temperatura</Text>
            </View>
          </View>

          <View style={styles.fieldGroup}>
            <Text style={[styles.fieldLabel, { color: theme.textMuted }]}>API BASE URL (OPCIONAL)</Text>
            <TextInput
              style={[styles.textInput, { backgroundColor: theme.background, borderColor: theme.border, color: theme.text }]}
              placeholder={
                llmProvider === 'ollama'
                  ? 'http://10.0.2.2:11434 (Emulador Android)'
                  : 'https://api.openai.com/v1'
              }
              placeholderTextColor={theme.textMuted + '80'}
              value={llmApiBase}
              onChangeText={setLlmApiBase}
              autoCapitalize="none"
              autoCorrect={false}
            />
            <Text style={[styles.helperText, { color: theme.textMuted }]}>
              Tip: En emuladores Android usa <Text style={{ fontWeight: 'bold' }}>http://10.0.2.2:11434</Text> para acceder a Ollama en tu máquina local.
            </Text>
          </View>

          <View style={styles.fieldGroup}>
            <View style={styles.labelRow}>
              <Text style={[styles.fieldLabel, { color: theme.textMuted }]}>CREATIVIDAD (TEMPERATURA)</Text>
              <Text style={[styles.tempValue, { color: theme.primary }]}>{llmTemperature.toFixed(1)}</Text>
            </View>
            <View style={styles.stepperContainer}>
              <TouchableOpacity
                style={[styles.stepperBtn, { backgroundColor: theme.background, borderColor: theme.border }]}
                onPress={() => setLlmTemperature((t) => Math.max(0, parseFloat((t - 0.1).toFixed(1))))}
              >
                <Text style={[styles.stepperText, { color: theme.text }]}>-</Text>
              </TouchableOpacity>
              <View style={styles.stepperBar}>
                <View
                  style={[
                    styles.stepperFill,
                    { backgroundColor: theme.primary, width: `${llmTemperature * 100}%` },
                  ]}
                />
              </View>
              <TouchableOpacity
                style={[styles.stepperBtn, { backgroundColor: theme.background, borderColor: theme.border }]}
                onPress={() => setLlmTemperature((t) => Math.min(1, parseFloat((t + 0.1).toFixed(1))))}
              >
                <Text style={[styles.stepperText, { color: theme.text }]}>+</Text>
              </TouchableOpacity>
            </View>
          </View>

          <View style={[styles.switchRow, { borderTopColor: theme.border + '40' }]}>
            <View style={{ flex: 1, marginRight: 10 }}>
              <Text style={[styles.switchLabel, { color: theme.text }]}>Tooling por Prompt (Experimental)</Text>
              <Text style={[styles.switchSub, { color: theme.textMuted }]}>
                Forzar el formateo de herramientas en el prompt
              </Text>
            </View>
            <Switch
              value={usePromptTooling}
              onValueChange={setUsePromptTooling}
              trackColor={{ false: theme.border, true: theme.primary + '80' }}
              thumbColor={usePromptTooling ? theme.primary : '#f4f3f4'}
            />
          </View>
        </View>

        {/* Card: Secrets (API Keys) */}
        <View style={[styles.card, { backgroundColor: theme.surface, borderColor: theme.border }]}>
          <View style={styles.cardHeader}>
            <View style={[styles.iconBadge, { backgroundColor: '#10b98115' }]}>
              <Key size={18} color="#10b981" />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={[styles.cardTitle, { color: theme.text }]}>Llaves de API (Secretos)</Text>
              <Text style={[styles.cardSub, { color: theme.textMuted }]}>Gestión cifrada de credenciales</Text>
            </View>
          </View>

          {/* Form to Add Key */}
          <View style={[styles.secretForm, { backgroundColor: theme.background, borderColor: theme.border }]}>
            <Text style={[styles.fieldLabel, { color: theme.textMuted, marginBottom: 8 }]}>GUARDAR / ACTUALIZAR CLAVE</Text>

            <TouchableOpacity
              style={[styles.selectTrigger, { backgroundColor: theme.surface, borderColor: theme.border, marginBottom: 10 }]}
              onPress={() => setActiveModal({ type: 'provider', target: 'main' })}
            >
              <Text style={[styles.selectValue, { color: theme.text }]}>
                {getProviderName(selectedKeyProvider)}
              </Text>
              <ChevronDown size={18} color={theme.textMuted} />
            </TouchableOpacity>

            <TextInput
              style={[styles.textInput, { backgroundColor: theme.surface, borderColor: theme.border, color: theme.text, marginBottom: 10 }]}
              placeholder="Pega tu API Key (ej. sk-...)"
              placeholderTextColor={theme.textMuted + '80'}
              value={newKeyValue}
              onChangeText={setNewKeyValue}
              secureTextEntry
              autoCapitalize="none"
            />

            <TouchableOpacity
              style={[styles.saveSecretBtn, { backgroundColor: theme.primary }]}
              onPress={handleSaveSecret}
              disabled={savingSecret}
            >
              {savingSecret ? (
                <ActivityIndicator size="small" color="#fff" />
              ) : (
                <>
                  <Plus size={16} color="#fff" style={{ marginRight: 6 }} />
                  <Text style={styles.saveSecretBtnText}>Guardar API Key</Text>
                </>
              )}
            </TouchableOpacity>
          </View>

          {/* List Stored Keys */}
          <Text style={[styles.fieldLabel, { color: theme.textMuted, marginTop: 16, marginBottom: 8 }]}>
            CLAVES GUARDADAS ({secrets.length})
          </Text>

          {secrets.length === 0 ? (
            <Text style={[styles.emptySecretText, { color: theme.textMuted }]}>No hay API Keys almacenadas aún.</Text>
          ) : (
            secrets.map((sec) => (
              <View key={sec.key_name} style={[styles.secretItem, { backgroundColor: theme.background, borderColor: theme.border }]}>
                <View style={{ flex: 1 }}>
                  <Text style={[styles.secretKeyName, { color: theme.text }]}>{sec.key_name}</Text>
                  <Text style={[styles.secretMasked, { color: theme.textMuted }]}>{sec.masked_value}</Text>
                </View>
                <TouchableOpacity onPress={() => handleDeleteSecret(sec.key_name)} style={styles.deleteSecretBtn}>
                  <Trash2 size={18} color={colors.error} />
                </TouchableOpacity>
              </View>
            ))
          )}
        </View>

        <View style={{ height: 40 }} />
      </ScrollView>

      {/* Modal Selector */}
      <Modal
        visible={activeModal !== null}
        transparent
        animationType="slide"
        onRequestClose={() => setActiveModal(null)}
      >
        <TouchableOpacity style={styles.modalOverlay} activeOpacity={1} onPress={() => setActiveModal(null)}>
          <View style={[styles.modalContent, { backgroundColor: theme.surface }]}>
            <View style={[styles.modalHandle, { backgroundColor: theme.border }]} />

            <View style={styles.modalHeader}>
              <Text style={[styles.modalTitle, { color: theme.text }]}>
                {activeModal?.type === 'provider' ? 'Seleccionar Proveedor' : 'Seleccionar Modelo'}
              </Text>
              <TouchableOpacity onPress={() => setActiveModal(null)}>
                <X size={20} color={theme.textMuted} />
              </TouchableOpacity>
            </View>

            {/* Search Input in Model Modal */}
            {activeModal?.type === 'model' && (
              <View style={[styles.searchBox, { backgroundColor: theme.background, borderColor: theme.border }]}>
                <Search size={16} color={theme.textMuted} style={{ marginRight: 8 }} />
                <TextInput
                  style={[styles.searchInputModal, { color: theme.text }]}
                  placeholder="Buscar modelo..."
                  placeholderTextColor={theme.textMuted}
                  value={modalSearchTerm}
                  onChangeText={setModalSearchTerm}
                />
              </View>
            )}

            <ScrollView style={styles.modalList} showsVerticalScrollIndicator={false}>
              {activeModal?.type === 'provider' ? (
                LLM_PROVIDERS.map((p) => (
                  <TouchableOpacity
                    key={p.id}
                    style={[styles.modalOption, { borderBottomColor: theme.border + '30' }]}
                    onPress={() => selectProvider(p.id, activeModal.target)}
                  >
                    <Text style={[styles.modalOptionText, { color: theme.text }]}>{p.name}</Text>
                  </TouchableOpacity>
                ))
              ) : activeModal ? (
                <>
                  {loadingModels[activeModal.target] && (
                    <View style={styles.loadingModelsRow}>
                      <ActivityIndicator size="small" color={theme.primary} />
                      <Text style={[styles.loadingModelsText, { color: theme.textMuted }]}>
                        Cargando modelos desde la API...
                      </Text>
                    </View>
                  )}

                  {getModelsForTarget(activeModal.target).map((item) => (
                    <TouchableOpacity
                      key={item.id}
                      style={[styles.modalOption, { borderBottomColor: theme.border + '30' }]}
                      onPress={() => selectModel(item.id, activeModal.target)}
                    >
                      <View style={{ flex: 1 }}>
                        <Text style={[styles.modalOptionText, { color: theme.text }]} numberOfLines={1}>
                          {item.name}
                        </Text>
                        <Text style={[styles.modalOptionSub, { color: theme.textMuted }]} numberOfLines={1}>
                          {item.id}
                        </Text>
                      </View>
                      {item.isApi && (
                        <View style={[styles.badgeApi, { backgroundColor: theme.primary + '15' }]}>
                          <Text style={[styles.badgeApiText, { color: theme.primary }]}>API</Text>
                        </View>
                      )}
                    </TouchableOpacity>
                  ))}
                </>
              ) : null}
            </ScrollView>
          </View>
        </TouchableOpacity>
      </Modal>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1 },
  centered: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  loadingText: { marginTop: 12, fontSize: 14, fontWeight: '500' },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
  },
  headerBtn: {
    width: 40,
    height: 40,
    justifyContent: 'center',
    alignItems: 'center',
    borderRadius: 12,
  },
  headerTitle: { fontSize: 18, fontWeight: '800', flex: 1, marginLeft: 8 },
  headerActions: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  saveBtn: {
    width: 38,
    height: 38,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
  },
  scrollContent: { padding: spacing.md },
  card: {
    borderRadius: 20,
    padding: spacing.md,
    marginBottom: spacing.md,
    borderWidth: 1,
    ...Platform.select({
      ios: {
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.05,
        shadowRadius: 10,
      },
      android: { elevation: 2 },
    }),
  },
  cardHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 16, gap: 12 },
  iconBadge: {
    width: 36,
    height: 36,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
  },
  cardTitle: { fontSize: 16, fontWeight: '700' },
  cardSub: { fontSize: 12, marginTop: 2 },
  fieldGroup: { marginBottom: 14 },
  labelRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 },
  fieldLabel: { fontSize: 10, fontWeight: '800', letterSpacing: 1 },
  refreshBtnInline: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  refreshText: { fontSize: 11, fontWeight: '700' },
  selectTrigger: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 12,
    paddingVertical: 12,
    borderRadius: 12,
    borderWidth: 1,
  },
  selectValue: { fontSize: 14, fontWeight: '600', flex: 1, marginRight: 8 },
  textInput: {
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderRadius: 12,
    borderWidth: 1,
    fontSize: 14,
  },
  helperText: { fontSize: 11, marginTop: 6, lineHeight: 16 },
  tempValue: { fontSize: 14, fontWeight: '800' },
  stepperContainer: { flexDirection: 'row', alignItems: 'center', gap: 10, marginTop: 4 },
  stepperBtn: {
    width: 36,
    height: 36,
    borderRadius: 10,
    borderWidth: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  stepperText: { fontSize: 18, fontWeight: '700' },
  stepperBar: { flex: 1, height: 8, backgroundColor: '#e2e8f0', borderRadius: 4, overflow: 'hidden' },
  stepperFill: { height: '100%', borderRadius: 4 },
  switchRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingTop: 12,
    borderTopWidth: 1,
    marginTop: 8,
  },
  switchLabel: { fontSize: 14, fontWeight: '700' },
  switchSub: { fontSize: 11, marginTop: 2 },
  secretForm: { padding: 12, borderRadius: 14, borderWidth: 1, marginBottom: 12 },
  saveSecretBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 10,
    borderRadius: 10,
  },
  saveSecretBtnText: { color: '#fff', fontSize: 13, fontWeight: '700' },
  emptySecretText: { fontSize: 12, fontStyle: 'italic', marginVertical: 8 },
  secretItem: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 10,
    paddingHorizontal: 12,
    borderRadius: 12,
    borderWidth: 1,
    marginBottom: 8,
  },
  secretKeyName: { fontSize: 13, fontWeight: '700' },
  secretMasked: { fontSize: 11, marginTop: 2, fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace' },
  deleteSecretBtn: { padding: 6 },
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'flex-end' },
  modalContent: { borderTopLeftRadius: 24, borderTopRightRadius: 24, padding: 20, maxHeight: '80%' },
  modalHandle: { width: 40, height: 4, borderRadius: 2, alignSelf: 'center', marginBottom: 16 },
  modalHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 },
  modalTitle: { fontSize: 18, fontWeight: '800' },
  searchBox: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    borderRadius: 12,
    borderWidth: 1,
    height: 40,
    marginBottom: 12,
  },
  searchInputModal: { flex: 1, fontSize: 14 },
  modalList: { maxHeight: 400 },
  modalOption: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 14,
    borderBottomWidth: 1,
  },
  modalOptionText: { fontSize: 15, fontWeight: '600' },
  modalOptionSub: { fontSize: 11, marginTop: 2 },
  loadingModelsRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 16, gap: 10 },
  loadingModelsText: { fontSize: 13 },
  badgeApi: { paddingHorizontal: 8, paddingVertical: 2, borderRadius: 6 },
  badgeApiText: { fontSize: 10, fontWeight: '800' },
});
