# Estado

_Última actualización: 2026-10-29 (endurecimiento del hito 10)_

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
- Hito 10, sesión 3 (bandeja, export y pestaña Bot): `GET /ideas/all` (todas las ideas del usuario, `created_at` descendente; 331 tests pasan, 1 omitido a propósito). Frontend: navegación Proyectos / Ideas / Bot sin router ni librería de estado (`view` en `project-dashboard.tsx`); `components/ideas/` (vista global con filtro por proyecto o sin proyecto, alta en la bandeja, asignar/desasignar, borrar con `AlertDialog`), alta de ideas en el drawer, `components/export/export-panel.tsx` (resumen y errores en el panel) y `components/bot/bot-commands.tsx` (tabla desde `GET /bot/commands`, sin duplicar el catálogo). Cierre de la sesión 2: sin rastro del paquete `cn`; etiqueta de estado ya no se estira; formularios de alta probados en navegador. `pnpm lint`, `typecheck` y `build` en verde. **Hito 10 completo.**
- Documentos base: CLAUDE.md, ROADMAP, architecture.

- `.claude/settings.json` sin coautoría de Claude; commits locales reescritos para quitarla (aún no estaban en el remoto).

## Sigue
- Probar el bot contra Telegram real (token y `TELEGRAM_ALLOWED_USER_ID` en `.env`).
- ~~Hito 10 de v0.1: dashboard conectado a la API~~ (completo, tres sesiones):
- Siguiente: v0.2, recordatorios y alertas de proyectos sin avance.
- Detalles del hito 10:
  1. ~~Cliente API y limpieza~~ (hecho).
  2. ~~Proyectos~~ (hecho, ver "Cierre de la sesión 2").
  3. ~~Bandeja, export y pestaña "Bot"~~ (hecho, ver "Cierre de la sesión 3").
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
4. [x] Tarjeta: estado con `lib/labels.ts`, porcentaje tal cual del backend (no recalcular), próxima acción visible, umbral de "abandonado" como constante nombrada en un solo lugar. Contador "N / máx" activos usando `/config`.
5. [x] Sustituir skeleton y aviso con CSS propio por los componentes shadcn skeleton y alert si no añaden dependencias (si hace falta alguna, justificarla antes de instalar). Comentar el motivo de `unrs-resolver: false` donde esté.
6. [x] Drawer del proyecto con secciones de hitos, ideas y decisiones: lectura, y marcar hito como hecho (el porcentaje debe refrescarse desde el backend).
7. [x] Formularios de alta: crear proyecto y crear hito. Validación mínima en cliente; la verdad la tiene el backend.
8. [x] Registrar decisión (el endpoint `POST /projects/{id}/decisions` existe) y cambios de estado desde la UI (activar, pausar, terminar).
9. [x] Errores en su sitio: 409 junto al control que lo causó, con el máximo real de `/config`; 422 de negocio junto al campo de próxima acción; 422 de validación mapeado por campo. El aviso global queda solo para errores sin contexto (red, 5xx).
10. [x] Verificación y cierre: `pnpm lint`, `typecheck` y `build` en verde; suite completa del backend (323 + nuevos). Prueba manual del flujo: crear proyecto, añadir hitos, activar con y sin próxima acción (422), superar el límite (409), marcar hito hecho y ver cambiar el porcentaje, y backend apagado. Si se puede abrir navegador, hacerlo y anotar qué se probó en navegador y qué solo a nivel API. Después, actualizar este archivo (y ROADMAP si cambia algo) en un commit propio. Entregar resumen para el chat de revisión: commits, archivos clave, decisiones, dependencias, resultado de lint/build/tests y pendientes para la sesión 3.

