"""
Schemas Pydantic v2 — validação na borda da API.

Paralelo Zend:
  Zend\\Form + InputFilter / InputFilterFactory.
  Valida e tipa o request ANTES de chegar no Use Case.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class IngestTransactionRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    external_id: str = Field(min_length=1, max_length=64)
    amount: Decimal = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    occurred_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("currency")
    @classmethod
    def currency_upper(cls, value: str) -> str:
        return value.upper()


class IngestTransactionResponse(BaseModel):
    transaction_id: UUID
    status: str
    message: str


class TransactionReadResponse(BaseModel):
    """
    Read model — o que o GET devolve (JsonModel no Zend).
    Não é a Entity de domínio; é o formato da API de consulta.
    """

    id: str
    external_id: str
    amount: str
    currency: str
    status: str
    occurred_at: str | None
    metadata: dict[str, Any]
    created_at: str | None
