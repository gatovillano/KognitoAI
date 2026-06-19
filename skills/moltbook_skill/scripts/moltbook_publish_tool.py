import logging
from typing import Type, Any, Optional
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool

from skills.moltbook_skill.scripts.moltbook_client import (
    request_moltbook,
    load_credentials,
    handle_verification_flow
)

logger = logging.getLogger(__name__)

class MoltbookPublishInput(BaseModel):
    action: str = Field(
        ...,
        description="The action to perform: 'post' (create a post), 'comment' (comment on a post or reply to comment), 'delete' (delete a post), 'pin' (pin a post), or 'unpin' (unpin a post)."
    )
    submolt: Optional[str] = Field(
        None,
        description="The submolt name to post in (e.g. 'general', 'aithoughts'). Required for 'post'."
    )
    title: Optional[str] = Field(
        None,
        description="The title of the post (max 300 chars). Required for 'post'."
    )
    content: Optional[str] = Field(
        None,
        description="The text body of the post or comment. Required for 'comment' and text 'post'."
    )
    url: Optional[str] = Field(
        None,
        description="The external URL for link posts."
    )
    type: str = Field(
        "text",
        description="The type of post: 'text', 'link', or 'image'."
    )
    post_id: Optional[str] = Field(
        None,
        description="The ID of the post. Required for 'comment', 'delete', 'pin', and 'unpin'."
    )
    comment_id: Optional[str] = Field(
        None,
        description="The parent comment ID. Provide only when replying to a specific comment (not the root post)."
    )

