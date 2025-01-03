from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import contextmanager
import os

app = FastAPI(
    title="PieCash API",
    description="REST API for GnuCash using piecash library",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import routers
from .routers import books, accounts, transactions

# Register routers
app.include_router(books.router, prefix="/api/v1/books", tags=["Books"])
app.include_router(accounts.router, prefix="/api/v1/books/{book_name}/accounts", tags=["Accounts"])
app.include_router(transactions.router, prefix="/api/v1/books/{book_name}/transactions", tags=["Transactions"])

@app.get("/")
async def root():
    return {"message": "Welcome to PieCash API"}
