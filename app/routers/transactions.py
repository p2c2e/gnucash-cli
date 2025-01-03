from fastapi import APIRouter, HTTPException, Path
from piecash import open_book, Transaction, Split
from ..utils import get_book_path
from ..models.transaction import TransactionCreate, TransactionInfo, SplitInfo
from typing import List
from datetime import datetime

router = APIRouter()

@router.get("/", response_model=List[TransactionInfo])
async def list_transactions(book_name: str = Path(..., description="Name of the book")):
    book_path = get_book_path(book_name)
    try:
        with open_book(book_path, readonly=True, open_if_lock=True) as book:
            return [
                TransactionInfo(
                    id=str(tx.guid),
                    currency=tx.currency.mnemonic,
                    description=tx.description,
                    post_date=tx.post_date,
                    enter_date=tx.enter_date,
                    notes=tx.notes,
                    splits=[
                        SplitInfo(
                            id=str(split.guid),
                            account_id=str(split.account.guid),
                            transaction_id=str(tx.guid),
                            value=split.value,
                            quantity=split.quantity,
                            memo=split.memo
                        )
                        for split in tx.splits
                    ]
                )
                for tx in book.transactions
            ]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/", response_model=TransactionInfo)
async def create_transaction(
    transaction: TransactionCreate,
    book_name: str = Path(..., description="Name of the book")
):
    book_path = get_book_path(book_name)
    try:
        with open_book(book_path, readonly=False, open_if_lock=True) as book:
            # Create new transaction
            new_tx = Transaction(
                currency=book.currencies(mnemonic=transaction.currency),
                description=transaction.description,
                post_date=transaction.post_date,
                enter_date=datetime.now(),
                notes=transaction.notes,
                book=book
            )
            
            # Create splits
            splits = []
            for split_data in transaction.splits:
                account = book.accounts(guid=split_data.account_id)
                split = Split(
                    account=account,
                    value=split_data.value,
                    quantity=split_data.quantity if split_data.quantity else split_data.value,
                    transaction=new_tx,
                    memo=split_data.memo
                )
                splits.append(split)
            
            # Verify splits balance
            if sum(s.value for s in splits) != 0:
                raise HTTPException(status_code=400, detail="Transaction splits must balance to zero")
            
            book.flush()
            
            return TransactionInfo(
                id=str(new_tx.guid),
                currency=new_tx.currency.mnemonic,
                description=new_tx.description,
                post_date=new_tx.post_date,
                enter_date=new_tx.enter_date,
                notes=new_tx.notes,
                splits=[
                    SplitInfo(
                        id=str(split.guid),
                        account_id=str(split.account.guid),
                        transaction_id=str(new_tx.guid),
                        value=split.value,
                        quantity=split.quantity,
                        memo=split.memo
                    )
                    for split in new_tx.splits
                ]
            )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
