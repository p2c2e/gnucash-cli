# GnuCash CLI Tool

A command-line interface for managing GnuCash books with advanced features for account management, reporting, and automation.
Uses piecash, pydantic-ai, OpenAI, GenAI / LLMs etc.

## Features

- Create and manage GnuCash books
- Bulk account creation from YAML files
- Generate financial reports
- Cash flow statement generation
- Currency management
- Template creation
- Backup management

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

- `create_book [name]` - Create a new GnuCash book
- `open_book [name]` - Open an existing book
- `create_accounts [file]` - Create accounts from YAML file
- `list_accounts` - Show all accounts with balances
- `transfer_funds [from] [to] [amount]` - Transfer money between accounts
- `generate_cashflow_statement` - Generate cash flow report
- `purge_backups [--days N|--before YYYY-MM-DD]` - Clean up old backups
- `save_as_template [name]` - Save book structure as template
- `set_default_currency [code]` - Change book's default currency
- `set_accounts_currency [code]` - Update all accounts' currency

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

Transfer money between accounts using natural language:

```
GnuCash> transfer 1000 from Checking to Savings
GnuCash> move 50.25 from Assets:Checking to Expenses:Groceries
GnuCash> pay 750 from Credit Card to Expenses:Rent desc "January rent"
```

Split transactions across multiple accounts:
```
GnuCash> split 1500 from Checking to Savings 1000 , Expenses:Groceries 300 and Expenses:Gas 200
```

Common patterns:
- Use "transfer", "move", or "pay" 
- Specify full account paths for clarity
- Add description with "desc" or "description"
- Date defaults to today, or specify: "date 2025-01-15"

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

Show Cashflow or Balance sheet
``` 
GnuCash> Show cashflow report for 2025
```

Show Balance Sheet
``` 
GnuCash> Generate Bal Sheet
```

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

Clean up old backup files:
```
GnuCash> purge_backups mybook --days 30
```

Or before specific date:
```
GnuCash> purge_backups mybook --before 2024-12-31
```

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
