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

**Estructura** (`app/bot/`): `parsing.py` (funciones puras de argumentos), `messages.py` (textos en español, traducción de estados y el único mapper de errores de dominio a mensajes), `commands.py` (una función por comando: `(session, user_id, args) -> texto`, usa los services), `app.py` (handlers async finos, filtro de usuario y ciclo de vida). Cada comando abre su propia sesión y corre en un hilo (`asyncio.to_thread`); el usuario sale de `UserService.get_or_create_user`, igual que `get_current_user`.

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

**Respuestas**: en español, sin emojis o mínimos. Los errores de dominio (límite de activos, proyecto inexistente, falta de próxima acción, hito inexistente) los traduce `messages.error_message`. Las respuestas se truncan a 4096 caracteres.

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
| POST | /export | exportar al vault de Obsidian |

Errores: 404 no existe, 409 límite de activos, 422 validación (p. ej. sin próxima acción).
