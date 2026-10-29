# Estado

_Última actualización: 2026-10-28_

## Hecho
- Esqueleto del backend (carpetas, `__init__.py`, `pyproject.toml` mínimo) y `.env.example`.
- Frontend de V0 copiado a `frontend/`. Instala y compila (`pnpm build` OK, `tsc --noEmit` OK). Usa datos mock.
- Hito 1: `config.py` (Settings), `db.py` (engine, SessionLocal, Base, `get_db`), `create_app()` con CORS, `GET /health` y `tests/test_health.py` (pasa). `uvicorn app.main:app` arranca y responde.
- Hito 2: Dockerfiles (backend `python:3.12-slim` no root; frontend multi-stage con `output: 'standalone'`), `docker-compose.yml` (volumen `kairos-data` en `/data`, vault por `VAULT_HOST_PATH` en `/vault`, healthcheck). Verificado: build OK, `/health` y frontend responden, el volumen persiste tras `down`/`up`.
- Documentos base: CLAUDE.md, ROADMAP, architecture.

- `.claude/settings.json` sin coautoría de Claude; commits locales reescritos para quitarla (aún no estaban en el remoto).

## Sigue
- Hito 3 de v0.1: modelos SQLAlchemy + migración inicial Alembic.

## Bloqueos
- Ninguno.

## Decisiones recientes
- `pyproject` limita el descubrimiento de paquetes a `app*` (si no, `pip install -e` falla por el layout plano).
- Python 3.13 local, `requires-python >=3.12`; sin versiones fijas en `pyproject` por ahora.
- pnpm vía corepack (12.3.4, versión válida).
- Estados en inglés (`idea|active|paused|done`); traducción en UI y bot.
- `ideas.project_id` nullable (bandeja de entrada); `projects.slug` para la carpeta de Obsidian.
- Hitos: `completed_at` lo gestiona el service; `position` es el orden manual.
- Borrar proyecto: hitos y decisiones en cascada; ideas `SET NULL`. Hitos/ideas/decisiones actualizan `last_activity_at`.
- Todo local: Docker Compose (SQLite en `/data`, vault en `/vault`), bot por long polling; desarrollo nativo. Archivos Docker listos (hito 2). Compose exige un `.env` (copiar de `.env.example`).

## Adaptaciones pendientes del frontend
1. `lib/api.ts`: cambiar mocks por `fetch` a `NEXT_PUBLIC_API_URL`; habilitar CORS en FastAPI.
2. `lib/types.ts`: IDs numéricos, estados en inglés con etiquetas en español, `ideas`/`decisions` como listas; porcentaje y días sin tocar calculados por el backend.
3. Límite de activos: hoy 3 fijo con `window.confirm`; debe ser rechazo del servidor (409) según config.
4. Tabs Ideas/Decisiones vacías: faltan listas y alta.
5. Faltan crear proyecto/hito, estados de carga y error.
6. Quitar `@vercel/analytics`, `generator: 'v0.app'`, `ignoreBuildErrors`; marca “Enfoque” → “Kairos”; `name` del package.
7. Dividir `project-dashboard.tsx` (un solo componente denso) en componentes pequeños.
