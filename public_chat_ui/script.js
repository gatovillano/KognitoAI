// public_chat_ui/script.js

document.addEventListener('DOMContentLoaded', () => {
    // La URL de nuestra API del core. Asegúrate de que el puerto coincida con tu docker-compose.yml.
    const API_BASE_URL = 'http://localhost:8889';
    const authToken = localStorage.getItem('kognito_auth_token');
    const currentPage = window.location.pathname.split('/').pop() || 'index.html';

    // --- LÓGICA DE ENRUTAMIENTO Y AUTENTICACIÓN ---
    
    // Si estamos en la página de chat pero no hay token, nos vamos al login.
    if (currentPage === 'chat.html' && !authToken) {
        window.location.href = 'index.html';
        return;
    }

    // Si estamos en la página de login y ya tenemos un token, vamos directo al chat.
    if (currentPage === 'index.html' && authToken) {
        window.location.href = 'chat.html';
        return;
    }

    // --- LÓGICA PARA LA PÁGINA DE LOGIN (index.html) ---
    if (currentPage === 'index.html') {
        const requestCodeView = document.getElementById('request-code-view');
        const verifyCodeView = document.getElementById('verify-code-view');
        const requestCodeForm = document.getElementById('request-code-form');
        const verifyCodeForm = document.getElementById('verify-code-form');
        const telegramIdInput = document.getElementById('telegram-id-input');
        const verificationCodeInput = document.getElementById('verification-code-input');
        const statusMessage = document.getElementById('status-message');
        const backToRequestButton = document.getElementById('back-to-request');

        let currentIdentifier = '';

        function showStatus(message, isError = false, isLoading = false) {
            statusMessage.textContent = message;
            statusMessage.className = 'status-message';
            if (message) {
                if (isLoading) {
                    statusMessage.classList.add('loading');
                } else {
                    statusMessage.classList.add(isError ? 'error' : 'success');
                }
            }
        }

        function showView(viewId) {
            document.querySelectorAll('.view').forEach(view => view.classList.remove('active'));
            document.getElementById(viewId).classList.add('active');
            showStatus('');
        }

        requestCodeForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            showStatus('Enviando código...', false, true);
            const identifier = telegramIdInput.value.trim();
            if (!identifier) return;
            currentIdentifier = identifier;

            try {
                const response = await fetch(`${API_BASE_URL}/api/auth/request-code`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ identifier: identifier })
                });
                const data = await response.json();
                if (!response.ok) throw new Error(data.detail || 'Error al solicitar el código.');
                showStatus(data.message, false);
                showView('verify-code-view');
            } catch (error) {
                showStatus(error.message, true);
            }
        });

        verifyCodeForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            showStatus('Verificando...', false, true);
            const code = verificationCodeInput.value.trim();
            if (!code || !currentIdentifier) return;

            try {
                const response = await fetch(`${API_BASE_URL}/api/auth/verify-code`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ identifier: currentIdentifier, code: code })
                });
                const data = await response.json();
                if (!response.ok) throw new Error(data.detail || 'Código incorrecto.');
                
                localStorage.setItem('kognito_auth_token', data.access_token);
                window.location.href = 'chat.html';
            } catch (error) {
                showStatus(error.message, true);
            }
        });

        backToRequestButton.addEventListener('click', () => showView('request-code-view'));
    }

    // --- LÓGICA PARA LA PÁGINA DE CHAT (chat.html) ---
    if (currentPage === 'chat.html') {
        const chatWindow = document.getElementById('chat-window');
        const chatInput = document.getElementById('chat-input');
        const sendBtn = document.getElementById('send-btn');
        const logoutBtn = document.getElementById('logout-btn');
        const welcomeMessage = document.querySelector('.welcome-message');
        const userNameEl = document.getElementById('user-name');
        const userAvatarEl = document.querySelector('.user-avatar');

        let currentUser = null; // Almacenará la info del usuario: { account_id, telegram_id, name }
        let isSending = false;

        // Función para obtener los datos del usuario y preparar el chat
        async function initializeChat() {
            try {
                const response = await fetch(`${API_BASE_URL}/api/users/me`, {
                    headers: { 'Authorization': `Bearer ${authToken}` }
                });

                if (!response.ok) {
                    // Si el token es inválido o expiró, el servidor devolverá un error.
                    throw new Error('Sesión inválida o expirada.');
                }
                
                const userData = await response.json();
                currentUser = userData; // Guardamos la información completa del usuario

                // Actualizar la UI con el nombre del usuario
                if (userNameEl) userNameEl.textContent = currentUser.name;
                if (userAvatarEl) userAvatarEl.textContent = (currentUser.name || 'U').charAt(0).toUpperCase();

            } catch (error) {
                console.error("Error de autenticación:", error.message);
                // Si falla la obtención del perfil, la sesión no es válida.
                localStorage.removeItem('kognito_auth_token');
                window.location.href = 'index.html';
            }
        }

        // Función para mostrar un mensaje en la ventana de chat
        function displayMessage(text, sender, isLoading = false) {
            if (welcomeMessage) {
                welcomeMessage.style.display = 'none';
            }

            // Si es un mensaje de la IA que ya está en estado "pensando", lo actualizamos.
            if (sender === 'ai' && !isLoading) {
                const thinkingBubble = document.querySelector('.message-bubble.thinking');
                if (thinkingBubble) {
                    thinkingBubble.innerHTML = marked.parse(text); // Usamos la librería marked para renderizar Markdown
                    thinkingBubble.classList.remove('thinking');
                    scrollToBottom();
                    return;
                }
            }

            const messageWrapper = document.createElement('div');
            messageWrapper.className = `chat-message ${sender}`;

            const avatar = document.createElement('div');
            avatar.className = 'message-avatar';
            if (sender === 'user') {
                avatar.textContent = (currentUser.name || 'U').charAt(0).toUpperCase();
            } else {
                const logo = document.createElement('img');
                logo.src = 'assets/logo.png';
                logo.alt = 'Kognito Logo';
                avatar.appendChild(logo);
            }

            const messageBubble = document.createElement('div');
            messageBubble.className = 'message-bubble';

            if (isLoading) {
                messageBubble.classList.add('thinking');
                messageBubble.innerHTML = '<span class="dot"></span><span class="dot"></span><span class="dot"></span>';
            } else {
                // Usamos `marked.parse` para convertir Markdown a HTML de forma segura.
                messageBubble.innerHTML = marked.parse(text);
            }

            messageWrapper.appendChild(avatar);
            messageWrapper.appendChild(messageBubble);
            chatWindow.appendChild(messageWrapper);
            scrollToBottom();
        }
        
        // Función principal para enviar un mensaje a la API
        async function sendMessage() {
            if (isSending || !currentUser) return;

            const messageText = chatInput.value.trim();
            if (!messageText) return;

            isSending = true;
            sendBtn.disabled = true;

            displayMessage(messageText, 'user');
            chatInput.value = '';
            adjustTextareaHeight();
            
            displayMessage('', 'ai', true); // Muestra el indicador "pensando..."

            try {
                // ¡CORRECCIÓN CLAVE! Incluimos la identidad del usuario en el payload.
                const payload = {
                    account_id: currentUser.account_id,
                    telegram_id: currentUser.telegram_id,
                    user_message: messageText
                };

                const response = await fetch(`${API_BASE_URL}/api/chat`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${authToken}`
                    },
                    body: JSON.stringify(payload)
                });

                const data = await response.json();
                if (!response.ok) {
                    throw new Error(data.detail || 'Error en la respuesta de la IA.');
                }
                
                displayMessage(data.response_text, 'ai');

            } catch (error) {
                displayMessage(`Lo siento, ocurrió un error: ${error.message}`, 'ai');
            } finally {
                isSending = false;
                sendBtn.disabled = false;
            }
        }

        // --- Funciones de Ayuda y Event Listeners ---

        function scrollToBottom() {
            chatWindow.scrollTop = chatWindow.scrollHeight;
        }

        function adjustTextareaHeight() {
            chatInput.style.height = 'auto';
            chatInput.style.height = `${chatInput.scrollHeight}px`;
        }
        
        logoutBtn.addEventListener('click', () => {
            localStorage.removeItem('kognito_auth_token');
            window.location.href = 'index.html';
        });

        sendBtn.addEventListener('click', sendMessage);

        chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
        
        chatInput.addEventListener('input', adjustTextareaHeight);

        // Iniciar todo
        initializeChat();
    }
});