"""
Bootstrap da aplicação — composition root HTTP.

Paralelo Zend:
  public/index.php + Application::init() + Module::onBootstrap()
  Registra rotas dos "módulos" (controllers v1).
"""

from __future__ import annotations

from fastapi import FastAPI

from app.api.v1.controllers.transaction_controller import router as transaction_router

app = FastAPI(
    title="StreamSentinel",
    version="0.2.0",
    description="Ingestão assíncrona de transações — Clean Architecture + CQRS",
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}


# Prefixo /api/v1 ≈ module route prefix no module.config.php
app.include_router(transaction_router, prefix="/api/v1")
