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
        
    // (Personalización eliminada)
        
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
    // Tareas
    taskListContainer: document.getElementById('task-list-container'),
    taskListLoader: document.getElementById('task-list-loader'),
    noTasksMessage: document.getElementById('no-tasks-message'),
    addTaskBtn: document.getElementById('add-task-btn'),
    // Contactos
    contactListContainer: document.getElementById('contact-list-container'),
    contactListLoader: document.getElementById('contact-list-loader'),
    noContactsMessage: document.getElementById('no-contacts-message'),
    addContactBtn: document.getElementById('add-contact-btn'),
        llmOutput: document.getElementById('llm-output'), // Nuevo elemento para la respuesta del LLM
        chatContainer: document.getElementById('chat-container'), // Contenedor para las burbujas de chat
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
            // Limpiar output anterior y añadir un mensaje de conexión como burbuja del bot
            elements.chatContainer.innerHTML = '';
            appendChatMessage("Conectado al LLM. Esperando respuesta...", 'bot');
            currentLlmResponse = "";
        };

        websocket.onmessage = function(event) {
            const message = JSON.parse(event.data);
            console.log("Mensaje WebSocket recibido:", message);

            switch (message.type) {
                case "llm_start":
                    currentLlmResponse = "";
                    appendChatMessage("El agente está pensando...", 'bot', true); // Se añade como "thinking" bubble
                    break;
                case "llm_chunk":
                    // Actualizar el contenido de la última burbuja del bot
                    updateLastBotBubble(message.chunk);
                    currentLlmResponse += message.chunk;
                    break;
                case "llm_end":
                    // Marcar la última burbuja del bot como completa
                    updateLastBotBubble("Respuesta completada.", false, true);
                    break;
                case "llm_error":
                    appendChatMessage(`Error del LLM: ${message.message}`, 'bot');
                    break;
                case "llm_status":
                    appendChatMessage(message.message, 'bot');
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
            appendChatMessage("WebSocket desconectado. Reconectando en 5 segundos...", 'bot');
            setTimeout(connectWebSocket, 5000); // Intentar reconectar
        };

        websocket.onerror = function(error) {
            console.error("WebSocket error:", error);
            appendChatMessage("Error en la conexión WebSocket.", 'bot');
            websocket.close();
        };
    }

    // --- Nuevas funciones para la gestión de burbujas de chat ---
    function appendChatMessage(message, sender, isThinking = false) {
        const messageWrapper = document.createElement('div');
        messageWrapper.classList.add('chat-bubble', `chat-bubble-${sender}`);
        if (isThinking) {
            messageWrapper.classList.add('thinking-bubble');
            messageWrapper.innerHTML = `<div class="chat-sender">${sender === 'user' ? 'Tú' : 'Agente'}</div><div class="chat-content">...</div>`;
        } else {
            messageWrapper.innerHTML = `<div class="chat-sender">${sender === 'user' ? 'Tú' : 'Agente'}</div><div class="chat-content">${message}</div>`;
        }
        elements.chatContainer.appendChild(messageWrapper);
        elements.chatContainer.scrollTop = elements.chatContainer.scrollHeight; // Auto-scroll
    }

    function updateLastBotBubble(chunk, append = true, isEnd = false) {
        const botBubbles = elements.chatContainer.querySelectorAll('.chat-bubble-bot');
        if (botBubbles.length > 0) {
            const lastBotBubble = botBubbles[botBubbles.length - 1];
            const chatContent = lastBotBubble.querySelector('.chat-content');
            if (chatContent) {
                if (append) {
                    chatContent.innerHTML += chunk;
                } else {
                    chatContent.innerHTML = chunk;
                }
                if (isEnd) {
                    lastBotBubble.classList.remove('thinking-bubble');
                }
                elements.chatContainer.scrollTop = elements.chatContainer.scrollHeight; // Auto-scroll
            }
        }
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
        // Buscar dinámicamente todas las vistas en el DOM
        const allViews = document.querySelectorAll('.view');
        console.log('showView: encontradas', allViews.length, 'vistas, buscando:', viewId);
        allViews.forEach(view => {
            const shouldBeActive = view.id === viewId;
            view.classList.toggle('active', shouldBeActive);
            console.log('  vista', view.id, '-> active:', shouldBeActive);
        });
        updateMainButton(viewId);

        // removed personalization-screen handler
        if (viewId === 'upload-screen') loadDocuments();
        if (viewId === 'agenda-screen') loadEvents();
        if (viewId === 'notes-screen') loadNotes();
        if (viewId === 'tasks-screen') loadTasks();
        if (viewId === 'contacts-screen') loadContacts();
        console.log('showView ->', viewId);
    }
    if (elements.iconButtons && elements.iconButtons.length) {
        console.log("Adjuntando eventListeners a iconButtons (count=", elements.iconButtons.length, ")");
        elements.iconButtons.forEach(button => {
        // make icon buttons accessible
        button.setAttribute('role', 'button');
        button.setAttribute('tabindex', '0');
        button.style.cursor = 'pointer';
        button.addEventListener('click', (ev) => { console.log('icon-button clicked, targetView=', button.dataset.targetView); showView(button.dataset.targetView); });
        button.addEventListener('keydown', (ev) => { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); showView(button.dataset.targetView); } });
        });
    } else {
        console.warn('No se encontraron iconButtons en el DOM');
    }
    if (elements.backButtons && elements.backButtons.length) {
        elements.backButtons.forEach(button => {
            button.addEventListener('click', () => showView('home-screen'));
        });
    } else {
        console.warn('No se encontraron backButtons en el DOM');
    }

    // --- 6. LÓGICA DEL BOTÓN PRINCIPAL DE TELEGRAM ---
    function updateMainButton(currentViewId) {
        tg.MainButton.hide();
        if (currentViewId === 'upload-screen' && elements.uploadForm && elements.uploadForm.checkValidity()) {
            tg.MainButton.setText(`Subir ${elements.fileInput.files.length} archivo(s)`).show();
        }
    }

    tg.onEvent('mainButtonClicked', function() {
        const activeView = document.querySelector('.view.active');
        if (!activeView) return;
        if (activeView.id === 'upload-screen') handleUpload();
    });

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

    // --- 10. FUNCIONALIDAD DE TAREAS ---
    async function loadTasks() {
        elements.taskListLoader.classList.remove('hidden');
        elements.taskListContainer.innerHTML = '';
        elements.noTasksMessage.classList.add('hidden');
        try {
            const tasks = await apiFetch('/api/tasks');
            if (!tasks || tasks.length === 0) {
                elements.noTasksMessage.classList.remove('hidden');
                return;
            }
            tasks.forEach(t => {
                const el = document.createElement('div');
                el.className = 'task-item';
                el.innerHTML = `
                    <div class="task-left">
                        <input type="checkbox" class="task-complete" data-id="${t.id}" ${t.is_completed ? 'checked' : ''}>
                    </div>
                    <div class="task-body">
                        <div class="task-desc">${t.description}</div>
                        <div class="task-meta">${t.end_date ? new Date(t.end_date).toLocaleString() : ''}</div>
                    </div>
                    <div class="task-actions">
                        <button class="task-edit" data-id="${t.id}">✎</button>
                        <button class="task-delete" data-id="${t.id}">🗑</button>
                    </div>
                `;
                el.querySelector('.task-complete').addEventListener('change', handleToggleTask);
                el.querySelector('.task-edit').addEventListener('click', () => handleEditTask(t));
                el.querySelector('.task-delete').addEventListener('click', () => handleDeleteTask(t.id));
                elements.taskListContainer.appendChild(el);
            });
        } catch (e) { tg.showAlert('Error al cargar tareas: ' + e.message); }
        finally { elements.taskListLoader.classList.add('hidden'); }
    }

    async function handleToggleTask(e) {
        const id = e.currentTarget.dataset.id;
        const completed = e.currentTarget.checked;
        try {
            await apiFetch(`/api/tasks/${id}`, 'PUT', { is_completed: completed });
            await loadTasks();
        } catch (err) { tg.showAlert('Error al actualizar la tarea: ' + err.message); }
    }

    // Modal wiring for tasks
    const taskModal = document.getElementById('task-modal');
    const taskForm = document.getElementById('task-form');
    const taskIdInput = document.getElementById('task-id-input');
    const taskDescInput = document.getElementById('task-desc-input');
    const taskDueInput = document.getElementById('task-due-input');
    const closeTaskModalBtn = document.getElementById('close-task-modal-btn');

    function openTaskModal(task) {
        if (task) {
            taskIdInput.value = task.id;
            taskDescInput.value = task.description || '';
            taskDueInput.value = task.end_date ? new Date(task.end_date).toISOString().slice(0,16) : '';
            document.getElementById('task-modal-title').innerText = 'Editar Tarea';
        } else {
            taskIdInput.value = '';
            taskDescInput.value = '';
            taskDueInput.value = '';
            document.getElementById('task-modal-title').innerText = 'Añadir Tarea';
        }
        taskModal.classList.remove('hidden');
        document.body.classList.add('modal-open');
    }

    function closeTaskModal() {
        taskModal.classList.add('hidden');
        document.body.classList.remove('modal-open');
    }

    closeTaskModalBtn.addEventListener('click', closeTaskModal);

    taskForm.addEventListener('submit', async (ev) => {
        ev.preventDefault();
        const id = taskIdInput.value;
        const payload = { description: taskDescInput.value };
        if (taskDueInput.value) payload.end_date = new Date(taskDueInput.value).toISOString();
        try {
            if (id) {
                await apiFetch(`/api/tasks/${id}`, 'PUT', payload);
            } else {
                await apiFetch('/api/tasks', 'POST', payload);
            }
            closeTaskModal();
            await loadTasks();
        } catch (e) { tg.showAlert('Error al guardar tarea: ' + e.message); }
    });

    elements.addTaskBtn && elements.addTaskBtn.addEventListener('click', () => openTaskModal(null));

    async function handleEditTask(task) { openTaskModal(task); }

    async function handleDeleteTask(taskId) {
        if (!confirm('¿Eliminar tarea?')) return;
        try {
            await fetch(`/api/tasks/${taskId}`, { method: 'DELETE', headers: { 'X-Telegram-Init-Data': tg.initData } });
            await loadTasks();
        } catch (e) { tg.showAlert('Error al eliminar tarea: ' + e.message); }
    }

    // --- 11. FUNCIONALIDAD DE CONTACTOS ---
    async function loadContacts() {
        elements.contactListLoader.classList.remove('hidden');
        elements.contactListContainer.innerHTML = '';
        elements.noContactsMessage.classList.add('hidden');
        try {
            const contacts = await apiFetch('/api/list-contact-profiles', 'POST', {});
            if (!contacts || contacts.length === 0) {
                elements.noContactsMessage.classList.remove('hidden');
                return;
            }
            contacts.forEach(c => {
                const el = document.createElement('div');
                el.className = 'contact-item';
                el.innerHTML = `
                    <div class="contact-left">
                        <div class="contact-name">${c.name || 'Sin nombre'}</div>
                        <div class="contact-meta">${c.email || ''} ${c.phone ? '· ' + c.phone : ''}</div>
                    </div>
                    <div class="contact-actions">
                        <button class="contact-edit" data-id="${c.id}">✎</button>
                        <button class="contact-delete" data-id="${c.id}">🗑</button>
                    </div>
                `;
                el.querySelector('.contact-edit').addEventListener('click', () => handleEditContact(c));
                el.querySelector('.contact-delete').addEventListener('click', () => handleDeleteContact(c.id));
                elements.contactListContainer.appendChild(el);
            });
        } catch (e) { tg.showAlert('Error al cargar contactos: ' + e.message); }
        finally { elements.contactListLoader.classList.add('hidden'); }
    }

    // Modal wiring for contacts
    const contactModal = document.getElementById('contact-modal');
    const contactForm = document.getElementById('contact-form');
    const contactIdInput = document.getElementById('contact-id-input');
    const contactNameInput = document.getElementById('contact-name-input');
    const contactEmailInput = document.getElementById('contact-email-input');
    const contactPhoneInput = document.getElementById('contact-phone-input');
    const closeContactModalBtn = document.getElementById('close-contact-modal-btn');

    function openContactModal(contact) {
        if (contact) {
            contactIdInput.value = contact.id;
            contactNameInput.value = contact.name || '';
            contactEmailInput.value = contact.email || '';
            contactPhoneInput.value = contact.phone || '';
            document.getElementById('contact-modal-title').innerText = 'Editar Contacto';
        } else {
            contactIdInput.value = '';
            contactNameInput.value = '';
            contactEmailInput.value = '';
            contactPhoneInput.value = '';
            document.getElementById('contact-modal-title').innerText = 'Añadir Contacto';
        }
        contactModal.classList.remove('hidden');
        document.body.classList.add('modal-open');
    }

    function closeContactModal() {
        contactModal.classList.add('hidden');
        document.body.classList.remove('modal-open');
    }

    closeContactModalBtn.addEventListener('click', closeContactModal);

    contactForm.addEventListener('submit', async (ev) => {
        ev.preventDefault();
        const id = contactIdInput.value;
        const payload = { name: contactNameInput.value, email: contactEmailInput.value, phone: contactPhoneInput.value };
        try {
            if (id) {
                await apiFetch(`/api/update-contact-profile/${id}`, 'POST', payload);
            } else {
                await apiFetch('/api/create-contact-profile', 'POST', payload);
            }
            closeContactModal();
            await loadContacts();
        } catch (e) { tg.showAlert('Error al guardar contacto: ' + e.message); }
    });

    elements.addContactBtn && elements.addContactBtn.addEventListener('click', () => openContactModal(null));

    async function handleEditContact(contact) { openContactModal(contact); }

    async function handleDeleteContact(contactId) {
        if (!confirm('¿Eliminar perfil de contacto?')) return;
        try {
            await apiFetch('/api/delete-contact-profile', 'POST', { profile_id: contactId });
            await loadContacts();
        } catch (e) { tg.showAlert('Error al eliminar contacto: ' + e.message); }
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