# Despliegue en el homelab (nova-brain)

> Estado: **preparado, pendiente de ejecutar en el servidor.** Todo lo de abajo se probó en un árbol temporal de dos
> directorios que imita el servidor (ver «Qué se probó»); nada se ha ejecutado aún en el servidor real.

Kairos corre en el servidor como el proyecto de Compose `nova-brain` (Debian 13, Docker Compose). El
`docker-compose.yml` del repo es la **única** fuente: no hay copias en `/srv/stacks`.

## Rutas en el servidor

| Qué | Ruta |
|---|---|
| Código (clon del repo) | `/srv/projects/nova-brain/app` |
| Vault de Obsidian (bind mount en `/vault`) | `/srv/projects/nova-brain/vault` |
| `.env` real (`chmod 600`, fuera de Git) | `/srv/stacks/nova-brain/.env` |
| Respaldos previos a cada actualización | `/srv/stacks/nova-brain/backups` |
| Volumen de datos (SQLite) | `nova-brain_kairos-data` |

## Mecanismo elegido: `.env` enlazado (opción 3)

Se evaluaron tres opciones para que el compose del repo lea el `.env` de `/srv/stacks`:

1. `--project-directory` + `--env-file`: **no sirve tal cual.** `--env-file` solo alimenta la interpolación (`${VAR}`);
   el `env_file: .env` del servicio backend se resuelve contra el directorio del proyecto, así que falla con
   «env file …/app/.env not found» y el contenedor no recibiría `TELEGRAM_BOT_TOKEN`. Habría que cambiar el compose.
2. Un compose mínimo en `/srv/stacks/nova-brain` con `include` (`project_directory` + `env_file`): **mismo fallo**
   por la misma razón.
3. **Enlace simbólico `app/.env` -> `/srv/stacks/nova-brain/.env`** (`.env` ya está en `.gitignore`): no cambia el
   compose, el flujo del PC no se altera y el nombre del proyecto sale de `COMPOSE_PROJECT_NAME` dentro del mismo `.env`.
   Todos los comandos se ejecutan desde `app/`, igual que en el PC.

El `.env` real nunca entra en Git: solo el enlace vive junto al código y Git lo ignora.

## Primera instalación (en el servidor, como `mateo`)

```bash
mkdir -p /srv/projects/nova-brain/vault /srv/stacks/nova-brain
git clone <URL-del-repo> /srv/projects/nova-brain/app
cd /srv/projects/nova-brain/app

install -m 600 .env.example /srv/stacks/nova-brain/.env
nano /srv/stacks/nova-brain/.env          # ver «Valores del .env en el servidor»
ln -s /srv/stacks/nova-brain/.env .env

docker compose config --quiet             # valida; no imprime el .env
docker compose up -d --build
docker compose ps                         # ambos Up y healthy
curl -s http://127.0.0.1:8000/health      # {"status":"ok"}
```

### Valores del `.env` en el servidor

```dotenv
COMPOSE_PROJECT_NAME=nova-brain
NEXT_PUBLIC_API_URL=http://localhost:8000
CORS_ORIGINS=["http://localhost:3000"]
TIMEZONE=America/Guayaquil
VAULT_HOST_PATH=/srv/projects/nova-brain/vault
NODE_BUILD_MEMORY_MB=384                  # opcional: limita la RAM de Node al compilar el frontend
TELEGRAM_BOT_TOKEN=<el token real>        # solo en este archivo
TELEGRAM_ALLOWED_USER_ID=<tu ID numérico>
```

`NEXT_PUBLIC_API_URL` se incrusta al compilar: si la cambias, `docker compose up -d --build`.

## Actualizar

```bash
bash /srv/projects/nova-brain/app/deploy/homelab/update.sh
```

Aborta si el árbol git está sucio o falta el `.env`. Hace un respaldo (`scripts/backup.sh` sobre
`nova-brain_kairos-data`, a `/srv/stacks/nova-brain/backups`) y aborta si falla; etiqueta las imágenes actuales
como `:rollback` (si están healthy); `git pull --ff-only`; `docker compose up -d --build`; espera a `healthy`
(180 s, `HEALTH_TIMEOUT`). Si falla, muestra el estado y las últimas líneas de log (con los tokens enmascarados) y
la receta para volver atrás. Nunca hace commits ni push. Las rutas se pueden sobrescribir por variable
(`APP_DIR`, `ENV_FILE`, `VOLUME`, `BACKUP_DIR`, `BACKUP_KEEP`, `HEALTH_TIMEOUT`).

### Volver atrás

```bash
cd /srv/projects/nova-brain/app
git reset --hard <hash previo>            # lo imprime update.sh
docker compose up -d --build              # o, sin reconstruir: docker tag <imagen>:rollback <imagen>:latest && docker compose up -d --no-build
```

Si la actualización trajo migraciones de Alembic, el esquema de la base **ya cambió** y el código viejo puede no
entenderlo: restaura también el respaldo previo (`update.sh` imprime el nombre exacto):

```bash
docker compose down
bash scripts/restore.sh /srv/stacks/nova-brain/backups/kairos-data-AAAAMMDD-HHmm.tgz nova-brain_kairos-data
docker compose up -d --build
```

`restore.sh` se niega si algún contenedor (incluso detenido) usa el volumen, pide escribir su nombre y conserva la
base anterior como `kairos.db.pre-restore` dentro del volumen.

## Acceso desde el PC (túnel SSH)

La API y el dashboard solo escuchan en `127.0.0.1` del servidor. En `~/.ssh/config` del PC:

```sshconfig
Host nova-brain
    HostName 192.168.100.50
    User mateo
    IdentityFile ~/.ssh/id_ed25519_homelab
    LocalForward 3000 127.0.0.1:3000
    LocalForward 8000 127.0.0.1:8000
```

`ssh -N nova-brain` y abre `http://localhost:3000`. No se abre ningún puerto del router.

## Avisos importantes

- **La API no tiene autenticación.** Lo único que la protege es que solo escucha en loopback y se accede por túnel
  SSH. No la publiques en la LAN ni en Internet.
- **El bot no puede correr en dos sitios a la vez.** Con el mismo token, dos procesos compiten por `getUpdates` y
  Telegram responde `409 Conflict`. Antes de arrancar el del servidor, para el del PC (`docker compose down`,
  `uvicorn`); y al volver al desarrollo nativo, para el del servidor o usa otro bot.
- El `mem_limit` (con `memswap_limit` igual; backend 256 MB, frontend 192 MB) es holgado respecto a lo medido (~86 y ~48 MiB de pico).

## Respaldos y Syncthing

- `backup.d/NN-nova-brain.sh.template`: plantilla del gancho para `/srv/scripts/backup.d/`. El contrato real de ese
  directorio no está inventado aquí: tiene `TODO` donde hay que ajustarlo a lo que defina el servidor.
- `syncthing/stignore.txt`: patrones para el `.stignore` del vault. El export escribe `.kairos-XXXX.tmp` en la
  carpeta destino y lo renombra al terminar (no usa archivos de bloqueo).
- **Syncthing replica, no respalda:** un borrado o una corrupción se replican. Lo que respalda es el backup cifrado
  del servidor.
