# Arquitectura

## Componentes

```
Telegram ──► bot/ handlers ─┐
                            ├──► services/ ──► SQLAlchemy ──► SQLite (fuente de verdad)
Next.js ──HTTP──► routers/ ─┘        │
                                     └──► exporters/ ──► Vault Obsidian (Markdown)
```

Todo corre en local. Un solo proceso: FastAPI + bot de Telegram (long polling). Routers y handlers son delgados; la lógica (límite de activos, porcentaje, actualización de `last_activity_at`) vive en `services/`. Los schemas (Pydantic) definen el contrato de la API.

## Esquema de BD

Timestamps en UTC. Estados en inglés.

**users**
| campo | tipo | notas |
|---|---|---|
| id | int PK | |
| telegram_id | bigint, unique, nullable | NULL = usuario local por defecto |
| created_at | datetime | |

Sin login ni contraseñas. Hoy opera un solo usuario; el modelo existe para poder aislar datos por usuario más adelante.

**projects**
| campo | tipo | notas |
|---|---|---|
| id | int PK | |
| user_id | int FK → users | NOT NULL, `ON DELETE CASCADE` |
| name | str | |
| slug | str | carpeta en Obsidian; `UNIQUE(user_id, slug)` |
| description | str | |
| status | enum | `idea`, `active`, `paused`, `done` |
| next_action | str, nullable | obligatoria en el service al pasar a `active` |
| last_activity_at | datetime | la actualizan los services |
| created_at | datetime | |

**milestones**: id, project_id → projects, title, done (bool), position (int, orden manual dentro del proyecto), completed_at (nullable; lo pone el service al marcar hecho y lo limpia al reabrir), created_at.

**ideas**: id, user_id → users (NOT NULL, `ON DELETE CASCADE`), project_id → projects (**nullable**, bandeja de entrada; `ON DELETE SET NULL`), content, created_at.

**decisions**: id, project_id → projects, title, rationale (el porqué), created_at.

Relaciones: un usuario tiene muchos proyectos (al borrarlo se borran en cascada, y de ahí hitos y decisiones). Un proyecto tiene muchos hitos, ideas y decisiones. Al borrar un proyecto: `milestones` y `decisions` en cascada; `ideas` con `ON DELETE SET NULL` (vuelven a la bandeja de entrada, conservando su `user_id`). El porcentaje no se guarda: `completed / total` de hitos (0 si no hay hitos).

Reglas:
- Todo se aísla por `user_id`: hitos y decisiones lo heredan vía `projects`; las ideas lo llevan directo (pueden no tener proyecto). Los services reciben `user_id` y filtran por él.
- Una idea asignada a un proyecto debe pertenecer al mismo `user_id` que el proyecto; lo valida el service (la BD solo garantiza que la idea tenga dueño).
- `get_current_user` (`app/deps.py`) es el único punto que decide quién es el usuario: en modo un solo usuario devuelve (creándolo si falta) el de `TELEGRAM_ALLOWED_USER_ID`, o el local por defecto (`telegram_id` NULL) si está vacío. Es lo único a reemplazar por auth real.
- Progreso: `hechos * 100 // total`, se trunca (1 de 3 = 33). Solo vale 100 si todos los hitos están hechos; sin hitos es 0.
- Máximo `MAX_ACTIVE_PROJECTS` en `active`; activar sin `next_action` se rechaza.
- Crear, completar o reabrir un hito, y crear una idea o decisión, actualiza `last_activity_at` del proyecto.

## Ejecución local

- Docker Compose (backend + frontend): SQLite en volumen `/data`; vault de Obsidian como bind mount en `/vault` (`OBSIDIAN_VAULT_PATH=/vault` dentro del contenedor).
- Bot con long polling: sin webhooks ni URL pública.
- Desarrollo diario nativo (`uvicorn --reload`, `pnpm dev`); Docker sirve para ejecutar el sistema completo.
- Obsidian es solo una carpeta de Markdown: el export funciona sin tener Obsidian instalado.

## Bot de Telegram

