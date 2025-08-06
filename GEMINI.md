# Kognito AI Project Overview

This document provides a high-level overview of the Kognito AI project structure, key components, and technologies used.

## Core Components

The project is a complex, multi-faceted application with several key components:

1.  **Backend API (`api/`)**: A Python-based API that seems to handle the core business logic, including user authentication, chat functionalities, document management, and knowledge graph interactions. It likely uses a framework like FastAPI or Flask.
2.  **Frontend (`src/`, `next.config.mjs`)**: A modern web application built with Next.js (React). It serves as the user interface for interacting with the system.
3.  **Core Logic (`core/`)**: Contains the central processing logic of the AI, including the agent itself (`agent.py`), LLM management (`llm_manager.py`), memory systems, and tool management. This appears to be the "brain" of the application.
4.  **Knowledge Graph (`knowledge_graph/`)**: A dedicated module for managing and interacting with a knowledge graph, with adapters for technologies like Neo4j. This is used for complex data relationships and insights.
5.  **Telegram Integration (`telegram_client/`, `telegram_panel/`)**: Components for running and managing a Telegram bot, suggesting the application can be controlled or provide notifications via Telegram.
6.  **Agent Tools (`tools/`)**: A large collection of individual Python scripts, each representing a specific capability or tool that the AI agent can use to perform tasks (e.g., searching, adding notes, analyzing code).
7.  **Containerization (`Dockerfile.*`, `docker-compose.yml`)**: The project is heavily reliant on Docker for creating consistent development and production environments, orchestrating multiple services (like the backend, frontend, and database).

## Technology Stack

-   **Backend**: Python (likely FastAPI/Flask)
-   **Frontend**: JavaScript/TypeScript, React, Next.js, Tailwind CSS
-   **Database**: Neo4j (for the knowledge graph), likely a relational DB like PostgreSQL as well (suggested by `pyrightconfig.json` and common practice).
-   **Orchestration**: Docker, Docker Compose
-   **Package Management**: `requirements.*.txt` (Python), `package.json` (Node.js)

## Key Files & Directories

-   `run_api.py`: Entry point to start the main backend API.
-   `run_telegram_bot.py`: Entry point for the Telegram bot.
-   `docker-compose.yml`: Defines the services, networks, and volumes for the entire application stack.
-   `requirements.txt` (and its variants): Define the Python dependencies for different parts of the application.
-   `package.json`: Defines the Node.js dependencies and scripts for the frontend.
-   `docs/`: Contains project documentation.
