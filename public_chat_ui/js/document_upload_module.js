// public_chat_ui/js/document_upload_module.js

import { apiUpload, API_ENDPOINTS } from './api.js';
import { displayMessage } from './ui_helpers.js'; // Opcional: para mostrar mensajes en el chat

// Elementos DOM del modal de subida de documentos (seleccionados en initDocumentUploadModule)
let uploadModal = null;
let closeUploadModalBtn = null;
let uploadForm = null;
let fileInput = null;
let topicInput = null;
let uploadStatus = null;
let fileCountSpan = null;

// Variable para el usuario actual (se establecerá desde chat_module)
let currentUserData = null;

/**
 * Establece los datos del usuario actual para que el módulo pueda usarlos en las peticiones API.
 * @param {object} userData - Objeto con datos del usuario (al menos account_id).
 */
export function setCurrentUserData(userData) {
    currentUserData = userData;
}

/**
 * Muestra el modal de subida de documentos.
 */
export function showUploadModal() {
    if (uploadModal) {
        uploadModal.classList.remove('hidden');
        // Resetear estado del modal
        if (uploadForm) uploadForm.reset();
        if (fileCountSpan) fileCountSpan.textContent = '0 archivos';
        if (uploadStatus) {
            uploadStatus.className = 'status-message';
            uploadStatus.textContent = '';
        }
    }
}

/**
 * Oculta el modal de subida de documentos.
 */
export function hideUploadModal() {
    if (uploadModal) {
        uploadModal.classList.add('hidden');
        if (uploadForm) uploadForm.reset(); // Asegurarse de resetear el formulario al cerrar
        if (fileCountSpan) fileCountSpan.textContent = '0 archivos';
        if (uploadStatus) {
            uploadStatus.className = 'status-message';
            uploadStatus.textContent = '';
        }
    }
}

/**
 * Actualiza el contador de archivos seleccionados en la interfaz.
 */
function updateFileCountDisplay() {
    if (fileInput && fileCountSpan) {
        fileCountSpan.textContent = `${fileInput.files.length} archivo(s)`;
    }
}

/**
 * Maneja el envío del formulario de subida de documentos.
 * @param {Event} event - El evento de envío del formulario.
 */
async function handleUploadFormSubmit(event) {
    event.preventDefault();

    const files = fileInput.files;
    const topic = topicInput.value.trim();

    if (files.length === 0 || !topic) {
        if (uploadStatus) {
            uploadStatus.textContent = 'Por favor, selecciona al menos un archivo y asigna un tema.';
            uploadStatus.className = 'status-message error';
        }
        return;
    }

    if (!currentUserData || !currentUserData.account_id) {
        if (uploadStatus) {
            uploadStatus.textContent = 'Error: Datos de usuario no disponibles para la subida.';
            uploadStatus.className = 'status-message error';
        }
        console.error('Error: currentUserData o account_id no están definidos en document_upload_module.');
        return;
    }

    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
        formData.append('files', files[i]);
    }
    formData.append('topic', topic);

    if (uploadStatus) {
        uploadStatus.textContent = `Subiendo ${files.length} archivo(s)...`;
        uploadStatus.className = 'status-message loading';
    }

    try {
        const result = await apiUpload(API_ENDPOINTS.uploadDocuments, formData);

        if (uploadStatus) {
            uploadStatus.textContent = result.message;
            uploadStatus.className = 'status-message success';
        }
        // Opcional: Si quieres mostrar el mensaje de confirmación en el chat principal también
        // displayMessage(`✅ ${result.message}`, 'ai'); 

        setTimeout(() => {
            hideUploadModal();
            // Si necesitas refrescar la lista de documentos en el chat, podrías emitir un evento
            // o llamar a una función proporcionada por chat_module.
            // Por ejemplo: if (typeof window.refreshDocumentList === 'function') window.refreshDocumentList();
        }, 2000);

    } catch (error) {
        if (uploadStatus) {
            uploadStatus.textContent = error.message;
            uploadStatus.className = 'status-message error';
        }
        console.error('Error al subir documentos:', error);
    }
}

/**
 * Inicializa los event listeners y selecciona los elementos DOM para el módulo de subida de documentos.
 */
export function initDocumentUploadModule() {
    // Seleccionar elementos DOM dentro de la función de inicialización
    uploadModal = document.getElementById('upload-modal');
    closeUploadModalBtn = document.getElementById('close-upload-modal-btn');
    uploadForm = document.getElementById('upload-form');
    fileInput = document.getElementById('file-input');
    topicInput = document.getElementById('topic-input');
    uploadStatus = document.getElementById('upload-status');
    fileCountSpan = document.getElementById('file-count');

    if (closeUploadModalBtn) closeUploadModalBtn.addEventListener('click', hideUploadModal);
    if (uploadModal) {
        uploadModal.addEventListener('click', (event) => {
            if (event.target === uploadModal) {
                hideUploadModal();
            }
        });
    }

    if (fileInput) fileInput.addEventListener('change', updateFileCountDisplay);
    if (uploadForm) uploadForm.addEventListener('submit', handleUploadFormSubmit);
}