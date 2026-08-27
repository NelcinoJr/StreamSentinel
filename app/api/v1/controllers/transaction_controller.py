"""
Controller FastAPI — borda HTTP.

Paralelo Zend:
  TransactionController::ingestAction()
    1. recebe request
    2. valida (Form/InputFilter → aqui Pydantic)
    3. chama Service/Use Case
    4. devolve ViewModel JSON com status 202

NÃO acessa Repository, Finder nem SQLAlchemy.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.api.v1.schemas.transaction_schema import (
    IngestTransactionRequest,
    IngestTransactionResponse,
)
from app.use_cases.ingest_transaction import (
    IngestTransactionInput,
    IngestTransactionResult,
    IngestTransactionUseCase,
)

router = APIRouter(prefix="/transactions", tags=["transactions"])


def get_ingest_use_case() -> IngestTransactionUseCase:
    """
    Factory simples (estilo ServiceManager factory do ZF).
    Wiring real (Redis) será plugado no composition root / Depends.
    """
    from app.api.deps import build_ingest_use_case

    return build_ingest_use_case()


@router.post(
    "",
    response_model=IngestTransactionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingestão assíncrona de transação",
)
async def ingest_transaction(
    body: IngestTransactionRequest,
    use_case: IngestTransactionUseCase = Depends(get_ingest_use_case),
) -> IngestTransactionResponse:
    result: IngestTransactionResult = await use_case.execute(
        IngestTransactionInput(
            external_id=body.external_id,
            amount=body.amount,
            currency=body.currency,
            occurred_at=body.occurred_at,
            metadata=body.metadata,
        )
    )
    return IngestTransactionResponse(
        transaction_id=result.transaction_id,
        status=result.status,
        message=result.message,
    )
