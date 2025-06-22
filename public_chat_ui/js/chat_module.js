// public_chat_ui/js/chat_module.js

import { API_ENDPOINTS, apiPost, apiGet, authToken, streamLLMResponse, API_BASE_URL } from './api.js'; // Importamos apiGet
import { displayMessage, scrollToBottom, adjustTextareaHeight, setChatElements, setTheme, initThemeSwitcher } from './ui_helpers.js';
import { initChatHistoryModule, loadChatHistory, createNewChat, selectChatThreadUI, getCurrentThreadId, refreshCurrentThreadTitle } from './chat_history_module.js';
import { initDocumentUploadModule, showUploadModal, setCurrentUserData as setDocUploadUserData } from './document_upload_module.js';

// Elementos DOM principales del chat (seleccionados en initChatModule)
let chatWindow = null;
let chatInput = null;
let sendBtn = null;
let logoutBtn = null;
let welcomeMessageElement = null;
let userNameEl = null;
let userAvatarEl = null;

// Elementos DOM de la sidebar y responsive
let sidebar = null;
let menuToggleBtn = null;
let sidebarCloseBtn = null;

// Botón para abrir el modal de subida de documentos
let uploadDocBtn = null;

let currentUser = null; // Guardará la información del usuario autenticado
let isSending = false; // Bandera para evitar envíos múltiples

/**
 * Carga el perfil del usuario y actualiza la UI.
 */
async function loadUserProfile() {
    try {
        // ¡CORRECCIÓN CLAVE AQUÍ! Usamos apiGet para obtener el perfil del usuario.
        const userData = await apiGet(API_ENDPOINTS.getUserProfile);
        
        currentUser = {
            account_id: userData.id,
            name: userData.name,
            email: userData.email,
            username: userData.username
        };

        if (userNameEl) userNameEl.textContent = currentUser.name || 'Usuario';
        if (userAvatarEl) userAvatarEl.textContent = (currentUser.name || 'U').charAt(0).toUpperCase();

        // Pasar los datos del usuario al módulo de subida de documentos
        setDocUploadUserData(currentUser);
    } catch (error) {
        console.error("Error al cargar el perfil del usuario:", error);
        // Si falla la carga del perfil, podría ser una sesión inválida.
        localStorage.removeItem('kognito_auth_token');
        window.location.href = 'index.html';
    }
}

/**
 * Maneja el envío de un mensaje de chat.
 */
async function sendMessage() {
    const currentThreadId = getCurrentThreadId();
    if (isSending || !currentUser || !currentThreadId) return;

    const messageText = chatInput.value.trim();
    if (!messageText) return;

    isSending = true;
    sendBtn.disabled = true;
    displayMessage(messageText, 'user');
    chatInput.value = '';
    adjustTextareaHeight();
    displayMessage('', 'ai', true);

    try {
        const payload = {
            thread_id: currentThreadId,
            account_id: currentUser.account_id,
            telegram_id: null, // No aplica para la UI web pública
            user_message: messageText
        };

        const data = await apiPost(API_ENDPOINTS.chat, payload);
        displayMessage(data.response_text, 'ai');

        setTimeout(() => {
            refreshCurrentThreadTitle();
        }, 500);
    } catch (error) {
        displayMessage(`Lo siento, ocurrió un error: ${error.message}`, 'ai');
    } finally {
        isSending = false;
        sendBtn.disabled = false;
    }
}

// Reemplaza la lógica de mostrar respuesta AI por streaming:
async function sendMessageWithStreaming(userMessage) {
    const currentThreadId = getCurrentThreadId();
    if (!currentThreadId) return;
    let aiMsgDiv = displayMessage('', 'ai', true); // Crea burbuja vacía
    await streamLLMResponse(userMessage, currentThreadId, (fullText, chunk) => {
        if (aiMsgDiv) aiMsgDiv.textContent = fullText;
        scrollToBottom();
    });
}

/**
 * Inicializa todos los event listeners y la lógica de la página de chat.
 */
