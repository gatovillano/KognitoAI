# Design Specification: Minimalist UI Redesign for Kognito AI

**Date:** 2026-07-24  
**Status:** Draft / Pending Review  
**Target:** Global Application UI (App Shell, Sidebar, Chat Workspace, Components & Theme)

---

## 1. Executive Summary
This design specification outlines the architectural and visual enhancements to transform Kognito AI into a ultra-clean, modern, minimalist interface. The redesign combines **Swiss Minimalist** borderless typography & layout principles with subtle **Modern Glassmorphism** (ambient background blurs, soft tonal contrasts, and refined micro-interactions).

---

## 2. Design System & Theme Enhancements (`src/app/globals.css` & `tailwind.config.ts`)

### 2.1 Color & Surface Hierarchy
- **Backgrounds:** Establish subtle tonal separation between main canvas (`--background`), side navigation (`--card-elevated`), and cards/popovers (`--card`) without harsh border dividers.
- **Borders:** Reduce global border visibility by using muted translucent borders (`border-border/30` to `border-border/40`).
- **Shadows:** Transition from hard multi-layer drop shadows to soft ambient elevation shadows (`0 4px 20px -2px rgba(0,0,0,0.05)` in light mode, `0 4px 20px -2px rgba(0,0,0,0.3)` in dark mode).

### 2.2 Modern Glassmorphism & Utilities
- Add utility classes:
  - `.glass-panel`: `backdrop-blur-md bg-card/75 border border-border/30 shadow-sm`
  - `.glass-input`: `backdrop-blur-lg bg-background/80 border border-border/40 focus:border-primary/50`
  - `.minimal-card`: `bg-card/60 hover:bg-card/90 border border-border/20 transition-all duration-200`

---

## 3. Component Architecture Redesign

### 3.1 Sidebar Navigation (`src/components/Sidebar.tsx`)
- **Visual Cleanliness:** Remove thick right border; use subtle background tone offset (`bg-card-elevated/80`) and clean `border-r border-border/20`.
- **Navigation Items:** Replace heavy highlight blocks with pill-style active indicators (subtle primary left accent or soft background tint).
- **Icons & Controls:** Compact icon size, hidden label overflow, and clean hover feedback.

### 3.2 Chat Workspace (`src/components/ChatMessage.tsx`, `ChatInputBar.tsx`, `EmptyChat.tsx`)
- **Chat Messages (`ChatMessage.tsx`):**
  - User bubbles: Soft muted background (`bg-user-bubble/80`) with clean typography.
  - Assistant responses: Full-width borderless background with generous padding (`py-4 px-6`), clean markdown styling, and action icons (copy, retry, thumbs) visible on hover or simplified toolbar.
- **Chat Input Bar (`ChatInputBar.tsx`):**
  - Redesign as a floating glassmorphic container (`rounded-2xl glass-input px-4 py-3 shadow-lg`).
  - Streamline attachment buttons, context selectors, and send button into a unified minimal action toolbar.
- **Empty State (`EmptyChat.tsx`):**
  - Ultra-clean welcome state with generous vertical whitespace, soft glowing branding accent, and minimal quick-prompt chips.

### 3.3 App Shell & Header (`src/components/AppShell.tsx`)
- **Top Navigation Bar:** Sticky frosted glass header (`backdrop-blur-md bg-background/80 border-b border-border/20`).
- **Breadcrumbs / Status:** Minimal text metrics and status indicators.

### 3.4 Cards, Dialogs & Utility UI (`src/components/ui/`)
- Adjust default `card.tsx` to use rounded-xl/2xl, subtle borders, and zero heavy shadows.
- Adjust `dialog.tsx` to use translucent overlay backdrop (`backdrop-blur-sm bg-black/40`).

---

## 4. Verification & Testing Plan
- **Visual Inspection:** Verify light and dark mode appearance across Sidebar, Chat, and Dialogs.
- **Responsive Layout:** Ensure sidebar collapse and chat input floating positioning function cleanly across window sizes.
- **Build Check:** Execute `npm run build` or Next.js type checks to ensure no broken imports or broken JSX components.
