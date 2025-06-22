// public_chat_ui/js/kb_create.js

document.addEventListener('DOMContentLoaded', () => {
    const backToDocsBtn = document.getElementById('back-to-docs-btn');
    if (backToDocsBtn) {
        backToDocsBtn.addEventListener('click', () => {
            window.location.href = 'documentos.html';
        });
    }
    const kbCreateBtn = document.getElementById('kb-create-confirm-btn');
    if (kbCreateBtn) {
        kbCreateBtn.addEventListener('click', () => {
            const kbName = document.getElementById('kb-name-input').value.trim();
            if (kbName) {
                window.location.href = `kb_upload.html?kb=${encodeURIComponent(kbName)}`;
            } else {
                alert('Por favor, ingresa un nombre para la base de conocimientos.');
            }
        });
    }
});