### Decisiones y avisos de la sesión
- `pnpm-workspace.yaml` tiene `allowBuilds: unrs-resolver: false` porque pnpm pedía aprobar el script de build de `unrs-resolver` (dependencia transitiva de `eslint-config-next`); usa binarios precompilados y no necesita compilar. En la iteración 5 hay que dejar un comentario con este motivo en ese archivo.
- Las pruebas manuales usan siempre BD y vault temporales: `DATABASE_URL` y `OBSIDIAN_VAULT_PATH` apuntan a la carpeta temporal, y `TELEGRAM_BOT_TOKEN`/`TELEGRAM_ALLOWED_USER_ID` van vacíos. En la sesión 1 se sobrescribió la BD pero no el vault (Settings lee `.env`); no se llamó a `/export`, así que no se escribió nada.
- `errorMessage(error, { maxActive })` se resuelve por `status + endpoint` (p. ej. `409 PATCH /projects/:id`); `fieldErrors(error)` mapea los issues de Pydantic por nombre de campo. El 409 de `/export` es otro conflicto (vault) y no se confunde con el límite de activos.
- Duda abierta: la verificación visual en navegador no se hizo en la sesión 1; se intentará en la iteración 10.
- Iteración 3: `StatusBadge` (compartido por la tarjeta y la tarjeta de foco, que sigue en el dashboard) vive en `components/projects/status-badge.tsx`; `ProgressBar` y `daysTone` quedaron privados en `project-card.tsx`. `ProjectList` incluye el bloque "No encontramos proyectos". Props con interfaz exportada por componente. Estado y llamadas a la API siguen en `project-dashboard.tsx`.
- Duda abierta (iteración 3): la condición `days > 30 && status === 'active'` se repite dos veces dentro de `ProjectCard`, y el texto de próxima acción vacía se resuelve distinto en la tarjeta ("Sin próxima acción definida") y en la tarjeta de foco ("Define una próxima acción..."). No se tocó; encaja con la iteración 4.
- Iteración 3 verificada por curl, no en navegador: el HTML SSR trae el título y el skeleton "Cargando proyectos" con backend temporal y un proyecto creado. Las tarjetas ya renderizadas no se vieron en un navegador.
- Duda abierta: el umbral de "abandonado" (>30 días) vive en el cliente solo como presentación.

### Cierre de la sesión 2 (iteraciones 4-10)
Commits: `d8efbf2` (`isAbandoned`, constantes de próxima acción, contador "N / máx"), `a74b42a` (shadcn Skeleton/Alert, comentario de `unrs-resolver`), `3939fa7` y `a4ed761` (drawer extraído; listas de ideas y decisiones), `27a89ff` (alta de hitos), `cc14ccf` (alta de proyecto), `6107a5b` (alta de decisión), `a18e899` (409/422 junto a su control).
- `lib/project-health.ts`: `ABANDONED_AFTER_DAYS = 30` e `isAbandoned(project)`; solo la tarjeta lo usa (la tarjeta de foco nunca mostró el aviso y no se le añadió).
- Texto de próxima acción vacía: la diferencia tarjeta ("Sin próxima acción definida") / foco ("Define una próxima acción...") es intencional; quedan como constantes en `lib/labels.ts`.
- Contador: "N / máx activos" con `GET /config`; si falla, cae a "N activos".
- Skeleton y Alert de shadcn. El CLI de shadcn añadió por error la dependencia `cn` (paquete ajeno) y importaba de ella: se revirtió y los archivos importan `@/lib/utils`. Sin dependencias nuevas.
- Drawer en `components/projects/` (`project-drawer`, `milestone-list/form`, `idea-list`, `decision-list/form`); `project-form` para el alta. Tras crear hito/decisión o marcar hecho se vuelve a pedir el proyecto: el porcentaje viene siempre del backend.
- Cambio de estado: sigue siendo el `select` del drawer (activar/pausar/terminar); no se añadieron botones.
- Errores: 409 bajo el select de estado (con el máximo real de `/config`); 422 de negocio y de validación de `next_action` bajo el campo; 422 de formularios por campo. El aviso global queda para red/5xx.
- Verificación: `pnpm lint`, `typecheck`, `build` en verde; backend 327 pasan, 1 omitido. Navegador: Chrome headless (no había navegador integrado ni Claude in Chrome), con backend temporal (`MAX_ACTIVE_PROJECTS=1`, BD y vault temporales) y script CDP. **Visto en pantalla**: tarjetas con datos reales y "1 / 1 activos", 409 bajo el select, 422 bajo el campo de próxima acción (input marcado), checkbox de hito que pasa el porcentaje de 50 % a 100 %, y error con "Reintentar" con el backend apagado. **Solo por API/código**: skeleton de carga (visto por SSR), alta de proyecto/hito/decisión desde sus formularios (compilan, no se enviaron en navegador), listas de ideas y decisiones con datos, tema claro.
- La etiqueta de estado estirada en la tarjeta se arregló en la sesión 3 (`align-items: flex-start`).
- Pendiente sesión 3: bandeja de ideas global, botón de export con resumen, pestaña Bot, alta de ideas desde el drawer.

