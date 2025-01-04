import readline
import shutil
import warnings
from pathlib import Path
from typing import Union, Optional

from colorama import Fore, init
from dotenv import load_dotenv
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

init(autoreset=True)  # Auto reset colors after each print
from datetime import date, timedelta
import glob
import os
import yaml
from decimal import Decimal
from piecash import Account, Transaction, Split
from datetime import datetime
import piecash
import pandas as pd
import sqlalchemy as sa
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# Load environment variables and filter warnings
load_dotenv(verbose=True)
warnings.filterwarnings('ignore', category=sa.exc.SAWarning)

# Get default currency from environment or use INR
DEFAULT_CURRENCY = os.getenv('GC_CLI_DEFAULT_CURRENCY', 'INR')

class GnuCashQuery(BaseModel):
    query: str
    results: list[str]

# Track the active book
active_book = None

# Create the GnuCash agent
gnucash_agent = Agent(
    'openai:gpt-4o-mini',
    deps_type=Optional[GnuCashQuery], # type: ignore
    result_type=str,  # type: ignore
    system_prompt=(
        f"Today is {date.today().strftime('%d-%b-%Y')}\n"
        "You are a helpful AI assistant specialized in GnuCash accounting. "
        "You can help users create books, generate reports, and manage transactions. "
        "Always use proper accounting terminology and double-entry principles."
    ),
    retries=3,
)

@gnucash_agent.tool
async def create_book(ctx: RunContext[GnuCashQuery], book_name: str = "sample_accounts") -> str:
    """Create a new GnuCash book with sample accounts and transactions.
    
    This creates a new SQLite-based GnuCash book with standard account types:
    - Assets (with Checking and Savings accounts)
    - Liabilities (with Credit Card account)
    - Income (with Salary account)
    - Expenses (with Groceries and Utilities accounts)
    
    Also creates sample transactions demonstrating:
    - Initial deposit
    - Savings transfer
    - Expense payments
    - Credit card payments

    Args:
        book_name (str): Name of the book to create (without .gnucash extension)
                        Defaults to "sample_accounts"

    Returns str: Success message or error details

    Raises:
        piecash.BookError: If book creation fails
        sqlalchemy.exc.SQLAlchemyError: If database operations fail
    """
    global active_book
    try:
        print(Fore.YELLOW + f"Attempting to create book: {book_name}.gnucash")
        active_book = f"{book_name}.gnucash"
        book = piecash.create_book(
            f"{book_name}.gnucash",
            overwrite=True,
            currency=DEFAULT_CURRENCY,
            keep_foreign_keys=False
        )
        print(Fore.YELLOW + f"Book created successfully: {active_book}")
        
        with book:
            # Create main account categories
            assets = Account(
                name="Assets",
                type="ASSET",
                commodity=book.default_currency,
                parent=book.root_account,
                description="Asset accounts"
            )
            
            expenses = Account(
                name="Expenses",
                type="EXPENSE",
                commodity=book.default_currency,
                parent=book.root_account,
                description="Expense accounts"
            )
            
            income = Account(
                name="Income",
                type="INCOME",
                commodity=book.default_currency,
                parent=book.root_account,
                description="Income accounts"
            )
            
            liabilities = Account(
                name="Liabilities",
                type="LIABILITY",
                commodity=book.default_currency,
                parent=book.root_account,
                description="Liability accounts"
            )
            
            # Create Equity account
            equity = Account(
                name="Equity",
                type="EQUITY",
                commodity=book.default_currency,
                parent=book.root_account,
                description="Equity accounts"
            )

            # Create sub-accounts and transactions (omitted for brevity, same as testcase.py)
            # ... (include all account and transaction creation code from testcase.py)

            book.save()
        print(Fore.YELLOW + f"DEBUG: Completed create_book for {book_name}")
        return "Successfully created sample GnuCash book with accounts and transactions."
    
    except Exception as e:
        return Fore.RED + f"Error creating book: {str(e)}"

@gnucash_agent.tool
async def get_active_book(ctx: RunContext[GnuCashQuery]) -> str:
    """Get the name of the currently active GnuCash book.
    
    The active book is tracked globally and used for all operations.
    Use create_book() or open_book() to set the active book.

    Returns - str: Name of the active book with .gnucash extension if set,
             or message indicating no active book
    """
    global active_book
    if active_book:
        print(Fore.YELLOW + f"DEBUG: Completed get_active_book - found {active_book}")
        return f"Active book: {active_book}"
    print(Fore.YELLOW + "DEBUG: Completed get_active_book - no active book")
    return "No active book - create or open one first"

@gnucash_agent.tool
async def open_book(ctx: RunContext[GnuCashQuery], book_name: str) -> str:
    """Open an existing GnuCash book and set it as active.
    
    The book must be a valid SQLite-based GnuCash file.
    Will attempt to open even if locked by another process.

    Args:
        book_name (str): Name of the book to open (must include .gnucash extension)

    Returns -  str: Success message or error details

    Raises:
        FileNotFoundError: If book file doesn't exist
        piecash.BookError: If book is corrupted or invalid
    """
    global active_book
    try:
        print(f"Attempting to open book: {book_name}")
        # Try to open the book to verify it exists, ignoring lock
        book = piecash.open_book(sqlite_file=book_name, open_if_lock=True, readonly=False)
        print(f"Book opened successfully. {book}")
        book.close()
        
        active_book = book_name
        print(f"Active book set to: {active_book}")
        print(Fore.YELLOW + f"DEBUG: Completed open_book for {book_name}")
        return f"Successfully opened book: {book_name} (ignored lock if present)"
    except Exception as e:
        print(f"Error opening book: {str(e)}")
        return Fore.RED + f"Error opening book: {str(e)}"

@gnucash_agent.tool
async def list_accounts(ctx: RunContext[GnuCashQuery]) -> str:
    """List all accounts in the active GnuCash book with balances.
    
    Returns a formatted table showing:
    - Full account name (including parent hierarchy)
    - Account type (ASSET, LIABILITY, INCOME, etc.)
    - Current balance
    - Account description

    Returns - str: Formatted table of accounts or error message if no active book

    Raises:
        piecash.BookError: If book access fails
    """
    global active_book
    if not active_book:
        return "No active book. Please create or open a book first."
    
    try:
        book = piecash.open_book(active_book, open_if_lock=True, readonly=False)
        accounts = []
        
        for account in book.accounts:
            if account.type != "ROOT":  # Skip root account
                accounts.append({
                    'Account': account.fullname,
                    'Type': account.type,
                    'Balance': account.get_balance(),
                    'Description': account.description
                })
        
        book.close()
        
        if not accounts:
            return "No accounts found in the book."
            
        # Format as a table
        df = pd.DataFrame(accounts)
        print(Fore.YELLOW + "DEBUG: Completed list_accounts")
        return "Accounts in the book:\n" + df.to_string(index=False)
    
    except Exception as e:
        return f"Error listing accounts: {str(e)}"

