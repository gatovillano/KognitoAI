'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import apiClient from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  DropdownMenuLabel,
} from '@/components/ui/dropdown-menu';
import {
  MessageSquare,
  Users,
  Bot,
  Sparkles,
  Plus,
  Send,
  Search,
  CheckCircle2,
  RefreshCw,
  Video,
  Radio,
  Presentation,
  Volume2,
  Copy,
  Check,
  GitFork,
  Clock,
  UserCheck,
  UserX,
  Shield,
  X,
  ChevronDown,
  ExternalLink,
  Share2,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { KognitoNativeVideoCall } from '@/components/KognitoNativeVideoCall';

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
  status: string; // 'active' | 'waiting_in_lobby' | 'rejected'
  role: string;   // 'host' | 'participant' | 'listener'
  joined_at: string;
}

interface Message {
  id: string;
  room_id: string;
  sender_id?: string;
  sender_name: string;
  content: string;
  is_kai: boolean;
  created_at: string;
}

interface Room {
  id: string;
  name?: string;
  is_group: boolean;
  room_type?: string;
  active_document_id?: string | null;
  parent_room_id?: string | null;
  created_by_id?: string;
  created_at: string;
  updated_at: string;
  participants: Participant[];
  last_message?: Message;
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
  const [copiedHeaderLink, setCopiedHeaderLink] = useState<boolean>(false);

  // Sub-salas
  const [subrooms, setSubrooms] = useState<Room[]>([]);
  const [showSubroomModal, setShowSubroomModal] = useState<boolean>(false);
  const [subroomName, setSubroomName] = useState<string>('');

  // Estado para videollamada nativa WebRTC (Nextcloud Talk Style)
  const [activeCall, setActiveCall] = useState<boolean>(false);
  const [incomingCall, setIncomingCall] = useState<{ callerName: string; senderAccountId: string } | null>(null);

  // Modal para nuevo chat
  const [showNewChatModal, setShowNewChatModal] = useState<boolean>(false);
  const [availableUsers, setAvailableUsers] = useState<UserSummary[]>([]);
  const [selectedUserIds, setSelectedUserIds] = useState<string[]>([]);
  const [groupName, setGroupName] = useState<string>('');
  const [isGroup, setIsGroup] = useState<boolean>(false);
  const [searchUser, setSearchUser] = useState<string>('');
  const [selectedRoomType, setSelectedRoomType] = useState<string>('default');

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

  // Detectar par de consulta URL (?join=ID o ?room=ID) para unirse automáticamente mediante enlace
  useEffect(() => {
    if (typeof window === 'undefined') return;
    const params = new URLSearchParams(window.location.search);
    const joinId = params.get('join') || params.get('room');
    if (joinId) {
      apiClient
        .post<Room>(`/api/kognito-chat/rooms/${joinId}/join`)
        .then((res) => {
          fetchRooms();
          setActiveRoomId(res.data.id);
        })
        .catch((err) => console.error('Error uniéndose a la sala por enlace:', err));
    }
  }, []);

  // Cargar sub-salas pertenecientes a la sala activa
  const fetchSubrooms = async (roomId: string) => {
    try {
      const res = await apiClient.get<Room[]>(`/api/kognito-chat/rooms/${roomId}/subrooms`);
      setSubrooms(res.data || []);
    } catch (e) {
      console.error('Error buscando sub-salas:', e);
    }
  };

  // Cargar mensajes y sub-salas cuando cambia la sala activa
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
    fetchSubrooms(activeRoomId);

    // Establecer WebSocket en tiempo real para esta sala
    if (wsRef.current) {
      wsRef.current.close();
    }

