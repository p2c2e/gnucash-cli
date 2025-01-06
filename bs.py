from datetime import datetime
from decimal import Decimal
import json
from typing import Dict, List, Optional, Union, Set
import piecash
from tabulate import tabulate
from collections import defaultdict

def calculate_balance_sheet(book: Union[str, piecash.Book], date: Optional[datetime] = None) -> dict:
    """
    Calculate a comprehensive balance sheet from a GnuCash book.

    Args:
        book: Either a path to GnuCash book (str) or an opened piecash Book object
        date: Optional date for balance sheet (defaults to current date)

    Returns:
        Dictionary containing the balance sheet data
    """
    if date is None:
        date = datetime.now()

    # Handle string path vs Book object
    if isinstance(book, str):
        book_obj = piecash.open_book(book, open_if_lock=True)
        should_close = True
    else:
        book_obj = book
        should_close = False

    try:
        balance_sheet = {
            "assets": defaultdict(lambda: defaultdict(Decimal)),
            "liabilities": defaultdict(lambda: defaultdict(Decimal)),
            "equity": defaultdict(lambda: defaultdict(Decimal)),
            "metadata": {
                "date": date.strftime("%Y-%m-%d"),
                "currency": "USD"  # Default to USD if currency not found
            }
        }

        # Try to get book currency, fallback to USD if not available
        try:
            if hasattr(book_obj, 'default_currency'):
                balance_sheet["metadata"]["currency"] = book_obj.default_currency.mnemonic
        except Exception as e:
            print(f"Warning: Could not determine book currency: {str(e)}")

        def get_latest_price(commodity) -> Decimal:
            """Helper function to get latest stock price"""
            try:
                if not commodity.prices:
                    return Decimal('0')
                latest_price = max(commodity.prices, key=lambda p: p.date)
                return Decimal(str(latest_price.value))
            except Exception as e:
                print(f"Warning: Could not get price for {commodity.mnemonic}: {str(e)}")
                return Decimal('0')

        def calculate_account_balance(account, at_date, processed_accounts: Set[str]) -> Decimal:
            """
            Calculate account balance considering splits up to given date.
            Handles both leaf accounts and parent accounts.
            """
            # Prevent double counting
            if account.fullname in processed_accounts:
                return Decimal('0')

            processed_accounts.add(account.fullname)

            try:
                # For parent accounts, sum up child accounts
                if account.children:
                    balance = sum(
                        calculate_account_balance(child, at_date, processed_accounts)
                        for child in account.children
                        if not child.placeholder
                    )
                    return balance

                # For leaf accounts, calculate from splits
                balance = Decimal('0')
                for split in account.splits:
                    if split.transaction.post_date and split.transaction.post_date <= at_date.date():
                        quantity = Decimal(str(split.quantity))

                        # Handle stock/mutual fund accounts
                        if account.type in ['STOCK', 'MUTUAL']:
                            price = get_latest_price(account.commodity)
                            balance += quantity * price
                        else:
                            balance += quantity

                # Convert to book currency if needed
                if (hasattr(book_obj, 'default_currency') and
                        account.commodity != book_obj.default_currency and
                        account.type not in ['STOCK', 'MUTUAL']):  # Skip conversion for already-valued stocks
                    try:
                        price = get_latest_price(account.commodity)
                        balance *= price
                    except Exception as e:
                        print(f"Warning: Currency conversion failed for {account.name}: {str(e)}")

                return balance

            except Exception as e:
                print(f"Warning: Error calculating balance for {account.name}: {str(e)}")
                return Decimal('0')

        # Track processed accounts to prevent double counting
        processed_accounts: Set[str] = set()

        # Process root accounts only
        for account in book_obj.accounts:
            try:
                # Skip if already processed or placeholder
                if account.fullname in processed_accounts or account.placeholder:
                    continue

                # Only process root accounts of each type
                if not account.parent or account.parent.type == 'ROOT':
                    # Determine account type category
                    if account.type in ['ASSET', 'BANK', 'CASH', 'STOCK', 'MUTUAL']:
                        category = "assets"
                    elif account.type in ['LIABILITY', 'CREDIT', 'PAYABLE']:
                        category = "liabilities"
                    elif account.type in ['EQUITY']:
                        category = "equity"
                    else:
                        continue

                    # Calculate balance including all children
                    balance = calculate_account_balance(account, date, processed_accounts)

                    # Add to appropriate category if balance is non-zero
                    if balance != 0:
                        parent_name = account.name
                        balance_sheet[category][parent_name]["Total"] = float(balance)

                        # Add individual child accounts if they exist
                        for child in account.children:
                            if not child.placeholder and child.fullname in processed_accounts:
                                child_balance = calculate_account_balance(child, date, set())  # New set to allow recalculation
                                if child_balance != 0:
                                    balance_sheet[category][parent_name][child.name] = float(child_balance)

            except Exception as e:
                print(f"Warning: Error processing account {account.name}: {str(e)}")
                continue

        # Calculate category totals
        for category in ["assets", "liabilities", "equity"]:
            category_total = Decimal('0')
            for parent_group in balance_sheet[category]:
                group_values = [v for k, v in balance_sheet[category][parent_group].items() if k != "Total"]
                group_total = sum(Decimal(str(v)) for v in group_values)
                balance_sheet[category][parent_group]["_total"] = float(group_total)
                category_total += group_total
            balance_sheet[category]["_total"] = float(category_total)

        return balance_sheet

    finally:
        # Close the book if we opened it
        if should_close:
            book_obj.close()

