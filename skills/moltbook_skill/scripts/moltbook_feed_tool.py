import logging
from typing import Type, Any, Optional
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool

from skills.moltbook_skill.scripts.moltbook_client import (
    request_moltbook,
    load_credentials
)

logger = logging.getLogger(__name__)

class MoltbookFeedInput(BaseModel):
    action: str = Field(
        ...,
        description="The action to perform: 'get_feed' (fetch general feed or submolt feed), 'search' (perform semantic search), 'list_submolts' (list all submolts), or 'get_submolt_info' (get community details)."
    )
    query: Optional[str] = Field(
        None,
        description="The search query. Natural language questions or concepts work best. Required for 'search'."
    )
    submolt: Optional[str] = Field(
        None,
        description="The submolt name (e.g. 'general', 'aithoughts'). Filters feed for 'get_feed' or gets info for 'get_submolt_info'."
    )
    sort: str = Field(
        "hot",
        description="Sorting option: 'hot', 'new', 'top', 'rising' (for feeds) or 'best', 'new', 'old' (for searches/comments)."
    )
    filter: str = Field(
        "all",
        description="Feed filter: 'all' (subscriptions + follows) or 'following' (only follows). Works with 'get_feed' when no submolt is specified."
    )
    cursor: Optional[str] = Field(
        None,
        description="Pagination cursor from 'next_cursor' in a previous response."
    )
    limit: int = Field(
        25,
        description="Number of results to retrieve (max 50 for search, max 100 for feed)."
    )

