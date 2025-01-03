from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

class BookCreate(BaseModel):
    filename: str
    currency: str = "INR"
    overwrite: bool = False

class BookOpen(BaseModel):
    filename: str
    readonly: bool = True
    open_if_lock: bool = False

class BookInfo(BaseModel):
    root_account: str
    default_currency: str
    num_transactions: int
    num_accounts: int
    num_commodities: int
