#!/usr/bin/env python3
"""
Reanuda la copia de kognitoalbums desde el servidor remoto (gatoserv-1).

Solo transfiere los archivos que faltan o cuyo tamano difiere.
Es idempotente y reanudable: se puede ejecutar cuantas veces se quiera.

Uso:
    python3 scripts/copiar_kognitoalbums.py            # copia todo lo que falte
    python3 scripts/copiar_kognitoalbums.py --check    # solo muestra el progreso

Variables de entorno opcionales:
    REMOTE_HOST, REMOTE_BASE, LOCAL_BASE, BATCH_SIZE
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time

REMOTE_HOST = os.getenv("REMOTE_HOST", "gato@100.124.39.12")
REMOTE_BASE = os.getenv(
    "REMOTE_BASE", "/run/media/gato/Almacenamiento/Nueva Fototeca/kognitoalbums"
)
LOCAL_BASE = os.getenv("LOCAL_BASE", os.path.expanduser("~/kognito-data/kognitoalbums"))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "120"))

SSH_OPTS = [
    "-o", "ConnectTimeout=20",
    "-o", "ServerAliveInterval=30",
    "-o", "ServerAliveCountMax=10",
    "-o", "RekeyLimit=1G",
]

REINTENTOS = 5
ESPERA_REINTENTO = 10


def log(msg: str) -> None:
    print(msg, flush=True)


def human(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def ssh(args: list[str], stdin_data: bytes | None = None, timeout: int = 120):
    return subprocess.run(
        ["ssh", *SSH_OPTS, REMOTE_HOST, *args],
        input=stdin_data,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )


def preflight() -> bool:
    """Comprueba que el servidor responde y que el disco esta montado."""
    cmd = (
        f"test -d '{REMOTE_BASE}' && "
        f"find '{REMOTE_BASE}' -type f -printf '.' | wc -c"
    )
    try:
        p = ssh([cmd], timeout=40)
    except subprocess.TimeoutExpired:
        log("ERROR: el servidor remoto no responde (timeout).")
        return False
    err = p.stderr.decode(errors="replace").strip()
    out = p.stdout.strip()

    # rc=255 => SSH no pudo conectar (servidor apagado / sin red)
    if p.returncode == 255:
        log(f"ERROR: no se puede conectar al servidor. {err[:200]}")
        return False
    # rc=1 con salida vacia => el directorio no existe (disco sin montar)
    if p.returncode != 0 or not out.isdigit():
        if "No existe" in err or "denegado" in err:
            log(f"ERROR: el disco no esta montado en el servidor. {err[:200]}")
        elif p.returncode == 1 and not out:
            log(f"ERROR: no existe la ruta remota: {REMOTE_BASE}")
            log("      -> monta el disco 'Almacenamiento' en el servidor remoto")
        else:
            log(f"ERROR preflight (rc={p.returncode}): {err[:300] or out[:200]}")
        return False

    log(f"==> Preflight OK: {out.decode()} archivos remotos")
    return True


def remote_manifest() -> dict[str, int]:
    cmd = f"find '{REMOTE_BASE}' -type f -printf '%s\\t%P\\n'"
    p = ssh([cmd], timeout=300)
    manifest: dict[str, int] = {}
    for line in p.stdout.decode(errors="replace").splitlines():
        if "\t" not in line:
            continue
        size_s, rel = line.split("\t", 1)
        try:
            manifest[rel] = int(size_s)
        except ValueError:
            continue
    return manifest


def local_manifest() -> dict[str, int]:
    manifest: dict[str, int] = {}
    for root, _dirs, files in os.walk(LOCAL_BASE):
        for fn in files:
            full = os.path.join(root, fn)
            try:
                manifest[os.path.relpath(full, LOCAL_BASE)] = os.path.getsize(full)
            except OSError:
                continue
    return manifest


def diff(rem: dict[str, int], loc: dict[str, int]) -> list[str]:
    """Archivos remotos que faltan localmente o difieren en tamano."""
    return sorted(rel for rel, size in rem.items() if loc.get(rel) != size)


def copiar_lote(lote: list[str]) -> bool:
    """Transfiere un lote de archivos. Devuelve True si todo fue bien."""
    payload = ("\0".join(lote) + "\0").encode("utf-8")
    remote_cmd = (
        f"cd '{REMOTE_BASE}' && "
        "tar --null --files-from=- --ignore-failed-read -cf -"
    )

    ssh_proc = subprocess.Popen(
        ["ssh", *SSH_OPTS, REMOTE_HOST, remote_cmd],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    tar_proc = subprocess.Popen(
        ["tar", "xf", "-", "-C", LOCAL_BASE],
        stdin=ssh_proc.stdout,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    assert ssh_proc.stdout is not None
    ssh_proc.stdout.close()

    _o, err_tar = tar_proc.communicate()
    try:
        ssh_proc.stdin.write(payload)
        ssh_proc.stdin.close()
    except BrokenPipeError:
        pass
    err_ssh = ssh_proc.stderr.read().decode(errors="replace")
    ssh_proc.wait()

    if tar_proc.returncode != 0 or ssh_proc.returncode != 0:
        log(f"    [lote fallo] tar={tar_proc.returncode} ssh={ssh_proc.returncode}")
        if err_tar:
            log(f"    tar: {err_tar.decode(errors='replace').strip()[:200]}")
        if err_ssh:
            log(f"    ssh: {err_ssh.strip()[:200]}")
        return False
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="solo muestra progreso")
    args = ap.parse_args()

    os.makedirs(LOCAL_BASE, exist_ok=True)

    if not preflight():
        return 2

    log("==> Leyendo manifiesto remoto...")
    rem = remote_manifest()
    log("==> Leyendo manifiesto local...")
    loc = local_manifest()

    total_remoto = len(rem)
    faltan = diff(rem, loc)
    hechos = total_remoto - len(faltan)
    bytes_hechos = sum(rem[r] for r in rem if r not in set(faltan))
    bytes_total = sum(rem.values())

    log("")
    log("=" * 56)
    log(f"  Archivos: {hechos}/{total_remoto}  ({hechos / max(total_remoto,1):.0%})")
    log(f"  Tamano:   {human(bytes_hechos)} / {human(bytes_total)}")
    log(f"  Pendientes: {len(faltan)} archivos, {human(sum(rem[f] for f in faltan))}")
    log("=" * 56)
    log("")

    if args.check:
        return 0
    if not faltan:
        log("==> TODO YA ESTA COPIADO")
        return 0

    # Copia por lotes para no perder todo si se corta la conexion
    lotes = [faltan[i : i + BATCH_SIZE] for i in range(0, len(faltan), BATCH_SIZE)]
    log(f"==> {len(lotes)} lotes de hasta {BATCH_SIZE} archivos")
    log("")

    completados = 0
    for i, lote in enumerate(lotes, 1):
        restante = len(faltan) - completados
        bytes_lote = sum(rem[f] for f in lote)
        log(f"--- Lote {i}/{len(lotes)} | {len(lote)} archivos | {human(bytes_lote)} "
            f"| quedan {restante}")

        ok = False
        servidor_caido = False
        for intento in range(1, REINTENTOS + 1):
            if copiar_lote(lote):
                ok = True
                break
            log(f"    reintento {intento}/{REINTENTOS} en {ESPERA_REINTENTO}s...")
            time.sleep(ESPERA_REINTENTO)
            if not preflight():
                log("")
                log("!! El servidor remoto dejo de responder: se aborta la copia.")
                log("!! Re-ejecuta el script cuando la maquina este encendida y el")
                log("!! disco 'Almacenamiento' montado.")
                servidor_caido = True
                break

        if ok:
            completados += len(lote)
            log(f"    OK  (progreso {completados}/{len(faltan)})")
        else:
            log(f"    FALLO el lote {i}")
            if servidor_caido:
                break
            log("    (se intentara de nuevo en la proxima ejecucion)")

    log("")
    log("=== Resumen ===")
    loc2 = local_manifest()
    faltan2 = diff(rem, loc2)
    log(f"Copiados ahora: {total_remoto - len(faltan2)}/{total_remoto}")
    if faltan2:
        log(f"Siguen faltando: {len(faltan2)} archivos "
            f"({human(sum(rem[f] for f in faltan2))})")
        log("Re-ejecuta el script para continuar.")
        return 1
    log("COPIA_FINIDA_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())