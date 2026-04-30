// src/components/SourceButton.tsx
import React, { useState } from 'react';
import { 
  View, 
  Text, 
  TouchableOpacity, 
  StyleSheet, 
  Linking, 
  Modal, 
  ScrollView, 
  Platform 
} from 'react-native';
import { 
  ExternalLink, 
  File as FileIcon, 
  Share2, 
  Notebook as NotebookText, 
  Github, 
  ChevronRight, 
  X,
  Database,
  BrainCircuit,
  Code
} from 'lucide-react-native';
import { spacing, borderRadius } from '../theme/colors';
import { useAuth } from '../context/AuthContext';
import { colors, lightColors } from '../theme/colors';

export interface Source {
  id: number | string;
  title: string;
  url: string;
  snippet: string;
  type: 'web' | 'document' | 'memory' | 'code' | 'database' | 'graph' | 'note' | 'github';
  metadata?: Record<string, any>;
  name?: string;
  is_cited?: boolean;
}

interface SourceButtonProps {
  source: Source;
  citationNumber: number;
}

export const SourceButton: React.FC<SourceButtonProps> = ({ source, citationNumber }) => {
  const [modalVisible, setModalVisible] = useState(false);
  const { isDarkMode } = useAuth();
  const theme = isDarkMode ? colors : lightColors;

  const getTypeStyles = () => {
    switch (source.type) {
      case 'web':
        return {
          icon: <ExternalLink size={12} color="#2563eb" />,
          color: isDarkMode ? 'rgba(37,99,235,0.15)' : 'rgba(37,99,235,0.1)',
          textColor: '#2563eb',
          borderColor: 'rgba(37,99,235,0.3)',
          label: 'Web'
        };
      case 'document':
        return {
          icon: <FileIcon size={12} color="#f97316" />,
          color: isDarkMode ? 'rgba(249,115,22,0.15)' : 'rgba(249,115,22,0.1)',
          textColor: '#f97316',
          borderColor: 'rgba(249,115,22,0.3)',
          label: 'Documento'
        };
      case 'memory':
        return {
          icon: <BrainCircuit size={12} color="#a855f7" />,
          color: isDarkMode ? 'rgba(168,85,247,0.15)' : 'rgba(168,85,247,0.1)',
          textColor: '#a855f7',
          borderColor: 'rgba(168,85,247,0.3)',
          label: 'Memoria'
        };
      case 'code':
        return {
          icon: <Code size={12} color="#64748b" />,
          color: isDarkMode ? 'rgba(100,116,139,0.15)' : 'rgba(100,116,139,0.1)',
          textColor: '#64748b',
          borderColor: 'rgba(100,116,139,0.3)',
          label: 'Código'
        };
      case 'database':
        return {
          icon: <Database size={12} color="#10b981" />,
          color: isDarkMode ? 'rgba(16,185,129,0.15)' : 'rgba(16,185,129,0.1)',
          textColor: '#10b981',
          borderColor: 'rgba(16,185,129,0.3)',
          label: 'Base de Datos'
        };
      case 'graph':
        return {
          icon: <Share2 size={12} color="#06b6d4" />,
          color: isDarkMode ? 'rgba(6,182,212,0.15)' : 'rgba(6,182,212,0.1)',
          textColor: '#06b6d4',
          borderColor: 'rgba(6,182,212,0.3)',
          label: 'Grafo'
        };
      case 'note':
        return {
          icon: <NotebookText size={12} color="#eab308" />,
          color: isDarkMode ? 'rgba(234,179,8,0.15)' : 'rgba(234,179,8,0.1)',
          textColor: '#eab308',
          borderColor: 'rgba(234,179,8,0.3)',
          label: 'Nota'
        };
      case 'github':
        return {
          icon: <Github size={12} color="#6366f1" />,
          color: isDarkMode ? 'rgba(99,102,241,0.15)' : 'rgba(99,102,241,0.1)',
          textColor: '#6366f1',
          borderColor: 'rgba(99,102,241,0.3)',
          label: 'GitHub'
        };
      default:
        return {
          icon: <FileIcon size={12} color={theme.primary} />,
          color: theme.primary + '15',
          textColor: theme.primary,
          borderColor: theme.primary + '30',
          label: 'Fuente'
        };
    }
  };

  const { icon, color, label, textColor, borderColor } = getTypeStyles();

  const handleOpenSource = () => {
    if (source.url && (source.type === 'web' || source.type === 'github')) {
      Linking.openURL(source.url);
    } else {
      setModalVisible(true);
    }
  };

  return (
    <>
      <TouchableOpacity 
        onPress={handleOpenSource}
        style={[
          styles.button, 
          { backgroundColor: color, borderColor: borderColor }
        ]}
        activeOpacity={0.7}
      >
        <View style={styles.iconContainer}>{icon}</View>
        <Text style={[styles.text, { color: textColor }]}>{citationNumber}</Text>
      </TouchableOpacity>

      <Modal
        visible={modalVisible}
        transparent
        animationType="slide"
        onRequestClose={() => setModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <TouchableOpacity 
            style={styles.modalBackground} 
            activeOpacity={1} 
            onPress={() => setModalVisible(false)} 
          />
          <View style={[styles.modalSheet, { backgroundColor: theme.surface }]}>
            <View style={[styles.modalHandle, { backgroundColor: theme.border }]} />
            
            <View style={styles.modalHeader}>
              <View style={[styles.typeBadge, { backgroundColor: color }]}>
                {React.cloneElement(icon as React.ReactElement<any>, { size: 16, color: textColor })}
              </View>
              <View style={styles.headerInfo}>
                <Text style={[styles.modalTitle, { color: theme.text }]} numberOfLines={2}>
                  {source.title}
                </Text>
                <Text style={[styles.modalSubtitle, { color: textColor }]}>
                  {label} {source.id ? `• #ID-${source.id}` : ''}
                </Text>
              </View>
              <TouchableOpacity onPress={() => setModalVisible(false)} style={styles.closeBtn}>
                <X size={20} color={theme.textMuted} />
              </TouchableOpacity>
            </View>

            <ScrollView style={styles.modalBody} showsVerticalScrollIndicator={false}>
              {source.snippet ? (
                <View style={styles.snippetContainer}>
                  <View style={[styles.quoteLine, { backgroundColor: textColor }]} />
                  <Text style={[styles.snippetText, { color: theme.textMuted }]}>
                    {source.snippet}
                  </Text>
                </View>
              ) : (
                <Text style={[styles.emptyText, { color: theme.textMuted }]}>
                  No hay previsualización disponible para esta fuente.
                </Text>
              )}

              {source.url && (
                <TouchableOpacity 
                  style={[styles.linkAction, { backgroundColor: theme.primary + '10' }]}
                  onPress={() => Linking.openURL(source.url)}
                >
                  <Text style={[styles.linkActionText, { color: theme.primary }]}>
                    Ver fuente original
                  </Text>
                  <ChevronRight size={16} color={theme.primary} />
                </TouchableOpacity>
              )}
            </ScrollView>
          </View>
        </View>
      </Modal>
    </>
  );
};

const styles = StyleSheet.create({
  button: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
    borderWidth: 1,
    marginRight: 6,
    marginBottom: 6,
  },
  iconContainer: {
    marginRight: 4,
  },
  text: {
    fontSize: 11,
    fontWeight: '800',
  },
  modalOverlay: {
    flex: 1,
    justifyContent: 'flex-end',
  },
  modalBackground: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0,0,0,0.5)',
  },
  modalSheet: {
    borderTopLeftRadius: 30,
    borderTopRightRadius: 30,
    padding: spacing.lg,
    maxHeight: '70%',
    ...Platform.select({
      ios: {
        shadowColor: '#000',
        shadowOffset: { width: 0, height: -10 },
        shadowOpacity: 0.1,
        shadowRadius: 15,
      },
      android: {
        elevation: 20,
      }
    })
  },
  modalHandle: {
    width: 40,
    height: 4,
    borderRadius: 2,
    backgroundColor: '#ccc',
    alignSelf: 'center',
    marginBottom: 20,
  },
  modalHeader: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 24,
  },
  typeBadge: {
    width: 44,
    height: 44,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 14,
  },
  headerInfo: {
    flex: 1,
    marginRight: 10,
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: '800',
    lineHeight: 22,
    letterSpacing: -0.5,
  },
  modalSubtitle: {
    fontSize: 11,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 1,
    marginTop: 4,
  },
  closeBtn: {
    padding: 4,
  },
  modalBody: {
    marginBottom: 20,
  },
  snippetContainer: {
    flexDirection: 'row',
    marginBottom: 24,
  },
  quoteLine: {
    width: 3,
    borderRadius: 1.5,
    marginRight: 14,
    opacity: 0.5,
  },
  snippetText: {
    flex: 1,
    fontSize: 15,
    lineHeight: 22,
    fontStyle: 'italic',
  },
  emptyText: {
    fontSize: 14,
    textAlign: 'center',
    fontStyle: 'italic',
    marginVertical: 40,
  },
  linkAction: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 16,
    borderRadius: 16,
    marginBottom: 10,
  },
  linkActionText: {
    fontSize: 15,
    fontWeight: '700',
  }
});
