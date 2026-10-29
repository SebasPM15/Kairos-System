from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.bot.app import bot_lifespan
from app.config import get_settings
from app.routers import bot, decisions, export, health, ideas, milestones, projects


def create_app() -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        # Long polling runs in this process, so run a single worker
        async with bot_lifespan(settings):
            yield

    app = FastAPI(title="Kairos", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(projects.router)
    app.include_router(milestones.router)
    app.include_router(ideas.router)
    app.include_router(decisions.router)
    app.include_router(export.router)
    app.include_router(bot.router)
    return app


app = create_app()
