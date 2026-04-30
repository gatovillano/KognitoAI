# 📋 Notas de Diagnóstico - KognitoAI
**Fecha:** 2026-03-18
**Estado:** ❌ Error de dependencias impide ejecución

---

## 🚨 Problema Identificado

**Error:** `ModuleNotFoundError: No module named 'langchain_core'`

**Impacto:** La aplicación no puede importar `core.agent` porque falta langchain_core.

---

## 🔍 Diagnóstico

### Dependencias clave (requirements.txt):
```
langchain>=0.3.27,<0.4.0
langchain-core>=0.3.74,<0.4.0
langchain-community>=0.3.27,<0.4.0
langgraph>=0.2.65
```

### Estado del sistema:
- Python: 3.12.3
- Virtual env existe: `venv/` (creado en mar 15)
- FastAPI funciona (importable)
- **LangChain NO funciona** (no instalado en el entorno activo)

### Posibles causas:

1. **Virtualenv no activado** - Se está usando python3 del sistema en lugar del venv
2. **Dependencias no instaladas** - `pip install -r requirements.txt` no ejecutado en el venv
3. **Conflictos de versiones** - Aunque requirements.txt tiene rangos flexibles, alguna dependencia podría fallar
4. **Instalación corrupta** - Paquetes instalados pero con problemas

---

## ✅ Solución Paso a Paso

### Paso 1: Activar virtualenv correctamente

```bash
cd /home/gato/Proyectos/KognitoAI/kognito-ai

# Activar venv (zsh)
source venv/bin/activate

# Verificar que estás en el venv
which python3  # Debería mostrar: /home/gato/Proyectos/KognitoAI/kognito-ai/venv/bin/python3
```

### Paso 2: Actualizar pip e instalar dependencias

```bash
# Actualizar pip dentro del venv
pip install --upgrade pip

# Instalar todas las dependencias
pip install -r requirements.txt

# Si hay errores, intentar con:
pip install -r requirements.txt --no-cache-dir
```

### Paso 3: Verificar instalación

```bash
# Listar paquetes clave
pip list | grep -i langchain
pip list | grep -i langgraph
pip list | grep -i fastapi

# Probar imports
python3 -c "import langchain; print('LangChain:', langchain.__version__)"
python3 -c "import langgraph; print('LangGraph:', langgraph.__version__)"
python3 -c "from core.agent import agent_graph; print('Agent OK')"
```

### Paso 4: Si hay conflictos de versiones

Si `pip install` falla por conflictos Python 3.12:

```bash
# Opción A: Forzar reinstalación limpia
pip uninstall langchain langchain-core langchain-community langgraph -y
pip install langchain==0.3.74 langchain-core==0.3.74 langgraph==0.2.65

# Opción B: Usar requirements.minimal.txt (si existe)
pip install -r requirements.minimal.txt
```

### Paso 5: Probar la aplicación

```bash
# Desde el directorio kognito-ai, con venv activado:
python run_api.py
```

Debería ver el logo ASCII y empezar a servir en http://localhost:8000

---

## 🐛 Si el problema persiste

### Verificar arquitectura de paquetes
```bash
python3 -c "import sys; print(sys.version)"
python3 -c "import platform; print(platform.machine())"
```

### Reinstalar desde cero
```bash
# Eliminar venv y recrear
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Ver logs de instalación
```bash
# Guardar log completo de instalación
pip install -r requirements.txt 2>&1 | tee install_log.txt
# Revisar install_log.txt en busca de errores
```

---

## 📊 Estado de Dependencias (esperado)

| Paquete | Versión mínima | Estado |
|---------|----------------|--------|
| fastapi | 0.100.0 | ✅ |
| uvicorn | 0.20.0 | ✅ |
| langchain | 0.3.27 | ❌ |
| langchain-core | 0.3.74 | ❌ |
| langchain-community | 0.3.27 | ❌ |
| langgraph | 0.2.65 | ❌ |
| pgvector | 0.2.0 | ? |
| neo4j | 5.15.0 | ? |
| google-auth | 2.20.0 | ? |

---

## 📝 Acciones Completadas

- [x] Leer requirements.txt
- [x] Verificar Python version
- [x] Identificar error: langchain_core faltante
- [x] Documentar pasos de solución

---

## 📞 Próximos Pasos

1. Tú ejecuta los pasos 1-3 de "Solución Paso a Paso"
2. Si tienes errores, comparte el output
3. Si funciona, proceder a revisar logs y testes (ver TODO.md de KognitoAI)

---

**Nota:** Este archivo es una nota técnica rápida. Para avances detallados, marcar tareas en `/home/gato/Proyectos/KognitoAI/kognito-ai/TODO.md`