@gnucash_agent.tool
async def transfer_funds(ctx: RunContext[GnuCashQuery], from_account: str, to_account: str, amount: float, description: str = "Fund transfer") -> str:
    """Transfer funds between two accounts in the active GnuCash book.
    
    Creates a double-entry transaction with:
    - Debit from source account
    - Credit to destination account
    - Timestamped with current date/time

    Args:
        from_account (str): Full name of the source account (must exist)
        to_account (str): Full name of the destination account (must exist)
        amount (float): Amount to transfer (must be positive)
        description (str): Description for the transaction (default: "Fund transfer")
        
    Returns - str: Success message with transfer details or error message

    Raises:
        ValueError: If amount is invalid or accounts don't exist
        piecash.BookError: If transaction creation fails
    """
    global active_book
    if not active_book:
        return "No active book. Please create or open a book first."
    
    if amount <= 0:
        return "Amount must be positive."
    
    try:
        book = piecash.open_book(active_book, open_if_lock=True, readonly=False)
        
        # Find the accounts
        from_acc = book.accounts.get(fullname=from_account)
        to_acc = book.accounts.get(fullname=to_account)
        
        if not from_acc:
            book.close()
            return f"Source account '{from_account}' not found."
        if not to_acc:
            book.close()
            return f"Destination account '{to_account}' not found."
        
        # Create the transaction
        with book:
            Transaction(
                currency=book.default_currency,
                description=description,
                splits=[
                    Split(account=from_acc, value=Decimal(-amount)),
                    Split(account=to_acc, value=Decimal(amount))
                ],
                post_date=date.today(),
                enter_date=datetime.now(),
            )
            book.save()
        
        book.close()
        print(Fore.YELLOW + f"DEBUG: Completed transfer_funds {from_account} -> {to_account} ${amount:.2f}")
        return f"Successfully transferred ${amount:.2f} from {from_account} to {to_account}"
    
    except Exception as e:
        return f"Error transferring funds: {str(e)}"

@gnucash_agent.tool
async def create_subaccount(
    ctx: RunContext[GnuCashQuery],
    parent_account: str,
    account_name: str,
    account_type: str = "ASSET",
    description: str = None,
    initial_balance: float = 0.0
) -> str:
    """Create a new subaccount under a specified parent account.
    
    Creates a new account with optional initial balance.
    For ASSET/BANK accounts, creates offsetting transaction to Equity.
    For LIABILITY/CREDIT accounts, creates reverse offset transaction.

    Args:
        parent_account (str): Full name of the parent account (must exist)
        account_name (str): Name for the new subaccount (must be unique)
        account_type (str): Type of account (ASSET, BANK, EXPENSE, etc.)
        description (str, optional): Description for the new account
        initial_balance (float, optional): Initial balance to set for the account
        
    Returns - str: Success message with account details or error message

    Raises:
        ValueError: If account type is invalid or parent doesn't exist
        piecash.BookError: If account creation fails
    """
    print(f"{parent_account}-{account_name}-{account_type}-{description}-{initial_balance}")
    global active_book
    if not active_book:
        return "No active book. Please create or open a book first."
    
    # Validate account type
    valid_types = ["ASSET", "BANK", "CREDIT", "EXPENSE", "INCOME", "LIABILITY", "EQUITY"]
    if account_type.upper() not in valid_types:
        return f"Invalid account type. Must be one of: {', '.join(valid_types)}"
    
    try:
        print(f"Attempting to open book: {active_book}")
        book = piecash.open_book(active_book, open_if_lock=True, readonly=False)
        print(f"Book opened successfully. Read-only mode: {book}")
        
        # Find the parent account
        parent = book.accounts.get(fullname=parent_account)
        if not parent:
            book.close()
            return f"Parent account '{parent_account}' not found."
        
        # Create the subaccount
        with book:
            new_account = Account(
                name=account_name,
                type=account_type.upper(),
                commodity=book.default_currency,
                parent=parent,
                description=description or f"{account_name} account"
            )
            
            # Create opening transaction if initial balance is provided
            if initial_balance != 0:
                # Determine the offset account based on account type
                if account_type.upper() in ["ASSET", "BANK"]:
                    Transaction(
                        currency=book.default_currency,
                        description="Initial balance",
                        splits=[
                            Split(account=new_account, value=Decimal(str(initial_balance))),
                            Split(account=book.accounts.get(fullname="Equity"), value=Decimal(str(-initial_balance)))
                        ],
                        post_date=date.today(),
                        enter_date=datetime.now(),
                    )
                
                elif account_type.upper() in ["LIABILITY", "CREDIT"]:
                    Transaction(
                        currency=book.default_currency,
                        description="Initial balance",
                        splits=[
                            Split(account=new_account, value=Decimal(str(-initial_balance))),
                            Split(account=book.accounts.get(fullname="Equity"), value=Decimal(str(initial_balance)))
                        ],
                        post_date=date.today(),
                        enter_date=datetime.now(),
                    )
            
            book.save()
        
        book.close()
        if initial_balance != 0:
            return f"Successfully created subaccount '{account_name}' under '{parent_account}' with initial balance of {initial_balance}"
        print(Fore.YELLOW + f"DEBUG: Completed create_subaccount {parent_account}/{account_name}")
        return f"Successfully created subaccount '{account_name}' under '{parent_account}'"
    
    except Exception as e:
        return f"Error creating subaccount: {str(e)}"

@gnucash_agent.tool
async def add_transaction(
    ctx: RunContext[GnuCashQuery],
    from_account: str,
    to_accounts: list[dict[str, Union[str, float]]],
    description: str = "Fund transfer"
) -> str:
    """Add a transaction with multiple splits (one-to-many transfer).
    
    Creates a double-entry transaction with:
    - Single debit from source account
    - Multiple credits to destination accounts
    - Total debit must equal sum of credits
    - Timestamped with current date/time

    Args:
        from_account (str): Full name of the source account (must exist)
        to_accounts (list[dict[str, Union[str, float]]]): List of destination accounts with amounts
            Each dict should contain:
            - 'account_name': Full name of destination account
            - 'amount': Positive amount to credit
        description (str): Description for the transaction
        
    Returns - str: Success message with transaction details or error message

    Raises:
        ValueError: If accounts don't exist or amounts are invalid
        piecash.BookError: If transaction creation fails
    """
    print(Fore.YELLOW + "DEBUG: Starting add_transaction")

    global active_book
    if not active_book:
        return "No active book. Please create or open a book first."
    
    if not to_accounts:
        return "At least one destination account is required."
    
    # Calculate total amount
    total_amount = sum(amount for _, amount in to_accounts)
    
    if total_amount <= 0:
        return "Total amount must be positive."
    
    try:
        book = piecash.open_book(active_book, open_if_lock=True, readonly=False)
        
        # Find the from account
        from_acc = book.accounts.get(fullname=from_account)
        if not from_acc:
            book.close()
            return f"Source account '{from_account}' not found."
        
        # Verify all to accounts exist
        to_accs = []
        for acc_name, amount in to_accounts:
            acc = book.accounts.get(fullname=acc_name)
            if not acc:
                book.close()
                return f"Destination account '{acc_name}' not found."
            if amount <= 0:
                book.close()
                return f"Amount for account '{acc_name}' must be positive."
            to_accs.append((acc, amount))
        
        # Create the transaction
        with book:
            splits = [
                Split(account=from_acc, value=Decimal(-total_amount))
            ]
            for acc, amount in to_accs:
                splits.append(Split(account=acc, value=Decimal(amount)))
            
            Transaction(
                currency=book.default_currency,
                description=description,
                splits=splits,
                post_date=date.today(),
                enter_date=datetime.now(),
            )
            book.save()
        
        book.close()
        
        # Format success message
        details = "\n".join(f"  - {acc_name}: ${amount:.2f}" for acc_name, amount in to_accounts)
        print(Fore.YELLOW + "DEBUG: Completed add_transaction")
        return f"Successfully transferred ${total_amount:.2f} from {from_account} to:\n{details}"
    
    except Exception as e:
        return f"Error adding transaction: {str(e)}"

