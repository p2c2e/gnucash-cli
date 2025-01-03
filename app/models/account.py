from pydantic import BaseModel
from typing import Optional, List
from decimal import Decimal
from enum import Enum
from datetime import datetime

class AccountType(str, Enum):
    ROOT = "ROOT"
    ASSET = "ASSET"
    LIABILITY = "LIABILITY"
    EQUITY = "EQUITY"
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"
    BANK = "BANK"
    CASH = "CASH"
    CREDIT = "CREDIT"
    MUTUAL = "MUTUAL"
    STOCK = "STOCK"
    RECEIVABLE = "RECEIVABLE"
    PAYABLE = "PAYABLE"
    TRADING = "TRADING"

class AccountCreate(BaseModel):
    name: str
    type: str
    parent_name: Optional[str] = None  # Now using account name instead of GUID
    commodity_mnemonic: Optional[str] = None
    description: Optional[str] = None

class AccountInfo(BaseModel):
    id: str
    name: str
    type: str
    fullname: str
    parent_id: Optional[str]
    commodity: str
    balance: Decimal
    description: Optional[str]
    children: List[str] = []
    placeholder: bool
    hidden: bool
    code: Optional[str]
    notes: Optional[str]
    last_modified: Optional[datetime]
    commodity_scu: int
    non_std_scu: bool
    reconciled_balance: Optional[Decimal]
    total_balance: Optional[Decimal]
