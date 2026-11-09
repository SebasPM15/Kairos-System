#!/usr/bin/env bash
# Restaura un respaldo kairos-data-*.tgz (de backup.sh/backup.ps1) en un volumen de Docker.
# Misma semántica que restore.ps1: se niega si algún contenedor (en ejecución o detenido) usa el volumen,
# pide escribir el nombre del volumen para confirmar, conserva la base anterior como kairos.db.pre-restore
# y comprueba integrity_check antes y después de reemplazar. Crea el volumen si no existe.
# Uso: scripts/restore.sh <archivo.tgz> <volumen> [--yes] [--overwrite-real]
#   --yes              omite la confirmación escrita (para scripts)
#   --overwrite-real   necesario para restaurar en kairos-system_kairos-data (el volumen del PC)
set -euo pipefail

REAL="kairos-system_kairos-data"
IMAGE="${KAIROS_BACKUP_IMAGE:-python:3.12.16-slim-trixie}"
YES=0
OVERWRITE_REAL=0
ARGS=()
for arg in "$@"; do
  case $arg in
    --yes|-y) YES=1 ;;
    --overwrite-real) OVERWRITE_REAL=1 ;;
    -h|--help) ARGS=(); break ;;
    -*) echo "Opción desconocida: $arg" >&2; ARGS=(); break ;;
    *) ARGS+=("$arg") ;;
  esac
done
if [ "${#ARGS[@]}" -ne 2 ]; then
  echo "Uso: $0 <archivo.tgz> <volumen> [--yes] [--overwrite-real]" >&2
  exit 2
fi
ARCHIVE=${ARGS[0]}
VOLUME=${ARGS[1]}

export MSYS_NO_PATHCONV=1   # Git Bash: no reescribir las rutas del contenedor (/data, /in)
fail() { echo "Error: $*" >&2; exit 1; }

[ -f "$ARCHIVE" ] || fail "No existe el archivo: $ARCHIVE"
DIR=$(cd -- "$(dirname -- "$ARCHIVE")" && pwd)
FILE=$(basename -- "$ARCHIVE")
printf '%s' "$FILE" | grep -Eq '^kairos-data-[0-9]{8}-[0-9]{4}\.tgz$' ||
  fail "El nombre del archivo debe parecerse a kairos-data-AAAAMMDD-HHmm.tgz."
if [ "$VOLUME" = "$REAL" ] && [ "$OVERWRITE_REAL" -ne 1 ]; then
  fail "Me niego a sobrescribir el volumen real '$REAL'. Restaura en otro volumen o añade --overwrite-real si de verdad es lo que quieres."
fi
docker info >/dev/null 2>&1 || fail "Docker no está en marcha."

# -a incluye contenedores detenidos: un 'compose up' posterior los reutilizaría con el volumen a medio restaurar
USERS=$(docker ps -aq --filter "volume=$VOLUME" 2>/dev/null || true)
[ -z "$USERS" ] || fail "Hay contenedores (en ejecución o detenidos) que usan '$VOLUME'. Elimínalos antes (docker compose down)."

if [ "$YES" -ne 1 ]; then
  printf "Esto reemplaza kairos.db en el volumen '%s'. Escribe el nombre del volumen para continuar: " "$VOLUME"
  IFS= read -r TYPED || TYPED=""
  [ "$TYPED" = "$VOLUME" ] || fail "La confirmación no coincide; no se cambió nada."
fi

if ! docker volume inspect "$VOLUME" >/dev/null 2>&1; then
  docker volume create "$VOLUME" >/dev/null || fail "No se pudo crear el volumen."
fi

MOUNT=$DIR
command -v cygpath >/dev/null 2>&1 && MOUNT=$(cygpath -m "$DIR")   # Docker Desktop en Windows quiere C:/...

docker run --rm -v "$VOLUME:/data" -v "$MOUNT:/in:ro" "$IMAGE" python -c '
import tarfile, os, shutil, sys, sqlite3
tmp = "/data/.restore-tmp"
shutil.rmtree(tmp, ignore_errors=True); os.makedirs(tmp)
with tarfile.open("/in/" + sys.argv[1]) as t:
    m = t.getmember("kairos.db")
    if not m.isfile(): sys.exit("kairos.db is not a regular file")
    t.extract(m, tmp, filter="data")
if sqlite3.connect(tmp + "/kairos.db").execute("pragma integrity_check").fetchone()[0] != "ok": sys.exit("restored database failed integrity_check")
if os.path.exists("/data/kairos.db"): os.replace("/data/kairos.db", "/data/kairos.db.pre-restore")
os.replace(tmp + "/kairos.db", "/data/kairos.db")
shutil.rmtree(tmp, ignore_errors=True)
os.chown("/data", 10001, 0); os.chown("/data/kairos.db", 10001, 0)
if sqlite3.connect("/data/kairos.db").execute("pragma integrity_check").fetchone()[0] != "ok": sys.exit("integrity_check failed after restore")
' "$FILE" || fail "El contenedor de restauración falló; la base anterior (si había) no se reemplazó."

echo "Restaurado $FILE en el volumen '$VOLUME'. Levanta el stack con: docker compose up -d"
