
import sys
import os
import logging

# Configurar logging para ver qué pasa
logging.basicConfig(level=logging.INFO)

# Añadir el path del proyecto
sys.path.append("/home/gato/KognitoAI/kognito-ai")

from utils.patches import apply_patches
from langchain_community.chat_message_histories import PostgresChatMessageHistory

def test_postgres_history_error():
    apply_patches()
    
    print("\n--- Test 1: URL malformada ---")
    try:
        # URL malformada para fallo inmediato
        history = PostgresChatMessageHistory(
            connection_string="not-a-url",
            session_id="test_session",
            table_name="test_table"
        )
    except Exception as e:
        print(f"Atrapada excepción esperada: {type(e).__name__}: {e}")

    print("\n--- Test 2: Simular objeto sin cursor y llamar a __del__ ---")
    # Creamos un objeto "roto" manualmente para ver si el parche funciona
    class BrokenHistory(PostgresChatMessageHistory):
        def __init__(self):
            self.connection_string = "foo"
            self.session_id = "bar"
            self.table_name = "baz"
            # NO definimos self.cursor ni self.connection

    broken = BrokenHistory()
    print("Objeto roto creado. Intentando eliminarlo...")
    try:
        del broken
        print("Objeto roto eliminado sin errores.")
    except Exception as e:
        print(f"ERROR al eliminar objeto roto: {type(e).__name__}: {e}")

    print("\nFin del test.")

if __name__ == "__main__":
    test_postgres_history_error()
