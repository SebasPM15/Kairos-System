# Arquitectura

## Componentes

```
Telegram ──► bot/ handlers ─┐
                            ├──► services/ ──► SQLAlchemy ──► SQLite (fuente de verdad)
Next.js ──HTTP──► routers/ ─┘        │
                                     └──► exporters/ ──► Vault Obsidian (Markdown)
```

Un solo proceso: FastAPI + bot de Telegram. Routers y handlers son delgados; la lógica (límite de activos, porcentaje, actualización de `last_activity_at`) vive en `services/`. Los schemas (Pydantic) definen el contrato de la API.

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

**milestones**: id, project_id → projects, title, done (bool), position (int), completed_at (nullable), created_at.

**ideas**: id, project_id → projects (**nullable**, bandeja de entrada), content, created_at.

**decisions**: id, project_id → projects, title, rationale (el porqué), created_at.

Relaciones: un proyecto tiene muchos hitos, ideas y decisiones (borrado en cascada). El porcentaje no se guarda: `completed / total` de hitos (0 si no hay hitos).

Reglas: máximo `MAX_ACTIVE_PROJECTS` en `active`; activar sin `next_action` se rechaza.

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
