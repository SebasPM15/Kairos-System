#!/usr/bin/env bash
# Backs up the Kairos Docker volume to a dated .tgz and keeps the newest ones (same behavior as backup.ps1).
# The database is copied with SQLite's backup API from a throwaway container that mounts the volume
# read-only: consistent while the backend runs, and unable to modify the real data. The archive is written
# under a .part name and renamed when complete, so a failure never leaves a partial .tgz.
# Usage: scripts/backup.sh [-v volume] [-d destination] [-k keep]
set -euo pipefail

VOLUME="kairos-system_kairos-data"
DEST="${HOME}/Backups/Kairos"
KEEP=14
IMAGE="python:3.12.16-slim-trixie"
while getopts "v:d:k:" opt; do
  case $opt in
    v) VOLUME=$OPTARG ;; d) DEST=$OPTARG ;; k) KEEP=$OPTARG ;;
    *) echo "usage: $0 [-v volume] [-d destination] [-k keep]" >&2; exit 2 ;;
  esac
done
case $KEEP in ''|*[!0-9]*|0) echo "keep must be a positive number" >&2; exit 2 ;; esac

export MSYS_NO_PATHCONV=1   # Git Bash: do not rewrite the container paths
PART=""
cleanup() { [ -n "$PART" ] && rm -f -- "$PART"; return 0; }
trap cleanup EXIT

docker volume inspect "$VOLUME" >/dev/null 2>&1 || { echo "Volume '$VOLUME' does not exist (is Docker running?)." >&2; exit 1; }
mkdir -p -- "$DEST"
DEST=$(cd -- "$DEST" && pwd)
MOUNT=$DEST
command -v cygpath >/dev/null 2>&1 && MOUNT=$(cygpath -m "$DEST")   # Docker Desktop wants C:/... on Windows
NAME="kairos-data-$(date +%Y%m%d-%H%M).tgz"
[ -e "$DEST/$NAME" ] && { echo "$NAME already exists; wait a minute and retry." >&2; exit 1; }
PART="$DEST/$NAME.part"

docker run --rm -v "$VOLUME:/data:ro" -v "$MOUNT:/out" "$IMAGE" python -c '
import sqlite3, tarfile, os, sys
src = sqlite3.connect("file:/data/kairos.db?mode=ro", uri=True)
os.makedirs("/tmp/snap", exist_ok=True)
dst = sqlite3.connect("/tmp/snap/kairos.db")
src.backup(dst); dst.close(); src.close()
chk = sqlite3.connect("/tmp/snap/kairos.db")
if chk.execute("pragma integrity_check").fetchone()[0] != "ok": sys.exit("integrity_check failed")
with tarfile.open("/out/" + sys.argv[1], "w:gz") as t: t.add("/tmp/snap/kairos.db", arcname="kairos.db")
' "$NAME.part" || { echo "The backup container failed." >&2; exit 1; }

[ -s "$PART" ] || { echo "No archive was produced." >&2; exit 1; }
mv -- "$PART" "$DEST/$NAME"
PART=""
echo "Backup written: $DEST/$NAME ($(wc -c < "$DEST/$NAME") bytes)"

# Retention: newest $KEEP files with the exact name pattern, in this folder only
ls -1 -- "$DEST" | grep -E '^kairos-data-[0-9]{8}-[0-9]{4}\.tgz$' | sort -r | tail -n +"$((KEEP + 1))" |
  while IFS= read -r old; do rm -f -- "$DEST/$old"; echo "Removed old backup: $old"; done