Long polling, en el mismo proceso que FastAPI. Los handlers son delgados: validan el comando, llaman a `services/` y responden; no tienen lógica de negocio.

**Estructura** (`app/bot/`): `catalog.py` (catálogo de comandos, ver abajo), `parsing.py` (funciones puras de argumentos), `messages.py` (textos en español, traducción de estados y el único mapper de errores de dominio a mensajes), `commands.py` (una función por comando: `(session, user_id, args) -> texto`, usa los services), `app.py` (handlers async finos, filtro de usuario y ciclo de vida). Cada comando abre su propia sesión y corre en un hilo (`asyncio.to_thread`); el usuario sale de `UserService.get_or_create_user`, igual que `get_current_user`.

**Seguridad**: solo atiende al usuario cuyo ID está en `TELEGRAM_ALLOWED_USER_ID`. Los mensajes y callbacks de cualquier otro usuario se ignoran en silencio (sin respuesta). El token nunca se registra: los loggers `httpx`/`httpcore` se suben a WARNING (sus URLs llevan el token) y los fallos de arranque solo registran el nombre de la excepción.

**Ciclo de vida**: el bot arranca y se detiene en el `lifespan` de `create_app`. Sin `TELEGRAM_BOT_TOKEN` o `TELEGRAM_ALLOWED_USER_ID` no arranca y se registra un aviso; si falla al iniciar, se registra y la API sigue. Long polling exige un solo proceso/worker (no usar `--workers`).

**Comandos**: el proyecto se identifica por su slug, antes de los dos puntos. Solo los hitos usan ID numérico.

| comando | efecto |
|---|---|
| `/proyecto <nombre>` | crea el proyecto en estado `idea` |
| `/idea [slug:] <texto>` | el prefijo cuenta como slug solo si es un proyecto del usuario; si no, todo el texto es la idea y va a la bandeja |
| `/hito <slug>: <título>` | crea un hito |
| `/hecho [id]` | marca el hito como hecho; sin argumento, muestra botones (`InlineKeyboard`) con los hitos pendientes |
| `/estado [slug]` | todos los proyectos (estado, progreso, días sin tocar, próxima acción), o uno con sus hitos y su ID |
| `/foco <slug>: <próxima acción>` | activa el proyecto y fija la próxima acción en un solo paso; si se alcanza el límite de activos, lo rechaza con un mensaje claro (409 en la API) |
| `/decision <slug>: <título> \| <porqué>` | registra una decisión con su razón |
| `/pausa <slug>` | pasa el proyecto a `paused` y conserva la próxima acción; libera un cupo de activos |
| `/terminar <slug>` | pasa el proyecto a `done` |
| `/exportar` | exporta al vault de Obsidian y responde con el resumen (proyectos, archivos escritos, sin cambios, carpetas huérfanas) |
| `/ayuda`, `/start` | lista de comandos con su sintaxis |

`/hecho` no cambia el estado: si el hito completado deja el proyecto al 100 %, añade una línea sugiriendo `/terminar` o agregar más hitos.

**Catálogo** (`app/bot/catalog.py`): `COMMAND_CATALOG` es la única fuente de verdad de los comandos (`name`, `syntax`, `description` en español). De él salen `/ayuda` y `/start` (`messages.HELP`), el menú de Telegram y `GET /bot/commands`. Los handlers de `app.py` se registran recorriendo el catálogo (`/hecho` tiene handler propio y `/start` es un alias de `/ayuda` fuera del catálogo), así que un comando nuevo se declara en el catálogo y en `commands.py`; un test falla si falta uno de los dos. Al arrancar, `register_menu` llama a `set_my_commands` con el catálogo; si falla solo se registra el nombre de la excepción y el bot sigue.

**Respuestas**: en español, sin emojis o mínimos. Los errores de dominio (límite de activos, proyecto inexistente, falta de próxima acción, hito inexistente) los traduce `messages.error_message`. Las respuestas se truncan a 4096 caracteres.

## Export al vault de Obsidian

