"""
KognitoAI Deep Research MCP Server Package.
Expone las capacidades de api/deep_research.py a través de Model Context Protocol (MCP).
"""

from .server import mcp, main

__all__ = ["mcp", "main"]