### Cierre de la sesión 3
Commits: `08f4ea9` (etiqueta de estado), `5089f38` (`GET /ideas/all`), `ecb1c43` (alta de ideas en el drawer), `1f62a67` (vista de ideas, filtro, navegación), `7cf32b1` (asignar/desasignar), `1e46507` (borrar con diálogo), `4ca2372` (export), `56d755b` (pestaña Bot), `6738748` (tema claro).
- Las ideas **no tienen estado** en BD/API (decisión: no se añade); la UI muestra "Bandeja" o el nombre del proyecto y el filtro es por proyecto / sin proyecto. `GET /ideas/all` se declara antes de cualquier ruta `/ideas/{id}`.
- Borrar una idea es solo en BD: **no borra el `.md` ya exportado** (el export nunca borra). El diálogo de confirmación lo dice. `AlertDialog` está escrito a mano en `components/ui/alert-dialog.tsx` sobre `@base-ui/react` (ya instalado) para no arriesgar otra dependencia ajena del CLI de shadcn; se monta dentro de `.dashboard` para heredar el tema.
- Asignar una idea a un proyecto actualiza su `last_activity_at`, así que la vista de ideas pide de nuevo los proyectos (sin skeleton).
- La tabla del bot saca los argumentos de `syntax` quitando `/<name>` (el catálogo no tiene campo de argumentos).
- Tema claro: `body` resolvía `--foreground` antes de `.light`, dejando texto casi blanco; se fijó `color` y fondo en `.dashboard`.
- Verificación: `pnpm lint`, `typecheck`, `build` en verde; backend 331 pasan y 1 omitido (`test_symlinked_file_leaving_the_vault_is_rejected`: en Windows sin privilegio no se pueden crear symlinks de archivo; es intencional y los de carpeta usan junctions). Navegador (Chrome headless con CDP, backend y vault temporales, `MAX_ACTIVE_PROJECTS=1`): **visto en pantalla** alta de proyecto, hito, decisión e idea en el drawer (con sus errores de campo vacío), bandeja con filtro, asignar/desasignar, diálogo de borrado (cancelar y confirmar), export (5 archivos escritos; segundo export 0 escritos / 5 sin cambios; carpeta huérfana informada; `Notas/keep.md`, `Kairos/huerfana/x.md` y un archivo manual en `Kairos/` siguen intactos), tabla del bot (11 comandos), tema claro y errores de conexión (export, Bot, Ideas, "Reintentar") con el backend apagado. **No probado**: skeleton de carga ni el 409 de `/export` sin vault configurado (el mensaje existe en `lib/labels.ts`; el 409 ya lo cubren los tests del backend).
- (Resuelto en el endurecimiento) Los botones de shadcn se veían sin fondo por falta de tokens.

### Endurecimiento del hito 10 (antes de v0.2)
Commits: `e916c15` (tokens de tema), `fac4e12` y `74d488b` (catálogo: `feat(api)` + `refactor(frontend)`), `ae503aa` (gitignore), `95888cc` (documentar `NEXT_PUBLIC_API_URL`).
- Tema: `globals.css` no tenía `@theme`, así que `bg-primary`, `bg-muted`, etc. no generaban clases. Se añadió un `@theme inline` que mapea los nombres de shadcn a las variables de V0 (`--soft`, `--line`, `--muted`, `--accent`) y se definieron `--primary`, `--primary-foreground` y `--destructive` en oscuro y claro. Primario: lima sobre texto oscuro en oscuro; oscuro sobre texto claro en claro.
- Catálogo del bot: `CommandInfo` tiene `name`, `args` y `description`; `syntax` es un campo calculado (`/<name> <args>`), así que no hay dos copias que desincronizar. `GET /bot/commands` devuelve los cuatro campos y la pestaña Bot usa `args`. 333 tests pasan, 1 omitido (symlink de archivo, intencional).
- Docker: `docker compose up -d --build` funciona con BD (volumen) y vault temporales y bot sin token. `NEXT_PUBLIC_API_URL` ya se pasaba como build arg (compose -> Dockerfile); se comprobó con un valor distinto del por defecto (`http://127.0.0.1:8000`): quedó incrustado en el JS compilado y el navegador llamó a ese origen. Solo hizo falta documentarlo (`.env.example`, `architecture.md`): cambiarla exige reconstruir.
- `next-env.d.ts` dejó de versionarse y `AGENTS.md` (lo genera `next dev`) se ignora, ambos en `frontend/.gitignore`; tras `pnpm build` y `pnpm dev` el árbol queda limpio.
- AlertDialog: con clic real, el foco entra al diálogo (en "Cancelar"), Escape lo cierra y el foco vuelve al botón "Borrar" que lo abrió; igual al cancelar. (Con `element.click()` por script el foco no vuelve porque el botón nunca lo tuvo.)
- Verificación: lint, typecheck y build en verde. Navegador (Chrome headless, contra el stack de Docker con datos temporales): botones "Añadir", "Exportar ahora" y "Borrar idea" con fondo y texto calculados en ambos temas (primario lima/oscuro, destructivo rojo translúcido), tabla del bot con la columna de argumentos. **Solo por código/API**: el resto de botones de shadcn (secundario, link) no se vieron.
- Nota: `docker compose` lee `env_file: .env`; para probar sin el `.env` real se usó un override con `env_file: !reset []`, `--env-file` temporal y proyecto `kairos-verify`, eliminado al terminar (contenedores, volumen e imágenes).

