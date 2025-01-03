from fastapi import APIRouter, HTTPException
from piecash import create_book, open_book
from ..utils import get_book_path
from ..models.book import BookCreate, BookOpen, BookInfo
import os

router = APIRouter()

@router.post("/create", response_model=BookInfo)
async def create_new_book(book_data: BookCreate):
    try:
        with create_book(
            sqlite_file=get_book_path(book_data.filename),
            currency=book_data.currency,
            overwrite=book_data.overwrite
        ) as book:
            return BookInfo(
                root_account=book.root_account.name,
                default_currency=book.default_currency.mnemonic,
                num_transactions=len(book.transactions),
                num_accounts=len(book.accounts),
                num_commodities=len(book.commodities)
            )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/open", response_model=BookInfo)
async def open_existing_book(book_data: BookOpen):
    try:
        with open_book(
            sqlite_file=get_book_path(book_data.filename),
            readonly=book_data.readonly,
            open_if_lock=True
        ) as book:
            return BookInfo(
                root_account=book.root_account.name,
                default_currency=book.default_currency.mnemonic,
                num_transactions=len(book.transactions),
                num_accounts=len(book.accounts),
                num_commodities=len(book.commodities)
            )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
