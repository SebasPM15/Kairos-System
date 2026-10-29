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

## Decisiones de arquitectura

1. El porcentaje no se guarda ni lo deduce la IA: se calcula con hitos (completados / total). La IA (v0.3) solo propone hitos o marca uno como hecho, y el usuario confirma.
2. Límite de proyectos activos (`MAX_ACTIVE_PROJECTS`, por defecto 3). Todo proyecto activo exige una próxima acción.
3. Cada proyecto guarda ideas, decisiones (con su porqué), hitos, estado y última actividad.
4. La BD es la fuente de verdad; el vault de Obsidian (una carpeta por proyecto) es una exportación.
5. El bot corre en el mismo proceso que FastAPI y llama a `services/`, no a HTTP.
6. Estados en inglés en BD y API (`idea|active|paused|done`); la traducción al español vive en UI y bot.

## Regla de sesión

Al terminar cada sesión, actualizar `docs/ESTADO.md`.

Ver `docs/ROADMAP.md` y `docs/architecture.md`.
