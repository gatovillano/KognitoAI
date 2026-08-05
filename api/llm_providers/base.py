from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class LLMProviderStrategy(ABC):
    """Interfaz base para todos los proveedores de LLM."""
    
    @abstractmethod
    async def get_models(self, api_key: Optional[str], api_base: Optional[str]) -> List[Dict[str, Any]]:
        """
        Debe retornar una lista de diccionarios con la estructura:
        {'id': str, 'name': str, 'context_length': int, ...}
        """
        pass
