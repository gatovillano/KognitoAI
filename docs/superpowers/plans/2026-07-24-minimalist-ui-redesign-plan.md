# Minimalist UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the Kognito AI interface into a ultra-clean, modern, borderless minimalist workspace with subtle glassmorphic touches.

**Architecture:** Update CSS design tokens in `globals.css`, streamline the component hierarchy across `Sidebar.tsx`, `ChatMessage.tsx`, `ChatInputBar.tsx`, `EmptyChat.tsx`, and `AppShell.tsx`, removing harsh borders, heavy shadows, and visual clutter.

**Tech Stack:** Next.js (React), Tailwind CSS, Lucide React icons, shadcn/ui primitives.

## Global Constraints
- Retain existing functionality, event handlers, and state management intact.
- Maintain full dark mode and light mode compatibility.
- Ensure all interactive elements keep unique identifiers (`id` attributes) for accessibility and testing.

---

### Task 1: Theme & Global Styles Redesign (`src/app/globals.css`)

**Files:**
- Modify: `src/app/globals.css`

**Interfaces:**
- Produces: Global CSS variables (`--background`, `--card`, `--card-elevated`, `--border`, etc.) and utility classes (`.glass-panel`, `.glass-input`, `.minimal-card`).

- [ ] **Step 1: Inspect and update CSS variables and glassmorphism utilities**

Edit `src/app/globals.css` to add refined glassmorphism class definitions, soft shadow tokens, and subtle border utilities.

- [ ] **Step 2: Verify CSS validity**

Run: `npx next lint` or `npm run build`
Expected: Success with no CSS syntax errors.

- [ ] **Step 3: Commit changes**

```bash
git add src/app/globals.css
git commit -m "style: add glassmorphism utilities and refine minimalist theme tokens"
```

---

### Task 2: Sidebar Navigation Redesign (`src/components/Sidebar.tsx`)

**Files:**
- Modify: `src/components/Sidebar.tsx`

**Interfaces:**
- Consumes: Theme variables, Lucide icons.
- Produces: Refined minimalist Sidebar component.

- [ ] **Step 1: Simplify Sidebar border and active navigation states**

In `src/components/Sidebar.tsx`:
- Change right border from hard border to `border-r border-border/20`.
- Update navigation link active states to use clean pill indicators with smooth background transitions.
- Simplify action button styling (e.g. New Chat, Collapse buttons).

- [ ] **Step 2: Verify build**

Run: `npx next build` or `npm run build`
Expected: Clean compilation.

- [ ] **Step 3: Commit changes**

```bash
git add src/components/Sidebar.tsx
git commit -m "style(sidebar): implement minimalist borderless navigation styling"
```

---

### Task 3: Chat Message & Conversation UI Redesign (`src/components/ChatMessage.tsx`, `src/components/CommonChat.tsx`)

**Files:**
- Modify: `src/components/ChatMessage.tsx`
- Modify: `src/components/CommonChat.tsx`

**Interfaces:**
- Consumes: Message object props, theme tokens.
- Produces: Borderless message bubbles, clean hover action bars.

- [ ] **Step 1: Refine `ChatMessage.tsx` message bubbles**

- Remove heavy container borders around assistant messages.
- User messages: Use soft rounded bubbles (`rounded-2xl bg-user-bubble/80`).
- Assistant messages: Clean borderless layout with subtle left accent or neutral background and smooth typography.
- Action icons (copy, retry, edit): Show with soft opacity and fade-in on hover.

- [ ] **Step 2: Streamline `CommonChat.tsx` layout**

- Clean up padding and scrollbar styling in `CommonChat.tsx`.

- [ ] **Step 3: Commit changes**

```bash
git add src/components/ChatMessage.tsx src/components/CommonChat.tsx
git commit -m "style(chat): redesign chat bubbles to borderless minimalist format"
```

---

### Task 4: Floating Glassmorphic Input Bar (`src/components/ChatInputBar.tsx`)

**Files:**
- Modify: `src/components/ChatInputBar.tsx`

**Interfaces:**
- Consumes: Input handlers, attachments, models selection.
- Produces: Floating capsule glass input bar.

- [ ] **Step 1: Redesign `ChatInputBar.tsx` container and controls**

- Wrap input area in a floating capsule container (`rounded-2xl glass-input shadow-lg px-4 py-3 border border-border/30`).
- Streamline button icons (Attachment, Model selector, Send button).
- Soften focus ring and remove heavy outline borders.

- [ ] **Step 2: Verify build**

Run: `npm run build`
Expected: Clean compilation.

- [ ] **Step 3: Commit changes**

```bash
git add src/components/ChatInputBar.tsx
git commit -m "style(input): transform ChatInputBar into floating glassmorphic container"
```

---

### Task 5: Minimalist Empty Chat & App Shell Refinement (`src/components/EmptyChat.tsx`, `src/components/AppShell.tsx`)

**Files:**
- Modify: `src/components/EmptyChat.tsx`
- Modify: `src/components/AppShell.tsx`

**Interfaces:**
- Consumes: Layout wrapper.
- Produces: Clean empty chat state and top bar.

- [ ] **Step 1: Simplify `EmptyChat.tsx` welcome screen**

- Clean up hero title and prompt cards into borderless, minimal chips.
- Add soft ambient brand glow effect.

- [ ] **Step 2: Refine `AppShell.tsx` header**

- Use subtle backdrop blur (`backdrop-blur-md bg-background/80 border-b border-border/20`) for header bar.

- [ ] **Step 3: Commit changes**

```bash
git add src/components/EmptyChat.tsx src/components/AppShell.tsx
git commit -m "style(shell): refine AppShell header and EmptyChat hero layout"
```

---

### Task 6: Build Verification & Final Sanity Check

- [ ] **Step 1: Run full production build verification**

Run: `npm run build`
Expected: Build passes with no TypeScript or Lint errors.

- [ ] **Step 2: Final commit if needed**
