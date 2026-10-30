# Roadmap

## v0.1 — base funcional

1. [x] Esqueleto del backend + `GET /health`
2. [x] Docker: Dockerfiles + docker-compose.yml + .dockerignore
3. [x] Modelos SQLAlchemy + migración inicial Alembic
4. [x] CRUD de proyectos con límite de activos y próxima acción obligatoria al activar
5. [x] Hitos + cálculo de porcentaje
6. [x] Ideas (incluye bandeja de entrada sin proyecto) y decisiones
7. [x] Tests de services y API
8. [x] Bot de Telegram: `/proyecto /idea /hito /hecho /estado /foco /decision`; filtro por TELEGRAM_ALLOWED_USER_ID
9. [x] Export a Markdown hacia el vault de Obsidian
10. [x] Dashboard conectado a la API (proyectos, ideas, export y pestaña Bot)

## Hitos 11 y 12 — pulido del dashboard (antes de v0.2)

11. [ ] (siguiente) **Shell y sistema de diseño**
    - Tokens de diseño y tema claro con contraste WCAG AA.
    - Header estable: las tabs no se mueven entre Proyectos, Ideas y Bot aunque cambien las acciones de cada vista.
    - Sidebar lateral colapsable, con el estado recordado y una zona de usuario placeholder.
    - Modales para "Nuevo proyecto" y "Exportar a Obsidian".
    - Toasts y banners.
    - Animaciones solo con `transform` y `opacity`, y respetando `prefers-reduced-motion`.
    - Corregir la pluralización ("1 días").
12. [ ] **Métricas**
    - Sección con proyectos por estado, avance por proyecto, hitos completados por semana e ideas capturadas vs. promovidas.
    - Evaluar `GET /metrics`: agregados calculados en el backend (router -> service -> repository), sin recalcular nada en el cliente.

**Transversal** (sin hito propio)
- i18n es/en (`next-intl`, a decidir).
- SEO básico: metadata, `lang` y título por vista.
- Auth cuando toque: `get_current_user` es el único punto a reemplazar.

**Dependencias a justificar antes de instalar**: `sonner` (toasts), `next-intl` (i18n) y `recharts` (gráficos de métricas). Ninguna se añade sin justificarla antes.

## Después

- **v0.2** — Recordatorios y alertas de proyectos sin avance.
- **v0.3** — Capa de IA: clasificar ideas por proyecto, proponer hitos, resumen semanal (el usuario confirma).
- **v0.4** — Búsqueda semántica con embeddings.
- **v1.0** — Agentes especializados con un orquestador.
