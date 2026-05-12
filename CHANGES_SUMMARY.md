# Summary of Changes to Remove Workspace Limit

The user requested to remove the limit of 10 workspaces shown in the dropdown menu for selecting workspaces in the note editing dialog.

## Root Cause
The backend API endpoint `/api/workspaces` has a default `limit` parameter of 10 (with a maximum of 100) for pagination purposes. When frontend applications called this endpoint without specifying a limit parameter, they would only receive the first 10 workspaces.

## Changes Made

Increased the limit parameter to 100 (the maximum allowed by the API) in all frontend locations where workspaces are fetched for display in dropdown menus or lists where users need to see all available workspaces:

1. **src/app/(dashboard)/notes/note-dialog.tsx** - Note editing dialog (primary focus)
   - Added `{ params: { limit: 100 } }` to the API call in `fetchWorkspaces` function

2. **src/hooks/useWorkspaces.ts** - Workspaces hook
   - Added `{ params: { limit: 100 } }` to the API call in `fetchWorkspaces` function

3. **src/contexts/WorkspaceContext.tsx** - Workspace context
   - Added `{ params: { limit: 100 } }` to the API call in `refreshWorkspaces` function

4. **src/app/(dashboard)/rag/edit-collection-dialog.tsx** - Edit collection dialog
   - Added `{ params: { limit: 100 } }` to the API call in `fetchWorkspaces` function

5. **src/app/(dashboard)/rag/share-document-dialog.tsx** - Share document dialog
   - Added `{ params: { limit: 100 } }` to the API call in `fetchWorkspaces` function

6. **src/app/(dashboard)/rag/share-collection-dialog.tsx** - Share collection dialog
   - Added `{ params: { limit: 100 } }` to the API call in `fetchWorkspaces` function

7. **src/app/(dashboard)/settings/page.tsx** - Settings page (sync tab)
   - Added `{ params: { limit: 100 } }` to the API call in `fetchWorkspaces` function

8. **src/app/(dashboard)/notes/edit/[id]/page.tsx** - Note edit page share dialog
   - Added `{ params: { limit: 100 } }` to the API call in `handleShare` function

9. **src/app/(dashboard)/workspaces/[id]/page.tsx** - Workspace dashboard share collection dialog
   - Added `{ params: { limit: 100 } }` to the API call in `loadAvailableWorkspaces` function

10. **src/app/(dashboard)/rag/github-repo-dialog.tsx** - GitHub repo dialog
    - Added `{ params: { limit: 100 } }` to the API call in `fetchData` function

## Note
The documents page (`src/app/(dashboard)/documents/page.tsx`) already implemented proper pagination to fetch all workspaces by looping through pages with a page size of 100, so no changes were needed there.

These changes ensure that users can see up to 100 workspaces in dropdown menus, which should cover virtually all use cases. If a user has more than 100 workspaces, they would need to implement a different solution (like search/filtering), but this is unlikely for typical usage.