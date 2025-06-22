// public_chat_ui/js/chat_history_module.js

import { API_ENDPOINTS, apiPost, apiGet, apiDeleteThread } from './api.js'; // Importamos apiGet
import { displayMessage, scrollToBottom, animateText } from './ui_helpers.js'; // Asegúrate de que displayMessage y scrollToBottom estén disponibles

// Elementos DOM del historial de chats
let chatHistoryList = null; // Se seleccionará en initChatHistoryModule
let newChatBtn = null; // Se seleccionará en initChatHistoryModule
let chatHistoryLoader = null; // Se seleccionará en initChatHistoryModule

let currentThreadId = null; // Variable interna para almacenar el ID del hilo de conversación actual

/**
 * Establece el ID del hilo de chat actual y actualiza la UI.
 * También carga los mensajes de ese hilo.
 * @param {string} threadId - El ID del hilo de chat a seleccionar.
 */
export async function selectChatThreadUI(threadId) {
    // Si el hilo ya está seleccionado, solo resalta visualmente y no recarga mensajes
    if (currentThreadId === threadId) {
        // Refresca la selección visual
        document.querySelectorAll('#chat-history-list li').forEach(li => {
            li.classList.remove('active');
        });
        const selectedThreadElement = document.querySelector(`[data-thread-id="${threadId}"]`);
        if (selectedThreadElement) {
            selectedThreadElement.classList.add('active');
        }
        return; // No recargar mensajes ni limpiar ventana
    }

    // Eliminar la clase 'active' de todos los hilos
    document.querySelectorAll('#chat-history-list li').forEach(li => {
        li.classList.remove('active');
    });

    // Añadir la clase 'active' al hilo seleccionado
    const selectedThreadElement = document.querySelector(`[data-thread-id="${threadId}"]`);
    if (selectedThreadElement) {
        selectedThreadElement.classList.add('active');
    }

    currentThreadId = threadId; // Establecer el hilo actual
    await loadMessagesForThread(threadId); // Cargar los mensajes de ese hilo

    // Opcional: Si el sidebar se abre en móvil al seleccionar, cerrarlo.
    const sidebar = document.querySelector('.sidebar');
    if (sidebar && sidebar.classList.contains('open')) {
        sidebar.classList.remove('open');
    }
}

/**
 * Obtiene el ID del hilo de chat actualmente seleccionado.
 * @returns {string|null} El ID del hilo actual, o null si no hay ninguno.
 */
export function getCurrentThreadId() {
    return currentThreadId;
}

/**
 * Carga el historial de mensajes para un hilo específico y los muestra en la ventana de chat.
 * @param {string} threadId - El ID del hilo cuyos mensajes se cargarán.
 */
async function loadMessagesForThread(threadId) {
    if (!chatHistoryList) return;

    try {
        // Usar apiGet para cargar mensajes de un hilo
        const messages = await apiGet(API_ENDPOINTS.getMessages(threadId));

        const chatWindowElement = document.getElementById('chat-window');
        if (chatWindowElement) chatWindowElement.innerHTML = ''; // Limpiar ventana de chat

        if (messages.length === 0) {
            displayMessage('¡Hola! Soy Kognito AI. ¿En qué puedo ayudarte hoy?', 'ai');
        } else {
            messages.forEach(msg => {
                displayMessage(msg.text, msg.sender); // Corrige para usar las claves correctas
            });
        }
        scrollToBottom();
    } catch (error) {
        console.error("Error al cargar mensajes del hilo:", error);
        displayMessage('Ocurrió un error al cargar los mensajes de este chat.', 'ai');
    }
}


/**
 * Carga la lista de hilos de chat del usuario y los muestra en la sidebar.
 */