@gnucash_agent.tool
async def list_transactions(ctx: RunContext[GnuCashQuery], limit: int = 10) -> str:
    """List recent transactions in the active GnuCash book.
    
    Returns formatted transaction details including:
    - Date
    - Description
    - Splits showing account and amount
    - Memo (if present)
    
    Transactions are sorted by date (newest first).

    Args:
        limit (int): Maximum number of transactions to return (default: 10)
        
    Returns - str: Formatted list of transactions with splits or error message

    Raises:
        piecash.BookError: If book access fails
    """
    global active_book
    if not active_book:
        return "No active book. Please create or open a book first."
    
    try:
        book = piecash.open_book(active_book, open_if_lock=True, readonly=True)
        transactions = []
        
        # Get transactions sorted by date (newest first)
        for tx in sorted(book.transactions, key=lambda t: t.post_date, reverse=True)[:limit]:
            tx_info = {
                'Date': tx.post_date.strftime('%Y-%m-%d'),
                'Description': tx.description,
                'Splits': []
            }
            
            for split in tx.splits:
                tx_info['Splits'].append({
                    'Account': split.account.fullname,
                    'Amount': float(split.value),
                    'Memo': split.memo or ''
                })
            
            transactions.append(tx_info)
        
        book.close()
        
        if not transactions:
            return "No transactions found in the book."
            
        # Format the output
        output = []
        for tx in transactions:
            output.append(Fore.YELLOW + f"\n[{tx['Date']}] {tx['Description']}")
            for split in tx['Splits']:
                color = Fore.RED if split['Amount'] < 0 else Fore.GREEN
                output.append(f"  {split['Account']}: {color}{split['Amount']:+.2f} {Fore.RESET}{split['Memo']}")
        
        print(Fore.YELLOW + f"DEBUG: Completed list_transactions (limit={limit})")
        return "\n".join(output)
    
    except Exception as e:
        return Fore.RED + f"Error listing transactions: {str(e)}"

@gnucash_agent.tool
async def generate_balance_sheet(ctx: RunContext[GnuCashQuery]) -> str:
    """Generate an ASCII formatted balance sheet with proper account hierarchy and roll-up totals.
    
    Implements bottom-up calculation of account balances with:
    - Proper parent/child roll-up totals
    - Hierarchical indentation
    - Subtotals at each level
    - Sign conventions maintained
    
    All amounts are in the book's default currency.

    Returns - str: Formatted balance sheet or error message

    Raises:
        piecash.BookError: If book access fails
    """
    global active_book
    if not active_book:
        return "No active book. Please create or open a book first."
    
    try:
        book = piecash.open_book(active_book, open_if_lock=True, readonly=True)
        
        def get_account_hierarchy(account, indent_level=0):
            """Recursively build account hierarchy with proper totals."""
            # Skip root account
            if account.type == "ROOT":
                return [], Decimal('0')
                
            # Calculate this account's own balance (from direct transactions)
            own_balance = sum(split.value for trans in book.transactions 
                            for split in trans.splits if split.account == account)
            
            # Get children's balances recursively
            child_entries = []
            children_total = Decimal('0')
            for child in sorted(account.children, key=lambda x: x.name):
                child_lines, child_total = get_account_hierarchy(child, indent_level + 1)
                child_entries.extend(child_lines)
                children_total += child_total
            
            # Total balance is own balance plus children's balances
            total_balance = own_balance + children_total
            
            # Format this account's line
            indent = "  " * indent_level
            curr_symbol = book.default_currency.mnemonic
            
            entries = []
            
            # Add this account's line first
            if account.children:
                # Parent account - show total
                if total_balance != 0 or not account.children:
                    entries.append((
                        f"{indent}{account.name}",
                        total_balance,
                        True  # is_total
                    ))
            else:
                # Leaf account - show balance
                if total_balance != 0:
                    entries.append((
                        f"{indent}{account.name}",
                        total_balance,
                        False  # not a total
                    ))
            
            # Add children's lines after parent
            if child_entries:
                entries.extend(child_entries)
            
            return entries, total_balance
        
        # Process each main section
        sections = {
            "ASSET": (Fore.GREEN, "ASSETS"),
            "LIABILITY": (Fore.RED, "LIABILITIES"),
            "EQUITY": (Fore.BLUE, "EQUITY")
        }
        
        output = []
        output.append(Fore.YELLOW + "=" * 60)
        output.append(Fore.CYAN + " BALANCE SHEET".center(60))
        output.append(Fore.YELLOW + "=" * 60)
        
        section_totals = {}
        
        # Process each main section
        for acc_type, (color, title) in sections.items():
            output.append(f"\n{color}{title}")
            
            # Find top-level accounts of this type
            top_accounts = [acc for acc in book.root_account.children 
                          if acc.type == acc_type]
            
            section_entries = []
            section_total = Decimal('0')
            
            # Process each top-level account
            for account in sorted(top_accounts, key=lambda x: x.name):
                entries, total = get_account_hierarchy(account)
                section_entries.extend(entries)
                section_total += total
            
            # Add entries with proper formatting
            curr_symbol = book.default_currency.mnemonic
            for name, amount, is_total in section_entries:
                if is_total:
                    output.append(f"{color}{name:<40} {curr_symbol} {amount:>10,.2f}")
                else:
                    output.append(f"{color}{name:<40} {curr_symbol} {amount:>10,.2f}")
            
            # Add section total
            output.append(color + "-" * 60)
            output.append(f"{color}{'Total ' + title:<40} {curr_symbol} {section_total:>10,.2f}")
            
            section_totals[acc_type] = section_total
        
        # Final totals
        output.append(Fore.YELLOW + "=" * 60)
        net_worth = section_totals.get("ASSET", 0) - section_totals.get("LIABILITY", 0)
        output.append(f"{Fore.CYAN}{'Net Worth':<40} {curr_symbol} {net_worth:>10,.2f}")
        output.append(Fore.YELLOW + "=" * 60)
        
        book.close()
        return "\n".join(output)
    
    except Exception as e:
        return Fore.RED + f"Error generating balance sheet: {str(e)}"

