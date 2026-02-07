import pandas as pd
import io
import os

def test_excel_support():
    print("Iniciando prueba de soporte Excel...")
    try:
        # Crear un DataFrame simple
        df = pd.DataFrame({'A': [1, 2, 3], 'B': ['x', 'y', 'z']})
        
        # Buffer de salida para guardar el Excel
        output = io.BytesIO()
        
        print("Intentando escribir archivo Excel (requiere openpyxl)...")
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        
        print("✅ Escritura de Excel exitosa.")
        
        # Intentar leerlo de vuelta
        output.seek(0)
        print("Intentando leer archivo Excel...")
        df_read = pd.read_excel(output, engine='openpyxl')
        
        print("✅ Lectura de Excel exitosa.")
        print("Contenido leído:")
        print(df_read)
        
        return True
    except ImportError as e:
        print(f"❌ Error: Falta una dependencia. {e}")
        return False
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return False

if __name__ == "__main__":
    success = test_excel_support()
    if not success:
        print("\nTIP: Si estás en Docker, asegúrate de reconstruir la imagen o ejecutar:")
        print("pip install openpyxl")
        exit(1)
    else:
        print("\n✨ ¡Todo parece estar en orden con las dependencias!")
        exit(0)
