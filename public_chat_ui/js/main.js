// public_chat_ui/js/main.js

import { API_BASE_URL, authToken, API_ENDPOINTS, apiGet } from './api.js'; // ¡Importamos apiGet!
import { initAuthModule } from './auth_module.js';
import { initChatModule } from './chat_module.js';

document.addEventListener('DOMContentLoaded', async () => {
    const currentPage = window.location.pathname.split('/').pop() || 'index.html';

    // Forzar tema claro en pantalla de login
    if (currentPage === 'index.html') {
        document.documentElement.setAttribute('data-theme', 'light');
        localStorage.setItem('kognito_theme', 'light');
    }

    /**
     * Verifica si el token de autenticación actual es válido haciendo una petición al backend.
     * @returns {Promise<boolean>} True si el token es válido, False en caso contrario.
     */
    async function isAuthTokenValid() {
        if (!authToken) {
            return false;
        }
        try {
            // ¡CORRECCIÓN CLAVE AQUÍ! Usamos apiGet para la petición.
            // Si tiene éxito (no lanza error), el token es válido.
            await apiGet(API_ENDPOINTS.getUserProfile);
            return true;
        } catch (error) {
            // Si apiGet lanza un error (ej. 401 Unauthorized), el token es inválido.
            console.warn('Error al validar el token (probablemente inválido o expirado):', error.message);
            localStorage.removeItem('kognito_auth_token'); // Limpiar token inválido
            return false;
        }
    }

    // Lógica de enrutamiento y verificación de token (ASÍNCRONA Y ROBUSTA)
    const tokenIsValid = await isAuthTokenValid();

    if (currentPage === 'chat.html' && !tokenIsValid) {
        window.location.href = 'index.html';
        return;
    }
    if (currentPage === 'index.html' && tokenIsValid) {
        window.location.href = 'chat.html';
        return;
    }

    // Si llegamos aquí, estamos en la página correcta (login sin token, o chat con token válido)
    // Inicializar módulos según la página actual
    if (currentPage === 'index.html') {
        initAuthModule();
    } else if (currentPage === 'chat.html') {
        initChatModule();
        // Navegación a Documentos
        const documentosBtn = document.getElementById('documentos-btn');
        if (documentosBtn) {
            documentosBtn.addEventListener('click', () => {
                window.location.href = 'documentos.html';
            });
        }
    }
});