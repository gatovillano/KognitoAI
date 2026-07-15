// src/components/chat/DeepResearchVisualizer.tsx
import React, { useMemo, useEffect, useState, useRef } from 'react';
import { View, Text, StyleSheet, Animated } from 'react-native';
import { BrainCircuit, Globe, Cpu, CheckCircle2, Sparkles, Loader2 } from 'lucide-react-native';
import { LinearGradient } from 'expo-linear-gradient';

interface DeepResearchVisualizerProps {
  progress: number;
  statusText: string;
  theme: any;
  isDarkMode: boolean;
}

const mapStatusToFirstPerson = (status: string): string => {
  if (!status) return 'Iniciando investigación...';
  if (status.includes('Verificando claridad')) {
      return 'Estoy analizando tu consulta para estructurar los objetivos de la investigación.';
  }
  if (status.includes('Generando el resumen de investigación')) {
      return 'Estoy trazando el mapa de ruta y definiendo el plan de investigación...';
  }
  if (status.includes('Resumen de investigación generado')) {
      return 'He establecido el plan. Estoy creando agentes investigadores especializados para comenzar.';
  }
  if (status.includes('Supervisor: Planificando iteración')) {
      const match = status.match(/iteración de investigación (\d+)\/(\d+)/i);
      if (match) {
          return `Como supervisor, estoy planificando y organizando la iteración de investigación ${match[1]} de ${match[2]}...`;
      }
      return 'Como supervisor, estoy coordinando el trabajo y planificando los siguientes pasos de los agentes.';
  }
  if (status.includes('Supervisor: Preparando herramientas')) {
      return 'Estoy preparando y calibrando las herramientas de búsqueda y análisis.';
  }
  if (status.includes('Investigando:')) {
      const match = status.match(/Investigando:\s*(.*?)(?:\s*\(Paso\s*(\d+)\/(\d+)\))?$/i);
      if (match) {
          const topic = match[1];
          const step = match[2] ? ` (Paso ${match[2]}/${match[3]})` : '';
          return `Estoy explorando y recolectando fuentes sobre: "${topic}"${step}.`;
      }
      return 'Estoy investigando y recolectando información de las fuentes seleccionadas...';
  }
  if (status.includes('Ejecutando herramientas para:')) {
      const topic = status.replace('Ejecutando herramientas para:', '').trim();
      return `Buscando información detallada y consultando bases de datos para: "${topic}"...`;
  }
  if (status.includes('Herramientas ejecutadas para:')) {
      const topic = status.replace('Herramientas ejecutadas para:', '').trim();
      return `He recopilado información relevante para: "${topic}".`;
  }
  if (status.includes('Sintetizando hallazgos para:')) {
      const topic = status.replace('Sintetizando hallazgos para:', '').trim();
      return `Estoy analizando, filtrando y consolidando las fuentes recopiladas para: "${topic}".`;
  }
  if (status.includes('Experto ')) {
      const match = status.match(/Experto\s+(.*?):\s*(.*?)(?:\s*\(Paso\s*(\d+)\/(\d+)\))?$/i);
      if (match) {
          const expert = match[1];
          const topic = match[2];
          const step = match[3] ? ` (Paso ${match[3]}/${match[4]})` : '';
          return `Mi especialista en ${expert} está buscando información y analizando en profundidad: "${topic}"${step}.`;
      }
      return 'El especialista asignado está analizando la información...';
  }
  if (status.includes('Ejecutando herramientas para experto')) {
      const match = status.match(/Ejecutando herramientas para experto\s+(.*?):\s*(.*)/i);
      if (match) {
          return `El especialista en ${match[1]} está extrayendo datos clave para: "${match[2]}"...`;
      }
      return 'El especialista está ejecutando herramientas de consulta especializada...';
  }
  if (status.includes('Sintetizando hallazgos del experto')) {
      const match = status.match(/Sintetizando hallazgos del experto\s+(.*?):\s*(.*)/i);
      if (match) {
          return `El especialista en ${match[1]} está redactando sus conclusiones para: "${match[2]}".`;
      }
      return 'El especialista está sintetizando sus hallazgos...';
  }
  if (status.includes('Generando el informe final')) {
      return 'Estoy redactando y estructurando el informe final con todos los hallazgos y recomendaciones.';
  }
  return status;
};

