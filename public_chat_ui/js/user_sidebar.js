import { API_ENDPOINTS, apiGet } from './api.js';

document.addEventListener('DOMContentLoaded', async () => {
    // ...existing code...
    // Actualizar nombre y avatar del usuario en el sidebar
    try {
        const userData = await apiGet(API_ENDPOINTS.getUserProfile);
        const userNameEl = document.getElementById('user-name');
        const userAvatarEl = document.getElementById('user-avatar');
        if (userNameEl) userNameEl.textContent = userData.name || 'Usuario';
        if (userAvatarEl) userAvatarEl.textContent = (userData.name || 'U').charAt(0).toUpperCase();
    } catch (e) {
        // Si falla, dejar el valor por defecto
    }
});
