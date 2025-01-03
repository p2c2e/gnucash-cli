from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

class SplitCreate(BaseModel):
    account_id: str
    value: Decimal
    quantity: Optional[Decimal] = None
    memo: Optional[str] = None

class SplitInfo(BaseModel):
    id: str
    account_id: str
    transaction_id: str
    value: Decimal
    quantity: Decimal
    memo: Optional[str]

class TransactionCreate(BaseModel):
    currency: str
    description: str
    post_date: datetime
    splits: List[SplitCreate]
    notes: Optional[str] = None

class TransactionInfo(BaseModel):
    id: str
    currency: str
    description: str
    post_date: datetime
    enter_date: datetime
    splits: List[SplitInfo]
    notes: Optional[str]