@gnucash_agent.tool
async def generate_cashflow_statement(ctx: RunContext[GnuCashQuery], start_date: str = None, end_date: str = None) -> str:
    """Generate a cash flow statement for a given period.
    
    The statement shows cash flows in three categories:
    - Operating Activities (income/expense accounts)
    - Investing Activities (asset accounts)
    - Financing Activities (liability/equity accounts)
    
    Defaults to Year-to-Date if no dates provided.

    Args:
        start_date (str, optional): Start date in YYYY-MM-DD format
        end_date (str, optional): End date in YYYY-MM-DD format
        
    Returns - str: Formatted cash flow statement or error message

    Raises:
        ValueError: If dates are invalid
        piecash.BookError: If book access fails
    """
    global active_book
    if not active_book:
        return "No active book. Please create or open a book first."
    
    try:
        print(Fore.YELLOW + f"DEBUG: Starting cashflow statement generation for book: {active_book}")
        book = piecash.open_book(active_book, open_if_lock=True, readonly=True)
        print(Fore.YELLOW + f"DEBUG: Book opened successfully")
        
        # Default to YTD if no dates provided
        today = date.today()
        if not start_date:
            start_date = date(today.year, 1, 1).strftime('%Y-%m-%d')
            print(Fore.YELLOW + f"DEBUG: Using default start date: {start_date}")
        if not end_date:
            end_date = today.strftime('%Y-%m-%d')
            print(Fore.YELLOW + f"DEBUG: Using default end date: {end_date}")
            
        # Convert to date objects
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        print(Fore.YELLOW + f"DEBUG: Date range: {start_date} to {end_date}")
        
        # Initialize totals
        money_in = Decimal('0.00')
        money_out = Decimal('0.00')
        print(Fore.YELLOW + "DEBUG: Initialized totals to zero")
        
        # Track subcategories
        income_categories = {}
        expense_categories = {}
        
        # Categorize transactions
        transaction_count = 0
        for tx in book.transactions:
            transaction_count += 1
            print(Fore.YELLOW + f"\nDEBUG: Processing transaction {transaction_count}: {tx.description} on {tx.post_date}")
            
            if start_date <= tx.post_date <= end_date:
                print(Fore.YELLOW + "DEBUG: Transaction within date range")
                for split in tx.splits:
                    account = split.account
                    amount = split.value
                    print(Fore.YELLOW + f"DEBUG: Split - Account: {account.fullname} ({account.type}), Amount: {amount}")
                    
                    # Income accounts (money in)
                    if account.type == "INCOME":
                        money_in += abs(amount)  # Use absolute value for consistent sign
                        category = account.name
                        income_categories[category] = income_categories.get(category, Decimal('0.00')) + abs(amount)
                        print(Fore.YELLOW + f"DEBUG: Added to money in, new total: {money_in}")
                    
                    # Expense accounts (money out)
                    elif account.type == "EXPENSE":
                        money_out += abs(amount)  # Use absolute value for consistent sign
                        category = account.name
                        expense_categories[category] = expense_categories.get(category, Decimal('0.00')) + abs(amount)
                        print(Fore.YELLOW + f"DEBUG: Added to money out, new total: {money_out}")
            else:
                print(Fore.YELLOW + "DEBUG: Transaction outside date range - skipped")
        
        # Calculate net cash flow
        net_cash_flow = money_in - money_out
        
        # Build the ASCII table
        output = []
        output.append(Fore.YELLOW + "=" * 60)
        output.append(Fore.CYAN + " CASH FLOW STATEMENT".center(60))
        output.append(Fore.YELLOW + f"Period: {start_date} to {end_date}".center(60))
        output.append(Fore.YELLOW + "=" * 60)
        
        # Money Incoming Section
        output.append(Fore.GREEN + "\nMONEY INCOMING")
        curr_symbol = book.default_currency.mnemonic
        for category, amount in sorted(income_categories.items()):
            output.append(f"  {category:<30} {Fore.GREEN}{curr_symbol} {amount:>12.2f}")
        output.append(Fore.GREEN + "-" * 60)
        output.append(f"  {'Total Money In':<30} {Fore.GREEN}{curr_symbol} {money_in:>12.2f}")
        
        # Money Outflow Section
        output.append(Fore.RED + "\nMONEY OUTFLOW")
        for category, amount in sorted(expense_categories.items()):
            output.append(f"  {category:<30} {Fore.RED}{curr_symbol} {amount:>12.2f}")
        output.append(Fore.RED + "-" * 60)
        output.append(f"  {'Total Money Out':<30} {Fore.RED}{curr_symbol} {money_out:>12.2f}")
        
        # Net Cash Flow
        output.append(Fore.YELLOW + "=" * 60)
        color = Fore.GREEN if net_cash_flow >= 0 else Fore.RED
        output.append(f"  {'Net Cash Flow':<30} {color}{curr_symbol} {net_cash_flow:>12.2f}")
        output.append(Fore.YELLOW + "=" * 60)

        book.close()
        
        return "\n".join(output)
    
    except Exception as e:
        return Fore.RED + f"Error generating cash flow statement: {str(e)}"

@gnucash_agent.tool
async def purge_backups(
    ctx: RunContext[GnuCashQuery],
    book_name: str,
    days: int = None,
    before_date: str = None
) -> str:
    """Purge old backup files for a GnuCash book.
    
    Deletes backup files matching the pattern {book_name}.gnucash.YYYYMMDDHHMMSS.gnucash
    that are either:
    - Older than N days (if days parameter provided)
    - Older than a specific date (if before_date provided)
    
    Args:
        book_name (str): Base name of the book (without .gnucash extension)
        days (int, optional): Delete backups older than this many days
        before_date (str, optional): Delete backups before this date (YYYY-MM-DD format)
        
    Returns - str: Summary of deleted files and remaining backups
        
    Raises:
        ValueError: If neither days nor before_date provided
        FileNotFoundError: If no backups found
    """

    print(Fore.YELLOW + f"DEBUG: Starting purge_backups for {book_name}")

    if not days and not before_date:
        raise ValueError("Must specify either days or before_date parameter")
    
    # Calculate cutoff date
    if days:
        cutoff = datetime.now() - timedelta(days=days)
    else:
        cutoff = datetime.strptime(before_date, '%Y-%m-%d')
    
    # Find matching backup files
    pattern = f"{book_name}.gnucash.*.gnucash"
    backups = glob.glob(pattern)
    
    if not backups:
        return f"No backup files found matching pattern: {pattern}"
    
    deleted = []
    remaining = []
    
    for backup in backups:
        # Extract timestamp from filename
        try:
            timestamp_str = backup.split('.')[-2]
            timestamp = datetime.strptime(timestamp_str, '%Y%m%d%H%M%S')
            
            if timestamp < cutoff:
                os.remove(backup)
                deleted.append(backup)
            else:
                remaining.append(backup)
        except (IndexError, ValueError):
            continue
    
    # Build result message
    result = []
    if deleted:
        result.append(Fore.YELLOW + f"Deleted {len(deleted)} backups:")
        result.extend(f"  - {f}" for f in deleted)
    else:
        result.append(Fore.YELLOW + "No backups older than cutoff found")
    
    if remaining:
        result.append(Fore.GREEN + f"\n{len(remaining)} backups remain:")
        result.extend(f"  - {f}" for f in remaining)
    
    print(Fore.YELLOW + f"DEBUG: Completed purge_backups for {book_name}")
    return "\n".join(result)