export async function initChatModule() {
    // 1. Seleccionar todos los elementos DOM
    chatWindow = document.getElementById('chat-window');
    chatInput = document.getElementById('chat-input');
    sendBtn = document.getElementById('send-btn');
    logoutBtn = document.getElementById('logout-btn');
    welcomeMessageElement = document.querySelector('.welcome-message');
    userNameEl = document.getElementById('user-name');
    userAvatarEl = document.getElementById('user-avatar');
    sidebar = document.querySelector('.sidebar');
    menuToggleBtn = document.getElementById('menu-toggle-btn');
    sidebarCloseBtn = document.getElementById('sidebar-close-btn');
    uploadDocBtn = document.getElementById('upload-doc-btn');
    // Declarar micBtn y audioWave solo aquí
    let micBtn = document.getElementById('mic-btn');
    let audioWave = document.getElementById('audio-wave');
    let mediaRecorder = null;
    let audioChunks = [];

    // 2. Configurar los helpers de UI con los elementos correctos
    setChatElements('chat-window', '.welcome-message', 'chat-input');
    
    // 3. Cargar el perfil del usuario
    await loadUserProfile();

    // 4. Inicializar los submódulos (historial y subida de documentos)
    initChatHistoryModule();
    initDocumentUploadModule();

    // 5. Configurar los event listeners del chat
    if (logoutBtn) logoutBtn.addEventListener('click', () => {
        localStorage.removeItem('kognito_auth_token');
        window.location.href = 'index.html';
    });
    if (sendBtn) sendBtn.addEventListener('click', sendMessage);
    if (chatInput) {
        chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) { 
                e.preventDefault(); 
                sendMessage(); 
            }
        });
        chatInput.addEventListener('input', () => {
            adjustTextareaHeight();
            sendBtn.disabled = chatInput.value.trim().length === 0;
        });
    }

    // 6. Lógica del menú responsive
    if (menuToggleBtn && sidebar) menuToggleBtn.addEventListener('click', () => sidebar.classList.add('open'));
    if (sidebarCloseBtn && sidebar) sidebarCloseBtn.addEventListener('click', () => sidebar.classList.remove('open'));
    document.addEventListener('click', (event) => {
        if (sidebar && sidebar.classList.contains('open') && !sidebar.contains(event.target) && !menuToggleBtn.contains(event.target)) {
            sidebar.classList.remove('open');
        }
    });

    // 7. Event listener para el botón de subir documentos (ahora solo en barra de input)
    uploadDocBtn = document.getElementById('upload-doc-btn');
    if (uploadDocBtn) uploadDocBtn.addEventListener('click', showUploadModal);
    // Eliminar el botón de subir documentos de la barra lateral si existe
    const sidebarUploadBtn = document.querySelector('.sidebar-nav #upload-doc-btn');
    if (sidebarUploadBtn) sidebarUploadBtn.remove();

    // 8. Inicializar el switcher de tema
    initThemeSwitcher();

    function showAudioWave() {
        audioWave.innerHTML = '';
        audioWave.classList.remove('hidden');
        for (let i = 0; i < 8; i++) {
            const bar = document.createElement('span');
            bar.style.animationDelay = `${i * 0.1}s`;
            audioWave.appendChild(bar);
        }
    }
    function hideAudioWave() {
        audioWave.classList.add('hidden');
        audioWave.innerHTML = '';
    }

    if (micBtn && audioWave && chatInput) {
        micBtn.addEventListener('mousedown', async () => {
            micBtn.classList.add('active');
            showAudioWave();
            if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                    mediaRecorder = new MediaRecorder(stream);
                    audioChunks = [];
                    mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
                    mediaRecorder.onstop = async () => {
                        hideAudioWave();
                        micBtn.classList.remove('active');
                        const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                        // Enviar al backend
                        const formData = new FormData();
                        formData.append('file', audioBlob, 'audio.webm');
                        try {
                            const resp = await fetch(`${API_BASE_URL}/api/transcribe-audio`, {
                                method: 'POST',
                                body: formData
                            });
                            const data = await resp.json();
                            if (data.transcription) {
                                chatInput.value = data.transcription;
                                chatInput.focus();
                            } else {
                                alert('No se pudo transcribir el audio.');
                            }
                        } catch (err) {
                            alert('Error al enviar el audio.');
                        }
                    };
                    mediaRecorder.start();
                } catch (err) {
                    hideAudioWave();
                    micBtn.classList.remove('active');
                    alert('No se pudo acceder al micrófono.');
                }
            }
        });
        micBtn.addEventListener('mouseup', () => {
            if (mediaRecorder && mediaRecorder.state === 'recording') {
                mediaRecorder.stop();
            }
        });
        micBtn.addEventListener('mouseleave', () => {
            if (mediaRecorder && mediaRecorder.state === 'recording') {
                mediaRecorder.stop();
            }
        });
    }
}