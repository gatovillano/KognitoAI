// public_chat_ui/js/ui_helpers.js

let chatWindowElement = null; // Se seleccionará en initChatModule
let welcomeMessageElement = null; // Se seleccionará en initChatModule
let chatInputElement = null; // Se seleccionará en initChatModule

/**
 * Establece los elementos DOM del chat para que puedan ser manipulados por las funciones de ayuda.
 * Debe ser llamado al inicializar el chat_module.
 * @param {string} chatWindowId - El ID del contenedor principal de mensajes (ej. 'chat-window').
 * @param {string} welcomeMessageSelector - El selector para el mensaje de bienvenida (ej. '.welcome-message').
 * @param {string} chatInputId - El ID del textarea de entrada de chat (ej. 'chat-input').
 */
export const setChatElements = (chatWindowId, welcomeMessageSelector, chatInputId) => {
    chatWindowElement = document.getElementById(chatWindowId);
    welcomeMessageElement = document.querySelector(welcomeMessageSelector);
    chatInputElement = document.getElementById(chatInputId);
    if (!chatWindowElement || !welcomeMessageElement || !chatInputElement) {
        console.error("No se pudieron encontrar todos los elementos del chat en ui_helpers.");
    }
};

/**
 * Muestra un mensaje en la ventana de chat.
 * @param {string} text - El contenido del mensaje.
 * @param {'user'|'ai'} sender - El remitente del mensaje ('user' o 'ai').
 * @param {boolean} isLoading - Si el mensaje es una burbuja de "pensando".
 */
export function displayMessage(text, sender, isLoading = false) {
    if (!chatWindowElement) {
        console.error("chatWindowElement no está configurado en displayMessage.");
        return;
    }
    if (welcomeMessageElement) welcomeMessageElement.style.display = 'none';

    // Normalizar sender para evitar errores visuales
    let normalizedSender = (sender === 'user' || sender === 'ai') ? sender : 'ai';

    // Si es un mensaje AI y no está cargando, buscar la burbuja de "pensando" para actualizarla.
    if (normalizedSender === 'ai' && !isLoading) {
        const thinkingBubble = chatWindowElement.querySelector('.message-bubble.thinking');
        if (thinkingBubble) {
            thinkingBubble.innerHTML = typeof marked !== 'undefined' ? marked.parse(text) : text;
            thinkingBubble.classList.remove('thinking');
            scrollToBottom();
            return;
        }
    }

    const messageWrapper = document.createElement('div');
    messageWrapper.className = `chat-message ${normalizedSender}`;

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    if (normalizedSender === 'user') {
        avatar.textContent = 'Yo'; 
    } else {
        const logo = document.createElement('img');
        logo.src = 'assets/logo.png'; // Ruta a tu logo de Kognito
        logo.alt = 'Kognito Logo';
        avatar.appendChild(logo);
    }

    const messageBubble = document.createElement('div');
    messageBubble.className = 'message-bubble';
    if (isLoading) {
        messageBubble.classList.add('thinking');
        messageBubble.innerHTML = '<span class="dot"></span><span class="dot"></span><span class="dot"></span>';
    } else {
        messageBubble.innerHTML = typeof marked !== 'undefined' ? marked.parse(text) : text;
    }

    messageWrapper.appendChild(avatar);
    messageWrapper.appendChild(messageBubble);
    chatWindowElement.appendChild(messageWrapper);
    scrollToBottom();
}

/**
 * Desplaza la ventana de chat hasta el final para ver el último mensaje.
 */
export function scrollToBottom() {
    if (chatWindowElement) chatWindowElement.scrollTop = chatWindowElement.scrollHeight;
}

/**
 * Ajusta la altura del textarea de entrada de chat para que se expanda con el contenido.
 */
export function adjustTextareaHeight() {
    if (chatInputElement) {
        chatInputElement.style.height = 'auto';
        chatInputElement.style.height = `${chatInputElement.scrollHeight}px`;
    }
}

/**
 * Anima el texto de un elemento mostrándolo letra por letra.
 * @param {HTMLElement} element - El elemento donde mostrar el texto.
 * @param {string} text - El texto a animar.
 * @param {number} speed - Milisegundos entre letras.
 */
export function animateText(element, text, speed = 30) {
    element.textContent = '';
    let i = 0;
    function type() {
        if (i < text.length) {
            element.textContent += text.charAt(i);
            i++;
            setTimeout(type, speed);
        }
    }
    type();
}

/**
 * Cambia el tema de la app (claro/oscuro) y lo guarda en localStorage.
 * @param {'light'|'dark'} theme
 */
export function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('kognito_theme', theme);
}

/**
 * Inicializa el tema guardado o el preferido por el sistema.
 */
export function initThemeSwitcher() {
    let theme = localStorage.getItem('kognito_theme');
    if (!theme) {
        theme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    setTheme(theme);
    // Botón de toggle
    const themeBtn = document.getElementById('theme-toggle-btn');
    if (themeBtn) {
        themeBtn.textContent = theme === 'dark' ? '☀️ Claro' : '🌙 Oscuro';
        themeBtn.onclick = () => {
            const newTheme = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
            setTheme(newTheme);
            themeBtn.textContent = newTheme === 'dark' ? '☀️ Claro' : '🌙 Oscuro';
        };
    }
}