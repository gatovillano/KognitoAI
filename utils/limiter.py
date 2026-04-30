from slowapi import Limiter
from slowapi.util import get_remote_address

# Instancia compartida del limitador para toda la aplicación
# Permite ser importada tanto en api/main.py como en los routers hijos sin dependencias circulares.
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])
