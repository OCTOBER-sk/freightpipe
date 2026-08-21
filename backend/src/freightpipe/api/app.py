"""FreightPipe — FastAPI application entry point."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from freightpipe.api.routes import router
from freightpipe.db.connection import close_pool, get_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    await get_pool()  # warm the connection pool
    yield
    await close_pool()


app = FastAPI(
    title="FreightPipe",
    description="Headless freight document normalization API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
