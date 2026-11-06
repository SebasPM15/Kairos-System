# Kairos

Asistente personal de seguimiento de proyectos: bot de Telegram + API FastAPI + dashboard Next.js + export Markdown a un vault de Obsidian. Registra ideas y decisiones por proyecto, mide el avance con hitos y avisa cuando un proyecto lleva días sin avance.

## Arranque rápido

- **Docker (uso diario)**: copia `.env.example` a `.env`, complétalo (token del bot, tu ID de Telegram, `VAULT_HOST_PATH`) y ejecuta `docker compose up -d --build`. API en `http://localhost:8000`, dashboard en `http://localhost:3000`. Los servicios se reinician solos (`restart: unless-stopped`).
- **Desarrollo nativo**: `uvicorn app.main:app --reload` en `backend/` y `pnpm dev` en `frontend/` (ver `CLAUDE.md`). No lo corras a la vez que Docker con el mismo token.
- **Respaldos**: `scripts/backup.ps1` y `scripts/restore.ps1` (o `scripts/backup.sh`).

## Documentación

- `CLAUDE.md`: convenciones y decisiones cerradas.
- `docs/architecture.md`: arquitectura, esquema de BD, endpoints, recordatorios y bot.
- `docs/ROADMAP.md`: versiones.
- `docs/ESTADO.md`: estado actual, despliegue local (arranque, logs, respaldo y restauración, tarea programada) y entorno de demo.