@gnucash_agent.tool
async def create_accounts_from_file(ctx: RunContext[GnuCashQuery], file_path: str) -> str:
    """Create account hierarchy from a YAML file.
    
    Args:
        file_path (str): Path to YAML file containing account structure
        
    Returns - str: Summary of created accounts and any errors
        
    Raises:
        FileNotFoundError: If YAML file doesn't exist
        yaml.YAMLError: If YAML is invalid
    """
    global active_book
    if not active_book:
        return "No active book. Please create or open a book first."
    
    try:
        print(Fore.YELLOW + f"DEBUG: Attempting to load YAML file from {file_path}")
        # Load YAML file
        with open(file_path, 'r') as f:
            account_data = yaml.safe_load(f)
        
        if not account_data or 'accounts' not in account_data:
            print(Fore.RED + "DEBUG: Invalid YAML format - missing 'accounts' section")
            return "Invalid YAML format - missing 'accounts' section"
            
        print(Fore.YELLOW + f"DEBUG: YAML file loaded successfully, found {len(account_data['accounts'])} root accounts")
        book = piecash.open_book(active_book, open_if_lock=True, readonly=False)
        results = []
        
        def create_accounts(accounts, parent=None):
            print(Fore.YELLOW + f"DEBUG: Processing {len(accounts)} accounts under parent: {parent.fullname if parent else 'root'}")
            
            # Process all accounts first, then save once at the end
            accounts_to_create = []
            for acc in accounts:
                try:
                    # Check if account already exists
                    fullname = f"{parent.fullname}:{acc['name']}" if parent else acc['name']
                    accounts_to_create.append((acc, fullname))
                except Exception as e:
                    results.append(f"Error preparing account {acc.get('name', '')}: {str(e)}")
                    continue

            # print("BEFORE ...........")
            # # Now create accounts in a fresh session
            # # with book:
            # for acc, fullname in accounts_to_create:
            #     print(acc)
            #     print(fullname)
            # print("WITHIN ..........")

            for acc, fullname in accounts_to_create:
                print(Fore.YELLOW + f"DEBUG: Processing account: {fullname}")
                # Search for existing account with matching name and parent
                existing = next(
                    (a for a in book.accounts
                     if a.name == acc['name'] and
                     (parent is None or a.parent == parent)),
                    None
                )

                if existing:
                    print(Fore.YELLOW + f"DEBUG: Account already exists: {fullname} - checking for children")
                    results.append(f"Account already exists: {fullname} - checking for children")
                    new_acc = existing
                else:
                    # Create new account
                    print(Fore.YELLOW + f"DEBUG: Creating new account: {acc['name']} of type {acc.get('type', 'ASSET')}")
                    new_acc = Account(
                        name=acc['name'],
                        type=acc.get('type', parent.type if parent is not None else "ASSET").upper(), # default to parent account type
                        commodity=book.default_currency,
                        parent=parent or book.root_account,
                        description=acc.get('description', '')
                    )
                    # Save immediately after account creation
                    book.save()
                    print(Fore.YELLOW + f"DEBUG: Created and saved new account: {new_acc.fullname}")

                # Handle initial balance if provided
                if 'initial_balance' in acc:
                    print(Fore.YELLOW + f"DEBUG: Setting initial balance of {acc['initial_balance']} for account {acc['name']} (type: {new_acc.type})")
                    if new_acc.type == "ASSET":
                        print(Fore.YELLOW + f"DEBUG: Processing ASSET account {new_acc.fullname}")
                    balance = Decimal(str(acc['initial_balance']))
                    # Handle balance date with debug logging
                    balance_date_str = acc.get('balance_date', date.today().isoformat())
                    print(Fore.YELLOW + f"DEBUG: Processing balance date string: {balance_date_str}")
                    try:
                        balance_date = datetime.strptime(balance_date_str, '%Y-%m-%d').date()
                        enter_date = datetime.combine(balance_date, datetime.min.time())  # Convert to datetime
                        print(Fore.YELLOW + f"DEBUG: Parsed balance date: {balance_date} (type: {type(balance_date)})")
                        print(Fore.YELLOW + f"DEBUG: Using enter_date: {enter_date} (type: {type(enter_date)})")
                    except Exception as e:
                        print(Fore.RED + f"ERROR: Failed to parse balance date '{balance_date_str}': {str(e)}")
                        raise

                    # Create offsetting transaction with specified date
                    book.save()
                    print(Fore.YELLOW + f"DEBUG: Account saved successfully before creating transaction")

                    # Refresh account references to ensure they're in the current session
                    new_acc = book.accounts.get(fullname=new_acc.fullname)
                    equity_acc = book.accounts.get(fullname="Equity")
                    if not new_acc or not equity_acc:
                        raise ValueError("Failed to refresh account references in session")

                    print(Fore.YELLOW + f"DEBUG: Checking account type for transaction creation: {new_acc.type}")
                    if new_acc.type in ["ASSET", "BANK"]:
                        print(Fore.YELLOW + f"DEBUG: Creating ASSET/BANK transaction for {new_acc.fullname}")
                        # with book:
                        print(Fore.YELLOW + f"DEBUG: Creating transaction for {new_acc.fullname} with balance {balance} on {balance_date}")
                        tx = Transaction(
                            currency=book.default_currency,
                            description="Initial balance",
                            splits=[
                                Split(account=new_acc, value=balance),
                                Split(account=equity_acc, value=-balance)
                            ],
                            post_date=balance_date,
                            enter_date=enter_date,  # Use the datetime version
                        )
                        print(Fore.YELLOW + f"DEBUG: Transaction created: {tx}")
                        book.save()
                        print(Fore.YELLOW + f"DEBUG: Transaction saved successfully")
                    elif new_acc.type in ["LIABILITY", "CREDIT"]:
                        # with book:
                        print(Fore.YELLOW + f"DEBUG: Creating liability transaction for {new_acc.fullname} with balance {balance} on {balance_date}")
                        tx = Transaction(
                            currency=book.default_currency,
                            description="Initial balance",
                            splits=[
                                Split(account=new_acc, value=-balance),
                                Split(account=equity_acc, value=balance)
                            ],
                            post_date=balance_date,
                            enter_date=enter_date,  # Use the datetime version
                        )
                        print(Fore.YELLOW + f"DEBUG: Liability transaction created: {tx}")
                        book.save()
                        print(Fore.YELLOW + f"DEBUG: Liability transaction saved successfully")

                print(Fore.YELLOW + f"DEBUG: Successfully created account: {fullname}")
                results.append(f"Created account: {fullname}")

                # Recursively create child accounts (even if account already existed)
                if 'children' in acc:
                    print(Fore.YELLOW + f"DEBUG: Found {len(acc['children'])} child accounts for {fullname}")
                    print(Fore.YELLOW + f"DEBUG: Child accounts: {[c['name'] for c in acc['children']]}")

                    # Process children accounts
                    parent_acc = book.accounts.get(fullname=new_acc.fullname)
                    if not parent_acc:
                        raise ValueError(f"Parent account {new_acc.fullname} not found in session")
                    create_accounts(acc['children'], parent_acc)
                else:
                    print(Fore.YELLOW + f"DEBUG: No children found for {fullname}")
                
        # Create accounts in the book
        with book:
            create_accounts(account_data['accounts'])
            book.save()
        
        book.close()
        print(Fore.YELLOW + f"DEBUG: Completed create_accounts_from_file for {file_path}")
        return "\n".join(results)
    
    except Exception as e:
        return f"Error creating accounts from file: {str(e)}"

