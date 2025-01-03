from fastapi import APIRouter, HTTPException, Path
from piecash import open_book
from ..utils import get_book_path
from ..models.account import AccountCreate, AccountInfo, AccountType
from typing import List

router = APIRouter()

@router.get("/", response_model=List[AccountInfo])
async def list_accounts(book_name: str = Path(..., description="Name of the book")):
    """List all accounts in the book with detailed metadata"""
    book_path = get_book_path(book_name)
    try:
        with open_book(book_path, readonly=True, open_if_lock=True) as book:
            return [
                AccountInfo(
                    id=str(account.guid),
                    name=account.name,
                    type=account.type,
                    fullname=account.fullname,
                    parent_id=str(account.parent.guid) if account.parent else None,
                    commodity=account.commodity.mnemonic,
                    balance=account.get_balance(),
                    description=account.description,
                    children=[str(child.guid) for child in account.children],
                    placeholder=account.placeholder,
                    hidden=account.hidden,
                    code=account.code,
                    notes=account.notes,
                    last_modified=account.last_modified,
                    commodity_scu=account.commodity_scu,
                    non_std_scu=account.non_std_scu,
                    reconciled_balance=account.get_balance(reconciledonly=True),
                    total_balance=account.get_balance(recurse=True)
                )
                for account in book.accounts
            ]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{account_guid}", response_model=AccountInfo)
async def get_account(
    book_name: str = Path(..., description="Name of the book"),
    account_guid: str = Path(..., description="GUID of the account")
):
    """Get details of a specific account by its GUID"""
    book_path = get_book_path(book_name)
    try:
        with open_book(book_path, readonly=True, open_if_lock=True) as book:
            account = book.accounts(guid=account_guid)
            if not account:
                raise HTTPException(status_code=404, detail="Account not found")
                
            return AccountInfo(
                id=str(account.guid),
                name=account.name,
                type=account.type,
                fullname=account.fullname,
                parent_id=str(account.parent.guid) if account.parent else None,
                commodity=account.commodity.mnemonic,
                balance=account.get_balance(),
                description=account.description,
                children=[str(child.guid) for child in account.children]
            )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/types", response_model=List[str])
async def list_account_types():
    """Get list of valid account types"""
    return [t.value for t in AccountType]

@router.post("/", response_model=AccountInfo)
async def create_account(
    account: AccountCreate,
    book_name: str = Path(..., description="Name of the book")
):
    book_path = get_book_path(book_name)
    try:
        with open_book(book_path, readonly=False, open_if_lock=True) as book:
            if account.parent_name:
                if account.parent_name.lower() == "root account":
                    parent = book.root_account
                else:
                    # Find parent account by name
                    parent = None
                    for acc in book.accounts:
                        if acc.name == account.parent_name:
                            parent = acc
                            break
                    if parent is None:
                        raise HTTPException(status_code=404, detail=f"Parent account '{account.parent_name}' not found")
            else:
                parent = book.root_account
            
            # Create account directly using Account class
            from piecash import Account
            new_account = Account(
                name=account.name,
                type=account.type,
                parent=parent,
                commodity=book.commodities(mnemonic=account.commodity_mnemonic) if account.commodity_mnemonic else book.default_currency,
                description=account.description,
                book=book
            )
            
            return AccountInfo(
                id=str(new_account.guid),
                name=new_account.name,
                type=new_account.type,
                fullname=new_account.fullname,
                parent_id=str(new_account.parent.guid) if new_account.parent else None,
                commodity=new_account.commodity.mnemonic,
                balance=new_account.get_balance(),
                description=new_account.description,
                children=[]
            )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