class MoltbookPublishTool(BaseTool):
    name: str = "moltbook_publish"
    description: str = (
        "Publish or manage content on Moltbook. Supports auto-verification of anti-spam math challenges.\n"
        "- 'post': Creates a new post in 'submolt'. Requires 'title', 'submolt', and optionally 'content'/'url'.\n"
        "- 'comment': Adds a comment to 'post_id'. Requires 'content', 'post_id'. If 'comment_id' is provided, it replies to that specific comment.\n"
        "- 'delete': Deletes a post. Requires 'post_id'.\n"
        "- 'pin': Pins a post (owner/moderator only, max 3). Requires 'post_id'.\n"
        "- 'unpin': Unpins a post. Requires 'post_id'."
    )
    args_schema: Type[BaseModel] = MoltbookPublishInput  # type: ignore
    account_id: str
    workspace_id: Optional[str] = Field(None, description="The ID of the user workspace.")

    async def _arun(
        self,
        action: str,
        submolt: Optional[str] = None,
        title: Optional[str] = None,
        content: Optional[str] = None,
        url: Optional[str] = None,
        type: str = "text",
        post_id: Optional[str] = None,
        comment_id: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        action = action.lower().strip()
        creds = load_credentials()
        if not creds.get("api_key"):
            return "Error: No Moltbook API key found. You must register an agent first."
            
        if action == "post":
            if not submolt or not title:
                return "Error: 'submolt' and 'title' are required to create a post."
                
            payload = {
                "submolt_name": submolt,
                "title": title,
                "type": type
            }
            if content:
                payload["content"] = content
            if url:
                payload["url"] = url
                
            res = await request_moltbook("POST", "posts", data=payload)
            
            if not res.get("success"):
                error = res.get("error", "Unknown error")
                hint = res.get("hint", "")
                return f"❌ Failed to create post: {error}. {hint}"
                
            # Perform AI verification flow if necessary
            verified_res = await handle_verification_flow("post", res)
            
            post_data = verified_res.get("post", {})
            p_id = post_data.get("id") or verified_res.get("content_id")
            
            if verified_res.get("verification_solved") is True:
                return (
                    f"🚀 **Post Created & Automatically Verified by KAI!**\n\n"
                    f"- **Title:** \"{title}\"\n"
                    f"- **Submolt:** `r/{submolt}`\n"
                    f"- **Post ID:** `{p_id}`\n"
                    f"- **Status:** Published (Verification solved successfully!)"
                )
            elif verified_res.get("verification_solved") is False:
                return (
                    f"⚠️ **Post Created but Auto-Verification Failed!**\n\n"
                    f"- **Post ID:** `{p_id}`\n"
                    f"- **Error:** {verified_res.get('verification_error')}\n"
                    f"- **Hint:** {verified_res.get('verification_hint')}\n"
                    f"Your content is pending. You can try to solve it manually by calling the verify endpoint."
                )
            else:
                # No verification was required
                return (
                    f"🚀 **Post Created & Published Instantly!**\n\n"
                    f"- **Title:** \"{title}\"\n"
                    f"- **Submolt:** `r/{submolt}`\n"
                    f"- **Post ID:** `{p_id}`\n"
                    f"- **Status:** Published (No verification was required)"
                )
                
        elif action == "comment":
            if not post_id or not content:
                return "Error: 'post_id' and 'content' are required to create a comment."
                
            payload = {"content": content}
            if comment_id:
                payload["parent_id"] = comment_id
                
            res = await request_moltbook("POST", f"posts/{post_id}/comments", data=payload)
            
            if not res.get("success"):
                error = res.get("error", "Unknown error")
                hint = res.get("hint", "")
                return f"❌ Failed to create comment: {error}. {hint}"
                
            # Perform AI verification flow if necessary
            verified_res = await handle_verification_flow("comment", res)
            
            c_data = verified_res.get("comment", {})
            c_id = c_data.get("id") or verified_res.get("content_id")
            
            if verified_res.get("verification_solved") is True:
                return (
                    f"💬 **Comment Posted & Automatically Verified by KAI!**\n\n"
                    f"- **Post ID:** `{post_id}`\n"
                    f"- **Comment ID:** `{c_id}`\n"
                    f"- **Status:** Published (Verification solved successfully!)"
                )
            elif verified_res.get("verification_solved") is False:
                return (
                    f"⚠️ **Comment Posted but Auto-Verification Failed!**\n\n"
                    f"- **Comment ID:** `{c_id}`\n"
                    f"- **Error:** {verified_res.get('verification_error')}\n"
                    f"Your comment is pending. Solve the challenge manually if needed."
                )
            else:
                return (
                    f"💬 **Comment Posted & Published Instantly!**\n\n"
                    f"- **Post ID:** `{post_id}`\n"
                    f"- **Comment ID:** `{c_id}`\n"
                    f"- **Status:** Published (No verification was required)"
                )
                
        elif action == "delete":
            if not post_id:
                return "Error: 'post_id' is required to delete a post."
                
            res = await request_moltbook("DELETE", f"posts/{post_id}")
            if res.get("success"):
                return f"🗑️ **Post `{post_id}` has been successfully deleted.**"
            else:
                error = res.get("error", "Unknown error")
                return f"❌ Failed to delete post: {error}"
                
        elif action == "pin":
            if not post_id:
                return "Error: 'post_id' is required to pin a post."
                
            res = await request_moltbook("POST", f"posts/{post_id}/pin")
            if res.get("success"):
                return f"📌 **Post `{post_id}` successfully pinned to the top of the submolt.**"
            else:
                error = res.get("error", "Unknown error")
                return f"❌ Failed to pin post: {error}"
                
        elif action == "unpin":
            if not post_id:
                return "Error: 'post_id' is required to unpin a post."
                
            res = await request_moltbook("DELETE", f"posts/{post_id}/pin")
            if res.get("success"):
                return f"📌 **Post `{post_id}` successfully unpinned.**"
            else:
                error = res.get("error", "Unknown error")
                return f"❌ Failed to unpin post: {error}"
                
        else:
            return f"Error: Unknown action '{action}'. Supported actions are: post, comment, delete, pin, unpin."

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("This tool does not support synchronous execution.")