## Entorno de demo
Base y vault aparte para revisar el dashboard a mano; nunca tocan `kairos.db` ni tu vault. `backend/scripts/seed_demo.py` carga los datos con los services (límite de activos, próxima acción y porcentaje calculado se respetan) y se niega a correr si la base no es de demo (el nombre del archivo debe incluir `demo`), si no hay tablas o si ya hay datos sin `--reset`. `--reset` borra solo los proyectos e ideas del usuario actual de esa base. La base de demo es `backend/demo.db` (ya ignorada por git); el vault de demo va en la carpeta temporal.

**PowerShell** (terminal 1, backend, desde `backend/`):
```powershell
.venv\Scripts\Activate.ps1
$env:DATABASE_URL = "sqlite:///./demo.db"
$env:OBSIDIAN_VAULT_PATH = "$env:TEMP\kairos-demo-vault"
$env:MAX_ACTIVE_PROJECTS = "3"
New-Item -ItemType Directory -Force $env:OBSIDIAN_VAULT_PATH | Out-Null
alembic upgrade head
python scripts/seed_demo.py
uvicorn app.main:app --reload
```
**bash** (Git Bash, desde `backend/`):
```bash
source .venv/Scripts/activate
export DATABASE_URL="sqlite:///./demo.db" OBSIDIAN_VAULT_PATH="$TEMP/kairos-demo-vault"
export TELEGRAM_BOT_TOKEN="" TELEGRAM_ALLOWED_USER_ID="" MAX_ACTIVE_PROJECTS=3
mkdir -p "$OBSIDIAN_VAULT_PATH"
alembic upgrade head
python scripts/seed_demo.py
uvicorn app.main:app --reload
```
**Bot sin token**: el backend lee `.env` desde su carpeta de trabajo (`backend/`), donde hoy no hay uno (el `.env` de Docker está en la raíz), así que el bot queda desactivado. Si algún día creas `backend/.env` con el token, quítalo mientras uses la demo: en PowerShell asignar `""` a una variable la borra en vez de vaciarla, por eso solo el bloque bash las vacía.

**Frontend** (terminal 2, desde `frontend/`): `pnpm dev` y abrir http://localhost:3000.

**Resetear** (con las mismas variables de entorno): `python scripts/seed_demo.py --reset`. Para empezar de cero, parar el backend, borrar `backend/demo.db` y la carpeta `kairos-demo-vault` de `%TEMP%`, y repetir `alembic upgrade head` y el seed. Para volver a lo normal, cerrar esas terminales (las variables solo viven en ellas) o ejecutar `Remove-Item Env:DATABASE_URL, Env:OBSIDIAN_VAULT_PATH` (PowerShell) / `unset DATABASE_URL OBSIDIAN_VAULT_PATH` (bash).

**Datos** (9 proyectos, 8 ideas):
- Activos (3, el máximo, todos con próxima acción): 0 % (0 de 4 hitos; título de 100+ caracteres y próxima acción de 200+), 60 % (3 de 5) y 80 % (4 de 5).
- Pausados (3): "Blog de cocina casera" con 47 días sin actividad (el «abandonado»), "Huerto urbano" y "Aprender guitarra" (sin próxima acción).
- Idea (2), terminado (1, 100 %).
- Decisiones (1 a 3) en cuatro proyectos y hitos hechos y pendientes mezclados. Ideas: 4 en la bandeja (una muy larga) y 4 repartidas en proyectos.
- La última actividad va de 1 a 47 días atrás (se retrocede la fecha a mano al final, porque los services siempre ponen «ahora») para ver los colores de «días sin tocar».
- El «abandonado» quedó **pausado**: con el límite de 3 ocupado por los activos no cabe un cuarto activo, y la UI solo muestra «Proyecto abandonado» en proyectos activos, así que ese aviso no aparece en la demo. Activarlo desde la UI (tras pausar otro) reinicia su actividad a «ahora».

## Adaptaciones pendientes del frontend
(hechas en la sesión 1: `lib/api.ts`, `lib/types.ts`, límite de activos por 409, estados de carga/error, limpieza de V0)
(todas hechas en las sesiones 1-3)
- El límite de activos (`MAX_ACTIVE_PROJECTS`) no lo expone ningún endpoint: el contador del encabezado muestra "N activos" sin denominador. Decidir en la sesión 2 si se añade a la API.
- Los umbrales de color de "días sin tocar" y "Proyecto abandonado" (>30 días) siguen en el cliente solo como presentación.