export async function loadChatHistory() {
    if (!chatHistoryList) return;

    if (chatHistoryLoader) chatHistoryLoader.style.display = 'block'; // Mostrar loader
    chatHistoryList.innerHTML = ''; // Limpiar lista actual

    try {
        // Usar apiGet para listar los hilos de chat
        const threads = await apiGet(API_ENDPOINTS.listThreads);
        let foundCurrent = false;
        if (threads.length === 0) {
            chatHistoryList.innerHTML = '<li>Aún no tienes chats guardados.</li>';
        } else {
            threads.forEach(thread => {
                const li = document.createElement('li');
                li.className = 'chat-thread-item';
                // Contenedor de título y botón
                const titleSpan = document.createElement('span');
                titleSpan.className = 'thread-title';
                if (thread.id === currentThreadId && thread.animatedTitle) {
                    animateText(titleSpan, thread.title);
                } else {
                    titleSpan.textContent = thread.title;
                }
                titleSpan.addEventListener('click', () => selectChatThreadUI(thread.id));

                // Botón eliminar
                const deleteBtn = document.createElement('button');
                deleteBtn.className = 'delete-thread-btn';
                deleteBtn.title = 'Eliminar conversación';
                deleteBtn.innerHTML = '🗑️';
                deleteBtn.addEventListener('click', async (e) => {
                    e.stopPropagation();
                    if (confirm('¿Seguro que quieres eliminar esta conversación?')) {
                        try {
                            await apiDeleteThread(thread.id);
                            li.remove();
                            // Si el hilo eliminado era el actual, limpiar ventana y resetear currentThreadId
                            if (getCurrentThreadId() === thread.id) {
                                const chatWindow = document.getElementById('chat-window');
                                if (chatWindow) chatWindow.innerHTML = '';
                                currentThreadId = null;
                            }
                        } catch (err) {
                            alert('Error al eliminar el chat: ' + (err.message || err));
                        }
                    }
                });

                li.appendChild(titleSpan);
                li.appendChild(deleteBtn);
                li.dataset.threadId = thread.id;
                chatHistoryList.appendChild(li);
                if (thread.id === currentThreadId) foundCurrent = true;
            });
            // Seleccionar el hilo actual si existe, si no el primero
            if (!foundCurrent && threads.length > 0) {
                currentThreadId = threads[0].id;
                await selectChatThreadUI(currentThreadId);
            } else if (foundCurrent) {
                // Refresca visualmente la selección
                const selectedThreadElement = document.querySelector(`[data-thread-id="${currentThreadId}"]`);
                if (selectedThreadElement) selectedThreadElement.classList.add('active');
            }
        }
    } catch (error) {
        console.error("Error al cargar el historial de chats:", error);
        // Si hay un error, mostrar un mensaje claro al usuario
        const errorItem = document.createElement('li');
        errorItem.textContent = 'Error al cargar el historial.';
        chatHistoryList.appendChild(errorItem);
    } finally {
        if (chatHistoryLoader) chatHistoryLoader.style.display = 'none'; // Ocultar loader
    }
}

/**
 * Crea un nuevo hilo de chat y lo selecciona.
 */
export async function createNewChat() {
    try {
        const newThread = await apiPost(API_ENDPOINTS.createThread, {}); // Crear hilo usa POST
        currentThreadId = newThread.id; // Establecer el nuevo como actual
        await loadChatHistory(); // Recargar el historial para que aparezca el nuevo chat
        await selectChatThreadUI(newThread.id); // Seleccionar el nuevo explícitamente
        displayMessage('¡Hola! Soy Kognito AI. ¿En qué puedo ayudarte en este nuevo chat?', 'ai');
    } catch (error) {
        console.error("Error al crear nuevo chat:", error);
        displayMessage('Lo siento, no pude crear un nuevo chat en este momento.', 'ai');
    }
}

/**
 * Refresca el título del hilo actual, animándolo si ha cambiado.
 */
export async function refreshCurrentThreadTitle() {
    // Recarga solo el hilo actual y anima el título si cambió
    if (!currentThreadId) return;
    try {
        const thread = await apiGet(API_ENDPOINTS.getThread(currentThreadId));
        // Buscar el elemento en la lista
        const li = document.querySelector(`[data-thread-id="${currentThreadId}"]`);
        if (li) {
            const titleSpan = li.querySelector('.thread-title');
            if (titleSpan && thread.title !== titleSpan.textContent) {
                // Siempre animar el título si es distinto
                animateText(titleSpan, thread.title);
                // Forzar actualización del texto al terminar la animación
                setTimeout(() => { titleSpan.textContent = thread.title; }, thread.title.length * 30 + 100);
            }
        }
    } catch (e) {
        // Silencioso
    }
}

/**
 * Inicializa los event listeners para el módulo de historial de chat y selecciona los elementos DOM.
 */
export function initChatHistoryModule() {
    // Seleccionar elementos DOM dentro de la función de inicialización
    chatHistoryList = document.getElementById('chat-history-list');
    newChatBtn = document.getElementById('new-chat-btn');
    chatHistoryLoader = chatHistoryList ? chatHistoryList.querySelector('.loader') : null;

    if (newChatBtn) {
        newChatBtn.addEventListener('click', createNewChat);
    }
    loadChatHistory(); // Cargar el historial al iniciar el módulo
}