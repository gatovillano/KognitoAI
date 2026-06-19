from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type, Any, Optional
import subprocess
import json
import os

class BrowserUseInput(BaseModel):
    """Input for browser-use skill"""
    action: str = Field(description="Action to perform: 'open', 'state', 'click', 'input', 'type', 'screenshot', 'close', 'back', 'scroll_down', 'scroll_up', 'tab_list', 'tab_new', 'tab_switch', 'tab_close', 'get_title', 'get_html', 'get_text', 'wait', 'cookies_get', 'cookies_set', 'cookies_clear', 'eval'")
    url: Optional[str] = Field(default=None, description="URL to navigate to (for 'open' action)")
    element_index: Optional[int] = Field(default=None, description="Element index for click/input (from state)")
    text: Optional[str] = Field(default=None, description="Text to type or input")
    path: Optional[str] = Field(default=None, description="Path for screenshot")
    amount: Optional[int] = Field(default=None, description="Scroll amount in pixels")
    tab_index: Optional[int] = Field(default=None, description="Tab index for switch/close")
    selector: Optional[str] = Field(default=None, description="CSS selector for wait or get_html")
    javascript: Optional[str] = Field(default=None, description="JavaScript code for eval action")
    domain: Optional[str] = Field(default=None, description="Domain for cookies")
    name: Optional[str] = Field(default=None, description="Cookie name")
    value: Optional[str] = Field(default=None, description="Cookie value")
    timeout: Optional[int] = Field(default=30000, description="Timeout in milliseconds")

class BrowserUseSkill(BaseTool):
    name: str = "browser_use_skill"
    description: str = """Browser automation skill for web testing, form filling, screenshots, and data extraction.
Use when the user needs to navigate websites, interact with web pages, fill forms, take screenshots, or extract information from web pages.

Actions:
- open: Navigate to URL
- state: Get current page state with clickable elements
- click: Click element by index
- input/type: Type text
- screenshot: Take screenshot
- close: Close browser
- back: Go back in history
- scroll_down/scroll_up: Scroll page
- tab_list/tab_new/tab_switch/tab_close: Tab management
- get_title/get_html/get_text: Extract data
- wait: Wait for element/text
- cookies_get/set/clear: Cookie management
- eval: Execute JavaScript"""
    args_schema: Type[BaseModel] = BrowserUseInput

    def _run(self, action: str, **kwargs) -> str:
        """Execute browser automation commands"""
        
        # Build command
        cmd_parts = ["browser-use"]
        
        # Add global flags based on context
        session = kwargs.get('session', 'default')
        
        try:
            if action == "open":
                url = kwargs.get('url')
                if not url:
                    return "Error: URL is required for 'open' action"
                cmd_parts.extend(["open", url])
                
            elif action == "state":
                cmd_parts.append("state")
                
            elif action == "click":
                element_index = kwargs.get('element_index')
                if element_index is None:
                    return "Error: element_index is required for 'click' action"
                cmd_parts.extend(["click", str(element_index)])
                
            elif action in ["input", "type"]:
                text = kwargs.get('text')
                element_index = kwargs.get('element_index')
                if element_index is None:
                    return "Error: element_index is required for 'input' action"
                if not text:
                    return "Error: text is required for 'input' action"
                cmd_parts.extend(["input", str(element_index), text])
                
            elif action == "screenshot":
                path = kwargs.get('path')
                if path:
                    cmd_parts.extend(["screenshot", path])
                else:
                    cmd_parts.append("screenshot")
                
            elif action == "close":
                cmd_parts.append("close")
                
            elif action == "back":
                cmd_parts.append("back")
                
            elif action == "scroll_down":
                amount = kwargs.get('amount', 500)
                cmd_parts.extend(["scroll", "down", "--amount", str(amount)])
                
            elif action == "scroll_up":
                amount = kwargs.get('amount', 500)
                cmd_parts.extend(["scroll", "up", "--amount", str(amount)])
                
            elif action == "tab_list":
                cmd_parts.append("tab", "list")
                
            elif action == "tab_new":
                url = kwargs.get('url')
                if url:
                    cmd_parts.extend(["tab", "new", url])
                else:
                    cmd_parts.extend(["tab", "new"])
                    
            elif action == "tab_switch":
                tab_index = kwargs.get('tab_index')
                if tab_index is None:
                    return "Error: tab_index is required for 'tab_switch' action"
                cmd_parts.extend(["tab", "switch", str(tab_index)])
                
            elif action == "tab_close":
                tab_index = kwargs.get('tab_index')
                if tab_index is not None:
                    cmd_parts.extend(["tab", "close", str(tab_index)])
                else:
                    cmd_parts.extend(["tab", "close"])
                    
            elif action == "get_title":
                cmd_parts.extend(["get", "title"])
                
            elif action == "get_html":
                selector = kwargs.get('selector')
                if selector:
                    cmd_parts.extend(["get", "html", "--selector", selector])
                else:
                    cmd_parts.extend(["get", "html"])
                    
            elif action == "get_text":
                cmd_parts.extend(["get", "text"])
                
            elif action == "wait":
                selector = kwargs.get('selector')
                if selector:
                    cmd_parts.extend(["wait", "selector", selector])
                else:
                    return "Error: selector is required for 'wait' action"
                    
            elif action == "cookies_get":
                url = kwargs.get('url')
                if url:
                    cmd_parts.extend(["cookies", "get", "--url", url])
                else:
                    cmd_parts.extend(["cookies", "get"])
                    
            elif action == "cookies_set":
                domain = kwargs.get('domain')
                name = kwargs.get('name')
                value = kwargs.get('value')
                if not all([domain, name, value]):
                    return "Error: domain, name, and value are required for 'cookies_set' action"
                cmd_parts.extend(["cookies", "set", "--domain", domain, "--name", name, "--value", value])
                
            elif action == "cookies_clear":
                url = kwargs.get('url')
                if url:
                    cmd_parts.extend(["cookies", "clear", "--url", url])
                else:
                    cmd_parts.extend(["cookies", "clear"])
                    
            elif action == "eval":
                javascript = kwargs.get('javascript')
                if not javascript:
                    return "Error: javascript is required for 'eval' action"
                cmd_parts.extend(["eval", javascript])
                
            else:
                return f"Error: Unknown action '{action}'"
            
            # Execute command
            result = subprocess.run(cmd_parts, capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                return f"Error executing command: {result.stderr}"
            
            return result.stdout
            
        except subprocess.TimeoutExpired:
            return "Error: Command timed out"
        except FileNotFoundError:
            return "Error: browser-use command not found. Please install it first."
        except Exception as e:
            return f"Error: {str(e)}"

# For use as a direct tool
def browser_use_action(action: str, **kwargs) -> str:
    """Helper function to use browser automation"""
    tool = BrowserUseSkill()
    return tool._run(action, **kwargs)