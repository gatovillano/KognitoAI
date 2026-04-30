# Skill: Local File Navigator 🗂️

## Descripción
Esta skill permite navegar y explorar el sistema de archivos local de la máquina donde se ejecuta KAI. Es ideal para:
- Explorar directorios y archivos
- Leer contenido de archivos de texto
- Obtener metadatos de archivos y carpetas
- Buscar archivos por patrones
- Navegar entre directorios

## ⚠️ Consideraciones de Seguridad
- **Solo accede a archivos locales** - No tiene acceso a red
- **Límite de lectura** - Los archivos de más de 1MB se truncarán
- **Permisos del sistema** - Solo puede acceder a archivos/directorios donde el usuario tenga permisos
- **No modifica archivos** - Es una skill de solo lectura

## Parámetros de Entrada

### `action` (requerido)
Tipo de operación a realizar. Opciones:
- `'list'`: Lista archivos y directorios en una ruta
- `'read'`: Lee el contenido de un archivo de texto
- `'info'`: Muestra metadatos detallados
- `'navigate'`: Cambia el directorio de trabajo actual
- `'search'`: Busca archivos/directorios por patrón

### `path` (opcional)
Ruta relativa o absoluta. Por defecto usa el directorio actual (`.`).

### `file_name` (opcional, para 'read')
Nombre del archivo a leer (debe estar en el `path` especificado).

### `pattern` (opcional, para 'search')
Patrón de búsqueda usando comodines:
- `*.py` - todos los archivos Python
- `*.txt` - todos los archivos de texto
- `documento*` - archivos que empiezan con "documento"
- `*.*` - todos los archivos con extensión

### `recursive` (opcional, para 'search')
Si `True`, busca en subdirectorios. Por defecto `False`.

### `max_results` (opcional, para 'search')
Número máximo de resultados a devolver. Por defecto 50.

## Ejemplos de Uso

### 1. Listar directorio actual
```json
{
  "action": "list",
  "path": "."
}
```

### 2. Leer un archivo de texto
```json
{
  "action": "read",
  "path": "./docs",
  "file_name": "README.md"
}
```

### 3. Obtener información de un archivo
```json
{
  "action": "info",
  "path": "/home/usuario/documentos/proyecto.py"
}
```

### 4. Navegar a otro directorio
```json
{
  "action": "navigate",
  "path": ".."
}
```

### 5. Buscar archivos Python recursivamente
```json
{
  "action": "search",
  "path": ".",
  "pattern": "*.py",
  "recursive": true,
  "max_results": 100
}
```

### 6. Buscar archivos PDF en una carpeta específica
```json
{
  "action": "search",
  "path": "/ruta/documentos",
  "pattern": "*.pdf",
  "recursive": false
}
```

## Formato de Salida

### Para `list`
```
📁 Contenido de: /ruta/completa
Total: 15 elementos

📂 Directorios:
  📁 src/ (245.7 KB)
  📁 docs/ (1.2 MB)
  📁 tests/ (89.3 KB)

📄 Archivos:
  📄 README.md (2.3 KB) - Modificado: 2024-01-15 10:30:00
  📄 setup.py (1.1 KB) - Modificado: 2024-01-14 15:20:00
```

### Para `read`
```
📖 Contenido de: /ruta/archivo.txt

[Contenido del archivo...]
```

### Para `info`
```
🔍 Información de: /ruta/archivo.txt
Tipo: Archivo
Tamaño: 2.3 KB
Creado: 2024-01-10 09:15:00
Modificado: 2024-01-15 10:30:00
Accedido: 2024-01-15 10:31:00
Permisos: 644
Extensión: .txt
```

### Para `navigate`
```
✅ Navegado a: /ruta/nueva
Directorio actual: /ruta/nueva
```

### Para `search`
```
🔍 Resultados de búsqueda: '*.py'
Ruta: /proyecto
Recursivo: True
Encontrados: 12 (mostrando hasta 50)

📄 main.py (5.2 KB)
📄 utils/helpers.py (2.1 KB)
📁 tests/test_main.py (3.4 KB)
```

## Limitaciones
- **Tamaño de archivo**: Archivos mayores a 1MB se truncarán en lectura
- **Codificación**: Solo lee archivos de texto (UTF-8, con fallback a ignorar errores)
- **Búsqueda**: Patrones simples con comodines (* y ?)
- **Sistema de archivos**: Solo acceso local, no redes ni URLs

## Casos de Uso Recomendados
✅ Revisar estructura de proyectos
✅ Leer archivos de configuración
✅ Buscar archivos específicos
✅ Ver metadatos de documentos
✅ Navegar por directorios de trabajo

## Casos de Uso NO Recomendados
❌ Modificar archivos (no tiene capacidad de escritura)
❌ Acceder a archivos del sistema protegidos (no tendrá permisos)
❌ Leer archivos binarios grandes (se truncarán)
❌ Acceder a recursos de red o URLs

## Notas Técnicas
- Utiliza `pathlib` para manipulación de rutas (compatible con Windows, Linux, macOS)
- Los paths relativos se resuelven desde el directorio actual de trabajo
- El directorio de trabajo persiste entre llamadas a la skill
- Para seguridad, se limita el tamaño máximo de lectura a 10KB por archivo

---

**Skill creada para KAI** - Navegación segura y eficiente del sistema de archivos local 🚀