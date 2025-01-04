# GnuCash CLI Tool

A command-line interface for managing GnuCash books with advanced features for account management, reporting, and automation.
Uses piecash, pydantic-ai, OpenAI, GenAI / LLMs etc.

## Features

- Create and manage GnuCash books
- Bulk account creation from YAML files
- Generate financial reports (PDF and console)
- Cash flow statement generation
- Balance sheet generation
- Currency management
- Template creation
- Backup management
- Account search and movement
- Transaction management
- PDF report export
- Automatic backup management

## Installation

1. Clone this repository
2. Install dependencies:
```bash
pip install piecash colorama python-dotenv pydantic pydantic-ai pandas PyYAML
``` 
OR
```
uv sync 
```
NOTE: You WILL need an OpenAI Key and should be set and saved in a file called .env at the root of this project 
## Quick Start

1. Start the CLI:
```bash
python gnucash_cli.py
```

Or open a specific book:
```bash
python gnucash_cli.py --book mybook.gnucash
```

2. Create a new book:
```
GnuCash> create_book mybook
```

## Bulk Account Creation

You can create multiple accounts at once using a YAML file. Example structure (SampleAccounts.yaml):

```yaml
accounts:
  - name: Assets
    type: ASSET
    children:
      - name: Investments
        children:
          - name: Stocks
            children:
              - name: Broker1
                initial_balance: 0.00
                balance_date: "2025-01-01"
                children:
                  - name: Growth Portfolio
                    initial_balance: 0.00
                  - name: Dividend Portfolio
                    initial_balance: 2000.00
```

To create accounts from a YAML file:
```
GnuCash> create_accounts_from_file SampleAccounts.yaml
```
OR (NOTE: This is true for all the command in this README)
Use a freeform way of mentioning your ask _like_ below:
```
GnuCash> init from SampleAccounts.yaml
```
## Available Commands

- `create_book [name]` - Create a new GnuCash book with sample accounts
- `open_book [name]` - Open an existing book
- `create_accounts_from_file [file]` - Create accounts from YAML file
- `list_accounts` - Show all accounts with balances
- `transfer_funds [from] [to] [amount]` - Transfer money between accounts
- `add_transaction [from] [to] [amount]` - Create complex transactions with multiple splits
- `list_transactions [limit]` - Show recent transactions
- `generate_cashflow_statement [start_date] [end_date]` - Generate cash flow report
- `generate_balance_sheet` - Generate balance sheet report
- `export_reports_pdf [filename]` - Export reports to PDF
- `purge_backups [book] [--days N|--before YYYY-MM-DD]` - Clean up old backups
- `save_as_template [name]` - Save book structure as template
- `set_default_currency [code]` - Change book's default currency
- `set_accounts_currency [code]` - Update all accounts' currency
- `search_accounts [pattern]` - Search accounts by name (supports regex)
- `move_account [account] [new_parent]` - Move account to new parent
- `get_default_currency` - Show current default currency

## Cash Flow Statement

The cash flow statement shows:
- Money Incoming (green)
  - Detailed breakdown by income category
  - Total money in
- Money Outflow (red)
  - Detailed breakdown by expense category
  - Total money out
- Net Cash Flow

## Creating Individual Subaccounts

You can create subaccounts one at a time using natural language commands:

```
GnuCash> create subaccount Savings under Assets with balance 1000
GnuCash> add account Groceries under Expenses
GnuCash> new account Credit Card type LIABILITY under Liabilities balance -500
```

Common patterns:
- Specify parent account using "under" or "in"
- Set initial balance with "balance" or "with balance"
- Optionally specify account type (defaults to same as parent)
- Add description with "desc" or "description"

Examples:
```
GnuCash> create account Emergency Fund under Assets:Savings balance 5000 desc "6 month emergency fund"
GnuCash> add account Rent type EXPENSE under Expenses with description "Monthly rent payments"
GnuCash> create Account BankC under "Current Assets" with balance 15000
```

## Managing Transactions

Transfer money between accounts:
```
GnuCash> transfer 1000 from Checking to Savings
GnuCash> move 50.25 from Assets:Checking to Expenses:Groceries
GnuCash> pay 750 from Credit Card to Expenses:Rent desc "January rent"
```

Complex transactions with multiple splits:
```
GnuCash> add_transaction from Checking to Savings 1000, Expenses:Groceries 300, Expenses:Gas 200
```

View recent transactions:
```
GnuCash> list_transactions 20
```

Transaction features:
- Double-entry accounting
- Timestamped with current date/time
- Multiple splits supported
- Detailed transaction history
- Color-coded output

## Currency Management

Set default currency:
```
GnuCash> set currency to USD
```

Update all accounts' currency:
```
GnuCash> set currency for all accounts to EUR
```

## Reports

Generate detailed financial reports:

Cash Flow Statement:
```
GnuCash> generate_cashflow_statement
GnuCash> show cashflow for 2025-01-01 to 2025-12-31
```

Balance Sheet:
```
GnuCash> generate_balance_sheet
GnuCash> show balance sheet
```

PDF Export:
```
GnuCash> export_reports_pdf my_report.pdf
```

Transaction History:
```
GnuCash> list_transactions 20
```

All reports include:
- Proper account hierarchy
- Roll-up totals
- Color-coded output
- Date filtering (where applicable)

## Templates

Save current book structure as template:
```
GnuCash> save template to mytemplate
```

This creates a new file without transactions but preserving:
- Account hierarchy
- Account properties
- Currency settings

## Backup Management

The CLI automatically manages backups:
- Creates timestamped backups during operations
- Moves old backups to backups/ directory
- Deletes backups older than 2 days by default

Manual backup cleanup:
```
GnuCash> purge_backups mybook --days 30
GnuCash> purge_backups mybook --before 2024-12-31
```

Configure backup retention:
- Set GC_CLI_PURGE_DAYS in .env for backup retention days
- Set GC_CLI_SWEEP_SECS for backup sweep interval
- Set GC_CLI_SWEEP_AGE_MINS for backup move age

## Error Handling

The tool provides colored output:
- Yellow: Debug/info messages
- Green: Success messages
- Red: Error messages

## Best Practices

1. Always close the CLI properly using 'quit'
2. Back up important books before major changes
3. Use templates for consistent account structures
4. Review generated reports regularly
5. Keep backup retention policy appropriate for your needs




## License

This project is licensed under the MIT License - see the LICENSE file for details.
