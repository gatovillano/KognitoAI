# File Manager SSH Tool 🗂️

## Descripción

Esta skill permite realizar operaciones CRUD (Create, Read, Update, Delete) en el sistema de archivos del host mediante SSH. Soporta autenticación por **llave SSH** y **contraseña**.

## Parámetros

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `operation` | string | Operación a realizar: `list_dir`, `read_file`, `write_file`, `mkdir`, `mv`, `rm`, etc. |
| `path` | string | Ruta del archivo o directorio |
| `options` | string | Parámetros adicionales según la operación |
| `config_override` | object | Configuración SSH personalizada (opcional) |

## Operaciones Disponibles

### 📖 READ
- `list_dir`: Lista archivos en un directorio
- `read_file`: Lee el contenido de un archivo
- `head`: Muestra las primeras líneas de un archivo
- `tail`: Muestra las últimas líneas de un archivo
- `stat`: Muestra información del archivo
- `file_type`: Determina el tipo de archivo
- `wc`: Cuenta líneas, palabras y caracteres
- `find`: Busca archivos por nombre o patrón
- `tree`: Muestra estructura de directorios
- `exists`: Verifica si existe un archivo o directorio

### ✏️ CREATE
- `write_file`: Crea o sobrescribe un archivo
- `mkdir`: Crea un directorio

### 🔄 UPDATE
- `mv`: Mueve o renombra archivos
- `chmod`: Cambia permisos
- `append`: Agrega contenido a un archivo

### 🗑️ DELETE
- `rm`: Elimina archivos
- `rmdir`: Elimina directorios vacíos

## Configuración SSH

```json
{
  "host": "host.docker.internal",
  "port": 22,
  "user": "gato",
  "auth_method": "key|password",
  "ssh_key_path": "/ruta/a/llave",
  "password": "contraseña"
}
```

## Ejemplos

```python
# Listar archivos
{"operation": "list_dir", "path": "/home"}

# Leer archivo
{"operation": "read_file", "path": "/tmp/test.txt"}

# Crear archivo
{"operation": "write_file", "path": "/tmp/nuevo.txt", "content": "Hola mundo"}

# Crear directorio
{"operation": "mkdir", "path": "/home/user/proyecto"}
```