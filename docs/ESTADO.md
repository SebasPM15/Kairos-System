# Estado

_Última actualización: 2026-10-30_

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
- Pulido del bot: `/start` y `/ayuda` (lista de comandos), `/pausa <slug>` y `/terminar <slug>` (vía `ProjectService.update`), y aviso en `/hecho` al llegar al 100 % (solo sugerencia, no cambia el estado). 231 tests pasan, sin red. Sigue sin probarse contra Telegram real.
- Hito 9: export al vault de Obsidian. `app/exporters/` (`markdown.py` puro, `vault.py` con `VaultWriter`/`FileSystemVaultWriter`, `project_exporter.py`), `POST /export` y `/exportar` en el bot; `VaultNotConfigured` y `UnsafeVaultPath` mapeados a 409 y a mensajes del bot. 316 tests pasan (1 se omite si no hay symlinks de archivo; en Windows los de carpeta usan junctions). Verificado en Docker con el bind mount `vault-dev`: el usuario no root (uid 10001) escribe, el segundo export no escribe nada, las carpetas huérfanas se informan y no se tocan; datos de prueba y `vault-dev/Kairos` eliminados.
- Catálogo único de comandos del bot: `app/bot/catalog.py` alimenta `/ayuda` y `/start`, el menú de Telegram (`set_my_commands` al arrancar; si falla solo se registra el nombre de la excepción) y `GET /bot/commands`. 323 tests pasan, sin red (nuevos en `test_bot_catalog.py`); ningún test existente cambió salvo que el bot falso de `test_bot_lifecycle.py` ahora define `set_my_commands`. Menú **no probado contra Telegram real**.
- Hito 10, sesión 1 (dashboard conectado, limpieza): `frontend/lib/types.ts` (tipos en inglés iguales a la API), `lib/labels.ts` (único mapa de estados al español y `errorMessage`), `lib/api.ts` (fetch nativo, `NEXT_PUBLIC_API_URL`, funciones por recurso y `ApiError` con `status`/`detail`; 0 = sin conexión, 409 = límite de activos, 422 = validación). El dashboard lista proyectos reales con skeleton, error con "Reintentar" y estado vacío; los hitos se cargan al abrir el detalle; el progreso y los días sin tocar vienen del backend. Sin `window.confirm`: el 409/422 se muestra como aviso con el mensaje en español. Quitados `@vercel/analytics`, `ignoreBuildErrors`, `generator: v0.app`, placeholders e iconos de V0; marca Kairos. `pnpm lint` (ESLint + `eslint-config-next`), `pnpm typecheck` y `pnpm build` en verde. CORS ya existía (`cors_origins`); añadido `tests/test_cors.py` y `CORS_ORIGINS` en `.env.example`. 326 tests pasan, sin red. Verificado a mano con backend temporal (`MAX_ACTIVE_PROJECTS=1`): 422 al activar sin acción, 409 al superar el límite y preflight CORS desde `localhost:3000`; el HTML servido por Next incluye el skeleton. **Los estados de error y el aviso del 409 no se vieron en un navegador** (solo la API y el SSR).
- Documentos base: CLAUDE.md, ROADMAP, architecture.

- `.claude/settings.json` sin coautoría de Claude; commits locales reescritos para quitarla (aún no estaban en el remoto).

## Sigue
- Probar el bot contra Telegram real (token y `TELEGRAM_ALLOWED_USER_ID` en `.env`).
- Hito 10 de v0.1: dashboard conectado a la API (ver "Adaptaciones pendientes del frontend"), en tres sesiones:
  1. ~~Cliente API y limpieza~~ (hecho).
  2. Proyectos (crear proyecto e hitos, manejo fino del 409/422, dividir `project-dashboard.tsx`; adaptaciones 5 y 7).
  3. Bandeja, export y pestaña "Bot" (ideas, decisiones, `POST /export` y los comandos desde `GET /bot/commands`; adaptación 4).
- Probar `/exportar` y abrir el vault real en Obsidian (hasta ahora solo probado con `vault-dev`).

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

- Export: el frontmatter guarda `status` en inglés (valor estable de BD) y el cuerpo lo muestra en español. `last_activity` en ISO UTC con segundos. Los hitos se ordenan por `position`; ideas y decisiones por ID (cronológico). Los títulos de hitos/proyectos se colapsan a una línea; las ideas multilínea se indentan bajo su viñeta. Los tests de symlink crean junctions en Windows si no hay privilegio de symlink.
- En la BD de Docker quedaron un proyecto "Kairos" (id 1) y una idea suelta de sesiones anteriores; no se tocaron.

## Hito 10 · Sesión 2: plan de iteraciones
Cada iteración = un commit pequeño y convencional, sin coautoría de Claude, con backend y frontend arrancables. Al terminar cada una: verificación mínima (lint/typecheck, y tests si se tocó backend) y reporte de 2-3 líneas. Si una iteración crece, se divide en dos commits. Fuera de alcance (sesión 3): bandeja de ideas global, botón de export con su resumen, pestaña Bot.

