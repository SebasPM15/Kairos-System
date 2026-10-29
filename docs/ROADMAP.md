# Roadmap

## v0.1 — base funcional

1. [x] Esqueleto del backend + `GET /health`
2. [ ] Docker: Dockerfiles + docker-compose.yml + .dockerignore
3. [ ] Modelos SQLAlchemy + migración inicial Alembic
4. [ ] CRUD de proyectos con límite de activos y próxima acción obligatoria al activar
5. [ ] Hitos + cálculo de porcentaje
6. [ ] Ideas (incluye bandeja de entrada sin proyecto) y decisiones
7. [ ] Tests de services y API
8. [ ] Bot de Telegram: `/proyecto /idea /hito /hecho /estado /foco /decision`
9. [ ] Export a Markdown hacia el vault de Obsidian
10. [ ] Dashboard conectado a la API (reemplazar mocks, ver `docs/ESTADO.md`)

## Después

- **v0.2** — Recordatorios y alertas de proyectos sin avance.
- **v0.3** — Capa de IA: clasificar ideas por proyecto, proponer hitos, resumen semanal (el usuario confirma).
- **v0.4** — Búsqueda semántica con embeddings.
- **v1.0** — Agentes especializados con un orquestador.
