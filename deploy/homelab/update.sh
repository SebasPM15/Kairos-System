#!/usr/bin/env bash
# Actualiza Kairos (nova-brain) en el servidor: respaldo previo, git pull --ff-only, rebuild y espera a healthy.
# Se ejecuta en el servidor. No hace commits ni push. Los valores por defecto son los del layout del servidor;
# cualquiera se puede sobrescribir por variable de entorno (así se prueba en un árbol temporal).
set -euo pipefail

APP_DIR="${APP_DIR:-/srv/projects/nova-brain/app}"
ENV_FILE="${ENV_FILE:-/srv/stacks/nova-brain/.env}"
VOLUME="${VOLUME:-nova-brain_kairos-data}"
BACKUP_DIR="${BACKUP_DIR:-/srv/stacks/nova-brain/backups}"
BACKUP_KEEP="${BACKUP_KEEP:-14}"
HEALTH_TIMEOUT="${HEALTH_TIMEOUT:-180}"

fail() { echo "Error: $*" >&2; exit 1; }

# Everything lives in a function: bash reads a script lazily, and git pull may rewrite this very file
main() {
  cd -- "$APP_DIR" || fail "No existe $APP_DIR."
  [ -f "$ENV_FILE" ] || fail "Falta el .env en $ENV_FILE."
  [ -f "$APP_DIR/.env" ] || fail "Falta $APP_DIR/.env (enlace al .env del stack): ln -s $ENV_FILE $APP_DIR/.env"
  [ -z "$(git status --porcelain)" ] || fail "El árbol git tiene cambios sin commitear; límpialo antes de actualizar."

  local prev images project_images img backup_file new migrations
  prev=$(git rev-parse HEAD)
  echo "Versión actual: $(git log -1 --format='%h %s' HEAD)"

  echo "Respaldo previo del volumen $VOLUME..."
  mkdir -p -- "$BACKUP_DIR"
  bash "$APP_DIR/scripts/backup.sh" "$VOLUME" --dest "$BACKUP_DIR" --keep "$BACKUP_KEEP" ||
    fail "El respaldo falló; no se actualiza."
  backup_file=$(ls -1 -- "$BACKUP_DIR" | grep -E '^kairos-data-[0-9]{8}-[0-9]{4}\.tgz$' | sort | tail -n 1)
  [ -n "$backup_file" ] || fail "No encuentro el respaldo recién creado en $BACKUP_DIR."

  # Tag the running images :rollback, but only if they are healthy (otherwise a broken build would overwrite it)
  project_images=$(docker compose config --images)
  if all_healthy; then
    for img in $project_images; do
      docker image inspect "$img" >/dev/null 2>&1 && docker tag "$img" "${img%%:*}:rollback"
    done
  else
    echo "Aviso: los servicios actuales no están healthy; no se etiquetan las imágenes :rollback."
  fi

  git pull --ff-only || fail "git pull --ff-only falló (¿historia divergente?). No se tocó nada más."
  new=$(git rev-parse HEAD)
  migrations=$(git diff --name-only "$prev" "$new" -- backend/alembic/versions)

  if [ "$prev" = "$new" ]; then
    echo "Ya estaba en la última versión; se reconstruye por si cambió el .env."
  fi
  if docker compose up -d --build && wait_healthy; then
    echo "Listo: $(git log -1 --format='%h %s' HEAD)"
    [ -z "$migrations" ] || echo "Hubo migraciones Alembic; el respaldo previo es $BACKUP_DIR/$backup_file"
    return 0
  fi

  echo >&2
  echo "La actualización no llegó a healthy en ${HEALTH_TIMEOUT}s. Últimas líneas de log:" >&2
  docker compose ps >&2 || true
  docker compose logs --no-color --tail 40 2>&1 | mask_secrets >&2 || true
  print_rollback "$prev" "$backup_file" "$migrations" "$project_images" >&2
  return 1
}

# Hides anything that looks like a Telegram bot token, just in case a library echoes it
mask_secrets() { sed -E 's/[0-9]{6,}:[A-Za-z0-9_-]{30,}/***/g'; }

container_health() {
  docker inspect --format '{{.State.Status}}/{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$1"
}

all_healthy() {
  local ids id
  ids=$(docker compose ps -q)
  [ -n "$ids" ] || return 1
  for id in $ids; do [ "$(container_health "$id")" = "running/healthy" ] || return 1; done
}

wait_healthy() {
  local waited=0
  echo "Esperando a que los servicios estén healthy (máx. ${HEALTH_TIMEOUT}s)..."
  while [ "$waited" -lt "$HEALTH_TIMEOUT" ]; do
    all_healthy && return 0
    sleep 3; waited=$((waited + 3))
  done
  return 1
}

print_rollback() {
  local prev=$1 backup_file=$2 migrations=$3 images=$4 img
  echo "Cómo volver atrás (en $APP_DIR):"
  echo "  git reset --hard $prev"
  echo "  docker compose up -d --build"
  echo "  (más rápido, sin reconstruir: retagea las imágenes y usa --no-build)"
  for img in $images; do
    docker image inspect "${img%%:*}:rollback" >/dev/null 2>&1 &&
      echo "    docker tag ${img%%:*}:rollback ${img%%:*}:latest"
  done
  if [ -n "$migrations" ]; then
    echo "Hubo migraciones Alembic: el esquema de la base YA cambió. Tras el reset hay que restaurar el respaldo previo:"
    echo "  docker compose down"
    echo "  bash scripts/restore.sh $BACKUP_DIR/$backup_file $VOLUME"
    echo "  docker compose up -d --build"
  fi
}

main "$@"
exit $?
