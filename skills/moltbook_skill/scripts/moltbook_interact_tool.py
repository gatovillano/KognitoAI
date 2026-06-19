import logging
from typing import Type, Any, Optional
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool

from skills.moltbook_skill.scripts.moltbook_client import (
    request_moltbook,
    load_credentials
)

logger = logging.getLogger(__name__)

class MoltbookInteractInput(BaseModel):
    action: str = Field(
        ...,
        description="The action to perform: 'upvote_post', 'downvote_post', 'upvote_comment', 'follow', 'unfollow', 'subscribe', or 'unsubscribe'."
    )
    post_id: Optional[str] = Field(
        None,
        description="The ID of the post. Required for 'upvote_post' and 'downvote_post'."
    )
    comment_id: Optional[str] = Field(
        None,
        description="The ID of the comment. Required for 'upvote_comment'."
    )
    agent_name: Optional[str] = Field(
        None,
        description="The name of the target molty agent. Required for 'follow' and 'unfollow'."
    )
    submolt: Optional[str] = Field(
        None,
        description="The name of the target submolt community. Required for 'subscribe' and 'unsubscribe'."
    )

class MoltbookInteractTool(BaseTool):
    name: str = "moltbook_interact"
    description: str = (
        "Interact with the Moltbook community.\n"
        "- 'upvote_post': Upvotes a post. Requires 'post_id'.\n"
        "- 'downvote_post': Downvotes a post. Requires 'post_id'.\n"
        "- 'upvote_comment': Upvotes a comment. Requires 'comment_id'.\n"
        "- 'follow': Follows a molty agent to customize your feed. Requires 'agent_name'.\n"
        "- 'unfollow': Unfollows a molty agent. Requires 'agent_name'.\n"
        "- 'subscribe': Subscribes to a submolt community. Requires 'submolt'.\n"
        "- 'unsubscribe': Unsubscribes from a submolt community. Requires 'submolt'."
    )
    args_schema: Type[BaseModel] = MoltbookInteractInput  # type: ignore
    account_id: str
    workspace_id: Optional[str] = Field(None, description="The ID of the user workspace.")

    async def _arun(
        self,
        action: str,
        post_id: Optional[str] = None,
        comment_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        submolt: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        action = action.lower().strip()
        creds = load_credentials()
        if not creds.get("api_key"):
            return "Error: No Moltbook API key found. You must register an agent first."
            
        if action == "upvote_post":
            if not post_id:
                return "Error: 'post_id' is required to upvote a post."
            res = await request_moltbook("POST", f"posts/{post_id}/upvote")
            if res.get("success"):
                author = res.get("author", {}).get("name", "the author")
                following_str = " (You already follow them!)" if res.get("already_following") else " (You don't follow them yet. Consider following!)"
                return f"👍 **Upvoted post `{post_id}` successfully!**\n- Author: @{author}{following_str}\n- Hint: {res.get('tip', '')}"
            else:
                error = res.get("error", "Unknown error")
                return f"❌ Failed to upvote post: {error}"
                
        elif action == "downvote_post":
            if not post_id:
                return "Error: 'post_id' is required to downvote a post."
            res = await request_moltbook("POST", f"posts/{post_id}/downvote")
            if res.get("success"):
                return f"👎 **Downvoted post `{post_id}` successfully.**"
            else:
                error = res.get("error", "Unknown error")
                return f"❌ Failed to downvote post: {error}"
                
        elif action == "upvote_comment":
            if not comment_id:
                return "Error: 'comment_id' is required to upvote a comment."
            res = await request_moltbook("POST", f"comments/{comment_id}/upvote")
            if res.get("success"):
                return f"👍 **Upvoted comment `{comment_id}` successfully!**"
            else:
                error = res.get("error", "Unknown error")
                return f"❌ Failed to upvote comment: {error}"
                
        elif action == "follow":
            if not agent_name:
                return "Error: 'agent_name' is required to follow an agent."
            res = await request_moltbook("POST", f"agents/{agent_name}/follow")
            if res.get("success"):
                return f"✅ **Now following molty @{agent_name}!** Their posts will now appear in your customized feed."
            else:
                error = res.get("error", "Unknown error")
                return f"❌ Failed to follow agent '{agent_name}': {error}"
                
        elif action == "unfollow":
            if not agent_name:
                return "Error: 'agent_name' is required to unfollow an agent."
            res = await request_moltbook("DELETE", f"agents/{agent_name}/follow")
            if res.get("success"):
                return f"✅ **Unfollowed @{agent_name}.**"
            else:
                error = res.get("error", "Unknown error")
                return f"❌ Failed to unfollow agent '{agent_name}': {error}"
                
        elif action == "subscribe":
            if not submolt:
                return "Error: 'submolt' is required to subscribe to a community."
            res = await request_moltbook("POST", f"submolts/{submolt}/subscribe")
            if res.get("success"):
                return f"✅ **Subscribed to community r/{submolt}!**"
            else:
                error = res.get("error", "Unknown error")
                return f"❌ Failed to subscribe to 'r/{submolt}': {error}"
                
        elif action == "unsubscribe":
            if not submolt:
                return "Error: 'submolt' is required to unsubscribe from a community."
            res = await request_moltbook("DELETE", f"submolts/{submolt}/subscribe")
            if res.get("success"):
                return f"✅ **Unsubscribed from community r/{submolt}.**"
            else:
                error = res.get("error", "Unknown error")
                return f"❌ Failed to unsubscribe from 'r/{submolt}': {error}"
                
        else:
            return f"Error: Unknown action '{action}'. Supported actions are: upvote_post, downvote_post, upvote_comment, follow, unfollow, subscribe, unsubscribe."

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("This tool does not support synchronous execution.")
