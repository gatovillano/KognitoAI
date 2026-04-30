// src/screens/ChatScreen.tsx
import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TextInput,
  TouchableOpacity,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
  LayoutAnimation,
  Modal,
  ScrollView,
  StatusBar,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useAuth } from '../context/AuthContext';
import { chatService, ChatMessage, ChatThread } from '../api/chatService';
import { workspaceService, Workspace } from '../api/workspaceService';
import { colors, lightColors, spacing, borderRadius } from '../theme/colors';
import { Send, Menu, List, Plus, ChevronDown, Briefcase, Sparkles, MessageSquare, History, X, Layout, FileText, Calendar } from 'lucide-react-native';
import Markdown from 'react-native-markdown-display';
import { useStreamingChat } from '../hooks/useStreamingChat';
import { LinearGradient } from 'expo-linear-gradient';
import { SourceButton } from '../components/SourceButton';
import { collectSourcesFromMessage } from '../utils/chatUtils';
import { MixedContentRenderer } from '../components/chat/MixedContentRenderer';
import { ReasoningBlock } from '../components/chat/ReasoningBlock';
import { SafeAreaView as RNSafeAreaView } from 'react-native-safe-area-context';


// Reasoning is now handled by ReasoningBlock.tsx inside MixedContentRenderer

export const ChatScreen = ({ navigation }: any) => {
  const { isDarkMode } = useAuth();
  const theme = isDarkMode ? colors : lightColors;
  const { user } = useAuth();

  // Workspace state
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [selectedWorkspace, setSelectedWorkspace] = useState<Workspace | null>(null);
  const [showWorkspacePicker, setShowWorkspacePicker] = useState(false);

  // Thread / message state
  const [threads, setThreads] = useState<ChatThread[]>([]);
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [loadingThreads, setLoadingThreads] = useState(true);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [showThreadList, setShowThreadList] = useState(false);
  const [showAppMenu, setShowAppMenu] = useState(false);

  const flatListRef = useRef<FlatList>(null);

  // Streaming
  const { sendMessage, currentResponse, currentReasoning, isLoading: isStreaming } = useStreamingChat({
    onChunk: () => flatListRef.current?.scrollToEnd({ animated: true }),
    onComplete: () => { if (activeThreadId) loadMessages(activeThreadId); },
    onError: (err) => console.error('Streaming error:', err),
  });

  // Load workspaces once
  useEffect(() => {
    workspaceService.listWorkspaces()
      .then(data => setWorkspaces(data?.workspaces || []))
      .catch(e => console.error('Error loading workspaces:', e));
  }, []);

  // Reload threads when workspace changes
  useEffect(() => {
    setActiveThreadId(null);
    setMessages([]);
    loadThreads();
  }, [selectedWorkspace]);

  const loadThreads = async () => {
    try {
      setLoadingThreads(true);
      const data = await chatService.listThreads(selectedWorkspace?.id);
      setThreads(data || []);
      if (data && data.length > 0) {
        setActiveThreadId(data[0].id);
      }
    } catch (error) {
      console.error('Error loading threads:', error);
    } finally {
      setLoadingThreads(false);
    }
  };

  const loadMessages = async (threadId: string) => {
    try {
      setLoadingMessages(true);
      const msgList = await chatService.listMessages(threadId);
      setMessages(msgList);
      setTimeout(() => flatListRef.current?.scrollToEnd({ animated: false }), 200);
    } catch (error) {
      console.error('Error loading messages:', error);
    } finally {
      setLoadingMessages(false);
    }
  };

  useEffect(() => {
    if (activeThreadId) loadMessages(activeThreadId);
  }, [activeThreadId]);

  const handleCreateThread = async () => {
    try {
      const newThread = await chatService.createThread('Nuevo Chat', selectedWorkspace?.id);
      setThreads(prev => [newThread, ...prev]);
      setActiveThreadId(newThread.id);
      setShowThreadList(false);
    } catch (error) {
      console.error('Error creating thread:', error);
    }
  };

  const handleSend = async () => {
    if (!inputMessage.trim() || !activeThreadId || !user?.id) return;

    const messageText = inputMessage.trim();
    setInputMessage('');

    const tempUserMsg: ChatMessage = {
      text: messageText,
      sender: 'user',
      created_at: new Date().toISOString(),
    };
    setMessages(prev => [...prev, tempUserMsg]);
    setTimeout(() => flatListRef.current?.scrollToEnd({ animated: true }), 100);

    await sendMessage({
      thread_id: activeThreadId,
      account_id: user.id,
      user_message: messageText,
      ...(selectedWorkspace ? { workspace_id: selectedWorkspace.id } : {}),
    } as any);
  };

  const markdownStyles = StyleSheet.create({
    body: { color: theme.text, fontSize: 16, lineHeight: 24, fontWeight: '400' },
    paragraph: { marginVertical: 8 },
    heading1: { color: theme.primary, fontWeight: '900', fontSize: 24, marginVertical: 12 },
    heading2: { color: theme.text, fontWeight: '800', fontSize: 20, marginVertical: 10 },
    heading3: { color: theme.text, fontWeight: '700', fontSize: 18, marginVertical: 8 },
    strong: { fontWeight: '800', color: isDarkMode ? '#fff' : '#000' },
    em: { fontStyle: 'italic' },
    link: { color: theme.primary, textDecorationLine: 'underline' },
    list_item: { marginVertical: 4 },
    bullet_list: { marginVertical: 8 },
    ordered_list: { marginVertical: 8 },
    code_inline: { 
        backgroundColor: isDarkMode ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.05)', 
        color: theme.primary,
        borderRadius: 4,
        paddingHorizontal: 6,
        fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace',
    },
    fence: {
        backgroundColor: isDarkMode ? '#111' : '#f0f0f0',
        borderRadius: 12,
        padding: 12,
        marginVertical: 10,
        borderWidth: 1,
        borderColor: isDarkMode ? '#333' : '#eee',
    },
    table: {
        borderWidth: 1,
        borderColor: theme.border,
        borderRadius: 8,
        marginVertical: 10,
    },
    tr: {
        borderBottomWidth: 1,
        borderColor: theme.border,
        flexDirection: 'row',
    },
    th: {
        backgroundColor: isDarkMode ? '#222' : '#f8f8f8',
        padding: 8,
        fontWeight: 'bold',
    },
    td: {
        padding: 8,
    }
  });



  const renderMessage = ({ item }: { item: ChatMessage }) => {
    const isUser = item.sender === 'user';
    const { additionalSources } = !isUser ? collectSourcesFromMessage(item.sources, item.ragContext) : { additionalSources: [] };

    return (
      <View style={[
        styles.messageWrapper,
        isUser 
          ? { justifyContent: 'flex-end', paddingLeft: 60, paddingHorizontal: 16 } 
          : { flexDirection: 'column', paddingHorizontal: 10 }
      ]}>
        {!isUser && (
           <View style={[styles.avatarCircle, { backgroundColor: theme.primary + '15', marginBottom: 6, marginLeft: 2 }]}>
              <Sparkles size={14} color={theme.primary} />
           </View>
        )}
        <View style={[
          styles.messageContent,
          isUser ? styles.userContent : styles.aiContent
        ]}>
          {!isUser && (
            <View style={styles.aiHeader}>
              <View style={[styles.brandBadge, { backgroundColor: theme.primary + '15', borderColor: theme.primary + '30' }]}>
                <Text style={[styles.brandText, { color: theme.primary }]}>KAI Intelligence</Text>
              </View>
              <Text style={[styles.modelText, { color: theme.textMuted }]}>Assistant</Text>
            </View>
          )}

          <View style={[
            styles.messageBubble,
            isUser ? styles.userBubble : styles.aiBubble
          ]}>
            {isUser ? (
               <LinearGradient
                  colors={[colors.primaryLight, colors.primary]}
                  start={{ x: 0, y: 0 }}
                  end={{ x: 1, y: 1 }}
                  style={styles.userGradient}
               >
                  <Text style={[styles.messageText, { color: '#fff' }]}>{item.text}</Text>
               </LinearGradient>
            ) : (
              <View style={styles.markdownContainer}>
                <MixedContentRenderer 
                  content={item.text}
                  contentParts={item.content_parts}
                  isDarkMode={isDarkMode} 
                  theme={theme} 
                  markdownStyles={markdownStyles} 
                />
              </View>
            )}
          </View>

          {/* Fuents Section */}
          {!isUser && additionalSources.length > 0 && (
            <View style={styles.sourcesWrapper}>
              <View style={styles.sourcesHeader}>
                <List size={10} color={theme.textMuted} style={{ marginRight: 6 }} />
                <Text style={[styles.sourcesHeaderText, { color: theme.textMuted }]}>Fuentes</Text>
              </View>
              <View style={styles.sourcesList}>
                {additionalSources.map((source, idx) => (
                  <SourceButton key={idx} source={source} citationNumber={idx + 1} />
                ))}
              </View>
            </View>
          )}
        </View>
      </View>
    );
  };

  // Workspace display name
  const workspaceLabel = selectedWorkspace ? selectedWorkspace.name : 'Inteligencia Global';

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: theme.background }]}>
      <StatusBar barStyle={isDarkMode ? 'light-content' : 'dark-content'} />

      {/* Header */}
      <View style={[styles.header, { borderBottomColor: theme.border + '40' }]}>
        <TouchableOpacity onPress={() => setShowThreadList(!showThreadList)} style={styles.headerBtn}>
          <History color={theme.text} size={22} />
        </TouchableOpacity>

        {/* Workspace Selector */}
        <TouchableOpacity
          style={[styles.workspaceSelector, { backgroundColor: theme.surface, borderColor: theme.border }]}
          onPress={() => setShowWorkspacePicker(true)}
        >
          <View style={[styles.wsDot, { backgroundColor: selectedWorkspace?.color || theme.primary }]} />
          <Text style={[styles.workspaceSelectorText, { color: theme.text }]} numberOfLines={1}>
            {workspaceLabel}
          </Text>
          <ChevronDown size={14} color={theme.textMuted} />
        </TouchableOpacity>

        <TouchableOpacity onPress={() => setShowAppMenu(!showAppMenu)} style={styles.headerBtn}>
          <Menu color={theme.text} size={22} />
        </TouchableOpacity>
      </View>

      {/* App Menu Dropdown */}
      {showAppMenu && (
        <View style={[styles.dropdownMenu, { backgroundColor: theme.surface, borderColor: theme.border }]}>
          <TouchableOpacity onPress={() => { setShowAppMenu(false); navigation.navigate('Home'); }} style={styles.dropdownItem}>
             <View style={styles.dropdownIconText}>
                <FileText size={16} color={theme.primary} style={{ marginRight: 10 }} />
                <Text style={[styles.dropdownText, { color: theme.text }]}>Mis Notas</Text>
             </View>
          </TouchableOpacity>
          <TouchableOpacity onPress={() => { setShowAppMenu(false); navigation.navigate('Calendar'); }} style={[styles.dropdownItem, { borderBottomWidth: 0 }]}>
             <View style={styles.dropdownIconText}>
                <Calendar size={16} color={theme.primary} style={{ marginRight: 10 }} />
                <Text style={[styles.dropdownText, { color: theme.text }]}>Calendario</Text>
             </View>
          </TouchableOpacity>
        </View>
      )}

      {/* Threads Drawer (Overlay style) */}
      {showThreadList && (
        <TouchableOpacity 
           style={styles.drawerOverlay} 
           activeOpacity={1} 
           onPress={() => setShowThreadList(false)}
        >
           <View style={[styles.threadDrawer, { backgroundColor: theme.surface, borderRightColor: theme.border }]}>
             <View style={styles.drawerHeader}>
               <Text style={[styles.drawerTitle, { color: theme.text }]}>Historial</Text>
               <TouchableOpacity onPress={handleCreateThread} style={styles.newChatBtn}>
                 <Plus color={theme.primary} size={20} />
               </TouchableOpacity>
             </View>
             {loadingThreads ? <ActivityIndicator size="small" color={theme.primary} style={{ margin: spacing.lg }} /> : (
               <FlatList
                 data={threads}
                 keyExtractor={t => t.id}
                 contentContainerStyle={{ padding: 8 }}
                 renderItem={({ item }) => (
                   <TouchableOpacity
                     style={[styles.threadItem, activeThreadId === item.id && { backgroundColor: theme.primary + '15' }]}
                     onPress={() => { setActiveThreadId(item.id); setShowThreadList(false); }}
                   >
                     <MessageSquare size={16} color={activeThreadId === item.id ? theme.primary : theme.textMuted} style={{ marginRight: 10 }} />
                     <Text style={[styles.threadTitle, { color: theme.text }, activeThreadId === item.id && { fontWeight: '700' }]} numberOfLines={1}>
                        {item.title}
                     </Text>
                   </TouchableOpacity>
                 )}
               />
             )}
           </View>
        </TouchableOpacity>
      )}

      {/* Chat Area */}
      <View style={styles.chatArea}>
        {loadingMessages ? (
          <View style={styles.centered}>
            <ActivityIndicator size="large" color={theme.primary} />
          </View>
        ) : (
          <FlatList
            ref={flatListRef}
            data={messages}
            keyExtractor={(_, index) => index.toString()}
            renderItem={renderMessage}
            contentContainerStyle={styles.messageList}
            showsVerticalScrollIndicator={false}
            ListEmptyComponent={
              !loadingMessages && !isStreaming ? (
                <View style={styles.emptyChat}>
                  <View style={[styles.aiLogoContainer, { backgroundColor: theme.surface, borderColor: theme.border }]}>
                     <Sparkles size={40} color={theme.primary} />
                  </View>
                  <Text style={[styles.emptyChatTitle, { color: theme.text }]}>
                    {selectedWorkspace ? `Kognito en ${selectedWorkspace.name}` : 'Kognito AI'}
                  </Text>
                  <Text style={[styles.emptyChatSub, { color: theme.textMuted }]}>
                    Potenciado por tus conocimientos. Hazme cualquier pregunta.
                  </Text>
                </View>
              ) : null
            }
            ListFooterComponent={
              isStreaming ? (
                <View style={[styles.messageWrapper, { flexDirection: 'column', paddingHorizontal: 10 }]}>
                   <View style={[styles.avatarCircle, { backgroundColor: theme.primary + '15', marginBottom: 6, marginLeft: 2 }]}>
                      <Sparkles size={14} color={theme.primary} />
                   </View>
                    <View style={styles.aiContent}>
                       <View style={styles.aiHeader}>
                         <View style={[styles.brandBadge, { backgroundColor: theme.primary + '15', borderColor: theme.primary + '30' }]}>
                           <Text style={[styles.brandText, { color: theme.primary }]}>KAI Intelligence</Text>
                         </View>
                         <Text style={[styles.modelText, { color: theme.textMuted }]}>Assistant</Text>
                       </View>
                       
                       {currentReasoning ? (
                          <ReasoningBlock 
                            content={currentReasoning} 
                            isDarkMode={isDarkMode} 
                            theme={theme} 
                            markdownStyles={markdownStyles} 
                          />
                       ) : null}
                      
                      <View style={styles.markdownContainer}>
                        <Text style={[styles.thinkingText, { color: theme.textMuted }]}>
                           {currentResponse || currentReasoning ? '' : 'Pensando...'}
                        </Text>
                        {currentResponse ? (
                          <MixedContentRenderer 
                            content={currentResponse} 
                            isDarkMode={isDarkMode} 
                            theme={theme} 
                            markdownStyles={markdownStyles} 
                          />
                        ) : null}
                      </View>
                   </View>
                </View>
              ) : null
            }
          />
        )}
      </View>

      {/* Input Area */}
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        keyboardVerticalOffset={Platform.OS === 'ios' ? 90 : 0}
      >
        <View style={[styles.inputWrapper, { borderTopColor: theme.border + '20' }]}>
           <View style={[styles.inputContainer, { backgroundColor: theme.surface, borderColor: theme.border }]}>
             <TextInput
               style={[styles.input, { color: theme.text }]}
               placeholder="Pregunta algo..."
               placeholderTextColor={theme.textMuted + '80'}
               value={inputMessage}
               onChangeText={setInputMessage}
               multiline
               maxLength={1000}
             />
             <TouchableOpacity
               style={[
                  styles.sendButton, 
                  { backgroundColor: inputMessage.trim() ? theme.primary : theme.border }
               ]}
               onPress={handleSend}
               disabled={!inputMessage.trim() || isStreaming}
             >
               <Send color={inputMessage.trim() ? "#fff" : theme.textMuted} size={18} />
             </TouchableOpacity>
           </View>
        </View>
      </KeyboardAvoidingView>

      {/* Workspace Picker Modal */}
      <Modal
        visible={showWorkspacePicker}
        transparent
        animationType="slide"
        onRequestClose={() => setShowWorkspacePicker(false)}
      >
        <TouchableOpacity
          style={styles.modalOverlay}
          activeOpacity={1}
          onPress={() => setShowWorkspacePicker(false)}
        >
          <View style={[styles.modalSheet, { backgroundColor: theme.surface }]}>
            <View style={[styles.modalHandle, { backgroundColor: theme.border }]} />
            <Text style={[styles.modalTitle, { color: theme.text }]}>Ámbito de Conocimiento</Text>

            <ScrollView showsVerticalScrollIndicator={false}>
              <TouchableOpacity
                style={[
                  styles.wsOption,
                  { borderColor: theme.border },
                  !selectedWorkspace && { backgroundColor: theme.primary + '10', borderColor: theme.primary + '30' },
                ]}
                onPress={() => { setSelectedWorkspace(null); setShowWorkspacePicker(false); }}
              >
                <View style={[styles.wsColorDot, { backgroundColor: theme.primary }]} />
                <View style={styles.wsOptionInfo}>
                  <Text style={[styles.wsOptionName, { color: theme.text }]}>Inteligencia Global</Text>
                  <Text style={[styles.wsOptionDesc, { color: theme.textMuted }]}>Acceso a todas tus notas y libretas</Text>
                </View>
                {!selectedWorkspace && (
                   <View style={[styles.checkCircle, { backgroundColor: theme.primary }]}>
                      <ChevronDown size={12} color="#fff" style={{ transform: [{ rotate: '-90deg' }] }} />
                   </View>
                )}
              </TouchableOpacity>

              {workspaces.map(ws => (
                <TouchableOpacity
                  key={ws.id}
                  style={[
                    styles.wsOption,
                    { borderColor: theme.border },
                    selectedWorkspace?.id === ws.id && { backgroundColor: (ws.color || theme.primary) + '10', borderColor: (ws.color || theme.primary) + '30' },
                  ]}
                  onPress={() => { setSelectedWorkspace(ws); setShowWorkspacePicker(false); }}
                >
                  <View style={[styles.wsColorDot, { backgroundColor: ws.color || theme.primary }]} />
                  <View style={styles.wsOptionInfo}>
                    <Text style={[styles.wsOptionName, { color: theme.text }]}>{ws.name}</Text>
                    {ws.description ? (
                      <Text style={[styles.wsOptionDesc, { color: theme.textMuted }]} numberOfLines={1}>
                        {ws.description}
                      </Text>
                    ) : null}
                  </View>
                  {selectedWorkspace?.id === ws.id && (
                     <View style={[styles.checkCircle, { backgroundColor: ws.color || theme.primary }]}>
                        <ChevronDown size={12} color="#fff" style={{ transform: [{ rotate: '-90deg' }] }} />
                     </View>
                  )}
                </TouchableOpacity>
              ))}
            </ScrollView>
            
            {/* Safe Area spacing for bottom indicators on Android/iOS */}
            <View style={{ height: Platform.OS === 'ios' ? 40 : 24 }} />
          </View>
        </TouchableOpacity>
      </Modal>

    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1 },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: spacing.lg,
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
  workspaceSelector: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 24,
    borderWidth: 1,
    maxWidth: 220,
    gap: 8,
  },
  wsDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  workspaceSelectorText: {
    fontSize: 13,
    fontWeight: '700',
    flex: 1,
  },
  chatArea: { flex: 1 },
  messageList: { paddingHorizontal: spacing.md, paddingBottom: spacing.xl },
  messageWrapper: {
     flexDirection: 'row',
     marginVertical: 12,
     gap: 12,
  },
  avatarCircle: {
     width: 32,
     height: 32,
     borderRadius: 16,
     justifyContent: 'center',
     alignItems: 'center',
  },
  messageContent: {
     flex: 1,
  },
  userContent: {
    alignItems: 'flex-end',
  },
  aiContent: {
    alignItems: 'flex-start',
    paddingLeft: 4,
  },
  aiHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 10,
    gap: 8,
  },
  brandBadge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 20,
    borderWidth: 1,
  },
  brandText: {
    fontSize: 9,
    fontWeight: '900',
    textTransform: 'uppercase',
    letterSpacing: 1,
  },
  modelText: {
    fontSize: 9,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 2,
    opacity: 0.5,
  },
  messageBubble: {
    borderRadius: 18,
    overflow: 'hidden',
  },
  userBubble: { 
     borderBottomRightRadius: 4,
  },
  userGradient: {
     padding: 12,
     paddingHorizontal: 16,
  },
  aiBubble: {
    width: '100%',
  },
  markdownContainer: {
    width: '100%',
    paddingRight: 10,
  },
  messageText: { fontSize: 16, lineHeight: 22, fontWeight: '500', letterSpacing: -0.2 },
  thoughtContainer: {
    marginBottom: 8,
    borderRadius: 12,
    borderWidth: 1,
    overflow: 'hidden',
    alignSelf: 'flex-start',
    width: '100%',
  },
  thoughtHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 10,
    paddingHorizontal: 12,
  },
  thoughtTitleRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  thoughtTitle: {
    fontSize: 12,
    fontWeight: '700',
    letterSpacing: 0.5,
    textTransform: 'uppercase',
  },
  thoughtBody: {
    padding: 12,
    paddingTop: 0,
    borderTopWidth: 0,
  },
  thoughtText: {
    fontSize: 13,
    lineHeight: 18,
    fontStyle: 'italic',
  },
  thinkingText: {
    fontSize: 14,
    fontStyle: 'italic',
    marginBottom: 4,
  },
  inputWrapper: {
     padding: spacing.md,
     paddingBottom: Platform.OS === 'ios' ? spacing.md : spacing.lg,
     borderTopWidth: 1,
  },
  sourcesWrapper: {
    marginTop: 12,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: 'rgba(0,0,0,0.05)',
  },
  sourcesHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  sourcesHeaderText: {
    fontSize: 10,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 1,
  },
  sourcesList: {
    flexDirection: 'row',
    flexWrap: 'wrap',
  },
  inputContainer: {
    flexDirection: 'row',
    borderRadius: 25,
    borderWidth: 1,
    paddingHorizontal: 12,
    paddingVertical: 6,
    alignItems: 'center',
  },
  input: {
    flex: 1,
    minHeight: 36,
    maxHeight: 120,
    paddingHorizontal: 8,
    paddingTop: 8,
    paddingBottom: 8,
    fontSize: 15,
    fontWeight: '500',
  },
  sendButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    justifyContent: 'center',
    alignItems: 'center',
    marginLeft: 8,
  },
  centered: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  emptyChat: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingTop: 60,
    paddingHorizontal: 40,
  },
  aiLogoContainer: {
     width: 80,
     height: 80,
     borderRadius: 40,
     borderWidth: 1,
     justifyContent: 'center',
     alignItems: 'center',
     marginBottom: 24,
  },
  emptyChatTitle: { fontSize: 22, fontWeight: '800', textAlign: 'center', marginBottom: 12 },
  emptyChatSub: { fontSize: 14, textAlign: 'center', opacity: 0.7, lineHeight: 20 },
  
  drawerOverlay: {
     position: 'absolute',
     top: 0,
     left: 0,
     right: 0,
     bottom: 0,
     backgroundColor: 'rgba(0,0,0,0.4)',
     zIndex: 1000,
  },
  threadDrawer: {
    width: 280,
    height: '100%',
    elevation: 10,
    borderRightWidth: 1,
  },
  drawerHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingTop: Platform.OS === 'ios' ? 60 : 30,
    paddingBottom: 16,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(0,0,0,0.05)',
  },
  drawerTitle: { fontSize: 18, fontWeight: '800' },
  newChatBtn: {
     padding: 6,
     borderRadius: 8,
     backgroundColor: 'rgba(0,191,255,0.1)',
  },
  threadItem: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 14,
    borderRadius: 12,
    marginVertical: 2,
  },
  threadTitle: { fontSize: 14, flex: 1 },
  
  dropdownMenu: {
    position: 'absolute',
    top: Platform.OS === 'ios' ? 100 : 60,
    right: spacing.lg,
    borderWidth: 1,
    borderRadius: 16,
    zIndex: 2000,
    padding: 6,
    minWidth: 170,
  },
  dropdownItem: {
    paddingVertical: 12,
    paddingHorizontal: 12,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(0,0,0,0.05)',
  },
  dropdownIconText: {
     flexDirection: 'row',
     alignItems: 'center',
  },
  dropdownText: { fontSize: 14, fontWeight: '600' },

  // Modal
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'flex-end',
  },
  modalSheet: {
    borderTopLeftRadius: 32,
    borderTopRightRadius: 32,
    padding: spacing.lg,
    paddingBottom: 0,
    maxHeight: '85%',
  },
  modalHandle: {
    width: 36,
    height: 4,
    borderRadius: 2,
    alignSelf: 'center',
    marginBottom: 20,
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: '800',
    marginBottom: 20,
    textAlign: 'center',
  },
  wsOption: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 14,
    borderWidth: 1,
    borderRadius: 16,
    marginBottom: 10,
    gap: 14,
  },
  wsColorDot: {
    width: 12,
    height: 12,
    borderRadius: 6,
  },
  wsOptionInfo: { flex: 1 },
  wsOptionName: { fontSize: 16, fontWeight: '700' },
  wsOptionDesc: { fontSize: 12, opacity: 0.6, marginTop: 2 },
  checkCircle: {
     width: 20,
     height: 20,
     borderRadius: 10,
     justifyContent: 'center',
     alignItems: 'center',
  }
});


