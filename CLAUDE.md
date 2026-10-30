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
- Decisiones cerradas (no cambiar sin pedirlo): BD fuente de verdad, vault unidireccional, `MAX_ACTIVE_PROJECTS=3`, estados en inglés en BD/API, porcentaje calculado en el backend.

## Regla de sesión

Al terminar cada sesión, actualizar `docs/ESTADO.md`.

Ver `docs/ROADMAP.md` y `docs/architecture.md`.
