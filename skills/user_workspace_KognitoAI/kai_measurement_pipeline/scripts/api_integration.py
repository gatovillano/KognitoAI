#!/usr/bin/env python3
"""
KAI API Integration Module
Handles communication with KAI API endpoints
"""
import asyncio
import aiohttp
import json
from typing import Dict, Any, Optional

class KAIApiClient:
    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    async def send_query(self, query: str, session: aiohttp.ClientSession) -> Dict[str, Any]:
        """Send query to KAI API"""
        payload = {
            "query": query,
            "context": "measurement_pipeline"
        }
        
        try:
            async with session.post(
                f"{self.api_url}/api/v1/query",
                headers=self.headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {"error": f"HTTP {response.status}", "response": await response.text()}
        except Exception as e:
            return {"error": str(e)}
    
    async def health_check(self) -> bool:
        """Check API health"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_url}/health", timeout=aiohttp.ClientTimeout(total=5)) as response:
                    return response.status == 200
        except:
            return False
