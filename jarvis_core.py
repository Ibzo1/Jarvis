import os
import re
import datetime
import pickle
import traceback
from openai import AzureOpenAI
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import notion_client

# Get the absolute path of the directory where this script is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class Jarvis:
    def __init__(self):
        self.client, self.deployment_name = self._initialize_azure_client()
        self.chat_history = []
        self.notion = self._initialize_notion()

    def _initialize_azure_client(self):
        """Initializes and returns the Azure OpenAI client."""
        load_dotenv()
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        api_key = os.getenv("AZURE_OPENAI_KEY")
        deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
        if not all([endpoint, api_key, deployment_name]):
            raise ValueError("Azure OpenAI credentials not found in .env file.")
        client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version="2024-02-01"
        )
        return client, deployment_name

    def _initialize_notion(self):
        """Initializes and returns the Notion client."""
        notion_api_key = os.getenv("NOTION_API_KEY")
        if not notion_api_key:
            print("Warning: NOTION_API_KEY not found. Notion features will be disabled.")
            return None
        return notion_client.Client(auth=notion_api_key)

    def get_response(self, user_question):
        """The main entry point for processing a user's command and routing to tools."""
        command = user_question.lower()
        context_for_llm = ""
        
        obsidian_keywords = ["obsidian", "vault", "my notes", "remember", "research on"]
        notion_keywords = ["notion", "assignments", "tasks", "dashboard", "email"]
        calendar_keywords = ["calendar", "schedule", "meeting", "event", "priorities", "busy", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", "today", "tomorrow", "week", "year"]
        snapshot_keywords = ["snapshot", "summary", "daily brief", "what's up"]

        if any(keyword in command for keyword in snapshot_keywords):
            context_for_llm = self._get_daily_snapshot()
        elif any(keyword in command for keyword in obsidian_keywords):
            context_for_llm = self._handle_obsidian_access(command)
        elif any(keyword in command for keyword in notion_keywords):
            context_for_llm = self._handle_notion_access(command)
        elif any(keyword in command for keyword in calendar_keywords):
            context_for_llm = self._handle_calendar_access(command)
        elif command.startswith("read "):
            context_for_llm = self._handle_file_reading(command)

        messages = [{"role": "system", "content": "You are Jarvis, a helpful and concise AI productivity assistant. Analyze the provided context and conversation history to answer the user's question directly and insightfully."}]
        for turn in self.chat_history:
            messages.append({"role": "user" if "You:" in turn else "assistant", "content": turn.split(":", 1)[1].strip()})
        if context_for_llm:
            messages.append({"role": "system", "content": f"Use the following new context to answer the user's question:\n{context_for_llm}"})
        messages.append({"role": "user", "content": user_question})
        
        response = self.client.chat.completions.create(model=self.deployment_name, messages=messages)
        response_text = response.choices[0].message.content

        self.chat_history.extend([f"You: {user_question}", f"Jarvis: {response_text}"])
        if len(self.chat_history) > 8: self.chat_history = self.chat_history[-8:]
            
        return response_text

    def run_daily_snapshot(self):
        """Gathers context and generates a formatted daily snapshot."""
        print("DEBUG: Gathering daily snapshot...")
        # Get today's events from the calendar
        calendar_context = self._handle_calendar_access("today")
        # Get tasks and emails from Notion
        notion_context = self._handle_notion_access("tasks and emails")
        
        snapshot_context = f"{calendar_context}\n\n{notion_context}"

        # Send the combined context to the LLM with a specific prompt
        messages = [{
            "role": "system",
            "content": "You are Jarvis. Analyze the provided context from the user's tools and generate a concise, well-formatted daily snapshot. Use headings for each section (e.g., Calendar, Notion Tasks). If a section has no information, state that clearly."
        }, {
            "role": "user",
            "content": f"Please provide my daily snapshot based on this information:\n{snapshot_context}"
        }]

        response = self.client.chat.completions.create(model=self.deployment_name, messages=messages)
        response_text = response.choices[0].message.content

        # Add this special interaction to chat history
        self.chat_history.extend(["You: (Requested Daily Snapshot)", f"Jarvis: {response_text}"])
        if len(self.chat_history) > 8: self.chat_history = self.chat_history[-8:]

        return response_text


    def _handle_obsidian_access(self, query):
        """Searches or lists notes from the Obsidian vault."""
        try:
            vault_path = os.getenv("OBSIDIAN_VAULT_PATH")
            if not vault_path: return "Context from Obsidian: OBSIDIAN_VAULT_PATH is not set in your .env file."
            vault_path = os.path.expanduser(vault_path.strip("'\""))
            keywords_to_remove = ["obsidian", "vault", "my notes", "remember about", "research on", "anything about", "search for", "in", "my", "about", "what", "are", "is", "a", "an", "the", "notes"]
            clean_query = query.lower()
            for keyword in keywords_to_remove: clean_query = clean_query.replace(keyword, "")
            search_terms = clean_query.strip().split()
            all_notes_content = ""; note_count = 0
            if not search_terms:
                all_notes_content = "Context from Obsidian Vault (File List):\n"
                for root, dirs, files in os.walk(vault_path):
                    for file in files:
                        if file.endswith(".md"): all_notes_content += f"- {file}\n"; note_count += 1
                return all_notes_content if note_count > 0 else "Context from Obsidian: Your vault appears to be empty."
            else:
                all_notes_content = f"Context from Obsidian Notes containing '{' '.join(search_terms)}':\n"
                for root, dirs, files in os.walk(vault_path):
                    for file in files:
                        if file.endswith(".md"):
                            with open(os.path.join(root, file), 'r', encoding='utf-8') as f: content = f.read()
                            if all(term in content.lower() for term in search_terms):
                                all_notes_content += f"\n--- Start of note: {file} ---\n{content[:500]}...\n"; note_count += 1
                return all_notes_content if note_count > 0 else f"Context from Obsidian: I couldn't find any notes containing the terms: {', '.join(search_terms)}."
        except Exception: return f"An unexpected error occurred in Obsidian tool:\n\n{traceback.format_exc()}"

    def _handle_notion_access(self, query):
        """Searches connected Notion databases."""
        if not self.notion: return "Context from Notion: Notion API key is not configured."
        try:
            response = self.notion.search(filter={"value": "database", "property": "object"})
            databases = response.get("results")
            if not databases: return "Context from Notion: No databases are shared with the Jarvis integration."
            all_db_content = "Context from Notion:\n"
            for db in databases:
                db_id = db["id"]; db_title = db.get("title", [{}])[0].get("plain_text", "Untitled Database")
                if "emails" in db_title.lower():
                    all_db_content += f"\n--- Recent Emails from '{db_title}' ---\n"
                    db_response = self.notion.databases.query(database_id=db_id, page_size=5)
                    for page in db_response.get("results", []):
                        title_prop = next((p for p in page["properties"].values() if p["type"] == "title"), None)
                        if title_prop and title_prop["title"]: all_db_content += f"- Subject: {title_prop['title'][0]['plain_text']}\n"
                else:
                    all_db_content += f"\n--- Items from '{db_title}' ---\n"
                    db_response = self.notion.databases.query(database_id=db_id)
                    for page in db_response.get("results", []):
                        title_prop = next((p for p in page["properties"].values() if p["type"] == "title"), None)
                        if title_prop and title_prop["title"]: all_db_content += f"- {title_prop['title'][0]['plain_text']}\n"
            return all_db_content
        except Exception as e: return f"Error accessing Notion: {e}"

    def _handle_calendar_access(self, command):
        """Fetches events from all available Google Calendars."""
        token_path = os.path.join(BASE_DIR, 'token.pickle'); creds_path = os.path.join(BASE_DIR, 'credentials.json')
        try:
            creds = None
            if os.path.exists(token_path):
                with open(token_path, 'rb') as token: creds = pickle.load(token)
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token: creds.refresh(Request())
                else:
                    SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']; flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
                    creds = flow.run_local_server(port=0)
                with open(token_path, 'wb') as token: pickle.dump(creds, token)
            service = build('calendar', 'v3', credentials=creds)
            now = datetime.datetime.now(datetime.UTC); time_min = now
            if "today" in command: time_max = (now + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0)
            elif "tomorrow" in command: time_min = (now + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0); time_max = (time_min + datetime.timedelta(days=1))
            elif "year" in command: time_max = now + datetime.timedelta(days=365)
            elif "week" in command: time_max = now + datetime.timedelta(weeks=1)
            else: time_max = now + datetime.timedelta(days=7)
            all_events = []
            calendar_list = service.calendarList().list().execute()
            for calendar in calendar_list.get('items', []):
                events_result = service.events().list(calendarId=calendar['id'], timeMin=time_min.isoformat(), timeMax=time_max.isoformat(), maxResults=25, singleEvents=True, orderBy='startTime').execute()
                all_events.extend(events_result.get('items', []))
            if not all_events: return "Context from calendar: No upcoming events found."
            all_events.sort(key=lambda x: x['start'].get('dateTime', x['start'].get('date')))
            event_list = "Context from calendar:\n"
            for event in all_events:
                start_raw = event['start'].get('dateTime', event['start'].get('date'))
                start = datetime.datetime.fromisoformat(start_raw.replace('Z', '+00:00')).strftime('%a, %b %d @ %I:%M %p')
                event_list += f"- {start}: {event['summary']}\n"
            return event_list
        except Exception as e: return f"Error accessing calendar: {e}"

    def _handle_file_reading(self, command):
        """Reads a single file from the local 'knowledge' directory."""
        match = re.search(r'read\s+([\w\.\-]+)', command)
        if not match: return "Jarvis: I see 'read', but couldn't find a filename."
        filename = match.group(1); file_path = os.path.join(BASE_DIR, "knowledge", filename)
        try:
            with open(file_path, 'r', encoding='utf-8') as f: return f"Context from file '{filename}':\n---\n{f.read()}\n---\n"
        except FileNotFoundError: return f"Jarvis: Error - I could not find '{filename}' in the knowledge folder."