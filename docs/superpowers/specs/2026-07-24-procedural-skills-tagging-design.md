# Design Spec: Procedural Skills Tagging System

## Goal
Implement a system that allows users to call specific procedural skills (e.g. `analysis_and_insights_skill`, `notes_skill`) in the chat input using the `/` symbol. 
When `/` is typed, an autocomplete dropdown should display the available skills list. When selected, the skill ID is inserted in the input text (e.g., `/notes_skill`).
When the message is processed by the agent, the backend parses the tagged skills, loads their associated `SKILL.md` instructions, and injects them directly into the agent's prompt during that execution turn.

---

## Proposed Architecture

### 1. Frontend: Autocomplete Trigger & Skill Loading
**File**: [ChatInputBar.tsx](file:///home/gato/Proyectos/KognitoAI/kognito-ai/src/components/ChatInputBar.tsx)

- Update `AutocompleteState` interface to accept `/` as a trigger.
- Update `handleMessageChange` regex to match `/` along with `#` and `@`:
  ```typescript
  const match = /(?:^|\s)(#|@|\/)([^\s]*)$/.exec(textBeforeCursor);
  ```
  And adjust `wordStartIndex` calculation:
  ```typescript
  const wordStartIndex = match.index + (match[0].match(/^\s/) ? 1 : 0);
  ```
- Update `updateAutocompleteOptions` to handle `/`:
  - Fetch available skills from `GET /api/skills/available`.
  - Cache results in a new ref `skillsCacheRef: React.MutableRefObject<string[] | null>`.
  - Filter list based on the search query.
- Update suggestions popover display text and icon when trigger is `/`:
  - Header: `"Skills Procedimentales"`
  - Icon: Render `BookMarked` instead of `Paperclip`.
- Ensure Keyboard navigation and click/Tab selection inserts the selected option properly as `/{skill_id}`.

### 2. Backend: Tag Extraction & Skill Instruction Injection
**File**: [agent.py](file:///home/gato/Proyectos/KognitoAI/kognito-ai/core/agent.py)

- Inside `call_model_node`:
  - Parse the user's message to find any tags matching `/([a-zA-Z0-9_\-]+)`.
  - Filter the matched tags against the list of actual available skills in the system to avoid false positives (like UI commands `/browser` or `/help`).
  - To do this matching flexibly, we'll map each available skill to multiple key patterns:
    - Base skill ID (e.g., `notes_skill`)
    - Skill ID without `_skill` suffix (e.g., `notes`)
    - Skill ID replacing underscores with hyphens (e.g., `notes-skill` or `notes`)
  - Load instructions/markdown of the explicitly tagged skills using `SkillManager._load_skill_markdowns`.
  - Prepend or merge these tagged skills into the `relevant_skills` list passed to `build_system_prompt`, ensuring they are loaded first.
  - Since `relevant_skills` instructions are injected in `procedural_instructions` in the system prompt, the LLM will strictly receive the full instructions of the tagged skills (e.g., from `SKILL.md`) for that turn.

---

## Verification Plan

### Manual Verification
1. Open the Chat Interface.
2. In the chat input, type `/`. Verify that the autocomplete dropdown appears showing available skills (like `analysis_and_insights_skill`, `notes_skill`, `developer_tools_skill`, etc.) with a bookmark icon and the heading "Skills Procedimentales".
3. Continue typing `/deve`. Verify that the options filter down to `developer_tools_skill`.
4. Press Enter or click on `developer_tools_skill`. Verify that `/developer_tools_skill ` is inserted at the cursor position.
5. Send a query tagging a skill (e.g., "resumen de mis ultimos chats /conversations_skill").
6. Verify in the agent logs that `relevant_skills` contains the tagged skill and its instructions are passed in the system prompt.
