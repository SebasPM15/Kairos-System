# Estado

_Última actualización: 2026-10-28_

## Hecho
- Esqueleto del backend (carpetas, `__init__.py`, `pyproject.toml` mínimo) y `.env.example`.
- Frontend de V0 copiado a `frontend/`. Instala y compila (`pnpm build` OK, `tsc --noEmit` OK). Usa datos mock.
- Hito 1: `config.py` (Settings), `db.py` (engine, SessionLocal, Base, `get_db`), `create_app()` con CORS, `GET /health` y `tests/test_health.py` (pasa). `uvicorn app.main:app` arranca y responde.
- Hito 2: Dockerfiles (backend `python:3.12-slim` no root; frontend multi-stage con `output: 'standalone'`), `docker-compose.yml` (volumen `kairos-data` en `/data`, vault por `VAULT_HOST_PATH` en `/vault`, healthcheck). Verificado: build OK, `/health` y frontend responden, el volumen persiste tras `down`/`up`.
- Hito 3: modelos `Project`/`Milestone`/`Idea`/`Decision` (uno por archivo en `app/models/`), `PRAGMA foreign_keys=ON` en cada conexión SQLite, migración inicial de Alembic (`env.py` lee `DATABASE_URL` de Settings, `render_as_batch`), `entrypoint.sh` que aplica `alembic upgrade head` antes de uvicorn, `backend/constraints.txt` con versiones fijas usado por el Dockerfile. 7 tests pasan. Verificado en Docker: tablas creadas en `/data/kairos.db` y datos persisten tras `down`/`up`.
- Preparación multiusuario (sin construirlo): modelo `User`, `projects.user_id` NOT NULL con cascada, slug `UNIQUE(user_id, slug)`, `app/deps.py::get_current_user`, `telegram_allowed_user_id` en Settings. Migración `a3f1c9d27b40` (batch) crea el usuario por defecto solo si ya hay proyectos y se los asigna. 14 tests pasan. Verificado en Docker sobre el volumen existente con filas sembradas: la migración aplica y hitos/decisiones/ideas se conservan.
- Hito 4: CRUD de proyectos. Capas `schemas/project.py`, `repositories/project_repository.py`, `services/project_service.py` (+ `errors.py`), `routers/projects.py` (404/409/422). 39 tests pasan. Verificado en Docker con curl a `/projects` (crear, activar sin acción -> 422, activar, listar, borrar).
- Hito 5: hitos + porcentaje. `schemas/milestone.py`, `repositories/milestone_repository.py` (filtra por `user_id` vía el proyecto), `services/milestone_service.py` (crear al final, listar, editar, borrar, reordenar sin huecos; `MilestoneNotFound`), `routers/milestones.py`. `ProjectRead` expone `progress`, `milestones_done` y `milestones_total`, calculados por `ProjectService` (no se guardan). 64 tests pasan. Verificado en Docker con curl (crear, completar, reordenar, borrar, 404) y datos de prueba eliminados.
- Ideas por usuario: `ideas.user_id` NOT NULL con cascada; migración `b7d2e41a9c15` asigna cada idea al dueño de su proyecto y las huérfanas al usuario configurado (o el más antiguo, o crea uno). 41 tests pasan. Verificado en Docker sobre el volumen existente con ideas sembradas (en proyecto y huérfana): se conservan con su dueño.
- Hito 6: ideas y decisiones. `schemas/idea.py`, `schemas/decision.py`, repositories filtrados por `user_id`, `IdeaService` y `DecisionService` (`IdeaNotFound`, `DecisionNotFound`), routers `ideas.py` y `decisions.py`. 103 tests pasan. Verificado en Docker con curl (bandeja, asignar/desasignar, 404 a proyecto ajeno, decisión sin rationale -> 422, borrar proyecto deja las ideas en la bandeja) y datos de prueba eliminados.
- Hito 7: tests y deuda. `pytest-cov` como dependencia de desarrollo (`constraints.txt` regenerado). Tests transversales: aislamiento entre usuarios en todos los routers, flujo completo (progress, `last_activity_at`, límite de activos), `alembic upgrade head` + `alembic check` sobre BD vacía, y cada error de dominio -> 404/409/422 (con un test que falla si se añade un error sin mapear). `ProjectService` ahora devuelve `ProjectRead`. 131 tests pasan; cobertura 99% (`pytest --cov=app --cov-report=term-missing`): lo único sin cubrir es `get_db`, que los tests sustituyen por override. Verificado en Docker (up, `/health`, `/projects`, down) y datos de prueba eliminados.
- Hito 8: bot de Telegram. `UserService.get_or_create_user` (lo reutiliza `get_current_user`), `app/bot/` con `parsing.py`, `messages.py`, `commands.py` y `app.py` (handlers finos, filtro por `TELEGRAM_ALLOWED_USER_ID` también en callbacks, `/hecho` sin argumento con InlineKeyboard) y arranque/parada del long polling en el lifespan de `create_app`. 214 tests pasan, todos sin red. **No probado contra Telegram real** (pendiente de hacer a mano).
- Documentos base: CLAUDE.md, ROADMAP, architecture.

- `.claude/settings.json` sin coautoría de Claude; commits locales reescritos para quitarla (aún no estaban en el remoto).

## Sigue
- Probar el bot contra Telegram real (token y `TELEGRAM_ALLOWED_USER_ID` en `.env`).
- Hito 9 de v0.1: export a Markdown hacia el vault de Obsidian.

## Bloqueos
- Ninguno.

## Deuda técnica
- Ninguna conocida.