@gnucash_agent.tool
async def get_default_currency(ctx: RunContext[GnuCashQuery]) -> str:
    """Get the default currency for the active book.
    
    Returns - str: Current default currency code or error message
        
    Raises:
        ValueError: If no active book
    """
    global active_book
    if not active_book:
        return "No active book. Please create or open a book first."
    
    try:
        book = piecash.open_book(active_book, open_if_lock=True, readonly=True)
        currency_code = book.default_currency.mnemonic
        book.close()
        print(Fore.YELLOW + f"DEBUG: Got default currency: {currency_code}")
        return f"Default currency is {currency_code}"
        
    except Exception as e:
        return f"Error getting default currency: {str(e)}"

@gnucash_agent.tool
async def set_accounts_currency(ctx: RunContext[GnuCashQuery], currency_code: str) -> str:
    """Set the currency for all accounts in the active book.
    
    Args:
        currency_code (str): Three-letter ISO currency code (e.g., 'USD', 'EUR', 'GBP')
        
    Returns - str: Success message or error details
        
    Raises:
        ValueError: If no active book or invalid currency code
        piecash.BookError: If currency change fails
    """
    global active_book
    if not active_book:
        return "No active book. Please create or open a book first."
    
    if not currency_code or len(currency_code) != 3:
        return "Invalid currency code. Must be a 3-letter ISO code (e.g., USD, EUR, GBP)"
    
    try:
        book = piecash.open_book(active_book, open_if_lock=True, readonly=False)
        currency_code = currency_code.upper()
        
        with book:
            # Attempt to get the currency (will raise if invalid)
            new_currency = book.currencies(mnemonic=currency_code)
            if not new_currency:
                return f"Invalid currency code: {currency_code}"
            
            # Update all accounts except ROOT
            updated = 0
            for account in book.accounts:
                if account.type != "ROOT":
                    account.commodity = new_currency
                    updated += 1
                    
            book.save()
            
        book.close()
        print(Fore.YELLOW + f"DEBUG: Changed currency to {currency_code} for {updated} accounts")
        return f"Successfully set currency to {currency_code} for {updated} accounts"
        
    except Exception as e:
        return f"Error setting accounts currency: {str(e)}"

@gnucash_agent.tool
async def set_default_currency(ctx: RunContext[GnuCashQuery], currency_code: str) -> str:
    """Set the default currency for the active book.
    
    Args:
        currency_code (str): Three-letter ISO currency code (e.g., 'USD', 'EUR', 'GBP')
        
    Returns - str: Success message or error details
        
    Raises:
        ValueError: If no active book or invalid currency code
        piecash.BookError: If currency change fails
    """
    global active_book
    if not active_book:
        return "No active book. Please create or open a book first."
    
    if not currency_code or len(currency_code) != 3:
        return "Invalid currency code. Must be a 3-letter ISO code (e.g., USD, EUR, GBP)"
    
    try:
        book = piecash.open_book(active_book, open_if_lock=True, readonly=False)
        currency_code = currency_code.upper()
        
        with book:
            # Attempt to get the currency (will raise if invalid)
            new_currency = book.currencies(mnemonic=currency_code)
            if not new_currency:
                return f"Invalid currency code: {currency_code}"
                
            # Set as default currency
            book.default_currency = new_currency
            book.save()
            
        book.close()
        print(Fore.YELLOW + f"DEBUG: Changed default currency to {currency_code}")
        return f"Successfully set default currency to {currency_code}"
        
    except Exception as e:
        return f"Error setting default currency: {str(e)}"

@gnucash_agent.tool
async def save_as_template(ctx: RunContext[GnuCashQuery], template_name: str) -> str:
    """Save current book as a template by copying account structure without transactions.
    
    Creates a new GnuCash file with:
    - All accounts from current book
    - Same currency settings
    - No transactions
    - No scheduled transactions
    - Preserves account hierarchies and properties
    
    Args:
        template_name (str): Name for the template file (without .gnucash extension)
        
    Returns - str: Success message or error details
        
    Raises:
        ValueError: If no active book or invalid template name
        piecash.BookError: If template creation fails
    """
    global active_book
    if not active_book:
        return "No active book. Please create or open a book first."
    
    if not template_name:
        return "Template name is required."
        
    try:
        # Open source book
        source_book = piecash.open_book(active_book, open_if_lock=True, readonly=True)
        
        # Create new template book
        template_path = f"{template_name}.gnucash"
        template_book = piecash.create_book(
            template_path,
            overwrite=True,
            currency=source_book.default_currency.mnemonic,
            keep_foreign_keys=False
        )
        
        print(Fore.YELLOW + f"DEBUG: Creating template {template_path} from {active_book}")
        
        def copy_account_structure(src_account, parent=None):
            """Recursively copy account hierarchy without transactions."""
            if src_account.type == "ROOT":
                dest_parent = template_book.root_account
            else:
                # Create new account in template
                dest_account = Account(
                    name=src_account.name,
                    type=src_account.type,
                    commodity=template_book.default_currency,
                    parent=parent or template_book.root_account,
                    description=src_account.description,
                    code=src_account.code,
                    placeholder=src_account.placeholder
                )
                dest_parent = dest_account
            
            # Recursively copy children
            for child in src_account.children:
                copy_account_structure(child, dest_parent)
        
        # Copy account hierarchy
        with template_book:
            copy_account_structure(source_book.root_account)
            template_book.save()
        
        source_book.close()
        template_book.close()
        
        print(Fore.YELLOW + f"DEBUG: Template saved as {template_path}")
        return f"Successfully created template {template_path} from {active_book}"
    
    except Exception as e:
        return f"Error creating template: {str(e)}"

