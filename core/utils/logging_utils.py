
import logging
import json
from typing import Any, Optional

# Colores ANSI para terminal
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class AgentLogger:
    """
    Utilidad para estandarizar y embellecer los logs del proceso del agente.
    """
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)

    def node_start(self, node_name: str, account_id: str):
        self.logger.info(f"{Colors.BOLD}{Colors.CYAN}⟳ [GRAFO]{Colors.ENDC} Nodo: {Colors.BOLD}{node_name}{Colors.ENDC} (Cuenta: {account_id})")

    def model_start(self, model_name: str):
        self.logger.info(f"{Colors.GREEN}🤖 [LLM]{Colors.ENDC} Generando con: {Colors.BOLD}{model_name}{Colors.ENDC}")

    def tool_call(self, tool_name: str, args: Any):
        # Truncar argumentos largos para limpieza
        args_str = json.dumps(args, ensure_ascii=False)
        if len(args_str) > 150:
            args_str = args_str[:147] + "..."
        self.logger.info(f"{Colors.BLUE}🛠️ [TOOL]{Colors.ENDC} Ejecutando: {Colors.BOLD}{tool_name}{Colors.ENDC} | Args: {args_str}")

    def tool_result(self, tool_name: str, success: bool, error_msg: Optional[str] = None):
        if success:
            self.logger.info(f"{Colors.GREEN}✅ [TOOL]{Colors.ENDC} Completado: {tool_name}")
        else:
            self.logger.error(f"{Colors.FAIL}❌ [TOOL]{Colors.ENDC} Falló: {tool_name} | Error: {error_msg}")

    def inference(self, tool_name: str, arg_name: str, value: str):
        self.logger.info(f"{Colors.WARNING}💡 [AI]{Colors.ENDC} Inferido {arg_name} para {tool_name}: {value[:50]}...")

    def info(self, msg: str):
        self.logger.info(f"ℹ️ {msg}")

    def warning(self, msg: str):
        self.logger.warning(f"⚠️ {msg}")

    def error(self, msg: str, exc_info: bool = False):
        self.logger.error(f"❌ {msg}", exc_info=exc_info)

    def isEnabledFor(self, level: int) -> bool:
        return self.logger.isEnabledFor(level)

    def debug(self, msg: str):
        self.logger.debug(msg)

# Objeto global de ejemplo si se quiere usar por defecto
agent_logger = AgentLogger("core.agent")
