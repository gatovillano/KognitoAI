import os
import json
import httpx
import logging
import re
from typing import Any, Dict, Optional
from core.llm_manager import get_fast_llm
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

MOLTBOOK_API_BASE = "https://www.moltbook.com/api/v1"
CREDENTIALS_FILE = os.path.expanduser("~/.config/moltbook/credentials.json")

def load_credentials() -> Dict[str, Optional[str]]:
    """Loads Moltbook credentials from env vars or credentials file."""
    api_key = os.environ.get("MOLTBOOK_API_KEY")
    agent_name = os.environ.get("MOLTBOOK_AGENT_NAME")
    
    if not api_key and os.path.exists(CREDENTIALS_FILE):
        try:
            with open(CREDENTIALS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                api_key = data.get("api_key")
                agent_name = data.get("agent_name")
        except Exception as e:
            logger.warning(f"Failed to read credentials file {CREDENTIALS_FILE}: {e}")
            
    return {"api_key": api_key, "agent_name": agent_name}

def save_credentials(api_key: str, agent_name: str) -> None:
    """Saves Moltbook credentials to credentials file."""
    os.makedirs(os.path.dirname(CREDENTIALS_FILE), exist_ok=True)
    try:
        with open(CREDENTIALS_FILE, "w", encoding="utf-8") as f:
            json.dump({"api_key": api_key, "agent_name": agent_name}, f, indent=2)
        logger.info(f"Saved credentials to {CREDENTIALS_FILE}")
    except Exception as e:
        logger.error(f"Failed to save credentials to {CREDENTIALS_FILE}: {e}")

def delete_credentials() -> bool:
    """Deletes Moltbook credentials file to reset configuration."""
    if os.path.exists(CREDENTIALS_FILE):
        try:
            os.remove(CREDENTIALS_FILE)
            logger.info(f"Deleted credentials file {CREDENTIALS_FILE}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete credentials file {CREDENTIALS_FILE}: {e}")
            raise e
    return False

async def solve_math_challenge(challenge_text: str) -> str:
    """Uses Kognito's fast LLM to parse and solve the obfuscated math challenge."""
    llm = get_fast_llm()
    if not llm:
        raise RuntimeError("Fast LLM not initialized or not available to solve verification challenge.")
        
    system_prompt = (
        "You are an expert mathematical solver specializing in parsing highly obfuscated "
        "and noisy text. The user will provide a challenge text that contains a simple math problem "
        "scattered with symbols, alternating capitals, and extra letters.\n\n"
        "Your task:\n"
        "1. Filter out all the noise, symbols, and extra letters to find the two numbers and the operator (+, -, *, /).\n"
        "2. Solve the mathematical expression.\n"
        "3. Output ONLY the calculated number. Format it with 2 decimal places if possible, "
        "but the most critical part is to provide a single number with NO surrounding text, explanation, or markdown.\n\n"
        "Example:\n"
        "Input: 'A] lO^bSt-Er S[wImS aT/ tW]eNn-Tyy mE^tE[rS aNd] SlO/wS bY^ fI[vE'\n"
        "Meaning: 'A lobster swims at twenty meters and slows by five' -> 20 - 5\n"
        "Output: 15.00"
    )
    
    user_prompt = f"Solve this challenge text:\n{challenge_text}"
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    
    logger.info(f"Submitting challenge to LLM: {challenge_text}")
    response = await llm.ainvoke(messages)
    content = response.content if hasattr(response, 'content') else str(response)
    content = content.strip()
    
    logger.info(f"LLM Challenge solver raw response: '{content}'")
    
    # Extract the first numeric match
    match = re.search(r"[-+]?\d*\.\d+|\d+", content)
    if match:
        val = float(match.group(0))
        formatted_val = f"{val:.2f}"
        logger.info(f"Parsed solved challenge answer: {formatted_val}")
        return formatted_val
        
    raise ValueError(f"Could not parse a numeric answer from LLM output: '{content}'")

async def request_moltbook(
    method: str,
    endpoint: str,
    data: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
    api_key_override: Optional[str] = None
) -> Dict[str, Any]:
    """Helper to perform requests to Moltbook API, automatically handling headers and tokens."""
    creds = load_credentials()
    api_key = api_override = api_key_override or creds["api_key"]
    
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
        
    url = f"{MOLTBOOK_API_BASE}/{endpoint.lstrip('/')}"
    
    # 🔒 Critical check: never send API key to non-Moltbook domains
    if not url.startswith("https://www.moltbook.com"):
        raise ValueError(f"CRITICAL SECURITY RESTRICTION: Attempted to send Moltbook API requests to non-authorized URL: {url}")
        
    async with httpx.AsyncClient(timeout=15.0) as client:
        logger.info(f"Moltbook Request: {method} {url}")
        if method.upper() == "GET":
            response = await client.get(url, headers=headers, params=params)
        elif method.upper() == "POST":
            response = await client.post(url, headers=headers, json=data, params=params)
        elif method.upper() == "PATCH":
            response = await client.patch(url, headers=headers, json=data, params=params)
        elif method.upper() == "DELETE":
            response = await client.delete(url, headers=headers, params=params)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
            
        # Parse JSON
        try:
            res_data = response.json()
        except Exception:
            res_data = {"success": response.is_success, "status_code": response.status_code, "text": response.text}
            
        logger.info(f"Moltbook Response status: {response.status_code}")
        return res_data

async def handle_verification_flow(content_type: str, content_response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Checks if a content response requires verification. If so, automatically
    solves the math challenge using the LLM and publishes the content.
    """
    # Check if verification is needed
    # The response can have verification_required: true, or verification_status == "pending", or a verification field
    is_pending = content_response.get("verification_status") == "pending" or content_response.get("verification_required") is True
    verification_data = content_response.get("verification") or (content_response.get(content_type, {}) if isinstance(content_response.get(content_type), dict) else {}).get("verification")
    
    if not is_pending or not verification_data:
        return content_response
        
    verification_code = verification_data.get("verification_code")
    challenge_text = verification_data.get("challenge_text")
    
    if not verification_code or not challenge_text:
        logger.warning("Verification is pending, but missing code or challenge text.")
        return content_response
        
    logger.info("🔒 Auto-solving AI verification challenge for Moltbook...")
    
    try:
        # Solve using LLM
        answer = await solve_math_challenge(challenge_text)
        
        # Submit verification
        verify_payload = {
            "verification_code": verification_code,
            "answer": answer
        }
        
        verify_res = await request_moltbook("POST", "verify", data=verify_payload)
        
        if verify_res.get("success"):
            logger.info("✅ Auto-verification successful!")
            # Merge verification success info into original response
            content_response["verification_solved"] = True
            content_response["verification_message"] = verify_res.get("message")
            content_response["verification_status"] = "verified"
        else:
            logger.error(f"❌ Auto-verification failed: {verify_res.get('error')}")
            content_response["verification_solved"] = False
            content_response["verification_error"] = verify_res.get("error")
            content_response["verification_hint"] = verify_res.get("hint")
            content_response["verification_status"] = "failed"
            
    except Exception as e:
        logger.error(f"Exception during verification auto-solve: {e}", exc_info=True)
        content_response["verification_solved"] = False
        content_response["verification_error"] = str(e)
        content_response["verification_status"] = "error"
        
    return content_response
