import os
from pathlib import Path

def get_book_path(book_name: str) -> str:
    """Convert a book name to its full path under /books directory"""
    books_dir = Path("books")
    if not books_dir.exists():
        books_dir.mkdir(parents=True)
        
    if not book_name.endswith('.gnucash'):
        book_name = f"{book_name}.gnucash"
        
    return str(books_dir / book_name)
