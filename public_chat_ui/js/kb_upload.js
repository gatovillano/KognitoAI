// public_chat_ui/js/kb_upload.js
import { apiUpload, API_ENDPOINTS, apiPost } from './api.js';
import { apiUpdateDocumentMetadata } from './document_metadata.js';

document.addEventListener('DOMContentLoaded', () => {
    const urlParams = new URLSearchParams(window.location.search);
    const kbName = urlParams.get('kb') || 'Base de conocimientos';
    document.getElementById('kb-title').textContent = kbName;

    const backToKbBtn = document.getElementById('back-to-kb-btn');
    if (backToKbBtn) {
        backToKbBtn.addEventListener('click', () => {
            window.location.href = 'documentos.html';
        });
    }

    const uploadBtn = document.getElementById('kb-upload-btn');
    const fileInput = document.getElementById('kb-file-input');
    const docList = document.getElementById('kb-doc-list');

    // Modal para previsualización
    let previewModal = document.createElement('div');
    previewModal.id = 'doc-preview-modal';
    previewModal.className = 'modal-overlay hidden';
    previewModal.innerHTML = `<div class='modal-content'><div class='modal-header'><h2>Documento</h2><button class='close-btn' id='close-preview-modal-btn'>×</button></div><div class='modal-body' id='preview-content'>Cargando...</div></div>`;
    document.body.appendChild(previewModal);

    function showPreview(content) {
        document.getElementById('preview-content').textContent = content;
        previewModal.classList.remove('hidden');
    }
    function hidePreview() {
        previewModal.classList.add('hidden');
    }
    document.addEventListener('click', (e) => {
        if (e.target.id === 'close-preview-modal-btn' || e.target === previewModal) hidePreview();
    });

    // Cargar documentos existentes al iniciar
    async function loadDocuments() {
        docList.innerHTML = '<div class="loader">Cargando documentos...</div>';
        try {
            const docs = await apiPost(API_ENDPOINTS.listDocuments, {});
            docList.innerHTML = '';
            const filtered = docs.filter(doc => doc.topic === kbName);
            if (filtered.length === 0) {
                docList.innerHTML = '<div class="hint">No hay documentos en esta base de conocimiento.</div>';
            } else {
                filtered.forEach(doc => {
                    const docItem = document.createElement('div');
                    docItem.className = 'kb-doc-item loaded';
                    docItem.innerHTML = `<span class='doc-icon'>📄</span> <span class='doc-name clickable'>${doc.title || doc.file_name}</span> <span class='doc-status'>Listo</span> <button class='edit-doc-btn' title='Editar'>✏️</button> <button class='delete-doc-btn' title='Eliminar'>🗑️</button>`;
                    // Visualización
                    docItem.querySelector('.doc-name').addEventListener('click', async () => {
                        try {
                            const res = await apiPost('/api/get-document-content', { file_name: doc.file_name });
                            showPreview(res.content || 'Sin contenido.');
                        } catch (e) {
                            showPreview('Error al cargar el contenido.');
                        }
                    });
                    // Edición de metadatos
                    docItem.querySelector('.edit-doc-btn').addEventListener('click', async () => {
                        const newTitle = prompt('Nuevo título para el documento:', doc.title || doc.file_name);
                        if (newTitle && newTitle !== doc.title) {
                            try {
                                await apiUpdateDocumentMetadata(doc.file_name, newTitle, undefined);
                                loadDocuments();
                            } catch (e) {
                                alert('Error al actualizar el título: ' + e.message);
                            }
                        }
                    });
                    docItem.querySelector('.delete-doc-btn').addEventListener('click', async () => {
                        if (confirm('¿Eliminar este documento?')) {
                            await apiUpload(API_ENDPOINTS.deleteDocument, createDeleteForm(doc.file_name));
                            loadDocuments();
                        }
                    });
                    docList.appendChild(docItem);
                });
            }
        } catch (e) {
            docList.innerHTML = '<div class="error">Error al cargar documentos.</div>';
        }
    }

    function createDeleteForm(fileName) {
        const form = new FormData();
        form.append('file_name', fileName);
        return form;
    }

    uploadBtn.addEventListener('click', () => {
        fileInput.click();
    });

    fileInput.addEventListener('change', async () => {
        const files = Array.from(fileInput.files);
        if (files.length === 0) return;
        uploadBtn.disabled = true;
        uploadBtn.textContent = 'Subiendo...';
        for (let idx = 0; idx < files.length; idx++) {
            const file = files[idx];
            const docItem = document.createElement('div');
            docItem.className = 'kb-doc-item loading';
            docItem.innerHTML = `<span class='doc-icon'>📄</span> <span class='doc-name'>${file.name}</span> <span class='doc-status'>Cargando...</span>`;
            docList.appendChild(docItem);
            const formData = new FormData();
            formData.append('files', file);
            formData.append('topic', kbName);
            try {
                await apiUpload(API_ENDPOINTS.uploadDocuments, formData);
                docItem.classList.remove('loading');
                docItem.classList.add('loaded');
                docItem.querySelector('.doc-status').textContent = 'Listo';
                docItem.querySelector('.doc-icon').textContent = '✅';
            } catch (e) {
                docItem.classList.remove('loading');
                docItem.classList.add('error');
                docItem.querySelector('.doc-status').textContent = 'Error';
                docItem.querySelector('.doc-icon').textContent = '❌';
            }
        }
        setTimeout(() => {
            uploadBtn.classList.add('move-bottom');
            uploadBtn.disabled = false;
            uploadBtn.textContent = 'Subir documentos';
            loadDocuments();
        }, 500);
    });

    loadDocuments();
});
