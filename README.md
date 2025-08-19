# Jarvis: A Desktop AI Assistant

Jarvis is a personalized AI assistant that runs on your desktop. It's designed to connect to your personal knowledge and productivity tools, providing intelligent, context-aware answers to your questions. You can summon Jarvis at any time with a global keyboard shortcut.

## Core Features

* **Sleek User Interface:** A minimal, modern UI that can be summoned with a global hotkey (`Command+Shift+J` on macOS).
* **Conversational Memory:** Remembers the last few turns of the conversation for follow-up questions.
* **Multi-Tool Architecture:** Capable of using different "tools" to gather information from various sources before answering.
* **Calendar Integration:** Connects to Google Calendar to provide information on your schedule and events.
* **Notion Integration:** Reads from your Notion databases to access tasks, assignments, and automatically synced emails.
* **Obsidian Integration:** Performs keyword searches and lists notes from your local Obsidian vault.
* **Daily Snapshot:** Can provide a high-level summary of your day's meetings and tasks.

## Technology Stack

* **Core AI:** Microsoft Azure OpenAI Service (running `gpt-4o-mini`)
* **Application Framework:** Python 3.11
* **GUI:** PySide6 (hosting a web-based UI with HTML/CSS/JS)
* **Connected Services (APIs):**
    * Google Calendar API
    * Notion API
* **Local Data Sources:**
    * Obsidian Vault (local markdown files)
* **Automation Pipeline:**
    * Make.com (for syncing Outlook emails to a Notion database)

## Architecture Overview

Jarvis operates using a tool-based AI agent architecture. When a user asks a question, a keyword-based router in `jarvis_core.py` selects the appropriate tool (e.g., `_handle_calendar_access`). The tool gathers relevant information (the "context") from its source. This context, along with the user's question and recent chat history, is then sent to the Azure OpenAI model, which synthesizes a final, insightful answer.

## Setup Guide

1.  **Clone the Repository:**
    ```bash
    git clone <your-repo-url>
    cd jarvis
    ```

2.  **Create Python Environment:** Ensure you have Python 3.11 installed.
    ```bash
    python3.11 -m venv venv
    source venv/bin/activate
    ```

3.  **Install Dependencies:** It's best practice to create a `requirements.txt` file.
    * Create a file named `requirements.txt` and paste the following lines into it:
        ```
        PySide6
        PySide6-WebEngine
        openai
        python-dotenv
        google-api-python-client
        google-auth-httplib2
        google-auth-oauthlib
        notion-client
        pynput
        ```
    * Install all libraries at once:
        ```bash
        pip install -r requirements.txt
        ```

4.  **Configure APIs & Services:**
    * **Google Calendar:** Follow the Google Cloud Console steps to create an OAuth 2.0 Client ID for a Desktop App, enable the Calendar API, and save the `credentials.json` file in the project root. Add yourself as a test user.
    * **Notion:** Create a new integration at [notion.so/my-integrations](https://www.notion.so/my-integrations) and get the Internal Integration Token. Share specific databases (e.g., "School Tasks", "Incoming Emails") with the integration.
    * **Azure OpenAI:** Use the GitHub Student Pack to create an Azure for Students account. In the Azure AI Studio, create a new project and deploy the `gpt-4o-mini` model as a real-time endpoint.
    * **Make.com:** Create a scenario to watch for new emails in your school Outlook and use the "Create a Database Item" action to save them to a Notion database.

5.  **Create `.env` File:**
    * Create a file named `.env` in the root directory. Copy the contents of `env.example` (see below) and fill in your secret keys.
    * Create a file named `env.example` with the following content as a template:
        ```ini
        # Azure OpenAI Credentials
        AZURE_OPENAI_ENDPOINT=""
        AZURE_OPENAI_KEY=""
        AZURE_OPENAI_DEPLOYMENT_NAME=""

        # Notion API Key
        NOTION_API_KEY=""

        # Obsidian Vault Path (Full path to the folder)
        OBSIDIAN_VAULT_PATH=""
        ```

6.  **Run the Application:**
    ```bash
    python jarvis_app.py
    ```

## How to Use

* The application runs in the background.
* Press `Command+Shift+J` (macOS) or `Ctrl+Shift+J` (Windows) to show/hide the window.
* Ask questions! (e.g., "What's my summary for today?", "What are my assignments in Notion?", "Search my vault for notes on bioremediation.")