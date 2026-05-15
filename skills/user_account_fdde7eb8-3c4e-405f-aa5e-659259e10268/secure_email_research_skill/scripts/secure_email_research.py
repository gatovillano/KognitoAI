import requests
import json
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type

class InputSchema(BaseModel):
    query: str = Field(description="Search query for secure email practices")

class SecureEmailResearchSkill(BaseTool):
    name: str = "secure_email_research"
    description: str = "Researches current best practices for secure email communication and key management using web search."
    args_schema: Type[BaseModel] = InputSchema

    def _run(self, query: str) -> str:
        # Use DuckDuckGo Instant Answer API
        url = "https://api.duckduckgo.com/"
        params = {
            "q": query,
            "format": "json",
            "no_html": "1",
            "skip_disambig": "1"
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            # Extract relevant information
            abstract = data.get('Abstract', '')
            abstract_text = data.get('AbstractText', '')
            related_topics = data.get('RelatedTopics', [])
            
            # Format the response
            result = f"# Secure Email Research Results for: {query}\n\n"
            if abstract:
                result += f"## Summary\n{abstract}\n\n"
            if abstract_text:
                result += f"## Abstract\n{abstract_text}\n\n"
            if related_topics:
                result += f"## Related Topics\n"
                for topic in related_topics[:5]:  # Limit to 5
                    if isinstance(topic, dict) and 'Text' in topic:
                        result += f"- {topic['Text']}\n"
                result += "\n"
            
            # If no results from API, provide fallback
            if not abstract and not abstract_text and not related_topics:
                result += "No specific findings from DuckDuckGo Instant Answer. Try refining your search or using a different approach.\n"
                result += "For secure email key management, consider:\n"
                result += "- Using strong, unique passphrases for private keys\n"
                result += "- Storing private keys offline or in secure hardware\n"
                result += "- Regularly rotating keys (e.g., annually)\n"
                result += "- Verifying key fingerprints through secure channels\n"
                result += "- Using reputable PGP implementations (e.g., GnuPG)\n"
                
            return result
            
        except Exception as e:
            return f"An error occurred during research: {str(e)}\n\nPlease try again or consult security best practices manuals."