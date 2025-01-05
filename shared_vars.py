# Track the active book
active_book: str = None

def get_active_book():
    return active_book

def set_active_book(value):
    global active_book  # needed to modify the global
    active_book = value