1. [x] Backend: `GET /config` -> `{"max_active_projects": N}` desde settings. Router delgado, test incluido, sin tocar la lógica del límite. (`e77da69` feat(api): GET /config exposes the active projects limit)
2. [x] `lib/api.ts` y errores: añadir `getConfig()`. Ajustar `ApiError` para distinguir por la FORMA del `detail`: string = error de negocio, lista = validación Pydantic (mapeable a errores por campo). `errorMessage()` debe depender de status + endpoint, con el texto del `detail` solo como respaldo. (`158a24b` feat(frontend): typed API errors by detail shape and getConfig)
3. [x] Extraer de `project-dashboard.tsx` la lista y la tarjeta de proyecto a `components/projects/`. Comportamiento idéntico, sin librería de estado nueva. (`ca4e3e3` StatusBadge, `dd5eb89` ProjectCard, `2315b67` ProjectList; todos `refactor(frontend)`)
4. [ ] Tarjeta: estado con `lib/labels.ts`, porcentaje tal cual del backend (no recalcular), próxima acción visible, umbral de "abandonado" como constante nombrada en un solo lugar. Contador "N / máx" activos usando `/config`.
5. [ ] Sustituir skeleton y aviso con CSS propio por los componentes shadcn skeleton y alert si no añaden dependencias (si hace falta alguna, justificarla antes de instalar). Comentar el motivo de `unrs-resolver: false` donde esté.
6. [ ] Drawer del proyecto con secciones de hitos, ideas y decisiones: lectura, y marcar hito como hecho (el porcentaje debe refrescarse desde el backend).
7. [ ] Formularios de alta: crear proyecto y crear hito. Validación mínima en cliente; la verdad la tiene el backend.
8. [ ] Registrar decisión (el endpoint `POST /projects/{id}/decisions` existe) y cambios de estado desde la UI (activar, pausar, terminar).
9. [ ] Errores en su sitio: 409 junto al control que lo causó, con el máximo real de `/config`; 422 de negocio junto al campo de próxima acción; 422 de validación mapeado por campo. El aviso global queda solo para errores sin contexto (red, 5xx).
10. [ ] Verificación y cierre: `pnpm lint`, `typecheck` y `build` en verde; suite completa del backend (323 + nuevos). Prueba manual del flujo: crear proyecto, añadir hitos, activar con y sin próxima acción (422), superar el límite (409), marcar hito hecho y ver cambiar el porcentaje, y backend apagado. Si se puede abrir navegador, hacerlo y anotar qué se probó en navegador y qué solo a nivel API. Después, actualizar este archivo (y ROADMAP si cambia algo) en un commit propio. Entregar resumen para el chat de revisión: commits, archivos clave, decisiones, dependencias, resultado de lint/build/tests y pendientes para la sesión 3.

### Decisiones y avisos de la sesión
- `pnpm-workspace.yaml` tiene `allowBuilds: unrs-resolver: false` porque pnpm pedía aprobar el script de build de `unrs-resolver` (dependencia transitiva de `eslint-config-next`); usa binarios precompilados y no necesita compilar. En la iteración 5 hay que dejar un comentario con este motivo en ese archivo.
- Las pruebas manuales usan siempre BD y vault temporales: `DATABASE_URL` y `OBSIDIAN_VAULT_PATH` apuntan a la carpeta temporal, y `TELEGRAM_BOT_TOKEN`/`TELEGRAM_ALLOWED_USER_ID` van vacíos. En la sesión 1 se sobrescribió la BD pero no el vault (Settings lee `.env`); no se llamó a `/export`, así que no se escribió nada.
- `errorMessage(error, { maxActive })` se resuelve por `status + endpoint` (p. ej. `409 PATCH /projects/:id`); `fieldErrors(error)` mapea los issues de Pydantic por nombre de campo. El 409 de `/export` es otro conflicto (vault) y no se confunde con el límite de activos.
- Duda abierta: la verificación visual en navegador no se hizo en la sesión 1; se intentará en la iteración 10.
- Iteración 3: `StatusBadge` (compartido por la tarjeta y la tarjeta de foco, que sigue en el dashboard) vive en `components/projects/status-badge.tsx`; `ProgressBar` y `daysTone` quedaron privados en `project-card.tsx`. `ProjectList` incluye el bloque "No encontramos proyectos". Props con interfaz exportada por componente. Estado y llamadas a la API siguen en `project-dashboard.tsx`.
- Duda abierta (iteración 3): la condición `days > 30 && status === 'active'` se repite dos veces dentro de `ProjectCard`, y el texto de próxima acción vacía se resuelve distinto en la tarjeta ("Sin próxima acción definida") y en la tarjeta de foco ("Define una próxima acción..."). No se tocó; encaja con la iteración 4.
- Iteración 3 verificada por curl, no en navegador: el HTML SSR trae el título y el skeleton "Cargando proyectos" con backend temporal y un proyecto creado. Las tarjetas ya renderizadas no se vieron en un navegador.
- Duda abierta: el umbral de "abandonado" (>30 días) vive en el cliente solo como presentación.

## Adaptaciones pendientes del frontend
(hechas en la sesión 1: `lib/api.ts`, `lib/types.ts`, límite de activos por 409, estados de carga/error, limpieza de V0)
4. Tabs Ideas/Decisiones vacías: faltan listas y alta (sesión 3). Hoy sin contadores: la API no los expone.
5. Faltan crear proyecto y hito (sesión 2).
7. Dividir `project-dashboard.tsx` (un solo componente denso) en componentes pequeños (sesión 2).
- El límite de activos (`MAX_ACTIVE_PROJECTS`) no lo expone ningún endpoint: el contador del encabezado muestra "N activos" sin denominador. Decidir en la sesión 2 si se añade a la API.
- Los umbrales de color de "días sin tocar" y "Proyecto abandonado" (>30 días) siguen en el cliente solo como presentación.
