import logging
import json
from typing import Type, Any, Optional
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool

from skills.moltbook_skill.scripts.moltbook_client import (
    request_moltbook,
    load_credentials
)

logger = logging.getLogger(__name__)

class MoltbookDashboardInput(BaseModel):
    action: str = Field(
        ...,
        description="The action to perform: 'get_home' (get main home dashboard), 'mark_read_by_post' (mark comments on a post as read), or 'mark_read_all' (mark all notifications read)."
    )
    post_id: Optional[str] = Field(
        None,
        description="The ID of the post. Required for 'mark_read_by_post'."
    )

class MoltbookDashboardTool(BaseTool):
    name: str = "moltbook_dashboard"
    description: str = (
        "View the central Moltbook home dashboard and manage notification read states.\n"
        "- 'get_home': Retrieves account summary, unread notifications count, recent follow activities, DMs, announcements, and recommended next actions.\n"
        "- 'mark_read_by_post': Marks all notifications for a specific post as read. Requires 'post_id'.\n"
        "- 'mark_read_all': Marks all account notifications as read."
    )
    args_schema: Type[BaseModel] = MoltbookDashboardInput  # type: ignore
    account_id: str
    workspace_id: Optional[str] = Field(None, description="The ID of the user workspace.")

    async def _arun(
        self,
        action: str,
        post_id: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        action = action.lower().strip()
        creds = load_credentials()
        if not creds.get("api_key"):
            return "Error: No Moltbook API key found. You must register an agent first."
            
        if action == "get_home":
            res = await request_moltbook("GET", "home")
            
            if "your_account" not in res:
                error = res.get("error", "Unknown error")
                return f"❌ Failed to retrieve home dashboard: {error}"
                
            account = res["your_account"]
            activity = res.get("activity_on_your_posts", [])
            dms = res.get("your_direct_messages", {})
            announcement = res.get("latest_moltbook_announcement") or {}
            follow_posts = res.get("posts_from_accounts_you_follow", {}).get("posts", [])
            actions = res.get("what_to_do_next", [])
            
            # Format output beautifully
            output = [
                f"🏠 **Moltbook Home Dashboard: {account.get('name')}**",
                f"- **Karma:** {account.get('karma', 0)} 🌟",
                f"- **Unread Notifications:** {account.get('unread_notification_count', 0)} 🔔",
                f"- **Direct Messages:** {dms.get('unread_message_count', 0)} unread | {dms.get('pending_request_count', 0)} pending requests\n"
            ]
            
            if announcement:
                output.append(f"📢 **Latest Announcement:**")
                output.append(f"  *Title:* \"{announcement.get('title', 'N/A')}\" (Post ID: `{announcement.get('post_id')}`)")
                output.append(f"  *Preview:* {announcement.get('preview', 'N/A')}\n")
                
            if activity:
                output.append("💬 **New Activity on Your Posts:**")
                for act in activity:
                    output.append(
                        f"  - **{act.get('post_title')}** (Submolt: `{act.get('submolt_name')}`)"
                    )
                    output.append(
                        f"    * {act.get('new_notification_count')} new notification(s) | Latest by: {', '.join(act.get('latest_commenters', []))}"
                    )
                    output.append(f"    * Preview: \"{act.get('preview')}\"")
                    output.append(f"    * ID: `{act.get('post_id')}`")
                output.append("")
                
            if follow_posts:
                output.append("👥 **Recent Posts from Accounts You Follow:**")
                for fp in follow_posts:
                    output.append(
                        f"  - **{fp.get('title')}** by @{fp.get('author_name')} in `{fp.get('submolt_name')}`"
                    )
                    output.append(
                        f"    * {fp.get('upvotes')} upvotes | {fp.get('comment_count')} comments"
                    )
                    output.append(f"    * Preview: \"{fp.get('content_preview')}\"")
                    output.append(f"    * ID: `{fp.get('post_id')}`")
                output.append("")
                
            if actions:
                output.append("🎯 **Recommended Next Actions:**")
                for act in actions:
                    output.append(f"  - {act}")
                    
            return "\n".join(output)
            
        elif action == "mark_read_by_post":
            if not post_id:
                return "Error: 'post_id' is required to mark notifications for a post as read."
                
            res = await request_moltbook("POST", f"notifications/read-by-post/{post_id}")
            if res.get("success"):
                return f"✅ Marked all notifications for post `{post_id}` as read."
            else:
                error = res.get("error", "Unknown error")
                return f"❌ Failed to mark notifications as read: {error}"
                
        elif action == "mark_read_all":
            res = await request_moltbook("POST", "notifications/read-all")
            if res.get("success"):
                return "✅ Marked all notifications as read."
            else:
                error = res.get("error", "Unknown error")
                return f"❌ Failed to mark all notifications as read: {error}"
                
        else:
            return f"Error: Unknown action '{action}'. Supported actions are: get_home, mark_read_by_post, mark_read_all."

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("This tool does not support synchronous execution.")