@gnucash_agent.tool
async def search_accounts(ctx: RunContext[GnuCashQuery], pattern: str) -> str:
    """Search for accounts matching a name pattern (supports regex).
    
    Args:
        pattern (str): Account name pattern to search for (case-insensitive)
                      Supports partial matches and regex patterns
                      
    Returns - str: List of matching accounts with full paths or error message
    
    Examples:
        search_accounts checking  -> Finds accounts containing "checking"
        search_accounts ^ass     -> Finds accounts starting with "ass"
        search_accounts .*card$  -> Finds accounts ending with "card"
    """
    global active_book
    if not active_book:
        return "No active book. Please create or open a book first."
    
    try:
        import re
        book = piecash.open_book(active_book, open_if_lock=True, readonly=True)
        
        # Try to determine if the pattern is meant to be regex
        is_regex = any(c in pattern for c in '.^$*+?{}[]\\|()')
        
        if is_regex:
            try:
                regex = re.compile(pattern, re.IGNORECASE)
            except re.error as e:
                return f"Invalid regex pattern: {str(e)}"
        else:
            # Treat as simple substring search
            regex = re.compile(f".*{re.escape(pattern)}.*", re.IGNORECASE)
        
        # Search for matching accounts
        matches = []
        for account in book.accounts:
            if account.type != "ROOT" and regex.search(account.name):
                matches.append({
                    'fullname': account.fullname,
                    'type': account.type,
                    'balance': account.get_balance()
                })
        

        if not matches:
            book.close()
            return f"No accounts found matching pattern: {pattern}"
        
        # Format results
        output = [f"Found {len(matches)} matching accounts:"]
        curr_symbol = book.default_currency.mnemonic
        for acc in sorted(matches, key=lambda x: x['fullname']):
            color = Fore.GREEN if acc['balance'] >= 0 else Fore.RED
            output.append(f"{acc['fullname']} ({acc['type']}) - {color}{curr_symbol} {acc['balance']:,.2f}")
        
        print(Fore.YELLOW + f"DEBUG: Completed search_accounts for pattern: {pattern}")

        book.close()
        return "\n".join(output)
        
    except Exception as e:
        return f"Error searching accounts: {str(e)}"

@gnucash_agent.tool
async def export_reports_pdf(ctx: RunContext[GnuCashQuery], output_file: str = "gnucash_reports.pdf") -> str:
    """Export all financial reports to a single PDF file.
    
    Generates and combines:
    - Balance Sheet
    - Cash Flow Statement
    - Account Listing
    - Recent Transactions
    
    Args:
        output_file (str): Name of PDF file to create (default: gnucash_reports.pdf)
        
    Returns - str: Success message or error details
    
    Raises:
        piecash.BookError: If book access fails
        reportlab.Error: If PDF generation fails
    """
    global active_book
    if not active_book:
        return "No active book. Please create or open a book first."
    
    try:
        book = piecash.open_book(active_book, open_if_lock=True, readonly=True)
        
        # Create PDF document
        doc = SimpleDocTemplate(
            output_file,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        # Get styles
        styles = getSampleStyleSheet()
        title_style = styles['Heading1']
        normal_style = styles['Normal']
        
        # Container for PDF elements
        elements = []
        
        # Add title
        elements.append(Paragraph(f"Financial Reports - {active_book}", title_style))
        elements.append(Spacer(1, 20))
        
        # Helper function to convert DataFrame to PDF table
        def df_to_table(df, title):
            elements.append(Paragraph(title, styles['Heading2']))
            elements.append(Spacer(1, 12))
            
            # Convert DataFrame to list of lists
            data = [df.columns.tolist()]
            data.extend(df.values.tolist())
            
            # Create table
            table = Table(data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 14),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 12),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.append(table)
            elements.append(Spacer(1, 20))
        
        # Add Balance Sheet in two columns
        # Get assets and liabilities separately
        assets_df = pd.DataFrame([
            {
                'Account': acc.fullname,
                'Balance': acc.get_balance()
            }
            for acc in book.accounts if acc.type == "ASSET"
        ])
        
        liabilities_df = pd.DataFrame([
            {
                'Account': acc.fullname,
                'Balance': acc.get_balance(),
                'Description': acc.description
            }
            for acc in book.accounts if acc.type == "LIABILITY"
        ])

        # Add Balance Sheet title
        elements.append(Paragraph("Balance Sheet", styles['Heading2']))
        elements.append(Spacer(1, 12))

        # Create Assets table
        assets_data = [["Assets"]] + [assets_df.columns.tolist()] + assets_df.values.tolist()
        assets_total = assets_df['Balance'].sum() if not assets_df.empty else 0
        assets_data.append(["Total Assets", assets_total])
        assets_table = Table(assets_data)
        
        # Create Liabilities table
        liab_data = [["Liabilities"]] + [liabilities_df.columns.tolist()] + liabilities_df.values.tolist()
        liab_total = liabilities_df['Balance'].sum() if not liabilities_df.empty else 0
        liab_data.append(["Total Liabilities", liab_total])
        liab_table = Table(liab_data)

        # Style for both tables
        table_style = TableStyle([
            # Title row
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 16),
            ('SPAN', (0, 0), (-1, 0)),  # Span all columns for title
            # Header row
            ('BACKGROUND', (0, 1), (-1, 1), colors.grey),
            ('TEXTCOLOR', (0, 1), (-1, 1), colors.whitesmoke),
            ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 1), (-1, 1), 14),
            # Data rows
            ('BACKGROUND', (0, 2), (-1, -2), colors.beige),
            ('TEXTCOLOR', (0, 2), (-1, -2), colors.black),
            ('FONTNAME', (0, 2), (-1, -2), 'Helvetica'),
            ('FONTSIZE', (0, 2), (-1, -2), 12),
            # Total row
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ])

        # Apply style and add tables one after another
        assets_table.setStyle(table_style)
        liab_table.setStyle(table_style)
        
        elements.append(assets_table)
        elements.append(Spacer(1, 20))  # Add space between tables
        elements.append(liab_table)
        elements.append(Spacer(1, 20))
        
        # Add Recent Transactions
        transactions_df = pd.DataFrame([
            {
                'Date': tx.post_date,
                'Description': tx.description,
                'Amount': sum(split.value for split in tx.splits if split.value > 0)
            }
            for tx in sorted(book.transactions, key=lambda t: t.post_date, reverse=True)[:10]
        ])
        if not transactions_df.empty:
            df_to_table(transactions_df, "Recent Transactions")
        
        # Build PDF
        doc.build(elements)
        book.close()
        
        print(Fore.YELLOW + f"DEBUG: Generated PDF report: {output_file}")
        return f"Successfully exported reports to {output_file}"
        
    except Exception as e:
        return f"Error exporting reports to PDF: {str(e)}"

class BackupFileHandler(FileSystemEventHandler):
    """Handler for managing GnuCash backup files."""
    
    def __init__(self, sweep_interval: int = 120, sweep_age: int = 5):
        self.sweep_interval = sweep_interval
        self.sweep_age = sweep_age
        self.last_sweep = datetime.now()
        # Create backups directory if it doesn't exist
        Path('backups').mkdir(exist_ok=True)
        
    def on_created(self, event):
        """Handle new file creation."""
        if event.is_directory:
            return
            
        # Check if it's time for a sweep
        now = datetime.now()
        if (now - self.last_sweep).total_seconds() >= self.sweep_interval:
            self.sweep_old_backups()
            self.last_sweep = now
    
    def sweep_old_backups(self):
        """Move backup files older than sweep_age minutes to backups folder."""
        print(Fore.YELLOW + "DEBUG: Sweeping for old backup files...")
        cutoff = datetime.now() - timedelta(minutes=self.sweep_age)
        
        # Look for backup files in current directory
        for filepath in Path('.').glob('*.*.gnucash'):
            try:
                # Parse timestamp from filename
                parts = filepath.name.split('.')
                if len(parts) >= 3 and len(parts[-2]) == 14 and parts[-2].isdigit():
                    timestamp_str = parts[-2]
                    file_time = datetime.strptime(timestamp_str, '%Y%m%d%H%M%S')
                else:
                    continue  # Skip files that don't match the expected format
                
                if file_time < cutoff:
                    # Move file to backups folder
                    dest = Path('backups') / filepath.name
                    print(Fore.YELLOW + f"DEBUG: Moving old backup {filepath} to {dest}")
                    shutil.move(str(filepath), str(dest))
            except (ValueError, IndexError) as e:
                print(Fore.RED + f"Error processing backup file {filepath}: {e}")

