// webapp/script.js - Versión FINAL Completa con Gestor de Notas

document.addEventListener('DOMContentLoaded', function () {
    // --- 1. INICIALIZACIÓN Y VERIFICACIÓN ---
    if (!window.Telegram || !window.Telegram.WebApp) {
        console.error("SDK de Telegram no encontrado.");
        document.body.innerHTML = '<h1>Error</h1><p>No se pudo cargar el SDK de Telegram.</p>';
        return;
    }
    const tg = window.Telegram.WebApp;

    // --- 2. REFERENCIAS A ELEMENTOS ---
    const elements = {
        views: document.querySelectorAll('.view'),
        iconButtons: document.querySelectorAll('.icon-button'),
        backButtons: document.querySelectorAll('.back-button'),
        
        // Personalización
        promptInput: document.getElementById('system-prompt-input'),
        restoreButton: document.getElementById('restore-default-button'),
        personalizationLoader: document.getElementById('personalization-loader'),
        
        // Documentos
        uploadForm: document.getElementById('upload-form'),
        fileInput: document.getElementById('file-input'),
        topicInput: document.getElementById('topic-input'),
        fileList: document.getElementById('file-list'),
        uploadLoader: document.getElementById('upload-loader'),
        docListContainer: document.getElementById('document-list-container'),
        docListLoader: document.getElementById('doc-list-loader'),
        noDocsMessage: document.getElementById('no-docs-message'),
        
        // Agenda
        eventListContainer: document.getElementById('event-list-container'),
        eventListLoader: document.getElementById('event-list-loader'),
        noEventsMessage: document.getElementById('no-events-message'),
        addEventBtn: document.getElementById('add-event-btn'),
        addEventModal: document.getElementById('add-event-modal'),
        closeEventModalBtn: document.getElementById('close-event-modal-btn'),
        addEventForm: document.getElementById('add-event-form'),
        eventDescriptionInput: document.getElementById('event-description-input'),
        eventDatetimeInput: document.getElementById('event-datetime-input'),
        eventReminderSelect: document.getElementById('event-reminder-select'),

        // Notas
        noteListContainer: document.getElementById('note-list-container'),
        noteListLoader: document.getElementById('note-list-loader'),
        noNotesMessage: document.getElementById('no-notes-message'),
        addNoteBtn: document.getElementById('add-note-btn'),
        noteModal: document.getElementById('note-modal'),
        noteModalTitle: document.getElementById('note-modal-title'),
        closeNoteModalBtn: document.getElementById('close-note-modal-btn'),
        noteForm: document.getElementById('note-form'),
        noteIdInput: document.getElementById('note-id-input'),
        noteTitleInput: document.getElementById('note-title-input'),
        noteContentInput: document.getElementById('note-content-input'),
        noteCategoryInput: document.getElementById('note-category-input'),
        llmOutput: document.getElementById('llm-output'), // Nuevo elemento para la respuesta del LLM
    };

    // --- 3. GESTIÓN DE WEBSOCKETS ---
    let websocket;
    let currentLlmResponse = ""; // Para acumular la respuesta del LLM

    function connectWebSocket() {
        if (!tg.initDataUnsafe || !tg.initDataUnsafe.user || !tg.initData) {
            console.error("Datos de usuario de Telegram o initData no disponibles para WebSocket.");
            return;
        }

        const userId = tg.initDataUnsafe.user.id;
        const token = tg.initData; // initData contiene el token de autenticación
        // Ajusta la URL si es necesario. Asumiendo que el backend está en el mismo host y puerto 8000
        const wsUrl = `ws://${window.location.hostname}:8000/ws/${userId}?token=${token}`;

        websocket = new WebSocket(wsUrl);

        websocket.onopen = function(event) {
            console.log("WebSocket conectado:", event);
            elements.llmOutput.innerHTML = "Conectado al LLM. Esperando respuesta...";
            currentLlmResponse = "";
        };

        websocket.onmessage = function(event) {
            const message = JSON.parse(event.data);
            console.log("Mensaje WebSocket recibido:", message);

            switch (message.type) {
                case "llm_start":
                    currentLlmResponse = "";
                    elements.llmOutput.innerHTML = "El agente está pensando...";
                    break;
                case "llm_chunk":
                    currentLlmResponse += message.chunk;
                    elements.llmOutput.innerHTML = currentLlmResponse;
                    break;
                case "llm_end":
                    elements.llmOutput.innerHTML = currentLlmResponse + "<br>Respuesta completada.";
                    // Aquí podrías manejar tool_code y sources si los necesitas en el frontend
                    break;
                case "llm_error":
                    elements.llmOutput.innerHTML = `Error del LLM: ${message.message}`;
                    break;
                case "llm_status":
                    elements.llmOutput.innerHTML = message.message;
                    break;
                case "tool_code":
                    // Mostrar el código de la herramienta si es relevante para el usuario
                    console.log("Código de herramienta:", message.tool_code);
                    break;
                case "tool_status":
                    // Actualizar el estado de la herramienta
                    console.log(`Estado de herramienta: ${message.tool_name} - ${message.status}`);
                    break;
                default:
                    console.log("Tipo de mensaje desconocido:", message.type);
            }
        };

        websocket.onclose = function(event) {
            console.log("WebSocket desconectado:", event);
            elements.llmOutput.innerHTML = "WebSocket desconectado. Reconectando en 5 segundos...";
            setTimeout(connectWebSocket, 5000); // Intentar reconectar
        };

        websocket.onerror = function(error) {
            console.error("WebSocket error:", error);
            elements.llmOutput.innerHTML = "Error en la conexión WebSocket.";
            websocket.close();
        };
    }

    let initialPrompt = '';

    // --- 4. FUNCIÓN CENTRAL PARA LLAMADAS A LA API ---
    async function apiFetch(endpoint, method = 'GET', body = null) {
        if (!tg.initData) throw new Error("Datos de usuario de Telegram no disponibles.");

        const headers = {
            'X-Telegram-Init-Data': tg.initData,
        };

        let fetchOptions = { method, headers };
        if (body instanceof FormData) {
            fetchOptions.body = body;
        } else if (body) {
            headers['Content-Type'] = 'application/json';
            fetchOptions.body = JSON.stringify(body);
        }

        const response = await fetch(endpoint, fetchOptions);
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || 'Error en el servidor.');
        return data;
    }

    // Adaptar apiPost a la nueva apiFetch para compatibilidad con llamadas existentes
    async function apiPost(endpoint, formData) {
        return apiFetch(endpoint, 'POST', formData);
    }

    // --- 5. LÓGICA DE NAVEGACIÓN ---
    function showView(viewId) {
        // tg.showAlert("Mostrando vista: " + viewId); // Comentado para reducir alertas
        elements.views.forEach(view => {
            view.classList.toggle('active', view.id === viewId);
            // tg.showAlert("Vista " + view.id + " activa: " + view.classList.contains('active')); // Comentado para reducir alertas
        });
        updateMainButton(viewId);

        if (viewId === 'personalization-screen') loadPrompt();
        if (viewId === 'upload-screen') loadDocuments();
        if (viewId === 'agenda-screen') loadEvents();
        if (viewId === 'notes-screen') loadNotes();
    }
    console.log("Adjuntando eventListeners a iconButtons");
    elements.iconButtons.forEach(button => {
        button.addEventListener('click', () => showView(button.dataset.targetView));
    });
    elements.backButtons.forEach(button => {
        button.addEventListener('click', () => showView('home-screen'));
    });

    // --- 6. LÓGICA DEL BOTÓN PRINCIPAL DE TELEGRAM ---
    function updateMainButton(currentViewId) {
        tg.MainButton.hide();
        if (currentViewId === 'personalization-screen' && elements.promptInput.value.trim() !== initialPrompt.trim()) {
            tg.MainButton.setText('Guardar Personalidad').show();
        } else if (currentViewId === 'upload-screen' && elements.uploadForm.checkValidity()) {
            tg.MainButton.setText(`Subir ${elements.fileInput.files.length} archivo(s)`).show();
        }
    }

    tg.onEvent('mainButtonClicked', function() {
        const activeView = document.querySelector('.view.active');
        if (!activeView) return;
        if (activeView.id === 'personalization-screen') handleSavePrompt();
        if (activeView.id === 'upload-screen') handleUpload();
    });

    // --- 7. FUNCIONALIDAD DE PERSONALIZACIÓN ---
    async function loadPrompt() {
        elements.personalizationLoader.classList.remove('hidden');
        elements.restoreButton.classList.add('hidden');
        try {
            // Usar apiFetch para GET
            const data = await apiFetch('/api/get-system-prompt', 'POST'); // Cambiado a POST según api/auth.py
            elements.promptInput.value = data.prompt;
            initialPrompt = data.prompt;
            elements.restoreButton.classList.toggle('hidden', !data.is_custom);
        } catch (e) { tg.showAlert(e.message); }
        finally { elements.personalizationLoader.classList.add('hidden'); }
    }

    async function handleSavePrompt() {
        tg.MainButton.showProgress();
        try {
            const formData = new FormData();
            formData.append('system_prompt', elements.promptInput.value);
            // Usar apiPost para POST
            await apiPost('/api/save-system-prompt', formData);
            await loadPrompt();
            tg.showAlert('Prompt guardado.');
            updateMainButton('personalization-screen');
        } catch (e) { tg.showAlert(e.message); }
        finally { tg.MainButton.hideProgress(); }
    }
    
    elements.restoreButton.addEventListener('click', () => {
        tg.showConfirm("¿Restaurar el prompt por defecto?", async (confirmed) => {
            if (confirmed) {
                elements.promptInput.value = '';
                await handleSavePrompt();
            }
        });
    });
    elements.promptInput.addEventListener('input', () => updateMainButton('personalization-screen'));

    // --- 8. FUNCIONALIDAD DEL GESTOR DE DOCUMENTOS ---
    function updateFileListUI() {
        elements.fileList.innerHTML = '';
        Array.from(elements.fileInput.files).forEach(file => {
            const item = document.createElement('div');
            item.className = 'file-item';
            item.innerHTML = `<span class="file-name">${file.name}</span><span class="file-size">${(file.size/1024).toFixed(1)}KB</span>`;
            elements.fileList.appendChild(item);
        });
        updateMainButton('upload-screen');
    }

    async function handleUpload() {
        if (!elements.uploadForm.checkValidity()) return tg.showAlert('Por favor, completa todos los campos.');
        tg.MainButton.showProgress();
        elements.uploadLoader.classList.remove('hidden');
        try {
            const formData = new FormData();
            Array.from(elements.fileInput.files).forEach(file => formData.append('files', file));
            formData.append('topic', elements.topicInput.value);
            const data = await apiPost('/api/documents/upload-document', formData); // Actualizado el endpoint
            tg.showAlert(data.message, async () => {
                elements.uploadForm.reset();
                updateFileListUI();
                await loadDocuments();
            });
        } catch (e) { tg.showAlert(e.message); }
        finally {
            tg.MainButton.hideProgress();
            elements.uploadLoader.classList.add('hidden');
        }
    }

    async function loadDocuments() {
        elements.docListLoader.classList.remove('hidden');
        elements.docListContainer.innerHTML = '';
        elements.noDocsMessage.classList.add('hidden');
        try {
            // Usar apiFetch para GET, ya que list-documents en api/documents.py es GET
            const documents = await apiFetch('/api/documents/list-documents'); // Actualizado el endpoint
            if (documents.length === 0) {
                elements.noDocsMessage.classList.remove('hidden');
            } else {
                documents.forEach(doc => {
                    const docEl = document.createElement('div');
                    docEl.className = 'doc-item';
                    docEl.innerHTML = `
                        <div class="doc-item-header"><span class="doc-title editable" data-filename="${doc.file_name}">${doc.title || doc.file_name}</span></div>
                        <div class="doc-meta"><span>Tema: <span class="doc-topic editable" data-filename="${doc.file_name}">${doc.topic || 'N/A'}</span></span></div>
                        <div class="doc-actions">
                            <button class="edit-btn" title="Editar" data-filename="${doc.file_name}">✏️</button>
                            <button class="delete-btn" title="Eliminar" data-filename="${doc.file_name}">🗑️</button>
                        </div>
                    `;
                    docEl.querySelector('.delete-btn').addEventListener('click', handleDeleteDocument);
                    docEl.querySelector('.edit-btn').addEventListener('click', () => handleEditDocument(doc));
                    docEl.querySelector('.doc-title').addEventListener('click', () => handleEditDocument(doc, 'title'));
                    docEl.querySelector('.doc-topic').addEventListener('click', () => handleEditDocument(doc, 'topic'));
                    elements.docListContainer.appendChild(docEl);
                });
            }
        } catch (e) { tg.showAlert('Error al cargar documentos: ' + e.message); }
        finally { elements.docListLoader.classList.add('hidden'); }
    }

    async function handleDeleteDocument(event) {
        const fileName = event.currentTarget.dataset.filename;
        tg.showConfirm(`¿Eliminar '${fileName}'? Esta acción es irreversible.`, async (confirmed) => {
            if (confirmed) {
                try {
                    // delete-document en api/documents.py es POST y espera un JSON en el body
                    const result = await apiFetch('/api/documents/delete-document', 'POST', { file_name: fileName }); // Actualizado el endpoint y el body
                    tg.showAlert(result.message);
                    await loadDocuments();
                } catch (e) { tg.showAlert('Error al eliminar: ' + e.message); }
            }
        });
    }

    async function handleEditDocument(doc, field) {
        let newTitle = doc.title;
        let newTopic = doc.topic;
        if (!field || field === 'title') {
            newTitle = prompt('Nuevo título para el documento:', doc.title || doc.file_name);
            if (!newTitle || newTitle === doc.title) return;
        }
        if (!field || field === 'topic') {
            newTopic = prompt('Nueva categoría/base de conocimiento:', doc.topic || '');
            if (!newTopic || newTopic === doc.topic) return;
        }
        try {
            // update-document-metadata en api/documents.py es POST y espera un JSON en el body
            const body = { file_name: doc.file_name };
            if (newTitle && newTitle !== doc.title) body.new_title = newTitle;
            if (newTopic && newTopic !== doc.topic) body.new_topic = newTopic;
            await apiFetch('/api/documents/update-document-metadata', 'POST', body); // Actualizado el endpoint y el body
            tg.showAlert('Metadatos actualizados.');
            await loadDocuments();
        } catch (e) {
            tg.showAlert('Error al actualizar metadatos: ' + e.message);
        }
    }

    elements.fileInput.addEventListener('change', updateFileListUI);
    elements.topicInput.addEventListener('input', () => updateMainButton('upload-screen'));
    
    // --- 9. FUNCIONALIDAD DEL GESTOR DE AGENDA ---
    async function loadEvents() {
        elements.eventListLoader.classList.remove('hidden');
        elements.eventListContainer.innerHTML = '';
        elements.noEventsMessage.classList.add('hidden');
        try {
            // list-events en api/agenda.py es POST y espera un JSON en el body
            const events = await apiFetch('/api/list-events', 'POST', {}); // Actualizado el endpoint y el body
            if (events.length === 0) {
                elements.noEventsMessage.classList.remove('hidden');
            } else {
                events.forEach(event => {
                    const eventEl = document.createElement('div');
                    eventEl.className = 'event-item';
                    const localDate = new Date(event.event_datetime_utc);
                    const day = localDate.getDate();
                    const month = localDate.toLocaleString('es-ES', { month: 'short' });
                    const time = localDate.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
                    eventEl.innerHTML = `
                        <div class="event-date"><span class="event-day">${day}</span><span class="event-month">${month}</span></div>
                        <div class="event-details">
                            <span class="event-description">${event.description}</span>
                            <span class="event-time">${time} (${event.user_timezone})</span>
                        </div>
                        <button class="event-cancel-btn" title="Cancelar Evento" data-event-id="${event.id}">×</button>
                    `;
                    eventEl.querySelector('.event-cancel-btn').addEventListener('click', handleCancelEvent);
                    elements.eventListContainer.appendChild(eventEl);
                });
            }
        } catch (e) { tg.showAlert('Error al cargar eventos: ' + e.message); }
        finally { elements.eventListLoader.classList.add('hidden'); }
    }

    async function handleCancelEvent(event) {
        const eventId = event.currentTarget.dataset.eventId;
        tg.showConfirm(`¿Estás seguro de que quieres cancelar este evento?`, async (confirmed) => {
            if (confirmed) {
                try {
                    // cancel-event en api/agenda.py es POST y espera un JSON en el body
                    const result = await apiFetch('/api/cancel-event', 'POST', { event_id: eventId }); // Actualizado el endpoint y el body
                    tg.showAlert(result.message);
                    await loadEvents();
                } catch (e) { tg.showAlert('Error al cancelar: ' + e.message); }
            }
        });
    }

    function openAddEventModal() {
        const now = new Date();
        now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
        elements.eventDatetimeInput.value = now.toISOString().slice(0, 16);
        elements.addEventModal.classList.remove('hidden');
        document.body.classList.add('modal-open');
    }

    function closeAddEventModal() {
        elements.addEventModal.classList.add('hidden');
        document.body.classList.remove('modal-open');
    }

    async function handleAddEvent(event) {
        event.preventDefault();
        const description = elements.eventDescriptionInput.value;
        const localDatetime = elements.eventDatetimeInput.value;
        const reminderOffset = elements.eventReminderSelect.value;
        if (!description || !localDatetime) return tg.showAlert('Por favor, completa todos los campos.');

        const eventDate = new Date(localDatetime);
        const eventISODatetime = eventDate.toISOString();

        tg.MainButton.showProgress();
        try {
            // add-event en api/agenda.py es POST y espera un JSON en el body
            const result = await apiFetch('/api/add-event', 'POST', {
                summary: description, // Asumo que la descripción es el summary
                description: description,
                event_date: eventDate.toISOString().slice(0, 10), // Extraer solo la fecha
                event_time: eventDate.toISOString().slice(11, 16), // Extraer solo la hora
                reminder_offset_minutes: parseInt(reminderOffset),
            }); // Actualizado el endpoint y el body
            tg.showAlert(result.message, async () => {
                closeAddEventModal();
                await loadEvents();
            });
        } catch (e) { tg.showAlert('Error al añadir evento: ' + e.message); }
        finally { tg.MainButton.hideProgress(); }
    }

    elements.addEventBtn.addEventListener('click', openAddEventModal);
    elements.closeEventModalBtn.addEventListener('click', closeAddEventModal);
    elements.addEventForm.addEventListener('submit', handleAddEvent);
    elements.addEventModal.addEventListener('click', (e) => { if (e.target === elements.addEventModal) closeAddEventModal(); });

    // --- 10. FUNCIONALIDAD DEL GESTOR DE NOTAS ---
    async function loadNotes() {
        elements.noteListLoader.classList.remove('hidden');
        elements.noteListContainer.innerHTML = '';
        elements.noNotesMessage.classList.add('hidden');
        try {
            // list-notes en api/notes.py es POST y espera un JSON en el body
            const notes = await apiFetch('/api/notes/list-notes', 'POST', {}); // Actualizado el endpoint y el body
            if (notes.length === 0) {
                elements.noNotesMessage.classList.remove('hidden');
            } else {
                notes.notes.forEach(note => { // Acceder a notes.notes por la paginación
                    const noteEl = document.createElement('div');
                    noteEl.className = 'note-item';
                    noteEl.innerHTML = `
                        <div class="note-header">
                            <span class="note-title">${note.title || 'Nota sin título'}</span>
                            ${note.category ? `<span class="note-category">${note.category}</span>` : ''}
                        </div>
                        <p class="note-content">${note.content}</p>
                        <div class="note-actions">
                            <button class="edit-btn" title="Editar Nota">✏️</button>
                            <button class="delete-btn" title="Eliminar Nota">🗑️</button>
                        </div>
                    `;
                    noteEl.querySelector('.edit-btn').addEventListener('click', () => openNoteModal(note));
                    noteEl.querySelector('.delete-btn').addEventListener('click', () => handleDeleteNote(note.id));
                    elements.noteListContainer.appendChild(noteEl);
                });
            }
        } catch (e) { tg.showAlert('Error al cargar notas: ' + e.message); }
        finally { elements.noteListLoader.classList.add('hidden'); }
    }

    function openNoteModal(note = null) {
        elements.noteForm.reset();
        if (note) {
            elements.noteModalTitle.innerText = 'Editar Nota';
            elements.noteIdInput.value = note.id;
            elements.noteTitleInput.value = note.title || '';
            elements.noteContentInput.value = note.content || '';
            elements.noteCategoryInput.value = note.category || '';
        } else {
            elements.noteModalTitle.innerText = 'Añadir Nueva Nota';
            elements.noteIdInput.value = '';
        }
        elements.noteModal.classList.remove('hidden');
        document.body.classList.add('modal-open');
    }

    function closeNoteModal() {
        elements.noteModal.classList.add('hidden');
        document.body.classList.remove('modal-open');
    }

    async function handleNoteFormSubmit(event) {
        event.preventDefault();
        const noteId = elements.noteIdInput.value;
        
        // add-note y update-note en api/notes.py son POST y esperan un JSON en el body
        const body = {
            title: elements.noteTitleInput.value,
            content: elements.noteContentInput.value,
            category: elements.noteCategoryInput.value,
        };

        const endpoint = noteId ? '/api/update-note' : '/api/add-note';
        if (noteId) {
            body.note_id = parseInt(noteId); // Convertir a entero
        }

        tg.MainButton.showProgress();
        try {
            const result = await apiFetch(endpoint, 'POST', body); // Actualizado el endpoint y el body
            tg.showAlert(result.message, async () => {
                closeNoteModal();
                await loadNotes();
            });
        } catch (e) {
            tg.showAlert('Error al guardar la nota: ' + e.message);
        } finally {
            tg.MainButton.hideProgress();
        }
    }

    async function handleDeleteNote(noteId) {
        tg.showConfirm('¿Estás seguro de que quieres eliminar esta nota?', async (confirmed) => {
            if (confirmed) {
                try {
                    // delete-note en api/notes.py es POST y espera un JSON en el body
                    const result = await apiFetch('/api/delete-note', 'POST', { note_id: noteId }); // Actualizado el endpoint y el body
                    tg.showAlert(result.message);
                    await loadNotes();
                } catch (e) {
                    tg.showAlert('Error al eliminar: ' + e.message);
                }
            }
        });
    }

    elements.addNoteBtn.addEventListener('click', () => openNoteModal());
    elements.closeNoteModalBtn.addEventListener('click', closeNoteModal);
    elements.noteModal.addEventListener('click', (e) => { if (e.target === elements.noteModal) closeNoteModal(); });
    elements.noteForm.addEventListener('submit', handleNoteFormSubmit);

    // --- 11. INICIO DE LA APLICACIÓN ---
    tg.ready(() => {
        tg.expand();
        showView('home-screen');
    });
});nada