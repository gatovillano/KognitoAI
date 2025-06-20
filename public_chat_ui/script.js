// public_chat_ui/script.js

document.addEventListener('DOMContentLoaded', () => {
    const API_BASE_URL = 'http://localhost:8007'; // URL de nuestra API FastAPI
    const authToken = localStorage.getItem('kognito_auth_token');
    const currentPage = window.location.pathname.split('/').pop();

    // --- LÓGICA DE ENRUTAMIENTO Y AUTENTICACIÓN ---
    
    // Si estamos en la página de chat pero no hay token, redirigir al login.
    if (currentPage === 'chat.html' && !authToken) {
        window.location.href = 'index.html';
        return;
    }

    // Si estamos en la página de login y ya hay un token, redirigir al chat.
    if (currentPage === 'index.html' && authToken) {
        window.location.href = 'chat.html';
        return;
    }

    // --- LÓGICA PARA LA PÁGINA DE LOGIN (index.html) ---
    if (currentPage === 'index.html' || currentPage === '') {
        const requestCodeView = document.getElementById('request-code-view');
        const verifyCodeView = document.getElementById('verify-code-view');
        const requestCodeForm = document.getElementById('request-code-form');
        const verifyCodeForm = document.getElementById('verify-code-form');
        const telegramIdInput = document.getElementById('telegram-id-input');
        const verificationCodeInput = document.getElementById('verification-code-input');
        const statusMessage = document.getElementById('status-message');
        const backToRequestButton = document.getElementById('back-to-request');

        let currentTelegramId = '';

        function showStatus(message, isError = false) {
            statusMessage.textContent = message;
            statusMessage.className = 'status-message';
            if (message) {
                statusMessage.classList.add(isError ? 'error' : 'success');
            }
        }

        function showView(viewId) {
            document.querySelectorAll('.view').forEach(view => view.classList.remove('active'));
            document.getElementById(viewId).classList.add('active');
            showStatus('');
        }

        requestCodeForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            showStatus('Enviando código...', false);
            const telegramId = telegramIdInput.value.trim();
            if (!telegramId) return;
            currentTelegramId = telegramId;

            try {
                const response = await fetch(`${API_BASE_URL}/api/auth/request-code`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ telegram_id: telegramId })
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
            showStatus('Verificando...', false);
            const code = verificationCodeInput.value.trim();
            if (!code || !currentTelegramId) return;

            try {
                const response = await fetch(`${API_BASE_URL}/api/auth/verify-code`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ telegram_id: currentTelegramId, code: code })
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
        const userNameEl = document.getElementById('user-name');
        const userAvatarEl = document.querySelector('.user-avatar');
        const logoutBtn = document.getElementById('logout-btn');

        function simpleMarkdownToHtml(text) {
             // Reemplazar bloques de código ```
            text = text.replace(/```([\s\S]*?)```/g, (match, code) => {
                const escapedCode = code.replace(/</g, '&lt;').replace(/>/g, '&gt;');
                return `<pre><code>${escapedCode.trim()}</code></pre>`;
            });
            // Reemplazar negrita **texto**
            text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
            // Reemplazar cursiva *texto*
            text = text.replace(/\*(.*?)\*/g, '<em>$1</em>');
            return text;
        }

        function displayMessage(sender, text) {
            chatWindow.querySelector('.welcome-message')?.remove();

            const messageEl = document.createElement('div');
            messageEl.classList.add('chat-message', sender);

            const avatarEl = document.createElement('div');
            avatarEl.classList.add('message-avatar');

            if (sender === 'ai') {
                const logoImg = document.createElement('img');
                logoImg.src = 'assets/logo.png';
                avatarEl.appendChild(logoImg);
            } else {
                 avatarEl.textContent = userNameEl.textContent.charAt(0).toUpperCase();
            }

            const contentEl = document.createElement('div');
            contentEl.classList.add('message-content');
            contentEl.innerHTML = simpleMarkdownToHtml(text);
            
            messageEl.appendChild(avatarEl);
            messageEl.appendChild(contentEl);
            chatWindow.appendChild(messageEl);
            chatWindow.scrollTop = chatWindow.scrollHeight;
        }
        
        async function sendMessage() {
            const messageText = chatInput.value.trim();
            if (!messageText) return;

            displayMessage('user', messageText);
            chatInput.value = '';
            chatInput.style.height = 'auto'; // Reset height
            sendBtn.disabled = true;

            // Mostrar "escribiendo..."
            const thinkingEl = document.createElement('div');
            thinkingEl.classList.add('chat-message', 'ai');
            thinkingEl.innerHTML = `
                <div class="message-avatar"><img src="assets/logo.png"></div>
                <div class="message-content">...</div>
            `;
            chatWindow.appendChild(thinkingEl);
            chatWindow.scrollTop = chatWindow.scrollHeight;
            
            try {
                const response = await fetch(`${API_BASE_URL}/api/web-chat`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${authToken}`
                    },
                    body: JSON.stringify({ user_message: messageText })
                });

                thinkingEl.remove();

                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.detail || 'Error en la respuesta del servidor.');
                }
                const data = await response.json();
                displayMessage('ai', data.response_text);
            } catch (error) {
                displayMessage('ai', `Lo siento, ocurrió un error: ${error.message}`);
            } finally {
                 sendBtn.disabled = false;
            }
        }

        async function fetchUserProfile() {
            try {
                 const response = await fetch(`${API_BASE_URL}/api/users/me`, {
                    headers: { 'Authorization': `Bearer ${authToken}` }
                });
                if (!response.ok) throw new Error('Sesión inválida.');
                const userData = await response.json();
                userNameEl.textContent = userData.first_name;
                userAvatarEl.textContent = userData.first_name.charAt(0).toUpperCase();
            } catch (error) {
                localStorage.removeItem('kognito_auth_token');
                window.location.href = 'index.html';
            }
        }

        sendBtn.addEventListener('click', sendMessage);
        chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
        chatInput.addEventListener('input', () => {
             chatInput.style.height = 'auto';
             chatInput.style.height = (chatInput.scrollHeight) + 'px';
        });

        logoutBtn.addEventListener('click', () => {
            localStorage.removeItem('kognito_auth_token');
            window.location.href = 'index.html';
        });

        fetchUserProfile();
    }
});