class MoltbookFeedTool(BaseTool):
    name: str = "moltbook_feed"
    description: str = (
        "Read feeds, search semantically, or explore submolts on Moltbook.\n"
        "- 'get_feed': Gets posts from your subscriptions/follows. Can filter by 'submolt' (gets submolt feed) and 'filter' (all or following). Supports 'sort', 'cursor', 'limit'.\n"
        "- 'search': Natural language semantic search for conceptual matches across all posts/comments. Requires 'query'. Supports 'limit', 'cursor'.\n"
        "- 'list_submolts': Lists all submolt communities.\n"
        "- 'get_submolt_info': Retrieves details about a specific submolt. Requires 'submolt'."
    )
    args_schema: Type[BaseModel] = MoltbookFeedInput  # type: ignore
    account_id: str
    workspace_id: Optional[str] = Field(None, description="The ID of the user workspace.")

    async def _arun(
        self,
        action: str,
        query: Optional[str] = None,
        submolt: Optional[str] = None,
        sort: str = "hot",
        filter: str = "all",
        cursor: Optional[str] = None,
        limit: int = 25,
        **kwargs: Any,
    ) -> str:
        action = action.lower().strip()
        creds = load_credentials()
        if not creds.get("api_key"):
            return "Error: No Moltbook API key found. You must register an agent first."
            
        if action == "get_feed":
            params = {
                "sort": sort,
                "limit": limit
            }
            if cursor:
                params["cursor"] = cursor
                
            if submolt:
                # Submolt specific feed
                # Endpoint: /api/v1/submolts/{submolt}/feed
                res = await request_moltbook("GET", f"submolts/{submolt}/feed", params=params)
            else:
                # General/Personalized feed
                params["filter"] = filter
                res = await request_moltbook("GET", "feed", params=params)
                
            if not res.get("success", True) or "posts" not in res:
                error = res.get("error", "Unknown error")
                return f"❌ Failed to fetch feed: {error}"
                
            posts = res["posts"]
            if not posts:
                return "📭 The feed is currently empty."
                
            output = [f"📚 **Moltbook Feed ({sort.upper()})**"]
            if submolt:
                output.append(f"📍 Community: `r/{submolt}`")
            elif filter == "following":
                output.append("👥 Filter: Accounts you follow")
            output.append("")
            
            for p in posts:
                output.append(
                    f"📝 **{p.get('title')}**\n"
                    f"   Author: @{p.get('author_name')} | Submolt: `r/{p.get('submolt_name')}`\n"
                    f"   Upvotes: {p.get('upvotes', 0)} | Comments: {p.get('comment_count', 0)}\n"
                    f"   Created: {p.get('created_at', 'N/A')} | Post ID: `{p.get('post_id') or p.get('id')}`\n"
                )
                if p.get("content_preview") or p.get("content"):
                    preview = p.get("content_preview") or p.get("content")[:150]
                    # Clean markdown code blocks from preview
                    preview = preview.replace("```", "").strip()
                    output.append(f"   > {preview}...\n")
                    
            if res.get("has_more") and res.get("next_cursor"):
                output.append(f"➡️ **More results available!** Use pagination cursor: `{res.get('next_cursor')}`")
                
            return "\n".join(output)
            
        elif action == "search":
            if not query:
                return "Error: 'query' is required to perform semantic search."
                
            params = {
                "q": query,
                "limit": min(limit, 50)
            }
            if cursor:
                params["cursor"] = cursor
                
            res = await request_moltbook("GET", "search", params=params)
            
            if not res.get("success"):
                error = res.get("error", "Unknown error")
                return f"❌ Semantic search failed: {error}"
                
            results = res.get("results", [])
            if not results:
                return f"🔍 No conceptual matches found for: \"{query}\""
                
            output = [
                f"🔍 **Moltbook Semantic Search Results**",
                f"Query: \"{query}\"\n"
            ]
            
            for r in results:
                res_type = r.get("type", "post")
                similarity = r.get("similarity", 0.0)
                author = r.get("author", {}).get("name", "Unknown")
                
                if res_type == "post":
                    output.append(
                        f"📝 [Post] **{r.get('title')}** (Similarity: {similarity:.2f})\n"
                        f"   Author: @{author} | Submolt: `r/{r.get('submolt', {}).get('name')}`\n"
                        f"   Upvotes: {r.get('upvotes', 0)} | Post ID: `{r.get('id')}`\n"
                    )
                else: # comment
                    post_title = r.get("post", {}).get("title", "N/A")
                    output.append(
                        f"💬 [Comment] on **\"{post_title}\"** (Similarity: {similarity:.2f})\n"
                        f"   Author: @{author} | Post ID: `{r.get('post_id')}` | Comment ID: `{r.get('id')}`\n"
                    )
                    
                content = r.get("content", "")
                if content:
                    output.append(f"   > {content[:180].strip()}...\n")
                    
            if res.get("has_more") and res.get("next_cursor"):
                output.append(f"➡️ **More results available!** Use pagination cursor: `{res.get('next_cursor')}`")
                
            return "\n".join(output)
            
        elif action == "list_submolts":
            res = await request_moltbook("GET", "submolts")
            
            if not isinstance(res, list) and not res.get("success", True):
                error = res.get("error", "Unknown error")
                return f"❌ Failed to list submolts: {error}"
                
            submolts = res if isinstance(res, list) else res.get("submolts", [])
            if not submolts:
                return "🌐 No communities found."
                
            output = ["🌐 **Moltbook Communities (Submolts)**\n"]
            for s in submolts:
                output.append(
                    f"- **r/{s.get('name')}** (\"{s.get('display_name')}\")\n"
                    f"  Description: {s.get('description', 'No description')}\n"
                    f"  Crypto Content: {'✅ Allowed' if s.get('allow_crypto') else '❌ Forbidden'}\n"
                )
            return "\n".join(output)
            
        elif action == "get_submolt_info":
            if not submolt:
                return "Error: 'submolt' is required to get community details."
                
            res = await request_moltbook("GET", f"submolts/{submolt}")
            
            if not res.get("success", True) or "submolt" not in res:
                error = res.get("error", "Unknown error")
                return f"❌ Failed to get submolt details: {error}"
                
            s = res["submolt"]
            return (
                f"🌐 **Submolt: r/{s.get('name')}**\n\n"
                f"- **Display Name:** {s.get('display_name')}\n"
                f"- **Description:** {s.get('description', 'No description')}\n"
                f"- **Crypto Allowed:** {'✅ Yes' if s.get('allow_crypto') else '❌ No'}\n"
                f"- **Owner:** @{s.get('owner_name', 'N/A')}\n"
                f"- **Members/Subscribers:** {s.get('subscribers_count', 0)}\n"
                f"- **Your Role:** `{res.get('your_role', 'member')}`"
            )
            
        else:
            return f"Error: Unknown action '{action}'. Supported actions are: get_feed, search, list_submolts, get_submolt_info."

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("This tool does not support synchronous execution.")
