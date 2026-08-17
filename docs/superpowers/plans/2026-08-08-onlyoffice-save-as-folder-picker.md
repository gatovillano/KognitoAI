# OnlyOffice Save As Folder Picker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow users editing or viewing documents in Documentos Cloud to save copies or convert document formats (e.g., DOCX to PDF) directly into a chosen folder in their cloud storage via a folder picker dialog.

**Architecture:** 
Frontend captures the OnlyOffice `onRequestSaveAs` event (and adds list action triggers) to pop up a `SaveAsFolderModal`. The modal collects the target filename, output extension, destination folder ID, and workspace ID, then calls the backend `POST /api/onlyoffice/save-as-copy` endpoint. The backend fetches/converts the document (using OnlyOffice `ConvertService` or direct download), stores it in user cloud storage, and creates a new `Document` DB record.

**Tech Stack:** Next.js (React, Tailwind CSS, Lucide icons, Radix UI Dialog & Select), FastAPI, SQLAlchemy (AsyncSession), OnlyOffice DocsAPI & ConvertService, httpx.

## Global Constraints
- Target workspace path: `/home/gato/Proyectos/KognitoAI/kognito-ai`
- Frontend file: `src/app/(dashboard)/documents/page.tsx`
- Backend file: `api/onlyoffice.py`
- Preservation of existing permissions and RAG indexing workflow.

---

### Task 1: Backend Save-As & Conversion Endpoint

**Files:**
- Modify: `api/onlyoffice.py:72-110` (Add `SaveAsCopyRequest` model)
- Modify: `api/onlyoffice.py:2000-2087` (Add `save_as_copy` endpoint & conversion helper)

**Interfaces:**
- Consumes: `get_current_account_id`, `get_db_session`, `ensure_onlyoffice_account_dir`, `process_document_for_rag`
- Produces: `POST /api/onlyoffice/save-as-copy` returning JSON dictionary of the created document.

- [ ] **Step 1: Define `SaveAsCopyRequest` Pydantic model**

```python
class SaveAsCopyRequest(BaseModel):
    source_url: Optional[str] = None
    document_id: Optional[str] = None
    filename: str
    folder_id: Optional[str] = None
    workspace_id: Optional[str] = None
    target_extension: str = "pdf"
```

- [ ] **Step 2: Add `POST /api/onlyoffice/save-as-copy` endpoint implementation**

Implement the handler to process `SaveAsCopyRequest`:
- Validate target `folder_id` and `workspace_id` permissions.
- If `source_url` is provided, download binary using `httpx.AsyncClient`.
- Else if `document_id` is provided and conversion is needed, call OnlyOffice `ConvertService.ashx` or duplicate file on disk.
- Save file in user's `ensure_onlyoffice_account_dir(...)` directory.
- Create and commit new `Document` model in database.
- Trigger background RAG processing (`process_document_for_rag`).

- [ ] **Step 3: Test backend syntax and python compilation**

Run: `python3 -m py_compile api/onlyoffice.py`
Expected: Clean exit (0 errors).

- [ ] **Step 4: Commit Task 1**

```bash
git add api/onlyoffice.py
git commit -m "feat(onlyoffice): add save-as-copy backend endpoint and conversion support"
```

---

### Task 2: Frontend OnlyOffice `onRequestSaveAs` Integration & SaveAs Modal

**Files:**
- Modify: `src/app/(dashboard)/documents/page.tsx`

**Interfaces:**
- Consumes: `POST /api/onlyoffice/save-as-copy`, `window.DocsAPI.DocEditor`, `allFolders`
- Produces: `SaveAsFolderModal` UI component, `onRequestSaveAs` event handler.

- [ ] **Step 1: Add modal state variables in `page.tsx`**

Add states:
- `isSaveAsDialogOpen`: boolean
- `saveAsSourceUrl`: string | null
- `saveAsDocId`: string | null
- `saveAsFilename`: string
- `saveAsTargetExtension`: string
- `saveAsTargetFolderId`: string ("null" for root)
- `saveAsTargetWorkspaceId`: string ("none" for default)
- `isSavingAs`: boolean

- [ ] **Step 2: Wire `onRequestSaveAs` in OnlyOffice `initEditor` callback**

Modify `initEditor` in `page.tsx`:
```tsx
const configWithEvents = {
  ...config,
  events: {
    onRequestSaveAs: (event: any) => {
      if (event?.data?.url) {
        setSaveAsSourceUrl(event.data.url);
        setSaveAsDocId(editingDoc?.id || null);
        const title = event.data.title || editingDoc?.filename || "documento_copia";
        const ext = title.split('.').pop() || "pdf";
        setSaveAsFilename(title.replace(/\.[^/.]+$/, ""));
        setSaveAsTargetExtension(ext);
        setIsSaveAsDialogOpen(true);
      }
    }
  }
};
```

- [ ] **Step 3: Add "Guardar como en carpeta..." item to document row actions menu**

Add menu item in file options dropdowns calling `openSaveAsModalForDoc(doc)`.

- [ ] **Step 4: Implement `SaveAsFolderModal` JSX Dialog in `page.tsx`**

Create `Dialog` component rendering:
- Input for filename.
- Select for output extension (`pdf`, `docx`, `xlsx`, `pptx`).
- Select for destination folder (`allFolders` + Root option).
- Quick inline button to create a new folder.
- Button "Guardar en esta carpeta" which calls `apiClient.post('/api/onlyoffice/save-as-copy', ...)`.

- [ ] **Step 5: Verify build of Next.js frontend**

Run: `npx next build` (or verify TypeScript compilation).

- [ ] **Step 6: Commit Task 2**

```bash
git add src/app/\(dashboard\)/documents/page.tsx
git commit -m "feat(documents): add SaveAsFolderModal and OnlyOffice onRequestSaveAs handler"
```
