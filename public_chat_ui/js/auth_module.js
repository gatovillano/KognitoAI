// public_chat_ui/js/auth_module.js

import { API_ENDPOINTS, showStatus, handleAuthSuccess, apiPost, setStatusMessageElement } from './api.js';

// No seleccionar elementos DOM aquí a nivel global. Se hará dentro de initAuthModule.
let mainAuthView = null;
let codeLoginView = null;
let showCodeLoginLink = null;
let showMainLoginLink = null;
let loginForm = null;
let registerForm = null;
let tabLinks = null;
let mainViews = null;
let requestCodeView = null;
let verifyCodeView = null;
let requestCodeForm = null;
let verifyCodeForm = null;
let telegramIdInput = null;
let verificationCodeInput = null;
let backToRequestButton = null;

let currentIdentifier = ''; // Para almacenar el identificador de Telegram en el flujo de código

/**
 * Muestra una sub-vista dentro de la sección de login por código.
 * @param {string} viewId - El ID de la vista a mostrar ('request-code-view' o 'verify-code-view').
 */
function showCodeLoginSubView(viewId) {
    if (requestCodeView) requestCodeView.classList.remove('active');
    if (verifyCodeView) verifyCodeView.classList.remove('active');
    const targetView = document.getElementById(viewId);
    if (targetView) targetView.classList.add('active');
    showStatus(''); // Limpia cualquier mensaje de estado anterior
}

/**
 * Función que maneja la lógica de autenticación de Telegram cuando se recibe el evento.
 * @param {object} user - El objeto de usuario proporcionado por el widget de Telegram.
 */
async function handleTelegramAuth(user) {
    showStatus('Procesando inicio de sesión con Telegram...', false);
    try {
        const data = await apiPost(API_ENDPOINTS.telegramCallback, user, false);
        handleAuthSuccess(data);
    } catch (error) {
        showStatus(error.message);
    }
}

/**
 * Inicializa todos los event listeners y la lógica de la página de autenticación.
 */
export function initAuthModule() {
    // 1. Seleccionar elementos DOM dentro de la función de inicialización
    mainAuthView = document.getElementById('main-auth-view');
    codeLoginView = document.getElementById('code-login-view');
    showCodeLoginLink = document.getElementById('show-code-login');
    showMainLoginLink = document.getElementById('show-main-login');
    loginForm = document.getElementById('login-form');
    registerForm = document.getElementById('register-form');
    tabLinks = document.querySelectorAll('.tab-link');
    mainViews = document.querySelectorAll('#main-auth-view .view');
    requestCodeView = document.getElementById('request-code-view');
    verifyCodeView = document.getElementById('verify-code-view');
    requestCodeForm = document.getElementById('request-code-form');
    verifyCodeForm = document.getElementById('verify-code-form');
    telegramIdInput = document.getElementById('telegram-id-input');
    verificationCodeInput = document.getElementById('verification-code-input');
    backToRequestButton = document.getElementById('back-to-request');

    setStatusMessageElement('status-message'); // Configurar el elemento de estado en api.js

    // ¡CAMBIO CLAVE! Escuchar el evento personalizado 'telegram-auth'.
    document.addEventListener('telegram-auth', (event) => {
        const user = event.detail; // Obtener los datos del usuario desde el evento
        handleTelegramAuth(user);
    });

    // 2. Lógica para cambiar entre vistas de autenticación (email/pass vs. código)
    if (showCodeLoginLink) {
        showCodeLoginLink.addEventListener('click', (e) => {
            e.preventDefault();
            if (mainAuthView) mainAuthView.style.display = 'none';
            if (codeLoginView) codeLoginView.style.display = 'block';
            showStatus('');
        });
    }

    if (showMainLoginLink) {
        showMainLoginLink.addEventListener('click', (e) => {
            e.preventDefault();
            if (mainAuthView) mainAuthView.style.display = 'block';
            if (codeLoginView) codeLoginView.style.display = 'none';
            showStatus('');
        });
    }

    // 3. Manejadores para login con Email y Registro (Pestañas)
    tabLinks.forEach(tab => {
        tab.addEventListener('click', () => {
            const targetTab = tab.getAttribute('data-tab');
            tabLinks.forEach(t => t.classList.remove('active'));
            mainViews.forEach(v => v.classList.remove('active'));
            tab.classList.add('active');
            const targetElement = document.getElementById(targetTab);
            if (targetElement) targetElement.classList.add('active');
        });
    });

    // 4. Envío del formulario de Login
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            showStatus('');
            const email = document.getElementById('login-email').value;
            const password = document.getElementById('login-password').value;
            try {
                const data = await apiPost(API_ENDPOINTS.login, { email, password }, false);
                handleAuthSuccess(data);
            } catch (error) {
                showStatus(error.message);
            }
        });
    }

    // 5. Envío del formulario de Registro
    if (registerForm) {
        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            showStatus('');
            const name = document.getElementById('register-name').value;
            const email = document.getElementById('register-email').value;
            const password = document.getElementById('register-password').value;
            try {
                const data = await apiPost(API_ENDPOINTS.register, { name: name || null, email, password }, false);
                handleAuthSuccess(data);
            } catch (error) {
                showStatus(error.message);
            }
        });
    }

    // 6. Manejadores para Login con Código de Telegram (legado)
    if (requestCodeForm) {
        requestCodeForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            showStatus('Enviando código...');
            currentIdentifier = telegramIdInput.value.trim();
            if (!currentIdentifier) {
                showStatus('Por favor, introduce tu identificador de Telegram.');
                return;
            }
            try {
                const data = await apiPost(API_ENDPOINTS.requestCode, { identifier: currentIdentifier }, false);
                showStatus(data.message, false);
                showCodeLoginSubView('verify-code-view');
            } catch (error) {
                showStatus(error.message, true);
            }
        });
    }

    if (verifyCodeForm) {
        verifyCodeForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            showStatus('Verificando...');
            const code = verificationCodeInput.value.trim();
            if (!code || !currentIdentifier) {
                showStatus('Por favor, introduce el código y tu identificador.', true);
                return;
            }
            try {
                const data = await apiPost(API_ENDPOINTS.verifyCode, { identifier: currentIdentifier, code: code }, false);
                handleAuthSuccess(data);
            } catch (error) {
                showStatus(error.message, true);
            }
        });
    }

    if (backToRequestButton) {
        backToRequestButton.addEventListener('click', () => showCodeLoginSubView('request-code-view'));
    }
}