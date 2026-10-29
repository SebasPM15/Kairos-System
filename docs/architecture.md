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

**projects**
| campo | tipo | notas |
|---|---|---|
| id | int PK | |
| name | str | |
| slug | str unique | carpeta en Obsidian |
| description | str | |
| status | enum | `idea`, `active`, `paused`, `done` |
| next_action | str, nullable | obligatoria en el service al pasar a `active` |
| last_activity_at | datetime | la actualizan los services |
| created_at | datetime | |

**milestones**: id, project_id → projects, title, done (bool), position (int, orden manual dentro del proyecto), completed_at (nullable; lo pone el service al marcar hecho y lo limpia al reabrir), created_at.

**ideas**: id, project_id → projects (**nullable**, bandeja de entrada), content, created_at.

**decisions**: id, project_id → projects, title, rationale (el porqué), created_at.

Relaciones: un proyecto tiene muchos hitos, ideas y decisiones. Al borrar un proyecto: `milestones` y `decisions` en cascada; `ideas` con `ON DELETE SET NULL` (vuelven a la bandeja de entrada). El porcentaje no se guarda: `completed / total` de hitos (0 si no hay hitos).

Reglas:
- Máximo `MAX_ACTIVE_PROJECTS` en `active`; activar sin `next_action` se rechaza.
- Crear, completar o reabrir un hito, y crear una idea o decisión, actualiza `last_activity_at` del proyecto.

## Ejecución local

- Docker Compose (backend + frontend): SQLite en volumen `/data`; vault de Obsidian como bind mount en `/vault` (`OBSIDIAN_VAULT_PATH=/vault` dentro del contenedor).
- Bot con long polling: sin webhooks ni URL pública.
- Desarrollo diario nativo (`uvicorn --reload`, `pnpm dev`); Docker sirve para ejecutar el sistema completo.
- Obsidian es solo una carpeta de Markdown: el export funciona sin tener Obsidian instalado.

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
