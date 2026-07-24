'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import apiClient from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import {
  MessageSquare,
  Users,
  Bot,
  Sparkles,
  Plus,
  Send,
  Search,
  UserCheck,
  CheckCircle2,
  RefreshCw,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface UserSummary {
  id: string;
  name?: string;
  username?: string;
  email?: string;
}

interface Participant {
  account_id: string;
  name?: string;
  username?: string;
  email?: string;
  joined_at: string;
}

interface Message {
  id: string;
  room_id: string;
  sender_id?: string | null;
  sender_name: string;
  content: string;
  is_kai: boolean;
  created_at: string;
}

interface Room {
  id: string;
  name?: string;
  is_group: boolean;
  created_by_id?: string;
  created_at: string;
  updated_at: string;
  participants: Participant[];
  last_message?: Message | null;
}

export default function KognitoChatPanel() {
  const { user } = useAuth();
  const [rooms, setRooms] = useState<Room[]>([]);
  const [activeRoomId, setActiveRoomId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState<string>('');
  const [loadingRooms, setLoadingRooms] = useState<boolean>(true);
  const [loadingMessages, setLoadingMessages] = useState<boolean>(false);
  const [sending, setSending] = useState<boolean>(false);

  // Modal para nuevo chat
  const [showNewChatModal, setShowNewChatModal] = useState<boolean>(false);
  const [availableUsers, setAvailableUsers] = useState<UserSummary[]>([]);
  const [selectedUserIds, setSelectedUserIds] = useState<string[]>([]);
  const [groupName, setGroupName] = useState<string>('');
  const [isGroup, setIsGroup] = useState<boolean>(false);
  const [searchUser, setSearchUser] = useState<string>('');

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);

  // Auto-scroll al final del chat
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Cargar salas al iniciar
  const fetchRooms = async () => {
    setLoadingRooms(true);
    try {
      const res = await apiClient.get<Room[]>('/api/kognito-chat/rooms');
      setRooms(res.data);
      if (res.data.length > 0 && !activeRoomId) {
        setActiveRoomId(res.data[0].id);
      }
    } catch (err) {
      console.error('Error cargando salas de KognitoChat:', err);
    } finally {
      setLoadingRooms(false);
    }
  };

  useEffect(() => {
    fetchRooms();
  }, []);

  // Cargar mensajes cuando cambia la sala activa
  useEffect(() => {
    if (!activeRoomId) return;

    const fetchMessages = async () => {
      setLoadingMessages(true);
      try {
        const res = await apiClient.get<Message[]>(`/api/kognito-chat/rooms/${activeRoomId}/messages`);
        setMessages(res.data);
      } catch (err) {
        console.error('Error cargando mensajes:', err);
      } finally {
        setLoadingMessages(false);
      }
    };

    fetchMessages();

    // Establecer WebSocket en tiempo real para esta sala
    if (wsRef.current) {
      wsRef.current.close();
    }

    const token = localStorage.getItem('access_token') || localStorage.getItem('token') || '';
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/api/kognito-chat/ws/${activeRoomId}?token=${encodeURIComponent(token)}`;

    try {
      const ws = new WebSocket(wsUrl);
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'new_message' && data.message) {
            setMessages((prev) => {
              if (prev.some((m) => m.id === data.message.id)) return prev;
              return [...prev, data.message];
            });
            // Actualizar lista de salas
            fetchRooms();
          }
        } catch (e) {
          console.error('Error parseando evento de WebSocket:', e);
        }
      };

      wsRef.current = ws;
    } catch (e) {
      console.error('Error abriendo conexión de WebSocket:', e);
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [activeRoomId]);

  // Cargar usuarios disponibles para iniciar chats
  const fetchAvailableUsers = async () => {
    try {
      const res = await apiClient.get<UserSummary[]>('/api/kognito-chat/users');
      setAvailableUsers(res.data);
    } catch (err) {
      console.error('Error buscando usuarios:', err);
    }
  };

  const handleOpenNewChat = () => {
    fetchAvailableUsers();
    setSelectedUserIds([]);
    setGroupName('');
    setIsGroup(false);
    setShowNewChatModal(true);
  };

  const handleCreateRoom = async () => {
    if (selectedUserIds.length === 0) return;
    try {
      const res = await apiClient.post<Room>('/api/kognito-chat/rooms', {
        participant_ids: selectedUserIds,
        name: isGroup ? groupName || 'Chat de Grupo' : undefined,
        is_group: isGroup,
      });

      setShowNewChatModal(false);
      await fetchRooms();
      setActiveRoomId(res.data.id);
    } catch (err) {
      console.error('Error creando sala:', err);
    }
  };

  // Enviar mensaje
  const handleSendMessage = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!inputText.trim() || !activeRoomId || sending) return;

    const contentToSend = inputText;
    setInputText('');
    setSending(true);

    try {
      const res = await apiClient.post<Message>(`/api/kognito-chat/rooms/${activeRoomId}/messages`, {
        content: contentToSend,
      });

      // Añadir localmente si aún no fue recibido vía WS
      setMessages((prev) => {
        if (prev.some((m) => m.id === res.data.id)) return prev;
        return [...prev, res.data];
      });

      fetchRooms();
    } catch (err) {
      console.error('Error enviando mensaje:', err);
    } finally {
      setSending(false);
    }
  };

  // Botón para pedir resumen a KAI
  const handleSummarizeWithKAI = () => {
    setInputText((prev) => (prev ? `${prev} @KAI` : '@KAI por favor resume esta conversación'));
  };

  const activeRoom = rooms.find((r) => r.id === activeRoomId);

  const getRoomDisplayName = (room: Room) => {
    if (room.is_group && room.name) return room.name;
    const otherParticipants = room.participants.filter((p) => p.account_id !== user?.id);
    if (otherParticipants.length === 0) return 'Chat Personal';
    return otherParticipants.map((p) => p.name || p.username || 'Usuario').join(', ');
  };

  return (
    <div className="flex h-[calc(100vh-4rem)] bg-background text-foreground rounded-lg border shadow-sm overflow-hidden">
      {/* BARRA LATERAL DE CHATS */}
      <div className="w-80 border-r border-border flex flex-col bg-muted/20">
        {/* Cabecera de la barra lateral */}
        <div className="p-4 border-b border-border flex items-center justify-between">
          <div className="flex items-center gap-2 font-semibold text-lg text-primary">
            <MessageSquare className="w-5 h-5 text-indigo-500" />
            <span>KognitoChat</span>
          </div>
          <Button size="sm" onClick={handleOpenNewChat} className="bg-indigo-600 hover:bg-indigo-700 text-white gap-1">
            <Plus className="w-4 h-4" />
            Nuevo
          </Button>
        </div>

        {/* Lista de salas */}
        <div className="flex-1 overflow-y-auto divide-y divide-border/40">
          {loadingRooms ? (
            <div className="p-8 text-center text-muted-foreground flex flex-col items-center gap-2">
              <RefreshCw className="w-5 h-5 animate-spin text-indigo-500" />
              <span>Cargando chats...</span>
            </div>
          ) : rooms.length === 0 ? (
            <div className="p-8 text-center text-muted-foreground">
              <Users className="w-10 h-10 mx-auto mb-2 opacity-40 text-indigo-400" />
              <p className="text-sm font-medium">Sin chats activos</p>
              <p className="text-xs mt-1">Inicia una conversación con cualquier usuario de la instancia.</p>
            </div>
          ) : (
            rooms.map((room) => {
              const isActive = room.id === activeRoomId;
              const displayName = getRoomDisplayName(room);
              const lastMsg = room.last_message;

              return (
                <button
                  key={room.id}
                  onClick={() => setActiveRoomId(room.id)}
                  className={`w-full p-3.5 text-left flex items-start gap-3 transition-colors ${
                    isActive ? 'bg-indigo-50/70 dark:bg-indigo-950/40 border-l-4 border-indigo-600' : 'hover:bg-muted/50'
                  }`}
                >
                  <Avatar className="w-10 h-10 border border-indigo-200 dark:border-indigo-800">
                    <AvatarFallback className="bg-indigo-100 dark:bg-indigo-900 text-indigo-700 dark:text-indigo-300 font-bold">
                      {displayName.substring(0, 2).toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                  <div className="flex-1 min-w-0">
                    <div className="flex justify-between items-baseline">
                      <h4 className="font-semibold text-sm truncate text-foreground">{displayName}</h4>
                      {lastMsg && (
                        <span className="text-[10px] text-muted-foreground ml-2 shrink-0">
                          {new Date(lastMsg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground truncate mt-0.5">
                      {lastMsg ? (
                        <span>
                          <strong className="font-medium text-foreground">{lastMsg.sender_name}:</strong> {lastMsg.content}
                        </span>
                      ) : (
                        <span className="italic text-xs opacity-75">Sin mensajes aún</span>
                      )}
                    </p>
                  </div>
                </button>
              );
            })
          )}
        </div>
      </div>

      {/* ÁREA PRINCIPAL DEL CHAT */}
      {activeRoom ? (
        <div className="flex-1 flex flex-col h-full bg-background">
          {/* Cabecera del chat activo */}
          <div className="p-4 border-b border-border flex items-center justify-between bg-card/50">
            <div className="flex items-center gap-3">
              <Avatar className="w-9 h-9 border border-indigo-300">
                <AvatarFallback className="bg-indigo-600 text-white font-bold">
                  {getRoomDisplayName(activeRoom).substring(0, 2).toUpperCase()}
                </AvatarFallback>
              </Avatar>
              <div>
                <h3 className="font-bold text-base text-foreground leading-tight">{getRoomDisplayName(activeRoom)}</h3>
                <p className="text-xs text-muted-foreground flex items-center gap-1.5 mt-0.5">
                  <Users className="w-3 h-3 text-indigo-500" />
                  <span>{activeRoom.participants.length} participante(s)</span>
                  <span className="text-border">•</span>
                  <span className="text-indigo-600 dark:text-indigo-400 font-medium flex items-center gap-1">
                    <Sparkles className="w-3 h-3" /> Escribe @KAI para invocar la IA
                  </span>
                </p>
              </div>
            </div>

            {/* Acciones rápidas */}
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={handleSummarizeWithKAI}
                className="text-xs border-indigo-300 dark:border-indigo-700 text-indigo-600 dark:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-950/60 gap-1.5"
              >
                <Bot className="w-3.5 h-3.5 text-indigo-500" />
                Resumir con @KAI
              </Button>
            </div>
          </div>

          {/* Hilo de mensajes */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-muted/10">
            {loadingMessages ? (
              <div className="flex justify-center items-center h-full text-muted-foreground gap-2">
                <RefreshCw className="w-5 h-5 animate-spin text-indigo-500" />
                <span>Cargando mensajes...</span>
              </div>
            ) : messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-center text-muted-foreground p-6">
                <Sparkles className="w-12 h-12 text-indigo-400 opacity-60 mb-2" />
                <h4 className="font-semibold text-foreground">Comienza la conversación</h4>
                <p className="text-xs max-w-sm mt-1">
                  Escribe un mensaje para los miembros del chat o usa <span className="font-mono text-indigo-600 font-bold">@KAI</span> para pedir ayuda al agente.
                </p>
              </div>
            ) : (
              messages.map((msg) => {
                const isMe = msg.sender_id === user?.id;
                const isKAI = msg.is_kai;

                if (isKAI) {
                  return (
                    <div key={msg.id} className="flex gap-3 my-3">
                      <div className="w-9 h-9 rounded-full bg-gradient-to-tr from-indigo-600 to-purple-600 flex items-center justify-center text-white shadow-md shrink-0">
                        <Bot className="w-5 h-5" />
                      </div>
                      <div className="flex-1 max-w-2xl bg-card border-2 border-indigo-500/30 dark:border-indigo-500/40 rounded-2xl rounded-tl-none p-4 shadow-sm relative">
                        <div className="flex items-center gap-2 mb-1.5">
                          <span className="font-bold text-xs bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
                            KAI Agent
                          </span>
                          <span className="text-[10px] bg-indigo-100 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300 font-semibold px-2 py-0.5 rounded-full flex items-center gap-1">
                            <Sparkles className="w-2.5 h-2.5" /> IA Respuesta
                          </span>
                          <span className="text-[10px] text-muted-foreground ml-auto">
                            {new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </span>
                        </div>
                        <div className="text-sm prose dark:prose-invert max-w-none text-foreground leading-relaxed">
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                        </div>
                      </div>
                    </div>
                  );
                }

                return (
                  <div key={msg.id} className={`flex gap-3 ${isMe ? 'justify-end' : 'justify-start'}`}>
                    {!isMe && (
                      <Avatar className="w-8 h-8 shrink-0 mt-1">
                        <AvatarFallback className="bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300 text-xs font-semibold">
                          {msg.sender_name.substring(0, 2).toUpperCase()}
                        </AvatarFallback>
                      </Avatar>
                    )}
                    <div
                      className={`max-w-xl rounded-2xl p-3.5 shadow-sm text-sm ${
                        isMe
                          ? 'bg-indigo-600 text-white rounded-tr-none'
                          : 'bg-card border border-border text-card-foreground rounded-tl-none'
                      }`}
                    >
                      {!isMe && <p className="text-[11px] font-bold text-indigo-500 mb-1">{msg.sender_name}</p>}
                      <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                      <span className={`block text-[10px] mt-1 text-right ${isMe ? 'text-indigo-200' : 'text-muted-foreground'}`}>
                        {new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                  </div>
                );
              })
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Formulario para enviar mensaje */}
          <form onSubmit={handleSendMessage} className="p-3 border-t border-border bg-card flex items-center gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setInputText((prev) => `${prev} @KAI `)}
              className="text-xs border-indigo-300 text-indigo-600 dark:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-950 font-bold px-2.5"
            >
              @KAI
            </Button>
            <Input
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Escribe un mensaje... (Menciona a @KAI para consultar a la IA)"
              className="flex-1 text-sm bg-background border-border focus-visible:ring-indigo-500"
              disabled={sending}
            />
            <Button type="submit" disabled={!inputText.trim() || sending} className="bg-indigo-600 hover:bg-indigo-700 text-white px-4">
              <Send className="w-4 h-4" />
            </Button>
          </form>
        </div>
      ) : (
        <div className="flex-1 flex flex-col items-center justify-center text-center p-8 bg-background">
          <MessageSquare className="w-16 h-16 text-indigo-400 opacity-40 mb-3" />
          <h3 className="text-xl font-bold text-foreground">Selecciona o Inicia un Chat</h3>
          <p className="text-sm text-muted-foreground max-w-md mt-1 mb-4">
            Comunícate en tiempo real con los usuarios de tu misma instancia de KognitoAI.
          </p>
          <Button onClick={handleOpenNewChat} className="bg-indigo-600 hover:bg-indigo-700 text-white gap-2">
            <Plus className="w-4 h-4" />
            Crear Nuevo Chat
          </Button>
        </div>
      )}

      {/* MODAL PARA NUEVO CHAT */}
      {showNewChatModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-card text-card-foreground border border-border rounded-xl shadow-2xl max-w-md w-full p-6 space-y-4">
            <h3 className="text-lg font-bold text-foreground flex items-center gap-2">
              <Users className="w-5 h-5 text-indigo-500" />
              Nuevo Chat de KognitoAI
            </h3>

            {/* Toggle Tipo de Chat */}
            <div className="flex gap-2 p-1 bg-muted rounded-lg">
              <button
                type="button"
                onClick={() => setIsGroup(false)}
                className={`flex-1 py-1.5 text-xs font-semibold rounded-md transition-all ${
                  !isGroup ? 'bg-background text-indigo-600 shadow-sm' : 'text-muted-foreground'
                }`}
              >
                Chat Individual (1 a 1)
              </button>
              <button
                type="button"
                onClick={() => setIsGroup(true)}
                className={`flex-1 py-1.5 text-xs font-semibold rounded-md transition-all ${
                  isGroup ? 'bg-background text-indigo-600 shadow-sm' : 'text-muted-foreground'
                }`}
              >
                Chat de Grupo
              </button>
            </div>

            {/* Nombre del grupo si aplica */}
            {isGroup && (
              <div>
                <label className="text-xs font-medium text-muted-foreground mb-1 block">Nombre del Grupo</label>
                <Input
                  value={groupName}
                  onChange={(e) => setGroupName(e.target.value)}
                  placeholder="Ej. Proyecto Innovación AI"
                  className="text-sm"
                />
              </div>
            )}

            {/* Buscador de Usuarios */}
            <div className="space-y-2">
              <label className="text-xs font-medium text-muted-foreground block">
                Selecciona {isGroup ? 'uno o varios usuarios' : 'un usuario'}:
              </label>
              <div className="relative">
                <Search className="w-4 h-4 absolute left-3 top-2.5 text-muted-foreground" />
                <Input
                  value={searchUser}
                  onChange={(e) => setSearchUser(e.target.value)}
                  placeholder="Buscar usuario por nombre o email..."
                  className="pl-9 text-xs"
                />
              </div>

              <div className="max-h-48 overflow-y-auto divide-y divide-border border rounded-md p-1 mt-2">
                {availableUsers.filter((u) =>
                  (u.name || u.username || u.email || '').toLowerCase().includes(searchUser.toLowerCase())
                ).length === 0 ? (
                  <p className="p-3 text-xs text-center text-muted-foreground">No se encontraron usuarios disponibles.</p>
                ) : (
                  availableUsers
                    .filter((u) => (u.name || u.username || u.email || '').toLowerCase().includes(searchUser.toLowerCase()))
                    .map((u) => {
                      const isSelected = selectedUserIds.includes(u.id);

                      const toggleSelect = () => {
                        if (isGroup) {
                          if (isSelected) {
                            setSelectedUserIds(selectedUserIds.filter((id) => id !== u.id));
                          } else {
                            setSelectedUserIds([...selectedUserIds, u.id]);
                          }
                        } else {
                          setSelectedUserIds([u.id]);
                        }
                      };

                      return (
                        <button
                          key={u.id}
                          type="button"
                          onClick={toggleSelect}
                          className={`w-full p-2.5 text-left flex items-center justify-between text-xs rounded-md transition-colors ${
                            isSelected ? 'bg-indigo-50 dark:bg-indigo-950/60 font-semibold' : 'hover:bg-muted'
                          }`}
                        >
                          <div>
                            <p className="text-foreground font-medium">{u.name || u.username || 'Usuario sin nombre'}</p>
                            <p className="text-[10px] text-muted-foreground">{u.email}</p>
                          </div>
                          {isSelected && <CheckCircle2 className="w-4 h-4 text-indigo-600" />}
                        </button>
                      );
                    })
                )}
              </div>
            </div>

            {/* Acciones */}
            <div className="flex justify-end gap-2 pt-2 border-t border-border">
              <Button variant="ghost" size="sm" onClick={() => setShowNewChatModal(false)}>
                Cancelar
              </Button>
              <Button
                size="sm"
                disabled={selectedUserIds.length === 0}
                onClick={handleCreateRoom}
                className="bg-indigo-600 hover:bg-indigo-700 text-white"
              >
                Crear Chat
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
