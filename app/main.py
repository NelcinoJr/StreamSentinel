"""
Bootstrap da aplicação — composition root HTTP.

Paralelo Zend:
  public/index.php + Application::init() + Module::onBootstrap()
  Registra rotas dos "módulos" (controllers v1).
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from app.api.v1.controllers.transaction_controller import router as transaction_router

app = FastAPI(
    title="StreamSentinel",
    version="0.2.0",
    description="Ingestão assíncrona de transações — Clean Architecture + CQRS",
)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def home() -> str:
    """
    Página inicial no browser (IndexController::indexAction).
    include_in_schema=False = não aparece no Swagger (é só vitrine).
    """
    return """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>StreamSentinel</title>
  <style>
    :root { color-scheme: light; }
    body {
      margin: 0; min-height: 100vh; display: grid; place-items: center;
      font-family: Georgia, "Times New Roman", serif;
      background: linear-gradient(160deg, #e8f1f5 0%, #f7f3ea 55%, #dfe8e4 100%);
      color: #1c2a32;
    }
    main { max-width: 36rem; padding: 2rem; }
    h1 { font-size: 2.4rem; margin: 0 0 0.4rem; letter-spacing: -0.02em; }
    p { margin: 0 0 1.4rem; line-height: 1.5; font-size: 1.05rem; }
    a {
      display: inline-block; margin: 0 0.6rem 0.6rem 0; padding: 0.65rem 1rem;
      text-decoration: none; color: #f7fafb; background: #1f4e5f;
      border: 1px solid #163944;
    }
    a.secondary { background: transparent; color: #1f4e5f; }
    small { display: block; margin-top: 1.2rem; opacity: 0.75; }
  </style>
</head>
<body>
  <main>
    <h1>StreamSentinel</h1>
    <p>API de ingestão assíncrona de transações. Para testar na tela, abra o Swagger.</p>
    <a href="/docs">Testar na tela (/docs)</a>
    <a class="secondary" href="/health">Health</a>
    <a class="secondary" href="/redoc">ReDoc</a>
    <small>POST/GET em /api/v1/transactions — 202, 409, consulta e listagem.</small>
  </main>
</body>
</html>
"""


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}


# Prefixo /api/v1 ≈ module route prefix no module.config.php
app.include_router(transaction_router, prefix="/api/v1")
