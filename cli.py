import os
import anthropic
from datetime import datetime, date
from decimal import Decimal
import piecash
import pandas as pd
import sqlalchemy as sa
import warnings
from typing import Dict, Any
import json

# Filter SQLAlchemy warnings
warnings.filterwarnings('ignore', category=sa.exc.SAWarning)

class GnuCashCLI:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        self.current_book = None
        self.functions = {
            'create_book': self.create_sample_book,
            'generate_reports': self.generate_reports,
            'close_book': self.close_book,
            'help': self.show_help
        }

    def get_book_context(self) -> str:
        """Get current book structure and state as context"""
        if not self.current_book:
            return "No book is currently open."
        
        context = []
        context.append("Current book structure:")
        for account in self.current_book.accounts:
            if account.type != "ROOT":
                balance = account.get_balance()
                context.append(f"- {account.fullname} ({account.type}): {balance}")
        
        return "\n".join(context)

    def process_command(self, user_input: str) -> None:
        """Process natural language command using Claude"""
        if not user_input.strip():
            return

        # Build system prompt with current context
        system_prompt = f"""You are a financial assistant that helps users interact with GnuCash through natural language.

Available functions and parameters:
- create_book(): Creates a new book with sample accounts
- generate_reports(report_type?: str): Generates reports. Optional report_type can be "balances", "transactions", or "summary"
- close_book(): Safely closes the current book
- help(): Shows available commands

Current state:
{self.get_book_context()}

Analyze the user's request and return a JSON object with the function to call and any parameters:
{{
    "function": "function_name",
    "parameters": {{
        "param_name": "param_value"
    }}
}}
"""

        message = self.client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=1000,
            temperature=0,
            system=system_prompt,
            messages=[
                {
                    "role": "user", 
                    "content": user_input
                }
            ]
        )

        try:
            result = json.loads(message.content[0].text)
            function_name = result.get('function')
            parameters = result.get('parameters', {})

            if function_name in self.functions:
                self.functions[function_name](**parameters)
            else:
                print("I don't understand that command. Type 'help' for available commands.")
        except Exception as e:
            print(f"Error processing command: {str(e)}")

    def create_sample_book(self) -> None:
        """Creates a new GNUCash book with sample accounts and transactions."""
        try:
            self.current_book = piecash.create_book(
                "sample_accounts.gnucash",
                overwrite=True,
                currency="USD",
                keep_foreign_keys=False
            )
            
            with self.current_book as book:
                # Create main accounts
                assets = piecash.Account(
                    name="Assets",
                    type="ASSET",
                    commodity=book.default_currency,
                    parent=book.root_account
                )
                
                expenses = piecash.Account(
                    name="Expenses",
                    type="EXPENSE",
                    commodity=book.default_currency,
                    parent=book.root_account
                )
                
                income = piecash.Account(
                    name="Income",
                    type="INCOME",
                    commodity=book.default_currency,
                    parent=book.root_account
                )
                
                # Create sample transactions
                checking = piecash.Account(
                    name="Checking",
                    type="BANK",
                    commodity=book.default_currency,
                    parent=assets
                )
                
                salary = piecash.Account(
                    name="Salary",
                    type="INCOME",
                    commodity=book.default_currency,
                    parent=income
                )
                
                # Add initial transaction
                piecash.Transaction(
                    currency=book.default_currency,
                    description="Initial balance",
                    splits=[
                        piecash.Split(account=checking, value=Decimal("1000.00")),
                        piecash.Split(account=salary, value=Decimal("-1000.00"))
                    ],
                    post_date=date.today()
                )
                
                book.save()
            print("Created new GnuCash book with sample accounts and transactions.")
        except Exception as e:
            print(f"Error creating book: {str(e)}")

    def generate_reports(self, report_type: str = None) -> None:
        """Generate and display reports from the current book.
        
        Args:
            report_type: Optional type of report to generate ("balances", "transactions", or "summary")
        """
        if not self.current_book:
            print("No book is currently open. Create or open a book first.")
            return

        try:
            if report_type in (None, "balances"):
                print("\nAccount Balances:")
                for account in self.current_book.accounts:
                    if account.type != "ROOT":
                        print(f"{account.fullname}: {account.get_balance()}")

            if report_type in (None, "transactions"):
                print("\nTransaction History:")
                for tx in self.current_book.transactions:
                    print(f"\nDate: {tx.post_date}")
                    print(f"Description: {tx.description}")
                    for split in tx.splits:
                        print(f"  {split.account.fullname}: {split.value}")
            
            if report_type in (None, "summary"):
                print("\nAccount Summary:")
                total_assets = sum(a.get_balance() for a in self.current_book.accounts 
                                 if a.type == "ASSET")
                total_liabilities = sum(a.get_balance() for a in self.current_book.accounts 
                                      if a.type == "LIABILITY")
                print(f"Total Assets: {total_assets}")
                print(f"Total Liabilities: {total_liabilities}")
                print(f"Net Worth: {total_assets - total_liabilities}")

        except Exception as e:
            print(f"Error generating reports: {str(e)}")

    def close_book(self) -> None:
        """Safely close the current book."""
        if self.current_book:
            try:
                self.current_book.close()
                print("Book closed successfully.")
                self.current_book = None
            except Exception as e:
                print(f"Error closing book: {str(e)}")
        else:
            print("No book is currently open.")

    def show_help(self) -> None:
        """Display available commands."""
        print("""
Available commands (use natural language):
- Create a new book with sample accounts
- Generate reports from the current book
- Close the current book
- Help (show this message)

Examples:
- "Create a new GnuCash book for me"
- "Show me the account balances and transactions"
- "Close the current book"
        """)

    def run(self) -> None:
        """Main CLI loop."""
        print("Welcome to the GnuCash CLI! Type 'help' for available commands.")
        print("Type 'exit' or 'quit' to end the program.")

        while True:
            try:
                user_input = input("\nWhat would you like to do? ").strip().lower()
                
                if user_input in ('exit', 'quit'):
                    if self.current_book:
                        self.close_book()
                    break
                
                self.process_command(user_input)
                
            except KeyboardInterrupt:
                print("\nExiting...")
                if self.current_book:
                    self.close_book()
                break
            except Exception as e:
                print(f"An error occurred: {str(e)}")

def main():
    cli = GnuCashCLI()
    cli.run()

if __name__ == "__main__":
    main()
