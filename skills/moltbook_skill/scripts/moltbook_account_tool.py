import logging
import traceback
from typing import Type, Any, Optional
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool

from skills.moltbook_skill.scripts.moltbook_client import (
    request_moltbook,
    save_credentials,
    load_credentials,
    delete_credentials
)

logger = logging.getLogger(__name__)

class MoltbookAccountInput(BaseModel):
    action: str = Field(
        ...,
        description="The action to perform: 'register' (register new agent), 'status' (check claim status), 'setup_email' (set owner human email), 'view_profile' (view a molty's profile details), or 'delete' (delete locally stored credentials to reset configuration)."
    )
    agent_name: Optional[str] = Field(
        None,
        description="The name of the agent. Required for 'register' and 'view_profile'."
    )
    description: Optional[str] = Field(
        None,
        description="The description of what the agent does. Optional/recommended for 'register'."
    )
    email: Optional[str] = Field(
        None,
        description="The human owner's email address. Required for 'setup_email'."
    )

class MoltbookAccountTool(BaseTool):
    name: str = "moltbook_account"
    description: str = (
        "Manage your Moltbook agent account.\n"
        "- 'register': Registers a new agent. Automatic credential saving. Requires 'agent_name' and optionally 'description'.\n"
        "- 'status': Checks the agent claim status (pending_claim or claimed).\n"
        "- 'setup_email': Sets the owner human email. Requires 'email'.\n"
        "- 'view_profile': Retrieves profile details for a specific agent. Requires 'agent_name'.\n"
        "- 'delete': Deletes local credentials from disk to allow configuring a new account."
    )
    args_schema: Type[BaseModel] = MoltbookAccountInput  # type: ignore
    account_id: str
    workspace_id: Optional[str] = Field(None, description="The ID of the user workspace.")

    async def _arun(
        self,
        action: str,
        agent_name: Optional[str] = None,
        description: Optional[str] = None,
        email: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        # ── LOG DE ENTRADA ──────────────────────────────────────────────────
        logger.info("=" * 60)
        logger.info(f"[moltbook_account] 🚀 INICIO DE EJECUCIÓN")
        logger.info(f"[moltbook_account] Action  : {action!r}")
        logger.info(f"[moltbook_account] Agent   : {agent_name!r}")
        logger.info(f"[moltbook_account] Desc    : {description!r}")
        logger.info(f"[moltbook_account] Email   : {email!r}")
        logger.info(f"[moltbook_account] Kwargs  : {kwargs!r}")
        logger.info("=" * 60)

        # Normalizar acción
        action = action.lower().strip()
        logger.info(f"[moltbook_account] 🔄 Acción normalizada: {action!r}")

        try:
            # ── REGISTER ────────────────────────────────────────────────────
            if action == "register":
                logger.info("[moltbook_account] 📝 Rama: REGISTER")
                if not agent_name:
                    logger.warning("[moltbook_account] ⚠️ agent_name faltante para register")
                    return "Error: 'agent_name' is required when registering a new agent."

                payload = {"name": agent_name}
                if description:
                    payload["description"] = description
                    logger.info(f"[moltbook_account] Payload register (sin API key): {{'name': {agent_name!r}, 'description': {description!r}}}")
                else:
                    logger.info(f"[moltbook_account] Payload register (sin API key): {{'name': {agent_name!r}}}")

                logger.info("[moltbook_account] 🌐 Llamando a request_moltbook POST agents/register ...")
                res = await request_moltbook("POST", "agents/register", data=payload)
                logger.info(f"[moltbook_account] 📡 Respuesta recibida (status OK={res.get('agent') is not None}): {self._safe_log_dict(res)}")

                if res.get("agent") and "api_key" in res["agent"]:
                    agent_info = res["agent"]
                    api_key = agent_info["api_key"]
                    claim_url = agent_info.get("claim_url")
                    verification_code = agent_info.get("verification_code")

                    logger.info(f"[moltbook_account] ✅ Agente detectado: {agent_name!r}")
                    logger.info(f"[moltbook_account] 🔑 API key recibida (len={len(api_key)})")
                    logger.info(f"[moltbook_account] 🔗 Claim URL : {claim_url!r}")
                    logger.info(f"[moltbook_account] 🧾 Verif code: {verification_code!r}")

                    # Guardar credenciales
                    logger.info(f"[moltbook_account] 💾 Guardando credenciales en disco ...")
                    save_credentials(api_key, agent_name)
                    logger.info("[moltbook_account] ✅ Credenciales guardadas exitosamente")

                    return (
                        f"🎉 **Agent Registered Successfully!**\n\n"
                        f"- **Agent Name:** {agent_name}\n"
                        f"- **Verification Code:** {verification_code}\n"
                        f"- **Claim URL:** {claim_url}\n\n"
                        f"⚠️ **IMPORTANT:** Share the Claim URL with your human immediately so they can claim and activate your account!\n"
                        f"Credentials have been saved to `~/.config/moltbook/credentials.json`."
                    )
                else:
                    error = res.get("error", "Unknown error")
                    hint = res.get("hint", "")
                    logger.error(f"[moltbook_account] ❌ Fallo en registro: error={error!r}, hint={hint!r}")
                    return f"❌ Failed to register agent: {error}. {hint}"

            # ── STATUS ──────────────────────────────────────────────────────
            elif action == "status":
                logger.info("[moltbook_account] 📊 Rama: STATUS")
                creds = load_credentials()
                logger.info(f"[moltbook_account] Credenciales cargadas: api_key_present={bool(creds.get('api_key'))}, agent_name={creds.get('agent_name')!r}")

                if not creds.get("api_key"):
                    logger.warning("[moltbook_account] ⚠️ No hay API key en credenciales")
                    return "Error: No Moltbook API key found. You must register an agent first."

                logger.info("[moltbook_account] 🌐 Llamando a request_moltbook GET agents/status ...")
                res = await request_moltbook("GET", "agents/status")
                logger.info(f"[moltbook_account] 📡 Respuesta status: {self._safe_log_dict(res)}")

                status = res.get("status", "unknown")
                logger.info(f"[moltbook_account] 📋 Estado final: {status!r}")

                return (
                    f"👤 **Moltbook Agent Status**\n\n"
                    f"- **Agent Name:** {creds.get('agent_name')}\n"
                    f"- **Claim Status:** `{status}`\n"
                    f"- **Description:** {res.get('description', 'N/A')}\n"
                    f"- **Message:** {res.get('message', 'No message')}"
                )

            # ── SETUP EMAIL ─────────────────────────────────────────────────
            elif action == "setup_email":
                logger.info("[moltbook_account] 📧 Rama: SETUP_EMAIL")
                if not email:
                    logger.warning("[moltbook_account] ⚠️ Email faltante para setup_email")
                    return "Error: 'email' is required to set up the owner email."

                creds = load_credentials()
                logger.info(f"[moltbook_account] Credenciales cargadas: api_key_present={bool(creds.get('api_key'))}")
                if not creds.get("api_key"):
                    logger.warning("[moltbook_account] ⚠️ No hay API key en credenciales")
                    return "Error: No Moltbook API key found. You must register an agent first."

                email_payload = {"email": email}
                logger.info(f"[moltbook_account] 🌐 Llamando POST agents/me/setup-owner-email con email={email!r} ...")
                res = await request_moltbook("POST", "agents/me/setup-owner-email", data=email_payload)
                logger.info(f"[moltbook_account] 📡 Respuesta setup-email: {self._safe_log_dict(res)}")

                if res.get("success"):
                    logger.info(f"[moltbook_account] ✅ Email setup exitoso para {email!r}")
                    return f"✅ Email setup link successfully sent to **{email}**. Your human should check their inbox to complete setup!"
                else:
                    error = res.get("error", "Unknown error")
                    hint = res.get("hint", "")
                    logger.error(f"[moltbook_account] ❌ Fallo setup-email: error={error!r}, hint={hint!r}")
                    return f"❌ Failed to setup owner email: {error}. {hint}"

            # ── VIEW PROFILE ────────────────────────────────────────────────
            elif action == "view_profile":
                logger.info("[moltbook_account] 👤 Rama: VIEW_PROFILE")
                if not agent_name:
                    logger.warning("[moltbook_account] ⚠️ agent_name faltante para view_profile")
                    return "Error: 'agent_name' is required to view a profile."

                logger.info(f"[moltbook_account] 🌐 Llamando GET agents/profile?name={agent_name!r} ...")
                res = await request_moltbook("GET", "agents/profile", params={"name": agent_name})
                logger.info(f"[moltbook_account] 📡 Respuesta profile: success={res.get('success')}, agent_present={res.get('agent') is not None}")

                if res.get("success") and "agent" in res:
                    agent = res["agent"]
                    logger.info(f"[moltbook_account] ✅ Perfil encontrado para {agent_name!r}: karma={agent.get('karma')}, followers={agent.get('follower_count')}")
                    owner = agent.get("owner") or {}
                    owner_info = ""
                    if owner:
                        owner_info = (
                            f"\n**Human Owner (X/Twitter):**\n"
                            f"- Name: {owner.get('x_name', 'N/A')}\n"
                            f"- Handle: @{owner.get('x_handle', 'N/A')}\n"
                            f"- Bio: {owner.get('x_bio', 'N/A')}\n"
                        )
                    return (
                        f"🦞 **Moltbook Profile: {agent.get('name')}**\n\n"
                        f"- **Description:** {agent.get('description', 'No description')}\n"
                        f"- **Karma:** {agent.get('karma', 0)} 🌟\n"
                        f"- **Followers:** {agent.get('follower_count', 0)} | **Following:** {agent.get('following_count', 0)}\n"
                        f"- **Posts:** {agent.get('posts_count', 0)} | **Comments:** {agent.get('comments_count', 0)}\n"
                        f"- **Claimed:** {'✅ Yes' if agent.get('is_claimed') else '❌ Pending'}\n"
                        f"- **Created At:** {agent.get('created_at', 'N/A')}\n"
                        f"{owner_info}"
                    )
                else:
                    error = res.get("error", "Unknown error")
                    logger.error(f"[moltbook_account] ❌ Fallo al obtener perfil de '{agent_name}': {error!r}")
                    return f"❌ Failed to fetch profile for '{agent_name}': {error}"

            # ── DELETE / RESET ──────────────────────────────────────────────
            elif action in ("delete", "reset"):
                logger.info(f"[moltbook_account] 🗑️  Rama: DELETE/RESET (action={action!r})")
                try:
                    existed = delete_credentials()
                    logger.info(f"[moltbook_account] Resultado delete_credentials: existed={existed}")
                    if existed:
                        logger.info("[moltbook_account] ✅ Credenciales borradas exitosamente")
                        return (
                            "🧹 **Moltbook Credentials Deleted successfully!**\n\n"
                            "The locally saved credentials in `~/.config/moltbook/credentials.json` have been deleted. "
                            "You can now register a new agent or configure another account using the 'register' action."
                        )
                    else:
                        logger.info("[moltbook_account] ℹ️ No había credenciales para borrar")
                        return "ℹ️ No Moltbook credentials were found in `~/.config/moltbook/credentials.json`. Nothing to delete."
                except Exception as e:
                    tb = traceback.format_exc()
                    logger.error(f"[moltbook_account] ❌ Excepción borrando credenciales: {e}\n{tb}")
                    return f"❌ Failed to delete credentials: {e}"

            # ── ACCIÓN DESCONOCIDA ──────────────────────────────────────────
            else:
                logger.warning(f"[moltbook_account] ⚠️ Acción desconocida recibida: {action!r}")
                return f"Error: Unknown action '{action}'. Supported actions are: register, status, setup_email, view_profile, delete."

        except Exception as e:
            tb = traceback.format_exc()
            logger.error(f"[moltbook_account] 💥 EXCEPCIÓN NO CONTROLADA en action={action!r}: {e}\n{tb}")
            return f"❌ Unexpected error during '{action}': {e}"

        finally:
            logger.info(f"[moltbook_account] 🏁 FIN DE EJECUCIÓN (action={action!r})")
            logger.info("=" * 60)

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("This tool does not support synchronous execution.")

    @staticmethod
    def _safe_log_dict(d: dict) -> dict:
        """Devuelve una copia del dict con campos sensibles ofuscados para logs."""
        SENSITIVE_KEYS = {"api_key", "password", "token", "secret", "authorization"}
        safe = {}
        for k, v in d.items():
            if any(s in k.lower() for s in SENSITIVE_KEYS):
                safe[k] = f"***REDACTED***" if v else None
            elif isinstance(v, dict):
                safe[k] = MoltbookAccountTool._safe_log_dict(v)
            else:
                safe[k] = v
        return safe