La BD es la fuente de verdad; el vault es una exportación de solo escritura (los cambios manuales se sobrescriben). Se dispara con `POST /export` o `/exportar` en el bot, y solo exporta los proyectos del usuario actual.

**Estructura** (bajo `Kairos/` dentro del vault):

```
Kairos/
  _bandeja.md              ideas sin proyecto
  <slug>/
    README.md              frontmatter YAML + estado, progreso, próxima acción y descripción
    hitos.md               checklist "- [x]" / "- [ ]" ordenado por position
    ideas.md               ideas del proyecto, con fecha
    decisiones.md          título, fecha y porqué de cada decisión
```

Todo en español; cada archivo lleva al inicio el aviso "Generado por Kairos desde la base de datos; los cambios manuales se sobrescriben" (en `README.md`, justo después del frontmatter para que Obsidian lo lea como propiedades). El frontmatter tiene `status` (valor en inglés, estable para consultas), `progress`, `milestones_done`, `milestones_total`, `next_action` y `last_activity` (ISO UTC). No incluye datos que cambien solos con el tiempo (como los días sin tocar), para que un export sin cambios reales no reescriba nada.

**Estructura del código** (`app/exporters/`): `markdown.py` (funciones puras de renderizado), `vault.py` (interfaz `VaultWriter` e implementación `FileSystemVaultWriter`) y `project_exporter.py` (`ProjectExporter`, que lee `ProjectRead` y las listas de hitos, ideas y decisiones desde los services, nunca por SQL; `build_exporter` es el único cableado, compartido por la API y el bot).

**Reglas**:
- **Rutas seguras**: cada ruta se resuelve y debe quedar dentro de `Kairos/`, que a su vez debe quedar dentro del vault; un slug con `..`, separadores o ruta absoluta, o un symlink que salga, lanza `UnsafeVaultPath` (409). Nunca se escribe fuera.
- **Nunca borrar**: una carpeta `Kairos/<carpeta>/` sin proyecto se informa como huérfana y no se toca (tampoco se borran archivos sueltos).
- **Idempotente y mínimo**: escritura atómica (archivo temporal en la misma carpeta + `os.replace`, con permisos 0644) y no se reescribe un archivo cuyo contenido no cambió.
- **Frontmatter seguro**: los strings se serializan con `json.dumps` (YAML válido), así `next_action` con dos puntos, comillas o saltos de línea no rompe el YAML.
- **Vault no configurado**: con `OBSIDIAN_VAULT_PATH` vacío o una raíz que no existe se lanza `VaultNotConfigured` (409; mensaje propio en el bot). La raíz del vault nunca se crea; `Kairos/` sí.
- Un vault pertenece a un solo usuario: las carpetas de otros usuarios cuentan como huérfanas y dos usuarios con el mismo slug se pisarían. Hoy opera un solo usuario.

**Respuesta** de `POST /export`: `{projects_exported, files_written, files_unchanged, orphans}`.

## Endpoints

| método | ruta | descripción |
|---|---|---|
| GET | /health | estado del servicio |
| GET, POST | /projects | listar (incluye porcentaje, días sin tocar) / crear |
| GET, PATCH, DELETE | /projects/{id} | detalle / actualizar (estado, próxima acción) / borrar |
| GET, POST | /projects/{id}/milestones | listar / crear |
| PATCH, DELETE | /milestones/{id} | editar o marcar hecho / borrar |
| GET, POST | /projects/{id}/ideas | listar / crear |
| GET, POST | /ideas | bandeja de entrada (sin proyecto) |
| PATCH, DELETE | /ideas/{id} | asignar a proyecto / borrar |
| GET, POST | /projects/{id}/decisions | listar / crear |
| GET | /bot/commands | catálogo de comandos del bot (`name`, `syntax`, `description`); estático, no llama a Telegram |
| POST | /export | exportar al vault de Obsidian; devuelve el resumen (proyectos, archivos escritos, sin cambios, carpetas huérfanas) |

Errores: 404 no existe, 409 límite de activos o vault no configurado / ruta fuera del vault, 422 validación (p. ej. sin próxima acción).
