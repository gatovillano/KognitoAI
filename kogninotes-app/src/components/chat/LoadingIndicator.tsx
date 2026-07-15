// src/components/chat/LoadingIndicator.tsx
import React, { useState, useEffect, useRef, useMemo } from 'react';
import { View, Text, StyleSheet, Animated, Easing } from 'react-native';

interface LoadingIndicatorProps {
  isComprehensiveAnalysisActive?: boolean;
  isKnowledgeAnalysisActive?: boolean;
  isDeepResearchActive?: boolean;
  toolName?: string;
  reactState?: string;
  theme: any;
}

export function LoadingIndicator({
  isComprehensiveAnalysisActive = false,
  isKnowledgeAnalysisActive = false,
  isDeepResearchActive = false,
  toolName,
  reactState,
  theme,
}: LoadingIndicatorProps) {
  const [thoughtIndex, setThoughtIndex] = useState(0);

  const thoughts = useMemo(() => [
    "Descifrando intencionalidad",
    "Explorando red semántica",
    "Sintetizando vectores de conocimiento",
    "Formulando respuesta lógica",
    "Verificando consistencia cognitiva",
    "Mapeando conexiones neuronales",
    "Procesando patrones contextuales",
    "Optimizando árbol de inferencia",
    "Analizando grafo de conocimiento",
    "Recuperando memorias asociativas",
  ], []);

  // Animación de los subtítulos de pensamiento
  const thoughtOpacity = useRef(new Animated.Value(0.45)).current;

  useEffect(() => {
    const thoughtTimer = setInterval(() => {
      // Fade out
      Animated.timing(thoughtOpacity, {
        toValue: 0,
        duration: 250,
        useNativeDriver: true,
      }).start(() => {
        setThoughtIndex((prev) => (prev + 1) % thoughts.length);
        // Fade in
        Animated.timing(thoughtOpacity, {
          toValue: 0.45,
          duration: 350,
          useNativeDriver: true,
        }).start();
      });
    }, 3000);

    return () => clearInterval(thoughtTimer);
  }, [thoughts.length]);

  // Animaciones del Plasma Orb
  const scalePulse = useRef(new Animated.Value(1)).current;
  const secondaryPulse = useRef(new Animated.Value(1)).current;
  const rotationAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    // Loop de escala para el orbe principal
    Animated.loop(
      Animated.sequence([
        Animated.timing(scalePulse, {
          toValue: 1.15,
          duration: 1500,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: true,
        }),
        Animated.timing(scalePulse, {
          toValue: 1,
          duration: 1500,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: true,
        }),
      ])
    ).start();

    // Loop de escala para el orbe secundario (desfasado)
    Animated.loop(
      Animated.sequence([
        Animated.timing(secondaryPulse, {
          toValue: 0.9,
          duration: 1900,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: true,
        }),
        Animated.timing(secondaryPulse, {
          toValue: 1.1,
          duration: 1900,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: true,
        }),
      ])
    ).start();

    // Loop de rotación para simular el conic-gradient en movimiento
    Animated.loop(
      Animated.timing(rotationAnim, {
        toValue: 1,
        duration: 8000,
        easing: Easing.linear,
        useNativeDriver: true,
      })
    ).start();
  }, []);

  const spin = rotationAnim.interpolate({
    inputRange: [0, 1],
    outputRange: ['0deg', '360deg'],
  });

  const palette = useMemo(() => {
    // Colores basados en el tema e idénticos a los del web client
    if (isDeepResearchActive)          return { c1: '#00aaff', c2: '#0077cc', label: 'Investigación Profunda' };
    if (isComprehensiveAnalysisActive) return { c1: '#00ccff', c2: '#00aaff', label: 'Análisis Comprensivo' };
    if (isKnowledgeAnalysisActive)     return { c1: '#0088dd', c2: '#005faa', label: 'Consultando Conocimiento' };
    if (toolName)                      return { c1: '#33bbff', c2: '#0099ee', label: `Ejecutando: ${toolName}` };
    return                                    { c1: '#00aaff', c2: '#0088cc', label: 'Kognito está pensando' };
  }, [isDeepResearchActive, isComprehensiveAnalysisActive, isKnowledgeAnalysisActive, toolName]);

  return (
    <View style={styles.container}>
      {/* Plasma Orb Container */}
      <View style={styles.orbContainer}>
        
        {/* Capa 1: Difuminado de ambiente lejano */}
        <Animated.View
          style={[
            styles.outerBleed,
            {
              backgroundColor: palette.c1 + '18',
              transform: [{ scale: scalePulse }],
            },
          ]}
        />

        {/* Capa 2: Nube secundaria desfasada */}
        <Animated.View
          style={[
            styles.secondaryCloud,
            {
              backgroundColor: palette.c2 + '22',
              transform: [{ scale: secondaryPulse }],
            },
          ]}
        />

        {/* Capa 3: Cuerpo rotativo de energía */}
        <Animated.View
          style={[
            styles.plasmaBody,
            {
              borderColor: palette.c1,
              backgroundColor: palette.c2 + '55',
              transform: [{ rotate: spin }],
            },
          ]}
        />

        {/* Capa 4: Núcleo interno brillante */}
        <Animated.View
          style={[
            styles.core,
            {
              backgroundColor: palette.c1,
              transform: [{ scale: scalePulse }],
            },
          ]}
        />
      </View>

      {/* Textos debajo del orbe */}
      <View style={styles.textWrapper}>
        <View style={styles.labelRow}>
          <Text style={[styles.primaryLabel, { color: palette.c1 }]}>
            {palette.label}
          </Text>
          {reactState && (
            <View style={[styles.badge, { backgroundColor: theme.border + '30', borderColor: theme.border + '50' }]}>
              <Text style={[styles.badgeText, { color: theme.textMuted }]}>{reactState}</Text>
            </View>
          )}
        </View>

        <Animated.View style={{ opacity: thoughtOpacity }}>
          <Text style={[styles.thoughtSubtitle, { color: theme.textMuted }]}>
            {thoughts[thoughtIndex]}
          </Text>
        </Animated.View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    paddingVertical: 20,
    width: '100%',
  },
  orbContainer: {
    width: 44,
    height: 44,
    justifyContent: 'center',
    alignItems: 'center',
  },
  outerBleed: {
    position: 'absolute',
    width: 70,
    height: 70,
    borderRadius: 35,
  },
  secondaryCloud: {
    position: 'absolute',
    width: 60,
    height: 60,
    borderRadius: 30,
  },
  plasmaBody: {
    position: 'absolute',
    width: 44,
    height: 44,
    borderRadius: 22,
    borderWidth: 3,
    borderStyle: 'dashed',
    opacity: 0.8,
  },
  core: {
    position: 'absolute',
    width: 16,
    height: 16,
    borderRadius: 8,
  },
  textWrapper: {
    alignItems: 'center',
    marginTop: 12,
  },
  labelRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginBottom: 4,
  },
  primaryLabel: {
    fontSize: 13,
    fontWeight: '600',
  },
  badge: {
    paddingHorizontal: 6,
    paddingVertical: 1.5,
    borderRadius: 4,
    borderWidth: 0.5,
  },
  badgeText: {
    fontSize: 8,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 1,
  },
  thoughtSubtitle: {
    fontSize: 10,
    fontWeight: '500',
    letterSpacing: 1,
    textTransform: 'uppercase',
    textAlign: 'center',
  },
});
