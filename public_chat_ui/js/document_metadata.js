import { API_BASE_URL, authToken } from './api.js';

export async function apiUpdateDocumentMetadata(fileName, newTitle, newTopic) {
    const formData = new FormData();
    formData.append('file_name', fileName);
    if (newTitle !== undefined) formData.append('new_title', newTitle);
    if (newTopic !== undefined) formData.append('new_topic', newTopic);
    const headers = {};
    if (authToken) headers['Authorization'] = `Bearer ${authToken}`;
    const response = await fetch(`${API_BASE_URL}/api/update-document-metadata`, {
        method: 'POST',
        headers,
        body: formData
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Error actualizando metadatos');
    return data;
}
