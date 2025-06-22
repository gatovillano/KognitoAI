// public_chat_ui/js/knowledge_base.js

import { apiPost } from './api.js';
import { apiUpdateDocumentMetadata } from './document_metadata.js';

document.addEventListener('DOMContentLoaded', () => {
    const knowledgeBaseCenter = document.querySelector('.knowledge-base-center');

    async function loadCollections() {
        knowledgeBaseCenter.innerHTML = '<div class="loader">Cargando colecciones...</div>';
        try {
            const docs = await apiPost('/api/list-documents', {});
            // Agrupar por topic
            const collections = {};
            docs.forEach(doc => {
                if (!collections[doc.topic]) collections[doc.topic] = [];
                collections[doc.topic].push(doc);
            });
            knowledgeBaseCenter.innerHTML = '';
            Object.keys(collections).forEach(topic => {
                const colBtn = document.createElement('button');
                colBtn.className = 'collection-btn';
                colBtn.innerHTML = `<span class='collection-icon'>📚</span> <span class='collection-name'>${topic}</span> <span class='collection-count'>(${collections[topic].length})</span> <button class='edit-collection-btn' title='Editar'>✏️</button>`;
                colBtn.querySelector('.edit-collection-btn').addEventListener('click', async (e) => {
                    e.stopPropagation();
                    const newTopic = prompt('Nuevo nombre para la base de conocimientos:', topic);
                    if (newTopic && newTopic !== topic) {
                        try {
                            // Actualizar todos los documentos de la colección
                            await Promise.all(collections[topic].map(doc => apiUpdateDocumentMetadata(doc.file_name, undefined, newTopic)));
                            loadCollections();
                        } catch (err) {
                            alert('Error al actualizar el nombre de la base: ' + err.message);
                        }
                    }
                });
                colBtn.addEventListener('click', () => {
                    window.location.href = `kb_upload.html?kb=${encodeURIComponent(topic)}`;
                });
                knowledgeBaseCenter.appendChild(colBtn);
            });
            // Botón para crear nueva base de conocimientos
            const createBtn = document.createElement('button');
            createBtn.className = 'create-kb-btn';
            createBtn.id = 'create-kb-btn';
            createBtn.textContent = '+ Crear nueva base de conocimientos';
            createBtn.addEventListener('click', () => {
                window.location.href = 'kb_create.html';
            });
            knowledgeBaseCenter.appendChild(createBtn);
        } catch (e) {
            knowledgeBaseCenter.innerHTML = '<div class="error">Error al cargar colecciones.</div>';
        }
    }

    loadCollections();

    const backToChatBtn = document.getElementById('back-to-chat-btn');
    if (backToChatBtn) {
        backToChatBtn.addEventListener('click', () => {
            window.location.href = 'chat.html';
        });
    }
});