export function DeepResearchVisualizer({ progress, statusText, theme, isDarkMode }: DeepResearchVisualizerProps) {
  const [logs, setLogs] = useState<string[]>([]);
  const pulseAnim = useRef(new Animated.Value(1)).current;
  const rotateAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (statusText) {
      const mappedMsg = mapStatusToFirstPerson(statusText);
      setLogs(prev => {
        if (prev.length > 0 && prev[0] === mappedMsg) return prev;
        return [mappedMsg, ...prev].slice(0, 3);
      });
    }
  }, [statusText]);

  useEffect(() => {
    Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, { toValue: 1.2, duration: 1000, useNativeDriver: true }),
        Animated.timing(pulseAnim, { toValue: 1, duration: 1000, useNativeDriver: true }),
      ])
    ).start();

    Animated.loop(
      Animated.timing(rotateAnim, { toValue: 1, duration: 2000, useNativeDriver: true })
    ).start();
  }, []);

  const spin = rotateAnim.interpolate({
    inputRange: [0, 1],
    outputRange: ['0deg', '360deg']
  });

  const latestFirstPersonMsg = logs[0] || mapStatusToFirstPerson(statusText);

  const milestones = useMemo(() => [
    {
      id: 'plan',
      title: 'Planificación y Configuración',
      description: 'Analizando la consulta y configurando el plan de investigación.',
      minProgress: 0,
      maxProgress: 20,
      icon: BrainCircuit,
    },
    {
      id: 'search',
      title: 'Exploración de Fuentes',
      description: 'Buscando en la web y recolectando fuentes relevantes.',
      minProgress: 21,
      maxProgress: 60,
      icon: Globe,
    },
    {
      id: 'expert',
      title: 'Análisis de Expertos',
      description: 'Agentes especialistas investigando a fondo cada tema.',
      minProgress: 61,
      maxProgress: 90,
      icon: Cpu,
    },
    {
      id: 'report',
      title: 'Generación de Informe',
      description: 'Estructurando y redactando el informe y recomendaciones.',
      minProgress: 91,
      maxProgress: 100,
      icon: CheckCircle2,
    }
  ], []);

  return (
    <View style={[
      styles.card, 
      { 
        backgroundColor: isDarkMode ? 'rgba(255,255,255,0.02)' : 'rgba(0,0,0,0.01)', 
        borderColor: theme.border + '40'
      }
    ]}>
      {/* Header */}
      <View style={styles.header}>
        <View style={styles.headerTitleRow}>
          <View style={[styles.iconBox, { backgroundColor: theme.primary + '15' }]}>
            <BrainCircuit size={20} color={theme.primary} />
          </View>
          <View>
            <View style={styles.innerTitleRow}>
              <Text style={[styles.title, { color: theme.text }]}>Deep Research</Text>
              <Sparkles size={12} color={theme.primary} style={{ opacity: 0.8 }} />
            </View>
            <View style={styles.pulseRow}>
              <Animated.View style={[styles.pulseDot, { backgroundColor: theme.primary, transform: [{ scale: pulseAnim }] }]} />
              <Text style={[styles.subText, { color: theme.textMuted }]}>PROCESANDO CONOCIMIENTO GLOBAL</Text>
            </View>
          </View>
        </View>
        
        <View style={styles.percentageRow}>
          <Text style={[styles.percentage, { color: theme.primary }]}>{Math.round(progress)}</Text>
          <Text style={[styles.percentSign, { color: theme.primary }]}>%</Text>
        </View>
      </View>

      {/* Progress Bar */}
      <View style={[styles.progressContainer, { backgroundColor: theme.border + '30' }]}>
        <View style={{ width: `${progress}%`, height: '100%' }}>
          <LinearGradient
            colors={[theme.primary, '#3b82f6', '#4f46e5']}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 0 }}
            style={styles.gradientBar}
          />
        </View>
      </View>

      {/* Milestones List */}
      <View style={styles.milestonesContainer}>
        {milestones.map((m, idx) => {
          const isCompleted = progress > m.maxProgress;
          const isActive = progress >= m.minProgress && progress <= m.maxProgress;
          const isPending = progress < m.minProgress;
          const Icon = isCompleted ? CheckCircle2 : m.icon;

          return (
            <View key={m.id} style={[styles.milestoneRow, isPending && { opacity: 0.3 }]}>
              {/* Connector line */}
              {idx < milestones.length - 1 && (
                <View style={[
                  styles.connector, 
                  { 
                    backgroundColor: isCompleted ? '#10b981' : theme.border + '60' 
                  }
                ]} />
              )}

              {/* Milestone Icon */}
              <View style={[
                styles.milestoneIconWrapper,
                {
                  borderColor: isCompleted ? '#10b981' : (isActive ? theme.primary : theme.border),
                  backgroundColor: isCompleted ? 'rgba(16,185,129,0.1)' : (isActive ? theme.primary + '15' : 'transparent')
                }
              ]}>
                {isActive && !isCompleted ? (
                  <View style={{ position: 'relative' }}>
                    <Icon size={14} color={theme.primary} />
                    <View style={[styles.badgeActiveDot, { backgroundColor: theme.primary }]} />
                  </View>
                ) : (
                  <Icon size={14} color={isCompleted ? '#10b981' : theme.textMuted} />
                )}
              </View>

              {/* Milestone Info */}
              <View style={styles.milestoneInfo}>
                <Text style={[
                  styles.milestoneTitle, 
                  { 
                    color: isCompleted ? '#10b981' : (isActive ? theme.primary : theme.text)
                  }
                ]}>
                  {m.title}
                </Text>
                <Text style={[styles.milestoneDesc, { color: theme.textMuted }]}>
                  {m.description}
                </Text>

                {/* Subtitle / Active Status Message */}
                {isActive && latestFirstPersonMsg ? (
                  <View style={[styles.statusBanner, { backgroundColor: theme.primary + '08', borderColor: theme.primary + '15' }]}>
                    <Animated.View style={{ transform: [{ rotate: spin }] }}>
                      <Loader2 size={12} color={theme.primary} />
                    </Animated.View>
                    <Text style={[styles.statusText, { color: theme.text }]}>
                      {latestFirstPersonMsg}
                    </Text>
                  </View>
                ) : null}
              </View>
            </View>
          );
        })}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    borderRadius: 24,
    borderWidth: 1,
    padding: 20,
    marginVertical: 12,
    marginHorizontal: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.1,
    shadowRadius: 10,
    elevation: 3,
    width: '98%',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  headerTitleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  iconBox: {
    width: 38,
    height: 38,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
  },
  innerTitleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  title: {
    fontSize: 16,
    fontWeight: '800',
    letterSpacing: -0.2,
  },
  pulseRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginTop: 2,
  },
  pulseDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
  },
  subText: {
    fontSize: 8,
    fontWeight: '700',
    letterSpacing: 0.8,
  },
  percentageRow: {
    flexDirection: 'row',
    alignItems: 'baseline',
  },
  percentage: {
    fontSize: 26,
    fontWeight: '900',
  },
  percentSign: {
    fontSize: 12,
    fontWeight: '700',
    marginLeft: 1,
  },
  progressContainer: {
    height: 8,
    borderRadius: 4,
    overflow: 'hidden',
    marginBottom: 20,
  },
  gradientBar: {
    width: '100%',
    height: '100%',
  },
  milestonesContainer: {
    paddingLeft: 4,
  },
  milestoneRow: {
    flexDirection: 'row',
    position: 'relative',
    paddingBottom: 22,
  },
  connector: {
    position: 'absolute',
    left: 13,
    top: 26,
    bottom: 0,
    width: 1.5,
  },
  milestoneIconWrapper: {
    width: 28,
    height: 28,
    borderRadius: 10,
    borderWidth: 1.5,
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 10,
  },
  badgeActiveDot: {
    position: 'absolute',
    top: -3,
    right: -3,
    width: 6,
    height: 6,
    borderRadius: 3,
  },
  milestoneInfo: {
    flex: 1,
    paddingLeft: 14,
  },
  milestoneTitle: {
    fontSize: 13,
    fontWeight: '700',
  },
  milestoneDesc: {
    fontSize: 11,
    marginTop: 1,
    lineHeight: 15,
  },
  statusBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    padding: 10,
    borderRadius: 12,
    borderWidth: 0.5,
    marginTop: 8,
  },
  statusText: {
    fontSize: 11,
    fontWeight: '600',
    flex: 1,
    lineHeight: 14,
  },
});
