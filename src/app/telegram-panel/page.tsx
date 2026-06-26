"use client";

import React, { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import apiClient from "@/lib/api";

// --- Tipos de Datos ---
interface DocumentItem {
  file_name: string;
  topic?: string;
  size_bytes?: number;
  uploaded_at?: string;
  workspace_id?: string;
}

interface NoteItem {
  id: string;
  title: string;
  content: string;
  category?: string;
  workspace_id?: string;
  updated_at?: string;
}

interface AgendaEvent {
  id: string;
  title: string;
  description?: string;
  start_date: string;
  end_date?: string;
  status?: string;
}

interface TaskItem {
  id: string;
  description: string;
  is_completed: boolean;
  start_date?: string;
  end_date?: string;
  status?: string;
}

interface ContactProfile {
  id: string;
  first_name: string;
  last_name?: string;
  email?: string;
  phone?: string;
  occupation?: string;
}

interface WorkspaceItem {
  id: string;
  name: string;
}

type TabType = "conocimiento" | "agenda" | "notas" | "tareas" | "contactos";

function PanelContent() {
  const searchParams = useSearchParams();
  const [activeTab, setActiveTab] = useState<TabType>("conocimiento");
  const [tokenReady, setTokenReady] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // --- Estados de Datos ---
  const [workspaces, setWorkspaces] = useState<WorkspaceItem[]>([]);
  const [activeWorkspaceId, setActiveWorkspaceId] = useState<string>("");

  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [notes, setNotes] = useState<NoteItem[]>([]);
  const [events, setEvents] = useState<AgendaEvent[]>([]);
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [contacts, setContacts] = useState<ContactProfile[]>([]);

  // --- Estados de Modales / Creación ---
  const [isNoteModalOpen, setIsNoteModalOpen] = useState(false);
  const [editingNote, setEditingNote] = useState<NoteItem | null>(null);
  const [noteForm, setNoteForm] = useState({ title: "", content: "", category: "" });

  const [isEventModalOpen, setIsEventModalOpen] = useState(false);
  const [eventForm, setEventForm] = useState({ title: "", description: "", start_date: "", end_date: "" });

  const [isTaskModalOpen, setIsTaskModalOpen] = useState(false);
  const [taskForm, setTaskForm] = useState({ description: "", start_date: "", end_date: "" });

  const [isContactModalOpen, setIsContactModalOpen] = useState(false);
  const [contactForm, setContactForm] = useState({ first_name: "", last_name: "", email: "", phone: "", occupation: "" });

  const [uploadTopic, setUploadTopic] = useState("General");
  const [uploadFiles, setUploadFiles] = useState<FileList | null>(null);

  // --- Inicialización y Autenticación ---
  useEffect(() => {
    const queryToken = searchParams.get("token");
    let tokenToUse = queryToken;

    if (queryToken) {
      localStorage.setItem("authToken", queryToken);
      apiClient.defaults.headers.common["Authorization"] = `Bearer ${queryToken}`;
    } else {
      tokenToUse = localStorage.getItem("authToken");
    }

    if (!tokenToUse) {
      setError("No se detectó un token de autenticación. Por favor abre este panel desde tu bot de Telegram.");
      return;
    }

    setTokenReady(true);
  }, [searchParams]);

  // --- Cargar Workspaces al inicio ---
  useEffect(() => {
    if (!tokenReady) return;

    const fetchWorkspaces = async () => {
      try {
        const res = await apiClient.get("/api/workspaces?limit=100");
        if (Array.isArray(res.data)) {
          setWorkspaces(res.data);
        } else if (res.data && Array.isArray(res.data.workspaces)) {
          setWorkspaces(res.data.workspaces);
        }
      } catch (err) {
        console.error("Error al cargar workspaces:", err);
      }
    };
    fetchWorkspaces();
  }, [tokenReady]);

  // --- Cargar datos de la pestaña activa ---
  useEffect(() => {
    if (!tokenReady) return;

    const loadTabData = async () => {
      setLoading(true);
      setError(null);
      try {
        const params: Record<string, string> = {};
        if (activeWorkspaceId) {
          params.workspace_id = activeWorkspaceId;
        }

        if (activeTab === "conocimiento") {
          const res = await apiClient.get("/api/list-documents", { params });
          setDocuments(Array.isArray(res.data) ? res.data : []);
        } else if (activeTab === "notas") {
          const res = await apiClient.post("/api/notes/list-notes", {
            skip: 0,
            limit: 100,
            workspace_id: activeWorkspaceId || null,
          });
          setNotes(res.data?.notes || []);
        } else if (activeTab === "agenda") {
          const res = await apiClient.get("/api/agenda/events", { params });
          setEvents(Array.isArray(res.data) ? res.data : []);
        } else if (activeTab === "tareas") {
          const res = await apiClient.get("/api/tasks", { params });
          setTasks(Array.isArray(res.data) ? res.data : []);
        } else if (activeTab === "contactos") {
          const res = await apiClient.get("/api/contact-profiles");
          setContacts(Array.isArray(res.data) ? res.data : []);
        }
      } catch (err: any) {
        console.error("Error al cargar datos:", err);
        setError("Error al obtener información del servidor.");
      } finally {
        setLoading(false);
      }
    };

    loadTabData();
  }, [tokenReady, activeTab, activeWorkspaceId]);

  // --- Acciones de Conocimiento ---
  const handleUploadDocument = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFiles || uploadFiles.length === 0) return;
    setLoading(true);
    try {
      const formData = new FormData();
      formData.append("file", uploadFiles[0]);
      formData.append("topic", uploadTopic);
      if (activeWorkspaceId) {
        formData.append("workspace_id", activeWorkspaceId);
      }

      await apiClient.post("/api/upload-document", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      // Recargar
      const params = activeWorkspaceId ? { workspace_id: activeWorkspaceId } : {};
      const res = await apiClient.get("/api/list-documents", { params });
      setDocuments(Array.isArray(res.data) ? res.data : []);
      setUploadFiles(null);
      alert("¡Documento subido y procesado con éxito!");
    } catch (err) {
      console.error("Error subiendo documento:", err);
      alert("Error al subir el documento.");
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteDocument = async (fileName: string, topic?: string) => {
    if (!confirm(`¿Estás seguro de eliminar "${fileName}"?`)) return;
    setLoading(true);
    try {
      await apiClient.post("/api/delete-document", {
        file_name: fileName,
        topic: topic || "General",
        workspace_id: activeWorkspaceId || null,
      });
      setDocuments(documents.filter((d) => d.file_name !== fileName));
    } catch (err) {
      console.error("Error eliminando documento:", err);
      alert("Error al eliminar el documento.");
    } finally {
      setLoading(false);
    }
  };

  // --- Acciones de Notas ---
  const handleSaveNote = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      if (editingNote) {
        // Actualizar
        await apiClient.post("/api/update-note", {
          note_id: editingNote.id,
          title: noteForm.title,
          content: noteForm.content,
          category: noteForm.category,
          workspace_id: activeWorkspaceId || null,
        });
      } else {
        // Crear
        await apiClient.post("/api/add-note", {
          title: noteForm.title,
          content: noteForm.content,
          category: noteForm.category,
          workspace_id: activeWorkspaceId || null,
        });
      }
      setIsNoteModalOpen(false);
      setEditingNote(null);
      setNoteForm({ title: "", content: "", category: "" });

      // Recargar
      const res = await apiClient.post("/api/notes/list-notes", {
        skip: 0,
        limit: 100,
        workspace_id: activeWorkspaceId || null,
      });
      setNotes(res.data?.notes || []);
    } catch (err) {
      console.error("Error al guardar nota:", err);
      alert("Error al guardar la nota.");
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteNote = async (id: string) => {
    if (!confirm("¿Estás seguro de eliminar esta nota?")) return;
    setLoading(true);
    try {
      await apiClient.post("/api/delete-note", { note_id: id });
      setNotes(notes.filter((n) => n.id !== id));
    } catch (err) {
      console.error("Error eliminando nota:", err);
      alert("Error al eliminar la nota.");
    } finally {
      setLoading(false);
    }
  };

  const handleEditNote = (note: NoteItem) => {
    setEditingNote(note);
    setNoteForm({ title: note.title, content: note.content, category: note.category || "" });
    setIsNoteModalOpen(true);
  };

  // --- Acciones de Agenda ---
  const handleSaveEvent = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await apiClient.post("/api/add-event", {
        title: eventForm.title,
        description: eventForm.description,
        start_date: eventForm.start_date,
        end_date: eventForm.end_date || null,
        workspace_id: activeWorkspaceId || null,
      });
      setIsEventModalOpen(false);
      setEventForm({ title: "", description: "", start_date: "", end_date: "" });

      // Recargar
      const params = activeWorkspaceId ? { workspace_id: activeWorkspaceId } : {};
      const res = await apiClient.get("/api/agenda/events", { params });
      setEvents(Array.isArray(res.data) ? res.data : []);
    } catch (err) {
      console.error("Error al crear evento:", err);
      alert("Error al guardar el evento.");
    } finally {
      setLoading(false);
    }
  };

  const handleCancelEvent = async (id: string) => {
    if (!confirm("¿Estás seguro de cancelar este evento?")) return;
    setLoading(true);
    try {
      await apiClient.post("/api/cancel-event", { event_id: id });
      setEvents(events.filter((e) => e.id !== id));
    } catch (err) {
      console.error("Error al cancelar evento:", err);
      alert("Error al cancelar el evento.");
    } finally {
      setLoading(false);
    }
  };

  // --- Acciones de Tareas ---
  const handleSaveTask = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await apiClient.post("/api/tasks", {
        description: taskForm.description,
        start_date: taskForm.start_date || null,
        end_date: taskForm.end_date || null,
        workspace_id: activeWorkspaceId || null,
      });
      setIsTaskModalOpen(false);
      setTaskForm({ description: "", start_date: "", end_date: "" });

      // Recargar
      const params = activeWorkspaceId ? { workspace_id: activeWorkspaceId } : {};
      const res = await apiClient.get("/api/tasks", { params });
      setTasks(Array.isArray(res.data) ? res.data : []);
    } catch (err) {
      console.error("Error al crear tarea:", err);
      alert("Error al guardar la tarea.");
    } finally {
      setLoading(false);
    }
  };

  const handleToggleTask = async (task: TaskItem) => {
    setLoading(true);
    try {
      const nextCompleted = !task.is_completed;
      await apiClient.put(`/api/tasks/${task.id}`, {
        description: task.description,
        is_completed: nextCompleted,
        status: nextCompleted ? "Hecho" : "Pendiente",
      });
      setTasks(tasks.map((t) => (t.id === task.id ? { ...t, is_completed: nextCompleted } : t)));
    } catch (err) {
      console.error("Error al actualizar tarea:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteTask = async (id: string) => {
    if (!confirm("¿Estás seguro de eliminar esta tarea?")) return;
    setLoading(true);
    try {
      await apiClient.delete(`/api/tasks/${id}`);
      setTasks(tasks.filter((t) => t.id !== id));
    } catch (err) {
      console.error("Error al eliminar tarea:", err);
      alert("Error al eliminar la tarea.");
    } finally {
      setLoading(false);
    }
  };

  // --- Acciones de Contactos ---
  const handleSaveContact = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await apiClient.post("/api/create-contact-profile", {
        first_name: contactForm.first_name,
        last_name: contactForm.last_name || null,
        email: contactForm.email || null,
        phone: contactForm.phone || null,
        occupation: contactForm.occupation || null,
      });
      setIsContactModalOpen(false);
      setContactForm({ first_name: "", last_name: "", email: "", phone: "", occupation: "" });

      // Recargar
      const res = await apiClient.get("/api/contact-profiles");
      setContacts(Array.isArray(res.data) ? res.data : []);
    } catch (err) {
      console.error("Error al crear perfil de contacto:", err);
      alert("Error al guardar el contacto.");
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteContact = async (id: string) => {
    if (!confirm("¿Estás seguro de eliminar este perfil?")) return;
    setLoading(true);
    try {
      await apiClient.post("/api/delete-contact-profile", { profile_id: id });
      setContacts(contacts.filter((c) => c.id !== id));
    } catch (err) {
      console.error("Error al eliminar contacto:", err);
      alert("Error al eliminar el contacto.");
    } finally {
      setLoading(false);
    }
  };

  if (error && !tokenReady) {
    return (
      <div className="flex flex-col items-center justify-center p-6 bg-slate-950 text-slate-100 rounded-2xl border border-slate-800 shadow-2xl max-w-md mx-auto my-12 text-center">
        <span className="text-4xl mb-4">🔑</span>
        <h2 className="text-xl font-bold mb-2">Autenticación Requerida</h2>
        <p className="text-slate-400 text-sm">{error}</p>
      </div>
    );
  }

  return (
    <div className="w-full max-w-md mx-auto min-h-screen bg-slate-950 flex flex-col text-slate-100 pb-20 select-none">
      {/* Top Header */}
      <div className="p-4 border-b border-slate-900 bg-slate-950/60 backdrop-blur sticky top-0 z-40 flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-xl">✨</span>
            <h1 className="text-lg font-bold bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">
              Kognito Bot
            </h1>
          </div>
          {loading && (
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-indigo-400"></div>
          )}
        </div>

        {/* Workspace Selector */}
        {workspaces.length > 0 && (
          <div className="flex items-center gap-2 mt-1">
            <label className="text-xs text-slate-400 font-medium whitespace-nowrap">Workspace:</label>
            <select
              value={activeWorkspaceId}
              onChange={(e) => setActiveWorkspaceId(e.target.value)}
              className="w-full bg-slate-900 border border-slate-800 rounded-xl px-2 py-1 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            >
              <option value="">Personal (Sin Workspace)</option>
              {workspaces.map((w) => (
                <option key={w.id} value={w.id}>
                  {w.name}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* Main Panel Viewport */}
      <div className="flex-1 p-4 overflow-y-auto">
        {/* --- PESTAÑA: CONOCIMIENTOS (DOCUMENTOS) --- */}
        {activeTab === "conocimiento" && (
          <div className="flex flex-col gap-4">
            <form onSubmit={handleUploadDocument} className="bg-slate-900/40 border border-slate-800 rounded-2xl p-4 flex flex-col gap-3">
              <h3 className="text-sm font-semibold text-slate-200">Añadir Conocimiento (Subir Archivo)</h3>
              <div className="flex flex-col gap-1.5">
                <input
                  type="file"
                  onChange={(e) => setUploadFiles(e.target.files)}
                  required
                  className="w-full text-xs text-slate-400 file:mr-3 file:py-1.5 file:px-3 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-indigo-600 file:text-white hover:file:bg-indigo-500"
                />
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-xs text-slate-400 font-medium">Categoría / Tema:</label>
                <input
                  type="text"
                  value={uploadTopic}
                  onChange={(e) => setUploadTopic(e.target.value)}
                  required
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
              </div>
              <button
                type="submit"
                disabled={loading}
                className="bg-indigo-600 hover:bg-indigo-500 py-2 rounded-xl text-xs font-semibold text-white transition-all shadow-md shadow-indigo-600/10"
              >
                📤 Subir y Procesar
              </button>
            </form>

            <div className="flex flex-col gap-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">Documentos Guardados</h3>
              {documents.length > 0 ? (
                <div className="flex flex-col gap-2">
                  {documents.map((d, idx) => (
                    <div key={idx} className="bg-slate-900/40 border border-slate-800/80 rounded-2xl p-3 flex justify-between items-center gap-3">
                      <div className="flex flex-col gap-0.5 overflow-hidden">
                        <span className="text-xs font-semibold text-slate-200 truncate">{d.file_name}</span>
                        <span className="text-[10px] text-indigo-400">{d.topic || "General"}</span>
                      </div>
                      <button
                        onClick={() => handleDeleteDocument(d.file_name, d.topic)}
                        className="p-1.5 bg-slate-800 hover:bg-rose-950/20 hover:text-rose-400 rounded-xl transition-all"
                      >
                        🗑️
                      </button>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-slate-500 text-center py-6">No hay documentos guardados.</p>
              )}
            </div>
          </div>
        )}

        {/* --- PESTAÑA: NOTAS --- */}
        {activeTab === "notas" && (
          <div className="flex flex-col gap-3">
            <div className="flex justify-between items-center mb-1">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">Tus Notas</h3>
              <button
                onClick={() => {
                  setEditingNote(null);
                  setNoteForm({ title: "", content: "", category: "" });
                  setIsNoteModalOpen(true);
                }}
                className="bg-indigo-600 hover:bg-indigo-500 px-3 py-1.5 rounded-xl text-xs font-bold"
              >
                + Nota
              </button>
            </div>

            {notes.length > 0 ? (
              <div className="flex flex-col gap-2">
                {notes.map((n) => (
                  <div key={n.id} className="bg-slate-900/40 border border-slate-800/80 rounded-2xl p-3 flex flex-col gap-2 hover:border-slate-700 transition-all">
                    <div className="flex justify-between items-start">
                      <div className="flex flex-col gap-0.5">
                        <span className="text-xs font-bold text-slate-200">{n.title}</span>
                        {n.category && (
                          <span className="text-[9px] bg-slate-800 text-indigo-400 px-2 py-0.5 rounded-full w-max">
                            {n.category}
                          </span>
                        )}
                      </div>
                      <div className="flex gap-1">
                        <button
                          onClick={() => handleEditNote(n)}
                          className="p-1 bg-slate-800 hover:bg-slate-700 rounded-lg text-xs"
                        >
                          ✏️
                        </button>
                        <button
                          onClick={() => handleDeleteNote(n.id)}
                          className="p-1 bg-slate-800 hover:bg-rose-950/25 hover:text-rose-400 rounded-lg text-xs"
                        >
                          🗑️
                        </button>
                      </div>
                    </div>
                    <p className="text-xs text-slate-400 line-clamp-3 whitespace-pre-wrap">{n.content}</p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-500 text-center py-6">No hay notas guardadas.</p>
            )}
          </div>
        )}

        {/* --- PESTAÑA: AGENDA --- */}
        {activeTab === "agenda" && (
          <div className="flex flex-col gap-3">
            <div className="flex justify-between items-center mb-1">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">Próximos Eventos</h3>
              <button
                onClick={() => setIsEventModalOpen(true)}
                className="bg-indigo-600 hover:bg-indigo-500 px-3 py-1.5 rounded-xl text-xs font-bold"
              >
                + Evento
              </button>
            </div>

            {events.length > 0 ? (
              <div className="flex flex-col gap-2">
                {events.map((e) => (
                  <div key={e.id} className="bg-slate-900/40 border border-slate-800/80 rounded-2xl p-3 flex justify-between items-center gap-3">
                    <div className="flex flex-col gap-0.5 overflow-hidden">
                      <span className="text-xs font-bold text-slate-200">{e.title}</span>
                      {e.description && <span className="text-[10px] text-slate-400 truncate">{e.description}</span>}
                      <span className="text-[9px] text-indigo-400">
                        📅 {new Date(e.start_date).toLocaleString("es-ES", { dateStyle: "short", timeStyle: "short" })}
                      </span>
                    </div>
                    <button
                      onClick={() => handleCancelEvent(e.id)}
                      className="p-1.5 bg-slate-800 hover:bg-rose-950/20 hover:text-rose-400 rounded-xl transition-all"
                    >
                      🗑️
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-500 text-center py-6">No hay eventos en la agenda.</p>
            )}
          </div>
        )}

        {/* --- PESTAÑA: TAREAS --- */}
        {activeTab === "tareas" && (
          <div className="flex flex-col gap-3">
            <div className="flex justify-between items-center mb-1">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">Mis Tareas</h3>
              <button
                onClick={() => setIsTaskModalOpen(true)}
                className="bg-indigo-600 hover:bg-indigo-500 px-3 py-1.5 rounded-xl text-xs font-bold"
              >
                + Tarea
              </button>
            </div>

            {tasks.length > 0 ? (
              <div className="flex flex-col gap-2">
                {tasks.map((t) => (
                  <div key={t.id} className="bg-slate-900/40 border border-slate-800/80 rounded-2xl p-3 flex justify-between items-center gap-3">
                    <div className="flex items-center gap-3 overflow-hidden">
                      <input
                        type="checkbox"
                        checked={t.is_completed}
                        onChange={() => handleToggleTask(t)}
                        className="rounded border-slate-700 bg-slate-950 text-indigo-600 focus:ring-indigo-500 h-4 w-4"
                      />
                      <span className={`text-xs font-medium truncate ${t.is_completed ? "line-through text-slate-500" : "text-slate-200"}`}>
                        {t.description}
                      </span>
                    </div>
                    <button
                      onClick={() => handleDeleteTask(t.id)}
                      className="p-1.5 bg-slate-800 hover:bg-rose-950/20 hover:text-rose-400 rounded-xl transition-all"
                    >
                      🗑️
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-500 text-center py-6">No hay tareas pendientes.</p>
            )}
          </div>
        )}

        {/* --- PESTAÑA: CONTACTOS --- */}
        {activeTab === "contactos" && (
          <div className="flex flex-col gap-3">
            <div className="flex justify-between items-center mb-1">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">Contactos / Perfiles</h3>
              <button
                onClick={() => setIsContactModalOpen(true)}
                className="bg-indigo-600 hover:bg-indigo-500 px-3 py-1.5 rounded-xl text-xs font-bold"
              >
                + Perfil
              </button>
            </div>

            {contacts.length > 0 ? (
              <div className="flex flex-col gap-2">
                {contacts.map((c) => (
                  <div key={c.id} className="bg-slate-900/40 border border-slate-800/80 rounded-2xl p-3 flex justify-between items-center gap-3">
                    <div className="flex flex-col gap-0.5">
                      <span className="text-xs font-bold text-slate-200">
                        {c.first_name} {c.last_name || ""}
                      </span>
                      {c.occupation && <span className="text-[10px] text-indigo-400">{c.occupation}</span>}
                      {c.phone && <span className="text-[9px] text-slate-500">📞 {c.phone}</span>}
                    </div>
                    <button
                      onClick={() => handleDeleteContact(c.id)}
                      className="p-1.5 bg-slate-800 hover:bg-rose-950/20 hover:text-rose-400 rounded-xl transition-all"
                    >
                      🗑️
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-500 text-center py-6">No hay contactos guardados.</p>
            )}
          </div>
        )}
      </div>

      {/* --- FORM MODAL: NOTAS --- */}
      {isNoteModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <form onSubmit={handleSaveNote} className="bg-slate-900 border border-slate-800 rounded-3xl p-5 w-full max-w-sm flex flex-col gap-3 shadow-2xl">
            <h3 className="text-sm font-bold text-slate-200">{editingNote ? "Editar Nota" : "Nueva Nota"}</h3>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-slate-400 font-medium">Título:</label>
              <input
                type="text"
                value={noteForm.title}
                onChange={(e) => setNoteForm({ ...noteForm, title: e.target.value })}
                required
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs focus:outline-none focus:ring-1 focus:ring-indigo-500 text-slate-200"
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-slate-400 font-medium">Categoría:</label>
              <input
                type="text"
                value={noteForm.category}
                onChange={(e) => setNoteForm({ ...noteForm, category: e.target.value })}
                placeholder="Ej: Personal, Reunión..."
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs focus:outline-none focus:ring-1 focus:ring-indigo-500 text-slate-200"
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-slate-400 font-medium">Contenido:</label>
              <textarea
                value={noteForm.content}
                onChange={(e) => setNoteForm({ ...noteForm, content: e.target.value })}
                required
                rows={4}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs focus:outline-none focus:ring-1 focus:ring-indigo-500 text-slate-200 resize-none"
              />
            </div>
            <div className="flex gap-2 justify-end mt-2">
              <button
                type="button"
                onClick={() => setIsNoteModalOpen(false)}
                className="px-4 py-2 bg-slate-850 hover:bg-slate-800 rounded-xl text-xs font-semibold"
              >
                Cancelar
              </button>
              <button
                type="submit"
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-xl text-xs font-semibold text-white shadow-lg shadow-indigo-600/20"
              >
                Guardar
              </button>
            </div>
          </form>
        </div>
      )}

      {/* --- FORM MODAL: EVENTOS --- */}
      {isEventModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <form onSubmit={handleSaveEvent} className="bg-slate-900 border border-slate-800 rounded-3xl p-5 w-full max-w-sm flex flex-col gap-3 shadow-2xl">
            <h3 className="text-sm font-bold text-slate-200">Nuevo Evento</h3>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-slate-400 font-medium">Título del Evento:</label>
              <input
                type="text"
                value={eventForm.title}
                onChange={(e) => setEventForm({ ...eventForm, title: e.target.value })}
                required
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs focus:outline-none focus:ring-1 focus:ring-indigo-500 text-slate-200"
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-slate-400 font-medium">Descripción:</label>
              <input
                type="text"
                value={eventForm.description}
                onChange={(e) => setEventForm({ ...eventForm, description: e.target.value })}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs focus:outline-none focus:ring-1 focus:ring-indigo-500 text-slate-200"
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-slate-400 font-medium">Fecha y Hora de Inicio:</label>
              <input
                type="datetime-local"
                value={eventForm.start_date}
                onChange={(e) => setEventForm({ ...eventForm, start_date: e.target.value })}
                required
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs focus:outline-none focus:ring-1 focus:ring-indigo-500 text-slate-200"
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-slate-400 font-medium">Fecha y Hora de Término (Opcional):</label>
              <input
                type="datetime-local"
                value={eventForm.end_date}
                onChange={(e) => setEventForm({ ...eventForm, end_date: e.target.value })}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs focus:outline-none focus:ring-1 focus:ring-indigo-500 text-slate-200"
              />
            </div>
            <div className="flex gap-2 justify-end mt-2">
              <button
                type="button"
                onClick={() => setIsEventModalOpen(false)}
                className="px-4 py-2 bg-slate-850 hover:bg-slate-800 rounded-xl text-xs font-semibold"
              >
                Cancelar
              </button>
              <button
                type="submit"
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-xl text-xs font-semibold text-white shadow-lg shadow-indigo-600/20"
              >
                Guardar
              </button>
            </div>
          </form>
        </div>
      )}

      {/* --- FORM MODAL: TAREAS --- */}
      {isTaskModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <form onSubmit={handleSaveTask} className="bg-slate-900 border border-slate-800 rounded-3xl p-5 w-full max-w-sm flex flex-col gap-3 shadow-2xl">
            <h3 className="text-sm font-bold text-slate-200">Nueva Tarea</h3>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-slate-400 font-medium">Descripción de la Tarea:</label>
              <input
                type="text"
                value={taskForm.description}
                onChange={(e) => setTaskForm({ ...taskForm, description: e.target.value })}
                required
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs focus:outline-none focus:ring-1 focus:ring-indigo-500 text-slate-200"
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-slate-400 font-medium">Fecha de Inicio (Opcional):</label>
              <input
                type="date"
                value={taskForm.start_date}
                onChange={(e) => setTaskForm({ ...taskForm, start_date: e.target.value })}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs focus:outline-none focus:ring-1 focus:ring-indigo-500 text-slate-200"
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-slate-400 font-medium">Fecha de Vencimiento (Opcional):</label>
              <input
                type="date"
                value={taskForm.end_date}
                onChange={(e) => setTaskForm({ ...taskForm, end_date: e.target.value })}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs focus:outline-none focus:ring-1 focus:ring-indigo-500 text-slate-200"
              />
            </div>
            <div className="flex gap-2 justify-end mt-2">
              <button
                type="button"
                onClick={() => setIsTaskModalOpen(false)}
                className="px-4 py-2 bg-slate-850 hover:bg-slate-800 rounded-xl text-xs font-semibold"
              >
                Cancelar
              </button>
              <button
                type="submit"
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-xl text-xs font-semibold text-white shadow-lg shadow-indigo-600/20"
              >
                Guardar
              </button>
            </div>
          </form>
        </div>
      )}

      {/* --- FORM MODAL: CONTACTOS --- */}
      {isContactModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <form onSubmit={handleSaveContact} className="bg-slate-900 border border-slate-800 rounded-3xl p-5 w-full max-w-sm flex flex-col gap-3 shadow-2xl">
            <h3 className="text-sm font-bold text-slate-200">Nuevo Perfil</h3>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-slate-400 font-medium">Nombre:</label>
              <input
                type="text"
                value={contactForm.first_name}
                onChange={(e) => setContactForm({ ...contactForm, first_name: e.target.value })}
                required
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs focus:outline-none focus:ring-1 focus:ring-indigo-500 text-slate-200"
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-slate-400 font-medium">Apellido (Opcional):</label>
              <input
                type="text"
                value={contactForm.last_name}
                onChange={(e) => setContactForm({ ...contactForm, last_name: e.target.value })}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs focus:outline-none focus:ring-1 focus:ring-indigo-500 text-slate-200"
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-slate-400 font-medium">Email (Opcional):</label>
              <input
                type="email"
                value={contactForm.email}
                onChange={(e) => setContactForm({ ...contactForm, email: e.target.value })}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs focus:outline-none focus:ring-1 focus:ring-indigo-500 text-slate-200"
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-slate-400 font-medium">Teléfono (Opcional):</label>
              <input
                type="text"
                value={contactForm.phone}
                onChange={(e) => setContactForm({ ...contactForm, phone: e.target.value })}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs focus:outline-none focus:ring-1 focus:ring-indigo-500 text-slate-200"
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-slate-400 font-medium">Ocupación (Opcional):</label>
              <input
                type="text"
                value={contactForm.occupation}
                onChange={(e) => setContactForm({ ...contactForm, occupation: e.target.value })}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs focus:outline-none focus:ring-1 focus:ring-indigo-500 text-slate-200"
              />
            </div>
            <div className="flex gap-2 justify-end mt-2">
              <button
                type="button"
                onClick={() => setIsContactModalOpen(false)}
                className="px-4 py-2 bg-slate-850 hover:bg-slate-800 rounded-xl text-xs font-semibold"
              >
                Cancelar
              </button>
              <button
                type="submit"
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-xl text-xs font-semibold text-white shadow-lg shadow-indigo-600/20"
              >
                Guardar
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Navigation Tab Bar (Bottom sticky) */}
      <div className="fixed bottom-0 left-0 right-0 max-w-md mx-auto bg-slate-950/80 backdrop-blur-lg border-t border-slate-900 p-2 flex justify-around items-center z-40">
        <button
          onClick={() => setActiveTab("conocimiento")}
          className={`flex flex-col items-center gap-1 text-[10px] font-semibold transition-all ${activeTab === "conocimiento" ? "text-indigo-400 scale-105" : "text-slate-500 hover:text-slate-300"}`}
        >
          <span className="text-lg">📚</span>
          <span>Saber</span>
        </button>
        <button
          onClick={() => setActiveTab("agenda")}
          className={`flex flex-col items-center gap-1 text-[10px] font-semibold transition-all ${activeTab === "agenda" ? "text-indigo-400 scale-105" : "text-slate-500 hover:text-slate-300"}`}
        >
          <span className="text-lg">🗓️</span>
          <span>Agenda</span>
        </button>
        <button
          onClick={() => setActiveTab("notas")}
          className={`flex flex-col items-center gap-1 text-[10px] font-semibold transition-all ${activeTab === "notas" ? "text-indigo-400 scale-105" : "text-slate-500 hover:text-slate-300"}`}
        >
          <span className="text-lg">📝</span>
          <span>Notas</span>
        </button>
        <button
          onClick={() => setActiveTab("tareas")}
          className={`flex flex-col items-center gap-1 text-[10px] font-semibold transition-all ${activeTab === "tareas" ? "text-indigo-400 scale-105" : "text-slate-500 hover:text-slate-300"}`}
        >
          <span className="text-lg">✅</span>
          <span>Tareas</span>
        </button>
        <button
          onClick={() => setActiveTab("contactos")}
          className={`flex flex-col items-center gap-1 text-[10px] font-semibold transition-all ${activeTab === "contactos" ? "text-indigo-400 scale-105" : "text-slate-500 hover:text-slate-300"}`}
        >
          <span className="text-lg">👥</span>
          <span>Perfiles</span>
        </button>
      </div>
    </div>
  );
}

export default function TelegramPanelPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-slate-950 flex flex-col justify-center items-center text-slate-400">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500 mb-4"></div>
        <p className="text-sm">Iniciando panel...</p>
      </div>
    }>
      <PanelContent />
    </Suspense>
  );
}