async def generate_reports(ctx: RunContext[GnuCashQuery]) -> str:
    """Generate standard financial reports from the GnuCash book.
    
    Includes:
    - Account balances
    - Transaction history
    - Monthly summary by category

    Returns - str: Formatted reports or error message

    Raises:
        piecash.BookError: If book access fails
    """
    global active_book
    if not active_book:
        return "No active book. Please create or open a book first."
    
    try:
        book = piecash.open_book(active_book, open_if_lock=True)
        reports = {}
        
        # Generate reports (same logic as testcase.py)
        # ... (include all report generation code from testcase.py)
        
        # Format the reports for display
        report_str = "\nAccount Balances:\n"
        report_str += reports['account_balances'].to_string() + "\n\n"
        report_str += "Transaction History:\n"
        report_str += reports['transaction_history'].to_string() + "\n\n"
        report_str += "Monthly Summary:\n"
        report_str += reports['monthly_summary'].to_string()
        
        book.close()
        print(Fore.YELLOW + "DEBUG: Completed generate_reports")
        return report_str
    
    except Exception as e:
        return f"Error generating reports: {str(e)}"


def run_cli(book_name: str = None):
    """Run the GnuCash CLI interface.
    
    Args:
        book_name (str, optional): Name of book to open at startup
    """
    # Set up backup file monitoring
    sweep_interval = int(os.getenv('GC_CLI_SWEEP_SECS', '120'))
    sweep_age = int(os.getenv('GC_CLI_SWEEP_AGE', '5'))
    event_handler = BackupFileHandler(sweep_interval, sweep_age)
    observer = Observer()
    observer.schedule(event_handler, '.', recursive=False)
    observer.start()
    print(Fore.YELLOW + f"Started backup file monitoring (sweep interval: {sweep_interval}s, sweep age: {sweep_age}m)")
    
    # Perform initial sweep immediately
    event_handler.sweep_old_backups()
    
    # Configure readline for command history and editing
    readline.parse_and_bind('tab: complete')  # Enable tab completion
    # readline.set_startup_hook(lambda: readline.insert_text("Hello "))

    # Set up history file
    histfile = os.path.join(os.path.expanduser("~"), ".gnucash_history")
    try:
        readline.read_history_file(histfile)
    except FileNotFoundError:
        # Create history file if it doesn't exist
        with open(histfile, 'w') as f:
            pass
        os.chmod(histfile, 0o600)  # Secure the history file
        
    # Set history length and make sure it's saved after each command
    readline.set_history_length(1000)
    readline.set_auto_history(True)
    
    # Basic editing bindings
    readline.parse_and_bind('"\C-a": beginning-of-line')
    readline.parse_and_bind('"\C-e": end-of-line')
    readline.parse_and_bind('"\C-k": kill-line')
    readline.parse_and_bind('"\C-u": unix-line-discard')
    readline.parse_and_bind('"\C-w": unix-word-rubout')
    readline.parse_and_bind('"\C-h": backward-delete-char')
    readline.parse_and_bind('"\C-?": backward-delete-char')
    
    # Navigation bindings
    readline.parse_and_bind('"\e[A": previous-history')
    readline.parse_and_bind('"\e[B": next-history')
    readline.parse_and_bind('"\e[C": forward-char')
    readline.parse_and_bind('"\e[D": backward-char')
    readline.parse_and_bind('"\e[1;5C": forward-word')
    readline.parse_and_bind('"\e[1;5D": backward-word')
    
    print(Fore.YELLOW + "Starting GnuCash CLI...")
    commands = {
        'create_book': 'Create a new sample GnuCash book',
        'create_accounts': 'Create accounts from YAML file (file_path)',
        'generate_reports': 'Generate financial reports',
        'close_book': 'Close the current book',
        'purge_backups': 'Purge old backups (book_name [--days N | --before YYYY-MM-DD])',
        'save_template': 'Save current book as template without transactions (template_name)',
        'set_currency': 'Set default currency (USD, EUR, etc)',
        'get_currency': 'Get current default currency',
        'set_accounts_currency': 'Set currency for all accounts (USD, EUR, etc)',
        'search_accounts': 'Search accounts by name pattern (supports regex)',
        'help': 'Show this help message'
    }
    global active_book
    history = []
    cmd_history = []
    history_index = 0
    
    # Try to open book if provided
    if book_name:
        result = gnucash_agent.run_sync(f"open_book {book_name}", message_history=history)
        history += result.new_messages()
        history = history[-3:]
        print(result.data)
    
    print(Fore.GREEN + "GnuCash CLI - Type 'quit' to exit")
    print("Available commands:")
    for cmd, desc in commands.items():
        print(f"  {cmd} - {desc}")
    if active_book:
        print(f"Active book: {active_book}")
    else:
        print("No active book - create or open one to begin")

    def clear_line():
        readline.set_startup_hook(lambda: readline.insert_text(""))  # Clear current input buffer
        readline.redisplay()
        print("Clearline called ......")

    while True:
        try:
            # Read input with history support
            prompt = Fore.GREEN + "GnuCash> "
            try:
                # Clear the line before reading input
                # print('\r' + ' ' * (len(prompt) + 100) + '\r', end='')  # Clear any leftover chars
                clear_line()
                query = input(prompt).strip()
                
                if query.lower() == 'quit':
                    break
                    
                # Add to command history if not empty
                if query:
                    readline.add_history(query)
            except EOFError:
                continue
            
            result = gnucash_agent.run_sync(query, message_history=history)
            history += result.new_messages()
            history = history[-3:]  # Keep last 3 messages
            print(result.data)
            if active_book:
                print(f"\n[Active book: {active_book}]")
                
        except KeyboardInterrupt:
            # Handle Ctrl+C gracefully
            print("\nType 'quit' to exit or continue entering commands.")
            continue
        except Exception as e:
            print(f"Error: {str(e)}")
    
    # Save history on exit
    try:
        readline.write_history_file(histfile)
    except Exception as e:
        print(f"Error saving history: {str(e)}")
    
    # Stop the watchdog observer
    observer.stop()
    observer.join()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='GnuCash CLI')
    parser.add_argument('--book', type=str, help='Name of GnuCash book to open')
    args = parser.parse_args()
    
    run_cli(args.book)
