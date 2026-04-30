# Host Terminal Skill 🖥️

## Descripción

Esta habilidad permite **ejecutar comandos de sistema directamente en tu máquina host** a través de una conexión SSH segura.

## Configuración

| Parámetro | Valor |
|-----------|-------|
| **Host** | `host.docker.internal` |
| **Usuario** | `gato` |
| **Puerto** | `22` (estándar) |
| **Autenticación** | Llave SSH ED25519 (`/tmp/kai_id_ed25519`) |

## Uso

```json
{
  "command": "tu_comando_aqui",
  "timeout": 30
}
```

## Parámetros

- `command` (string, requerido): Comando a ejecutar
- `timeout` (integer, opcional): Timeout en segundos (default: 30)

## Ejemplos

| Objetivo | Comando |
|----------|---------|  
| Info del sistema | `uname -a` |
| Contenedores Docker | `docker ps` |
| Espacio en disco | `df -h` |
| Memoria | `free -h` |
| IP | `hostname -I` |