    try {
      const apiHost = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8889';
      const cleanHost = apiHost.replace(/^https?:\/\//, '');
      const wsProtocol = apiHost.startsWith('https') ? 'wss:' : 'ws:';
      const token = typeof window !== 'undefined' ? localStorage.getItem('authToken') : null;

      const wsUrl = `${wsProtocol}//${cleanHost}/api/kognito-chat/ws/${activeRoomId}${token ? `?token=${encodeURIComponent(token)}` : ''}`;
      const ws = new WebSocket(wsUrl);

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          if (data.type === 'new_message' && data.message) {
            setMessages((prev) => {
              if (prev.some((m) => m.id === data.message.id)) return prev;
              return [...prev, data.message];
            });
          } else if (data.type === 'kai_stream_start') {
            setMessages((prev) => [
              ...prev,
              {
                id: data.message_id,
                room_id: activeRoomId,
                sender_name: 'KAI',
                content: '',
                is_kai: true,
                created_at: new Date().toISOString(),
              },
            ]);
          } else if (data.type === 'kai_stream_chunk') {
            setMessages((prev) =>
              prev.map((m) => {
                if (m.id === data.message_id) {
                  return { ...m, content: m.content + data.chunk };
                }
                return m;
              })
            );
          } else if (data.type === 'lobby_user_joined' || data.type === 'lobby_user_admitted' || data.type === 'lobby_user_rejected') {
            fetchRooms();
          } else if (data.type === 'subroom_created') {
            fetchSubrooms(activeRoomId);
          } else if (data.type === 'call_initiate' && data.sender_account_id !== user?.id) {
            setIncomingCall({
              callerName: data.caller_name || 'Un participante',
              senderAccountId: data.sender_account_id,
            });
          } else if (data.type === 'call_end') {
            setActiveCall(false);
            setIncomingCall(null);
          }
        } catch (e) {
          console.error('Error procesando mensaje WS:', e);
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
  }, [activeRoomId, user?.id]);

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
    setSelectedRoomType('default');
    setShowNewChatModal(true);
  };

  const handleCreateRoom = async () => {
    try {
      const res = await apiClient.post<Room>('/api/kognito-chat/rooms', {
        participant_ids: selectedUserIds,
        name: isGroup ? groupName || 'Chat de Grupo' : (selectedUserIds.length === 0 ? groupName || undefined : undefined),
        is_group: isGroup || selectedUserIds.length === 0,
        room_type: selectedRoomType,
      });

      setShowNewChatModal(false);
      await fetchRooms();
      setActiveRoomId(res.data.id);
    } catch (err) {
      console.error('Error creando sala:', err);
    }
  };

  // Crear Sub-sala
  const handleCreateSubroom = async () => {
    if (!activeRoomId || !subroomName.trim()) return;
    try {
      const res = await apiClient.post<Room>(`/api/kognito-chat/rooms/${activeRoomId}/subrooms`, {
        name: subroomName,
        room_type: 'default',
      });
      setShowSubroomModal(false);
      setSubroomName('');
      await fetchSubrooms(activeRoomId);
      setActiveRoomId(res.data.id);
    } catch (e) {
      console.error('Error creando sub-sala:', e);
    }
  };

  // Moderar usuario en Sala de Espera (Lobby)
  const handleLobbyAction = async (participantAccountId: string, action: 'admit' | 'reject') => {
    if (!activeRoomId) return;
    try {
      await apiClient.post(`/api/kognito-chat/rooms/${activeRoomId}/lobby/${participantAccountId}`, { action });
      await fetchRooms();
    } catch (e) {
      console.error('Error moderando sala de espera:', e);
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
      await apiClient.post<Message>(`/api/kognito-chat/rooms/${activeRoomId}/messages`, {
        content: contentToSend,
      });
    } catch (err) {
      console.error('Error enviando mensaje:', err);
      setInputText(contentToSend);
    } finally {
      setSending(false);
    }
  };

  // Iniciar videollamada nativa WebRTC
  const handleStartNativeVideoCall = async () => {
    if (!activeRoomId) return;
    setActiveCall(true);
    try {
      await apiClient.post(`/api/kognito-chat/rooms/${activeRoomId}/messages`, {
        content: `📹 **${user?.name || user?.username || 'Un usuario'}** ha iniciado una videollamada nativa en esta sala.`,
      });
    } catch (e) {
      console.error('Error enviando notificación de llamada al chat:', e);
    }
  };

  // Copiar Enlace de Sala
  const handleCopyHeaderLink = () => {
    if (!activeRoomId) return;
    const url = `${window.location.origin}/kognito-chat?join=${activeRoomId}`;
    navigator.clipboard.writeText(url);
    setCopiedHeaderLink(true);
    setTimeout(() => setCopiedHeaderLink(false), 2500);
  };

  // Botón para pedir resumen a KAI
  const handleSummarizeWithKAI = () => {
    setInputText((prev) => (prev ? `${prev} @KAI` : '@KAI por favor resume esta conversación'));
  };

  const activeRoom = rooms.find((r) => r.id === activeRoomId);
  const currentParticipant = activeRoom?.participants.find((p) => p.account_id === user?.id);
  const isInLobby = currentParticipant?.status === 'waiting_in_lobby';
  const isHost = activeRoom?.created_by_id === user?.id || currentParticipant?.role === 'host';
  const waitingParticipants = activeRoom?.participants.filter((p) => p.status === 'waiting_in_lobby') || [];

  const getRoomDisplayName = (room: Room) => {
    if (room.is_group && room.name) return room.name;
    const otherParticipants = room.participants.filter((p) => p.account_id !== user?.id);
    if (otherParticipants.length > 0) {
      const other = otherParticipants[0];
      return other.name || other.username || other.email || 'Usuario';
    }
    return room.name || 'Sala Pública Compartible';
  };

  return (
    <div className="flex h-[calc(100vh-4rem)] bg-background overflow-hidden border rounded-xl shadow-sm">
      {/* BARRA LATERAL: LISTA DE SALAS */}
      <div className="w-80 border-r border-border flex flex-col bg-muted/20">
        <div className="p-4 border-b border-border flex items-center justify-between">
          <div className="flex items-center gap-2">
            <MessageSquare className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
            <h2 className="font-bold text-lg text-foreground">KognitoChat</h2>
          </div>
          <Button onClick={handleOpenNewChat} size="sm" className="bg-indigo-600 hover:bg-indigo-700 text-white gap-1 text-xs">
            <Plus className="w-4 h-4" />
            Nuevo Chat
          </Button>
        </div>

        {/* Lista de Chats */}
        <div className="flex-1 overflow-y-auto divide-y divide-border/50">
          {loadingRooms ? (
            <div className="flex justify-center items-center h-32 text-muted-foreground gap-2">
              <RefreshCw className="w-4 h-4 animate-spin" />
              <span className="text-xs">Cargando conversaciones...</span>
            </div>
          ) : rooms.length === 0 ? (
            <div className="p-6 text-center text-muted-foreground text-xs space-y-2">
              <p>No tienes conversaciones activas.</p>
              <Button onClick={handleOpenNewChat} variant="outline" size="sm" className="text-xs">
                Iniciar un chat
              </Button>
            </div>
          ) : (
            rooms.map((room) => {
              const displayName = getRoomDisplayName(room);
              const isActive = room.id === activeRoomId;
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
                      <h4 className="font-semibold text-sm truncate text-foreground flex items-center gap-1.5">
                        <span>{displayName}</span>
                        {room.room_type === 'webinar' && <Badge className="bg-purple-600 text-[9px] px-1 py-0">Webinar</Badge>}
                      </h4>
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
                <h3 className="font-bold text-base text-foreground leading-tight flex items-center gap-2">
                  <span>{getRoomDisplayName(activeRoom)}</span>
                  {activeRoom.room_type && (
                    <Badge className="bg-indigo-600 text-white uppercase text-[9px] font-mono">
                      {activeRoom.room_type}
                    </Badge>
                  )}
                </h3>
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

            {/* MENÚ DE ACCIONES Y COMPARTIR */}
            <div className="flex items-center gap-2">
              {/* Botón Compartir Rápido */}
              <Button
                variant="outline"
                size="sm"
                onClick={handleCopyHeaderLink}
                className="text-xs border-indigo-300 dark:border-indigo-700 text-indigo-600 dark:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-950/60 gap-1.5 font-medium"
                title="Copiar enlace de webinar o sala pública para invitados"
              >
                {copiedHeaderLink ? (
                  <>
                    <Check className="w-3.5 h-3.5 text-emerald-500" />
                    <span>¡Enlace copiado!</span>
                  </>
                ) : (
                  <>
                    <Share2 className="w-3.5 h-3.5 text-indigo-500" />
                    <span className="hidden sm:inline">Compartir</span>
                  </>
                )}
              </Button>

              {/* Dropdown Acciones Unificado */}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="default" size="sm" className="text-xs bg-indigo-600 hover:bg-indigo-700 text-white gap-1.5 font-semibold shadow-sm">
                    <span>Acciones</span>
                    <ChevronDown className="w-3.5 h-3.5" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-60">
                  <DropdownMenuLabel className="text-[10px] uppercase font-bold text-muted-foreground tracking-wider">Acciones de Sala</DropdownMenuLabel>

                  <DropdownMenuItem onClick={handleStartNativeVideoCall} className="gap-2 cursor-pointer py-2 font-medium text-xs">
                    <Video className="w-4 h-4 text-emerald-500" />
                    <div>
                      <p className="font-semibold text-foreground">Iniciar Videollamada</p>
                      <p className="text-[10px] text-muted-foreground">Transmisión nativa WebRTC</p>
                    </div>
                  </DropdownMenuItem>

                  <DropdownMenuItem onClick={handleCopyHeaderLink} className="gap-2 cursor-pointer py-2 font-medium text-xs">
                    {copiedHeaderLink ? (
                      <Check className="w-4 h-4 text-emerald-500" />
                    ) : (
                      <Share2 className="w-4 h-4 text-indigo-500" />
                    )}
                    <div>
                      <p className="font-semibold text-foreground">Compartir Enlace Webinar</p>
                      <p className="text-[10px] text-muted-foreground">Link directo para invitados sin login</p>
                    </div>
                  </DropdownMenuItem>

                  <DropdownMenuItem
                    onClick={() => { if (activeRoomId) window.open(`/join/${activeRoomId}`, '_blank'); }}
                    className="gap-2 cursor-pointer py-2 font-medium text-xs"
                  >
                    <ExternalLink className="w-4 h-4 text-purple-500" />
                    <div>
                      <p className="font-semibold text-foreground">Abrir Página de Invitados</p>
                      <p className="text-[10px] text-muted-foreground">Formulario pre-join para webinar</p>
                    </div>
                  </DropdownMenuItem>

                  <DropdownMenuSeparator />
                  <DropdownMenuLabel className="text-[10px] uppercase font-bold text-muted-foreground tracking-wider">Colaboración</DropdownMenuLabel>

                  <DropdownMenuItem onClick={() => setShowSubroomModal(true)} className="gap-2 cursor-pointer py-2 font-medium text-xs">
                    <GitFork className="w-4 h-4 text-indigo-500" />
                    <div>
                      <p className="font-semibold text-foreground">Crear Sub-sala</p>
                      <p className="text-[10px] text-muted-foreground">Grupo derivado de la sesión</p>
                    </div>
                  </DropdownMenuItem>

                  <DropdownMenuSeparator />
                  <DropdownMenuLabel className="text-[10px] uppercase font-bold text-muted-foreground tracking-wider">Asistente IA</DropdownMenuLabel>

                  <DropdownMenuItem onClick={handleSummarizeWithKAI} className="gap-2 cursor-pointer py-2 font-medium text-xs">
                    <Bot className="w-4 h-4 text-indigo-500" />
                    <div>
                      <p className="font-semibold text-foreground">Resumir con @KAI</p>
                      <p className="text-[10px] text-muted-foreground">Sintetizar la conversación</p>
                    </div>
                  </DropdownMenuItem>

                  <DropdownMenuItem
                    onClick={() => setInputText('@KAI ')}
                    className="gap-2 cursor-pointer py-2 font-medium text-xs"
                  >
                    <Sparkles className="w-4 h-4 text-purple-500" />
                    <div>
                      <p className="font-semibold text-foreground">Consultar a @KAI</p>
                      <p className="text-[10px] text-muted-foreground">Mencionar al asistente</p>
                    </div>
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>

          {/* BARRA DE SUB-SALAS DISPONIBLES */}
          {subrooms.length > 0 && (
            <div className="px-4 py-2 bg-indigo-50/50 dark:bg-indigo-950/30 border-b border-indigo-200 dark:border-indigo-900 flex items-center gap-2 overflow-x-auto text-xs">
              <span className="font-semibold text-indigo-700 dark:text-indigo-300 flex items-center gap-1 shrink-0">
                <GitFork className="w-3.5 h-3.5" /> Sub-salas activas:
              </span>
              {subrooms.map((sub) => (
                <Button
                  key={sub.id}
                  variant={sub.id === activeRoomId ? 'secondary' : 'outline'}
                  size="sm"
                  onClick={() => setActiveRoomId(sub.id)}
                  className="h-6 text-[10px] px-2.5 rounded-full"
                >
                  {sub.name}
                </Button>
              ))}
            </div>
          )}

          {/* BARRA DE MODERACIÓN DE SALA DE ESPERA (LOBBY PARA EL ANFITRIÓN) */}
          {isHost && waitingParticipants.length > 0 && (
            <div className="p-3 bg-purple-900/20 border-b border-purple-500/30 flex items-center justify-between">
              <div className="flex items-center gap-2 text-xs text-purple-300">
                <Clock className="w-4 h-4 text-purple-400 animate-pulse" />
                <span>
                  <strong>{waitingParticipants.length} usuario(s)</strong> esperando en la Sala de Espera (Lobby).
                </span>
              </div>
              <div className="flex items-center gap-2">
                {waitingParticipants.map((p) => (
                  <div key={p.account_id} className="flex items-center gap-1 bg-background border border-border px-2 py-1 rounded-md text-xs">
                    <span className="font-medium">{p.name || p.username || 'Invitado'}</span>
                    <Button size="icon" variant="ghost" onClick={() => handleLobbyAction(p.account_id, 'admit')} className="h-5 w-5 text-emerald-500 hover:bg-emerald-950">
                      <UserCheck className="w-3.5 h-3.5" />
                    </Button>
                    <Button size="icon" variant="ghost" onClick={() => handleLobbyAction(p.account_id, 'reject')} className="h-5 w-5 text-rose-500 hover:bg-rose-950">
                      <UserX className="w-3.5 h-3.5" />
                    </Button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* PANTALLA DE SALA DE ESPERA (LOBBY) PARA INVITADOS */}
          {isInLobby ? (
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-center bg-background space-y-4">
              <div className="w-16 h-16 rounded-full bg-purple-500/20 border-2 border-purple-500 flex items-center justify-center animate-pulse">
                <Clock className="w-8 h-8 text-purple-400" />
              </div>
              <div>
                <h3 className="text-xl font-bold text-foreground">Estás en la Sala de Espera (Lobby)</h3>
                <p className="text-sm text-muted-foreground max-w-md mt-1">
                  El anfitrión del Webinar debe aprobar tu solicitud antes de ingresar al chat y videollamada.
                </p>
              </div>
              <Badge variant="secondary" className="bg-purple-950 text-purple-300 border-purple-500/30">
                Esperando autorización del anfitrión...
              </Badge>
            </div>
          ) : (
            /* HILO DE MENSAJES (RENDERIZADO COMPLETO EN MARKDOWN) */
            <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-muted/10">
              {loadingMessages ? (
                <div className="flex justify-center items-center h-full text-muted-foreground gap-2">
                  <RefreshCw className="w-5 h-5 animate-spin text-indigo-500" />
                  <span className="text-sm">Cargando historial...</span>
                </div>
              ) : messages.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-muted-foreground text-center space-y-2">
                  <MessageSquare className="w-12 h-12 stroke-1 text-muted-foreground/50" />
                  <p className="text-sm font-medium">Esta sala aún no tiene mensajes.</p>
                  <p className="text-xs">¡Escribe tu primer mensaje o menciona a <strong>@KAI</strong> para consultar al asistente de IA!</p>
                </div>
              ) : (
                messages.map((msg) => {
                  const isMe = msg.sender_id === user?.id;
                  const isKai = msg.is_kai;

                  return (
                    <div key={msg.id} className={`flex flex-col ${isMe ? 'items-end' : 'items-start'}`}>
                      <div className="flex items-center gap-1.5 mb-1 px-1">
                        <span className="text-xs font-semibold text-foreground flex items-center gap-1">
                          {isKai && <Bot className="w-3.5 h-3.5 text-indigo-500 inline" />}
                          {msg.sender_name}
                        </span>
                        <span className="text-[10px] text-muted-foreground">
                          {new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>

                      <div
                        className={`max-w-[75%] p-3 rounded-2xl text-sm leading-relaxed shadow-sm ${
                          isMe
                            ? 'bg-indigo-600 text-white rounded-tr-none'
                            : isKai
                            ? 'bg-indigo-950/20 border border-indigo-500/30 text-foreground rounded-tl-none'
                            : 'bg-card border border-border text-foreground rounded-tl-none'
                        }`}
                      >
                        {/* RENDERIZADO MARKDOWN COMPLETO PARA TODOS LOS MENSAJES */}
                        <div className={`prose text-xs max-w-none break-words ${isMe ? 'prose-invert text-white' : 'dark:prose-invert text-foreground'}`}>
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
              <div ref={messagesEndRef} />
            </div>
          )}

          {/* Caja de Entrada de Texto */}
          {!isInLobby && (
            <form onSubmit={handleSendMessage} className="p-3 border-t border-border bg-card flex items-center gap-2">
              <Input
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                placeholder="Escribe tu mensaje en Markdown... (Menciona a @KAI para consultar la IA)"
                className="flex-1 text-sm bg-background border-border"
                disabled={sending}
              />
              <Button
                type="submit"
                disabled={!inputText.trim() || sending}
                className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 shrink-0 gap-1.5"
              >
                <Send className="w-4 h-4" />
                <span>Enviar</span>
              </Button>
            </form>
          )}
        </div>
      ) : (
        <div className="flex-1 flex flex-col items-center justify-center p-8 text-center bg-background">
          <Avatar className="w-20 h-20 mb-4 border border-indigo-300">
            <AvatarFallback className="bg-indigo-100 text-indigo-600 text-2xl font-bold">KC</AvatarFallback>
          </Avatar>
          <h3 className="text-xl font-bold text-foreground">Bienvenido a KognitoChat</h3>
          <p className="text-sm text-muted-foreground max-w-sm mt-1 mb-6">
            Comunícate en tiempo real con usuarios de tu organización, realiza videollamadas nativas y consulta a tu asistente KAI.
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
                Chat de Grupo / Sala Pública
              </button>
            </div>

            {/* SELECCIÓN DEL TIPO DE CONVERSACIÓN (ESTILO NEXTCLOUD TALK) */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-muted-foreground block">
                Tipo de conversación:
              </label>
              <div className="grid grid-cols-2 gap-2">
                {/* 1. Predeterminado */}
                <div
                  onClick={() => setSelectedRoomType('default')}
                  className={`p-2.5 border rounded-xl cursor-pointer transition-all ${
                    selectedRoomType === 'default'
                      ? 'border-indigo-600 bg-indigo-50/50 dark:bg-indigo-950/40 font-medium ring-2 ring-indigo-500/20'
                      : 'border-border hover:bg-muted/40'
                  }`}
                >
                  <div className="flex items-center gap-1.5 text-xs font-bold text-foreground">
                    <MessageSquare className="w-3.5 h-3.5 text-indigo-500" />
                    <span>Predeterminado</span>
                  </div>
                  <p className="text-[10px] text-muted-foreground mt-1 leading-tight">
                    Envía mensajes, crea hilos e inicia llamadas de voz y video.
                  </p>
                </div>

                {/* 2. Webinar */}
                <div
                  onClick={() => setSelectedRoomType('webinar')}
                  className={`p-2.5 border rounded-xl cursor-pointer transition-all ${
                    selectedRoomType === 'webinar'
                      ? 'border-purple-600 bg-purple-50/50 dark:bg-purple-950/40 font-medium ring-2 ring-purple-500/20'
                      : 'border-border hover:bg-muted/40'
                  }`}
                >
                  <div className="flex items-center gap-1.5 text-xs font-bold text-foreground">
                    <Radio className="w-3.5 h-3.5 text-purple-500" />
                    <span>Webinar</span>
                  </div>
                  <p className="text-[10px] text-muted-foreground mt-1 leading-tight">
                    Conversación restringida con sala de espera (Lobby) para invitados.
                  </p>
                </div>

                {/* 3. Presentación */}
                <div
                  onClick={() => setSelectedRoomType('presentation')}
                  className={`p-2.5 border rounded-xl cursor-pointer transition-all ${
                    selectedRoomType === 'presentation'
                      ? 'border-blue-600 bg-blue-50/50 dark:bg-blue-950/40 font-medium ring-2 ring-blue-500/20'
                      : 'border-border hover:bg-muted/40'
                  }`}
                >
                  <div className="flex items-center gap-1.5 text-xs font-bold text-foreground">
                    <Presentation className="w-3.5 h-3.5 text-blue-500" />
                    <span>Presentación</span>
                  </div>
                  <p className="text-[10px] text-muted-foreground mt-1 leading-tight">
                    Presentaciones internas con carga directa de documentos OnlyOffice/Drive.
                  </p>
                </div>

                {/* 4. Voice Room */}
                <div
                  onClick={() => setSelectedRoomType('voice_room')}
                  className={`p-2.5 border rounded-xl cursor-pointer transition-all ${
                    selectedRoomType === 'voice_room'
                      ? 'border-emerald-600 bg-emerald-50/50 dark:bg-emerald-950/40 font-medium ring-2 ring-emerald-500/20'
                      : 'border-border hover:bg-muted/40'
                  }`}
                >
                  <div className="flex items-center gap-1.5 text-xs font-bold text-foreground">
                    <Volume2 className="w-3.5 h-3.5 text-emerald-500" />
                    <span>Voice room</span>
                  </div>
                  <p className="text-[10px] text-muted-foreground mt-1 leading-tight">
                    Únete directamente a la llamada solo de voz, ideal para reuniones breves.
                  </p>
                </div>
              </div>
            </div>

            {/* Nombre del grupo si aplica */}
            {(isGroup || selectedUserIds.length === 0) && (
              <div>
                <label className="text-xs font-medium text-muted-foreground mb-1 block">Nombre de la Sala (opcional)</label>
                <Input
                  value={groupName}
                  onChange={(e) => setGroupName(e.target.value)}
                  placeholder="Ej. Reunión Estratégica AI"
                  className="text-sm"
                />
              </div>
            )}

            {/* Buscador de Usuarios */}
            <div className="space-y-2">
              <label className="text-xs font-medium text-muted-foreground block">
                Invitar usuarios ahora (opcional):
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
                onClick={handleCreateRoom}
                className="bg-indigo-600 hover:bg-indigo-700 text-white"
              >
                {selectedUserIds.length === 0 ? 'Crear Sala por Enlace' : 'Crear Chat'}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL PARA CREAR SUB-SALA */}
      {showSubroomModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-xl shadow-2xl max-w-sm w-full p-6 space-y-4">
            <h3 className="text-lg font-bold flex items-center gap-2">
              <GitFork className="w-5 h-5 text-indigo-500" />
              Crear Sub-sala (Breakout Room)
            </h3>
            <p className="text-xs text-muted-foreground">
              Las sub-salas permiten dividir a los participantes en grupos de trabajo secundarios sin salir de la reunión principal.
            </p>
            <div>
              <label className="text-xs font-medium mb-1 block">Nombre de la Sub-sala</label>
              <Input
                value={subroomName}
                onChange={(e) => setSubroomName(e.target.value)}
                placeholder="Ej. Grupo 1 - Discusión Técnica"
                className="text-sm"
              />
            </div>
            <div className="flex justify-end gap-2 pt-2 border-t border-border">
              <Button variant="ghost" size="sm" onClick={() => setShowSubroomModal(false)}>
                Cancelar
              </Button>
              <Button size="sm" onClick={handleCreateSubroom} disabled={!subroomName.trim()} className="bg-indigo-600 hover:bg-indigo-700 text-white">
                Crear Sub-sala
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* COMPONENTE DE VIDEOLLAMADA NATIVA WEBRTC (NEXTCLOUD TALK STYLE) */}
      {(activeCall || incomingCall) && activeRoom && (
        <KognitoNativeVideoCall
          roomId={activeRoom.id}
          roomName={getRoomDisplayName(activeRoom)}
          roomType={activeRoom.room_type}
          activeDocumentId={activeRoom.active_document_id}
          currentUserId={user?.id || ''}
          currentUserName={user?.name || user?.username || 'Usuario'}
          ws={wsRef.current}
          incomingCallData={incomingCall}
          onClose={() => {
            setActiveCall(false);
            setIncomingCall(null);
          }}
        />
      )}
    </div>
  );
}