## Decisiones recientes
- `pyproject` limita el descubrimiento de paquetes a `app*` (si no, `pip install -e` falla por el layout plano).
- Python 3.13 local, `requires-python >=3.12`; sin versiones fijas en `pyproject` por ahora.
- pnpm vía corepack (12.3.4, versión válida).
- Estados en inglés (`idea|active|paused|done`); traducción en UI y bot.
- `ideas.project_id` nullable (bandeja de entrada); `projects.slug` para la carpeta de Obsidian.
- Hitos: `completed_at` lo gestiona el service; `position` es el orden manual.
- Borrar proyecto: hitos y decisiones en cascada; ideas `SET NULL`. Hitos/ideas/decisiones actualizan `last_activity_at`.
- Todo local: Docker Compose (SQLite en `/data`, vault en `/vault`), bot por long polling; desarrollo nativo. Archivos Docker listos (hito 2). Compose exige un `.env` (copiar de `.env.example`).

- `UTCDateTime` (TypeDecorator) devuelve datetimes aware en UTC aunque SQLite guarde naive; rechaza datetimes naive al escribir.
- La migración usa `sa.DateTime(timezone=True)` (no importa tipos de la app). Regenerar constraints: `pip freeze --exclude-editable` desde el venv, sin `kairos-backend`.
- Autogenerate: tras cambiar modelos, revisar la migración a mano.

- Diseño del bot (ver `architecture.md`): solo responde a `TELEGRAM_ALLOWED_USER_ID` (el resto se ignora en silencio); proyecto por slug antes de `:`, solo los hitos usan ID; `/foco` activa y fija la próxima acción en un paso y respeta el límite; los handlers traducen errores de dominio a mensajes en español.

- Migraciones SQLite: `env.py` apaga `PRAGMA foreign_keys` durante la migración; si no, el batch (DROP de `projects`) borraría en cascada hitos y decisiones. La migración usa `naming_convention` para poder soltar el UNIQUE sin nombre de la inicial.
- Si había proyectos antes de configurar `TELEGRAM_ALLOWED_USER_ID`, su usuario por defecto queda con `telegram_id` NULL y `get_current_user` creará otro al configurarlo; asignar el ID a mano en `users` en ese caso.
- El service de ideas (hito 6) debe validar que una idea asignada a un proyecto tenga el mismo `user_id` que el proyecto.
- Los services nuevos deben recibir `user_id` (hito 4 en adelante).

- Proyectos: el slug se genera al crear (sin acentos, sufijo `-2`, `-3` por usuario) y no cambia al renombrar. Activar exige `next_action` no vacía y cupo; un proyecto ya activo no cuenta contra sí mismo. En PATCH, `null` solo limpia `next_action`; en los demás campos significa "sin cambio". No se puede limpiar la próxima acción de un proyecto activo.
- Progreso: `completed * 100 // total` (trunca, así 100 solo si todos están hechos; 0 sin hitos). `ProjectService` devuelve `ProjectRead` (construido solo en `_to_reads`, una consulta agrupada en `list`); `days_since_activity` se calcula en el schema. API, bot y export deben consumir `ProjectRead`, no el ORM. Los tests de services que mutan `last_activity_at` obtienen la entidad con `session.get(Project, id)`.
- Hitos: `position` va de 0 a n-1 sin huecos; mover o borrar renumera. Una posición mayor que el final se ajusta al final. Marcar hecho/reabrir solo actúa si el estado cambia; en PATCH, `null` significa "sin cambio". Crear, completar y reabrir actualizan `last_activity_at`; editar título/posición y borrar no.
- Los services reciben `session`, `user_id` y `settings` por constructor; el router los arma con `Depends`.
- Bot: las funciones de `commands.py` toman `get_settings()` internamente (los tests lo parchean en `app.bot.commands`). El decorador `_reply` mapea errores de dominio/validación y trunca a 4096. Un slug inexistente en `/hito`, `/foco`, `/decision` y `/estado` responde "no existe ese proyecto"; solo `/idea` degrada a bandeja. `/hecho` es idempotente (re-marcar un hito hecho no falla). Si el bot no puede iniciar (token inválido, sin red) se registra solo el nombre de la excepción y la API sigue.

- Ideas: en PATCH, `project_id` ausente = sin cambio y `null` = vuelve a la bandeja (`model_fields_set`); `content` no admite `null`. Crear en un proyecto o asignar a uno distinto actualiza `last_activity_at`; bandeja, desasignar, editar contenido y borrar no. `POST /projects/{id}/ideas` usa el proyecto de la ruta e ignora `project_id` del cuerpo.
- Decisiones: sin edición; crear actualiza `last_activity_at`, borrar no. Título y porqué se recortan y no pueden quedar vacíos (422).

## Adaptaciones pendientes del frontend
1. `lib/api.ts`: cambiar mocks por `fetch` a `NEXT_PUBLIC_API_URL`; habilitar CORS en FastAPI.
2. `lib/types.ts`: IDs numéricos, estados en inglés con etiquetas en español, `ideas`/`decisions` como listas; porcentaje y días sin tocar calculados por el backend.
3. Límite de activos: hoy 3 fijo con `window.confirm`; debe ser rechazo del servidor (409) según config.
4. Tabs Ideas/Decisiones vacías: faltan listas y alta.
5. Faltan crear proyecto/hito, estados de carga y error.
6. Quitar `@vercel/analytics`, `generator: 'v0.app'`, `ignoreBuildErrors`; marca “Enfoque” → “Kairos”; `name` del package.
7. Dividir `project-dashboard.tsx` (un solo componente denso) en componentes pequeños.
