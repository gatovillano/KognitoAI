# Project Files Documentation

This document provides a detailed explanation of the functionality of each file and directory in the KognitoAI project. The descriptions are based on the file names, directory structure, and inferred purposes. For precise details, reviewing the actual content of specific files may be necessary.

## Root Directory Files

- **.env.local**: Contains environment-specific configuration variables for the project, typically used for local development settings like API keys, database URLs, etc.
- **.gitignore**: Specifies intentionally untracked files to ignore by Git, such as build outputs, temporary files, and sensitive data.
- **components.json**: Likely a configuration or manifest file for project components, possibly used by a framework or build tool.
- **docker-compose.yml**: Defines and runs multi-container Docker applications, specifying services, networks, and volumes for the project components.
- **Dockerfile.core**, **Dockerfile.frontend**, **Dockerfile.telegram**, **Dockerfile.webapp**: Docker configuration files for building images for different parts of the application (core backend, frontend, Telegram bot, and webapp respectively).
- **next.config.mjs**: Configuration file for Next.js, a React framework, used to customize build, runtime, and development settings.
- **nginx.conf**: Configuration file for Nginx, likely used as a reverse proxy or web server in the project deployment.
- **package-lock.json**, **package.json**: Node.js project manifest and lock files, detailing dependencies, scripts, and project metadata.
- **postcss.config.js**: Configuration for PostCSS, a tool for transforming CSS with JavaScript plugins, often used with Tailwind CSS.
- **README.md**: A markdown file typically containing an overview, installation instructions, and usage information for the project.
- **requirements.txt**, **requirements.webapp.txt**: Lists Python dependencies for the project and specifically for the webapp component.
- **run_api.py**, **run_telegram_bot.py**, **run_telegram_panel.py**: Python scripts to start the API, Telegram bot, and Telegram panel respectively.
- **tailwind.config.ts**: Configuration for Tailwind CSS, a utility-first CSS framework, defining custom styles, themes, and plugins.
- **tsconfig.json**: TypeScript configuration file, specifying compiler options and project structure for TypeScript files.

## Core Directory (`core/`)

- **agenda_manager.py**: Manages agenda-related functionalities, possibly handling scheduling and event tracking.
- **agent.py**: Likely the core logic for an agent or bot, central to the application's AI or automation features.
- **config.py**: Contains configuration settings for the core application, such as database connections or API endpoints.
- **database.py**: Handles database interactions, including connection setup, queries, and data management.
- **memory_manager.py**: Manages memory or state for the application, possibly for maintaining context in conversations or processes.
- **notes_manager.py**: Manages note-taking functionalities, allowing creation, retrieval, and modification of notes.
- **reminders_manager.py**: Handles reminder functionalities, including setting and triggering reminders.

## Public Directory (`public/`)

- **logo-completo.png**, **logo-simple.png**: Image files for the project logos, used in the user interface or branding.

## Source Directory (`src/`)

### App Directory (`src/app/`)

- **globals.css**: Global CSS styles for the application.
- **layout.tsx**: Defines the overall layout structure for the Next.js application.
- **(dashboard)/layout.tsx**: Layout specific to the dashboard section of the application.
- **(dashboard)/page.tsx**: Main page component for the dashboard.
- **(dashboard)/chat/[id]/page.tsx**: Page component for individual chat views within the dashboard.
- **(dashboard)/rag/columns.tsx**: Defines column structures, likely for a data table in the RAG (Retrieval-Augmented Generation) feature.
- **(dashboard)/rag/data-table.tsx**: Component for rendering a data table in the RAG section.
- **(dashboard)/rag/page.tsx**: Main page for the RAG feature within the dashboard.
- **login/page.tsx**: Login page component for user authentication.

### Components Directory (`src/components/`)

- **Sidebar.tsx**: A UI component for the sidebar, likely used for navigation within the dashboard.
- **ui/**: Contains reusable UI components from a library like shadcn/ui, including avatar, button, card, dialog, dropdown-menu, form, input, label, resizable, scroll-area, sonner, table, toast, and toaster components.

### Contexts Directory (`src/contexts/`)

- **AuthContext.tsx**: Provides authentication context for managing user login state and permissions across the application.

### Hooks Directory (`src/hooks/`)

- **use-toast.ts**: Custom hook for managing toast notifications in the application.

### Lib Directory (`src/lib/`)

- **api.ts**: Contains functions or configurations for API interactions.
- **utils.ts**: Utility functions used throughout the application.

## Telegram Client Directory (`telegram_client/`)

- **bot_manager.py**: Manages the Telegram bot's operations and interactions.
- **notification_scheduler.py**: Schedules notifications to be sent via the Telegram bot.
- **tools.py**: Utility functions or tools specific to the Telegram client.
- **handlers/**: Contains handler scripts for different types of Telegram interactions:
  - **admin_handlers.py**: Handles admin-specific commands or actions.
  - **callback_query_handler.py**: Manages callback queries from inline buttons or menus.
  - **command_handlers.py**: Processes command inputs from users.
  - **document_handlers.py**: Handles document uploads or interactions.
  - **message_handlers.py**: Processes incoming messages from users.

## Telegram Panel Directory (`telegram_panel/`)

- **index.html**, **script.js**, **style.css**: Files for a web-based control panel or interface for managing the Telegram bot.

## Tools Directory (`tools/`)

This directory contains various Python scripts for specific functionalities or integrations, likely used by the core application or agent:
- **add_note_tool.py**, **delete_note_tool.py**, **update_note_tool.py**, **get_notes_tool.py**: Tools for managing notes.
- **analyze_text_for_insights_tool.py**: Analyzes text to derive insights, possibly for AI-driven features.
- **cancel_event_tool.py**, **schedule_event_tool.py**, **get_agenda_tool.py**: Tools for event and agenda management.
- **delete_document_tool.py**, **get_document_content_tool.py**, **get_document_list_tool.py**, **update_document_metadata_tool.py**: Document management tools.
- **get_proactive_insights_tool.py**, **proactive_knowledge_linker_tool.py**: Tools for generating proactive insights and linking knowledge.
- **github_repo_tool.py**: Integration with GitHub for repository interactions.
- **image_generation_tool.py**: Tool for generating images, possibly using AI models.
- **memory_add_tool.py**: Adds data to memory or context for the application.
- **set_reminder_tool.py**: Sets reminders for users.
- **update_user_profile.py**: Updates user profile information.
- **web_scraper_tool.py**, **web_search_tool.py**: Tools for scraping web content and performing web searches.

## Utils Directory (`utils/`)

- **analyze_text_for_insights.py**: Utility for text analysis, similar to the tool but possibly more generic.
- **db_session.py**: Manages database sessions or connections.
- **document_parser.py**: Parses documents for content extraction or processing.
- **embeddings.py**: Handles embeddings, likely for machine learning or NLP tasks.
- **helpers.py**: General helper functions used across the project.
- **image_generation.py**: Utility for image generation processes.
- **paginator.py**: Provides pagination functionality for lists or data sets.
- **security.py**: Contains security-related functions, such as encryption or authentication checks.

## Webapp Directory (`webapp/`)

- This directory appears to be empty or not detailed in the current view, but based on the Dockerfile.webapp, it likely contains the backend web application code.

This markdown will be updated or refined as more detailed information about specific files is reviewed or provided.
