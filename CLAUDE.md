# Kairos

Asistente personal de seguimiento de proyectos: bot de Telegram + API FastAPI + dashboard Next.js + export Markdown a un vault de Obsidian. Objetivo: registrar ideas y decisiones por proyecto, medir avance real y no abandonar proyectos.

## Comandos

```bash
# Backend (desde backend/)
python -m venv .venv && .venv\Scripts\activate
pip install -e ".[dev]"
uvicorn app.main:app --reload          # API + bot en el mismo proceso
pytest                                  # tests
alembic upgrade head                    # aplicar migraciones
alembic revision --autogenerate -m "msg"

# Sistema completo (Docker, desde la raíz)
docker compose up -d
docker compose down
docker compose logs -f

# Frontend (desde frontend/)
pnpm install
pnpm dev
pnpm build
pnpm contrast                            # auditoría WCAG de los tokens; correr al cambiar cualquier color en globals.css
```

Copiar `.env.example` a `.env` y completar. El `.env` nunca se commitea.

## Convenciones

- Código, identificadores y comentarios en **inglés**. Comentarios solo cuando son necesarios y breves (explican el porqué, no el qué).
- Textos de UI, docs y mensajes del bot en **español**.
- Commits convencionales (`feat:`, `fix:`, `docs:`, `chore:`, `test:`, `refactor:`), pequeños, uno por paso lógico.
- Clean code y principios SOLID; patrones de diseño cuando aporten (repository, service, inyección de dependencias). Sin sobreingeniería.
- Services contienen la lógica; routers y handlers del bot son delgados (validan, delegan, responden).
- No agregar dependencias ni documentación sin necesidad.
- Los commits no llevan coautoría de Claude (configurado en `.claude/settings.json`).

## Decisiones de arquitectura

1. El porcentaje no se guarda ni lo deduce la IA: se calcula con hitos (completados / total). La IA (v0.3) solo propone hitos o marca uno como hecho, y el usuario confirma.
2. Límite de proyectos activos (`MAX_ACTIVE_PROJECTS`, por defecto 3). Todo proyecto activo exige una próxima acción.
3. Cada proyecto guarda ideas, decisiones (con su porqué), hitos, estado y última actividad.
4. La BD es la fuente de verdad; el vault de Obsidian (una carpeta por proyecto) es una exportación.
5. El bot corre en el mismo proceso que FastAPI y llama a `services/`, no a HTTP.
6. Estados en inglés en BD y API (`idea|active|paused|done`); la traducción al español vive en UI y bot.

7. Todo corre local: Docker Compose (backend + frontend), SQLite en volumen `/data`, vault de Obsidian como bind mount en `/vault`, bot con long polling (sin webhooks ni URL pública). El desarrollo diario es nativo (`uvicorn --reload`, `pnpm dev`). Obsidian es solo una carpeta de Markdown: el export no requiere tenerlo instalado.

## Reglas fijas

- Nunca leer ni imprimir `.env` ni el token del bot.
- Las pruebas manuales usan solo BD y `OBSIDIAN_VAULT_PATH` temporales (y bot sin token); nunca la SQLite ni el vault reales.
- Commits convencionales, pequeños, sin coautoría de Claude.
- Respetar las capas del backend: routers delgados -> services -> repositories.
- En tareas de diseño/UI, usar los skills de diseño que existan en `~/.claude/skills` (p. ej. `impeccable`, `ui-ux-pro-max`, `design-system`, `ui-styling`) y comprobar el resultado en navegador; los skills de marketing no aplican.
- Todo cambio de UI se verifica a 390/768/1024/1280 px sin scroll horizontal, en ambos temas, y con nombres de 120 caracteres (con y sin espacios).
- Si el usuario debe actuar, no es un toast. Los toasts son efímeros, confirman algo ya hecho y nunca llevan la única vía para resolver un problema.
- El tema (clase `light` / `dark`) vive en `<html>`, nunca en un contenedor; los portales (Dialog, Toaster, AlertDialog) van a `body` y lo heredan. Las preferencias (`kairos-theme`, `kairos-sidebar`) se leen en un script inline del `<head>` y se guardan siempre dentro de `try/catch`.
- Las páginas del dashboard viven bajo `frontend/app/(app)/`, cuyo layout monta `DashboardProvider`, `AppShell` y `Toaster` una sola vez.
- Decisiones cerradas (no cambiar sin pedirlo): BD fuente de verdad, vault unidireccional, `MAX_ACTIVE_PROJECTS=3`, estados en inglés en BD/API, porcentaje calculado en el backend.
- Despliegue (el compose del repo es la única fuente; ver `deploy/homelab/README.md`): puertos solo en `127.0.0.1`, `restart: always`, `mem_limit` (con `memswap_limit` igual) y `healthcheck` en cada servicio, imágenes base con tag fijo (se actualiza a propósito, nunca `latest`), `.env` real fuera de Git (en el servidor, enlazado desde `/srv/stacks/nova-brain`). Scripts y plantillas del servidor en `deploy/homelab/`; `.gitattributes` mantiene LF en lo que se ejecuta en Linux.

## Regla de sesión

Al terminar cada sesión, actualizar `docs/ESTADO.md`.

Ver `docs/ROADMAP.md` y `docs/architecture.md`.