# Rest of the code remains the same...
def render_balance_sheet(balance_sheet: Dict) -> str:
    """
    Render a balance sheet dictionary as a formatted table.

    Args:
        balance_sheet: Dictionary containing balance sheet data

    Returns:
        Formatted string containing the balance sheet table
    """
    headers = ["Category", "Group", "Account", "Amount"]
    rows = []

    def format_amount(amount: float) -> str:
        """Helper function to format amounts"""
        return f"{amount:,.2f} {balance_sheet['metadata']['currency']}"

    # Process each category
    for category in ["assets", "liabilities", "equity"]:
        category_name = category.title()
        first_group = True

        for group, accounts in balance_sheet[category].items():
            if group == "_total":
                continue

            group_first_account = True

            for account, amount in accounts.items():
                if account == "_total":
                    continue

                rows.append([
                    category_name if first_group and group_first_account else "",
                    group if group_first_account else "",
                    account,
                    format_amount(amount)
                ])

                group_first_account = False

            # Add group total
            rows.append([
                "",
                "Total " + group,
                "",
                format_amount(accounts["_total"])
            ])

            first_group = False

        # Add category total
        rows.append([
            "Total " + category_name,
            "",
            "",
            format_amount(balance_sheet[category]["_total"])
        ])

        # Add separator between categories
        rows.append(["", "", "", ""])

    # Generate table
    table = tabulate(
        rows,
        headers=headers,
        tablefmt="grid",
        colalign=("left", "left", "left", "right")
    )

    # Add metadata header
    header = f"Balance Sheet as of {balance_sheet['metadata']['date']}\n"
    return header + table

def generate_balance_sheet(book_path: str, as_of_date: Optional[datetime] = None) -> tuple[dict, str]:
    """
    Generate both JSON and table format balance sheets.

    Args:
        book_path: Path to GnuCash book
        as_of_date: Optional date for balance sheet

    Returns:
        Tuple of (balance sheet dict, formatted table string)
    """
    try:
        balance_sheet = calculate_balance_sheet(book_path, as_of_date)
        table = render_balance_sheet(balance_sheet)
        return balance_sheet, table
    except Exception as e:
        raise Exception(f"Failed to generate balance sheet: {str(e)}")