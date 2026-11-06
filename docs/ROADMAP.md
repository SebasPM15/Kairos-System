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

11. [x] **Shell y sistema de diseño**
    - Tokens de diseño y tema claro con contraste WCAG AA (`pnpm contrast` audita los pares).
    - Header estable: la navegación no se mueve entre Proyectos, Ideas y Bot.
    - Sidebar lateral colapsable (estado recordado, zona de usuario placeholder) y menú off-canvas en móvil.
    - Modales para "Nuevo proyecto" y "Exportar a Obsidian"; el drawer del proyecto es un Dialog lateral.
    - Toasts para confirmaciones efímeras y errores accionables en línea.
    - Animaciones solo con `transform` y `opacity`, y respetando `prefers-reduced-motion`.
    - Pluralización correcta (`formatCount` / `pluralLabel`).
    - Rutas reales (`/proyectos`, `/ideas`, `/bot`) y tema persistido en `<html>`.
    - Controles y formularios con componentes propios sobre `@base-ui/react` (Field, Input, Textarea, Select, SearchInput, Checkbox, Button con estado de carga) y anillo de foco consistente.
12. [x] **Métricas**
    - Ruta `/metricas` con proyectos por estado, avance por proyecto, hitos completados por semana e ideas capturadas vs. asignadas a un proyecto.
    - `GET /metrics?weeks=` (1 a 52, por defecto 12): agregados calculados en el backend (router -> service -> repository), semanas de lunes a domingo en `TIMEZONE`. Gráficos propios en HTML y CSS, sin dependencias nuevas salvo `tzdata` en el backend.
    - `ideas.assigned_at` (migración con backfill) para contar las asignaciones por semana.

**Optimización de bundle** [x] (bloque propio tras el hito 12): diálogos diferidos con `next/dynamic` (−11.5 kB en `/proyectos`) y el tooltip de Base UI cargado solo cuando el sidebar está colapsado (−23.9 kB). `/proyectos`: 251.4 → 216.0 kB.

**Transversal** (sin hito propio)
- i18n es/en (`next-intl`, a decidir).
- SEO básico: metadata, `lang` y título por vista.
- Auth cuando toque: `get_current_user` es el único punto a reemplazar.

**Dependencias a justificar antes de instalar**: `next-intl` (i18n). No se añade sin justificarla antes. (`sonner` quedó descartado: los toasts usan `@base-ui/react/toast`.)

## Después

- **v0.2** [x] — Recordatorios y alertas de proyectos sin avance, y señal de «bot caído».
    - Alertas calculadas en vivo en el backend (`stalled` para activos a los 7 días y pausados a los 30; `ready_to_finish` para activos con todos los hitos hechos), con umbrales en `Settings` y expuestos en `GET /config`.
    - Un resumen diario por Telegram (tarea asyncio en el lifespan, sin dependencias nuevas) con máximo 5 proyectos, botones Posponer 7 d / Silenciar y comandos `/recordatorios`, `/posponer`, `/silenciar` y `/reactivar`. Anti-ruido: un resumen por día local, repeticiones limitadas, horas de silencio en `TIMEZONE`.
    - `GET /reminders` y `PATCH /projects/{id}/reminders`; bloque «Necesitan atención» en `/proyectos` con posponer, silenciar y reactivar.
    - `GET /bot/status` (`disabled | running | failed | stopped`, solo códigos y nombres de excepción), tarjeta de estado en la pestaña Bot y banner persistente de bot caído.
- **v0.3** — Capa de IA: clasificar ideas por proyecto, proponer hitos, resumen semanal (el usuario confirma). Aplazados desde v0.2: el recordatorio de hito sin completar durante mucho tiempo (hoy `created_at` de los hitos pendientes no distingue casos) y el de activo sin próxima acción (el service ya impide que exista; sería un chequeo de integridad).
- **v0.4** — Búsqueda semántica con embeddings.
- **v1.0** — Agentes especializados con un orquestador.
