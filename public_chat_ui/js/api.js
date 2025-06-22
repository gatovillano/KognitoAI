// public_chat_ui/js/api.js

export const API_BASE_URL = 'https://apibase.gatoslibres.art'; 

export const authToken = localStorage.getItem('kognito_auth_token');

let statusMessageElement = null;

export const setStatusMessageElement = (elementId) => {
    statusMessageElement = document.getElementById(elementId);
    if (!statusMessageElement) {
        console.warn(`Elemento #${elementId} para mensajes de estado no encontrado.`);
    }
};

export const showStatus = (message, isError = true) => {
    if (!statusMessageElement) {
        console.warn('Elemento de mensaje de estado no configurado. El mensaje no se mostrará en la UI.');
        return;
    }
    statusMessageElement.textContent = message;
    statusMessageElement.className = 'status-message';
    statusMessageElement.style.display = message ? 'block' : 'none';
    if (message) {
        statusMessageElement.classList.add(isError ? 'error' : 'success');
    }
};

export const handleAuthSuccess = (data) => {
    if (data.access_token) {
        localStorage.setItem('kognito_auth_token', data.access_token);
        window.location.href = 'chat.html';
    } else {
        showStatus(data.detail || 'Ocurrió un error inesperado al autenticar.');
    }
};

/**
 * Función genérica para realizar peticiones POST a la API.
 * @param {string} endpoint - La ruta específica de la API.
 * @param {object} payload - El cuerpo de la petición (objeto JSON).
 * @param {boolean} requiresAuth - Si la petición requiere un token de autenticación (por defecto, sí).
 * @returns {Promise<object>} - La respuesta JSON del servidor.
 */
export async function apiPost(endpoint, payload, requiresAuth = true) {
    const headers = { 'Content-Type': 'application/json' };
    if (requiresAuth && authToken) {
        headers['Authorization'] = `Bearer ${authToken}`;
    }

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: 'POST', // Método POST
        headers: headers,
        body: JSON.stringify(payload),
    });

    const data = await response.json();
    if (!response.ok) {
        throw new Error(data.detail || `Error en la petición POST a ${endpoint}`);
    }
    return data;
}

/**
 * Función genérica para realizar peticiones GET a la API.
 * @param {string} endpoint - La ruta específica de la API.
 * @param {boolean} requiresAuth - Si la petición requiere un token de autenticación (por defecto, sí).
 * @returns {Promise<object>} - La respuesta JSON del servidor.
 */
export async function apiGet(endpoint, requiresAuth = true) {
    const headers = {};
    if (requiresAuth && authToken) {
        headers['Authorization'] = `Bearer ${authToken}`;
    }

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: 'GET', // Método GET
        headers: headers,
    });

    const data = await response.json();
    if (!response.ok) {
        throw new Error(data.detail || `Error en la petición GET a ${endpoint}`);
    }
    return data;
}

/**
 * Función para subir archivos a la API (utiliza FormData).
 * @param {string} endpoint - La ruta específica de la API.
 * @param {FormData} formData - El objeto FormData que contiene los archivos y otros campos.
 * @param {boolean} requiresAuth - Si la petición requiere un token de autenticación (por defecto, sí).
 * @returns {Promise<object>} - La respuesta JSON del servidor.
 */
export async function apiUpload(endpoint, formData, requiresAuth = true) {
    const headers = {};
    if (requiresAuth && authToken) {
        headers['Authorization'] = `Bearer ${authToken}`;
    }

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: 'POST',
        headers: headers,
        body: formData,
    });

    const data = await response.json();
    if (!response.ok) {
        throw new Error(data.detail || `Error en la subida a ${endpoint}`);
    }
    return data;
}

/**
 * Elimina un hilo de chat por su ID.
 * @param {string} threadId - El ID del hilo a eliminar.
 * @returns {Promise<void>} Lanza error si falla.
 */
export async function apiDeleteThread(threadId) {
    const resp = await fetch(`${API_BASE_URL}/api/threads/${threadId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${authToken}` }
    });
    if (!resp.ok && resp.status !== 204) {
        throw new Error('No se pudo eliminar el chat.');
    }
}

export async function streamLLMResponse(userMessage, threadId, onChunk) {
    const response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${authToken}` },
        body: JSON.stringify({ user_message: userMessage, thread_id: threadId })
    });
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let result = '';
    while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        const text = decoder.decode(value);
        result += text;
        if (onChunk) onChunk(result, text);
    }
    return result;
}

export const API_ENDPOINTS = {
    login: `/api/auth/login`,
    register: `/api/auth/register`,
    telegramCallback: `/api/auth/telegram/callback`,
    requestCode: `/api/auth/request-code`,
    verifyCode: `/api/auth/verify-code`,
    getUserProfile: `/api/users/me`, // Este será GET
    listThreads: `/api/threads`, // Este será GET
    createThread: `/api/threads`, // Este será POST
    getMessages: (threadId) => `/api/threads/${threadId}/messages`, // Este será GET
    chat: `/api/chat`, // Este será POST
    uploadDocuments: `/api/upload-document`, // Este será POST
    getSystemPrompt: `/api/get-system-prompt`, // Este será GET (para panel Telegram WebApp)
    saveSystemPrompt: `/api/save-system-prompt`, // Este será POST (para panel Telegram WebApp)
    listDocuments: `/api/list-documents`, // Este será GET (para panel Telegram WebApp)
    deleteDocument: `/api/delete-document`, // Este será POST (para panel Telegram WebApp)
    listNotes: `/api/list-notes`, // Este será GET (para panel Telegram WebApp)
    addNote: `/api/add-note`, // Este será POST (para panel Telegram WebApp)
    updateNote: `/api/update-note`, // Este será POST (para panel Telegram WebApp)
    deleteNote: `/api/delete-note`, // Este será POST (para panel Telegram WebApp)
    listEvents: `/api/list-events`, // Este será GET (para panel Telegram WebApp)
    addEvent: `/api/add-event`, // Este será POST (para panel Telegram WebApp)
    cancelEvent: `/api/cancel-event`, // Este será POST (para panel Telegram WebApp)
    getThread: (threadId) => `/api/threads/${threadId}`,
};