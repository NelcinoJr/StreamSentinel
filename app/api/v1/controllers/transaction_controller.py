"""
Controller FastAPI — borda HTTP.

Paralelo Zend:
  TransactionController
    - ingestAction()  → POST 202 (fila)
    - getAction()     → GET  por id (Finder)
    - listAction()    → GET  por período (Finder)

NÃO acessa Repository/Finder/SQLAlchemy direto — só Use Cases.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import (
    build_get_transaction_use_case,
    build_ingest_use_case,
    build_list_transactions_use_case,
)
from app.api.v1.schemas.transaction_schema import (
    IngestTransactionRequest,
    IngestTransactionResponse,
    TransactionReadResponse,
)
from app.use_cases.get_transaction import GetTransactionUseCase
from app.use_cases.ingest_transaction import (
    IngestTransactionInput,
    IngestTransactionResult,
    IngestTransactionUseCase,
)
from app.use_cases.list_transactions import ListTransactionsUseCase

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post(
    "",
    response_model=IngestTransactionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingestão assíncrona de transação",
)
async def ingest_transaction(
    body: IngestTransactionRequest,
    use_case: IngestTransactionUseCase = Depends(build_ingest_use_case),
) -> IngestTransactionResponse:
    # 1) body já validado pelo Pydantic (Form/InputFilter)
    # 2) chama Service
    # 3) 202 = aceito, Worker grava depois
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


@router.get(
    "/{transaction_id}",
    response_model=TransactionReadResponse,
    summary="Busca transação por ID (leitura / Finder)",
)
async def get_transaction(
    transaction_id: UUID,
    use_case: GetTransactionUseCase = Depends(build_get_transaction_use_case),
) -> TransactionReadResponse:
    # Equivale a getAction($id) no Zend
    row = await use_case.execute(transaction_id)
    if row is None:
        # 404 = recurso não existe (como throw NotFound no ZF)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )
    return TransactionReadResponse(**row)


@router.get(
    "",
    response_model=list[TransactionReadResponse],
    summary="Lista transações por período (Finder / relatório)",
)
async def list_transactions(
    started_at: datetime = Query(..., description="Início do período (ISO)"),
    ended_at: datetime = Query(..., description="Fim do período (ISO)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    use_case: ListTransactionsUseCase = Depends(build_list_transactions_use_case),
) -> list[TransactionReadResponse]:
    # Equivale a listAction com query string no Zend
    rows = await use_case.execute(
        started_at=started_at,
        ended_at=ended_at,
        limit=limit,
        offset=offset,
    )
    return [TransactionReadResponse(**row) for row in rows]
