from datetime import datetime
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from . import models, database, schemas, crud, security
from .database import get_db

app = FastAPI(title="Finance Tracker API")

# Allow your Vue dev server origin (adjust when deploying)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # add your frontend dev URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create tables
models.Base.metadata.create_all(bind=database.engine)


# --- Auth / Users ---

# Create user (register)
@app.post("/users/", response_model=dict)  # Змінено response_model
def register_user(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = crud.get_user_by_email(db, user_in.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = crud.create_user(db, user_in)
    access_token = security.create_access_token(data={"sub": user.email})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": schemas.UserRead.from_orm(user)  # Додаємо дані користувача
    }

@app.post("/token", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # OAuth2PasswordRequestForm has fields username & password (we use username for email)
    user = crud.authenticate_user(db, email=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    access_token = security.create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}


# Get current logged-in user
@app.get("/profile", response_model=schemas.UserRead)
def read_current_user(current_user: models.User = Depends(security.get_current_user)):
    return current_user

# Update current user
@app.put("/profile", response_model=schemas.UserRead)
def update_current_user(
    user_in: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    updated_user = crud.update_user(db, current_user.id, user_in)
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
    return updated_user

# Delete current user
@app.delete("/profile", status_code=204)
def delete_current_user(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    crud.delete_user(db, current_user.id)
    return None  # Змінено: без тіла відповіді

# Видалено /users/ і /users/{user_id} для безпеки

# Get all users

# @app.get("/users/", response_model=list[schemas.UserRead])
# def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(security.get_current_user)):
#     return crud.get_users(db, skip=skip, limit=limit)

# Get user by ID

# @app.get("/users/{user_id}", response_model=schemas.UserRead)
# def read_user(user_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(security.get_current_user)):
#     user = crud.get_user(db, user_id)
#     if not user:
#         raise HTTPException(status_code=404, detail="User not found")
#     return user


# --- Categories ---
@app.post("/categories/", response_model=schemas.CategoryRead)
def create_category(cat_in: schemas.CategoryCreate, db: Session = Depends(get_db), current_user: models.User = Depends(security.get_current_user)):
    return crud.create_category(db, current_user.id, cat_in)

@app.get("/profile/categories", response_model=list[schemas.CategoryRead])  # Змінено шлях для консистентності
def read_user_categories(db: Session = Depends(get_db), current_user: models.User = Depends(security.get_current_user)):
    return crud.get_user_categories(db, current_user.id)

@app.get("/categories/{category_id}", response_model=schemas.CategoryRead)
def read_category(category_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(security.get_current_user)):
    category = crud.get_category(db, category_id, current_user.id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found or not yours")
    return category

@app.put("/categories/{category_id}", response_model=schemas.CategoryRead)
def update_category(category_id: int, cat_in: schemas.CategoryUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(security.get_current_user)):
    updated = crud.update_category(db, category_id, current_user.id, cat_in)
    if not updated:
        raise HTTPException(status_code=404, detail="Category not found or not yours")
    return updated

@app.delete("/categories/{category_id}", status_code=204)
def delete_category(category_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(security.get_current_user)):
    deleted = crud.delete_category(db, category_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Category not found or not yours")
    return None  # Змінено: без тіла відповіді

# --- Transactions ---
@app.post("/transactions/", response_model=schemas.TransactionRead)
def create_transaction(tx_in: schemas.TransactionCreate, db: Session = Depends(get_db), current_user: models.User = Depends(security.get_current_user)):
    if tx_in.category_id:
        cat = db.query(models.Category).filter(models.Category.id == tx_in.category_id).first()
        if not cat or cat.user_id != current_user.id:
            raise HTTPException(status_code=400, detail="Invalid category")
    tx = crud.create_transaction(db, current_user.id, tx_in)
    return tx

# @app.get("/transactions/{transaction_id}", response_model=schemas.TransactionRead)
# def read_transaction(transaction_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(security.get_current_user)):
#     transaction = crud.get_transaction(db, transaction_id, current_user.id)
#     if not transaction:
#         raise HTTPException(status_code=404, detail="Transaction not found or not yours")
#     return transaction
@app.get("/profile/transactions", response_model=list[schemas.TransactionRead])
def read_user_transactions(
    filters: schemas.TransactionFilter = Depends(),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
    skip: int = 0,
    limit: int = 100
):
    return crud.get_user_transactions(db, current_user.id, filters, skip, limit)

@app.put("/transactions/{transaction_id}", response_model=schemas.TransactionRead)
def update_transaction(transaction_id: int, tx_in: schemas.TransactionUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(security.get_current_user)):
    if tx_in.category_id:
        cat = db.query(models.Category).filter(models.Category.id == tx_in.category_id).first()
        if not cat or cat.user_id != current_user.id:
            raise HTTPException(status_code=400, detail="Invalid category")
    updated = crud.update_transaction(db, transaction_id, current_user.id, tx_in)
    if not updated:
        raise HTTPException(status_code=404, detail="Transaction not found or not yours")
    return updated

@app.delete("/transactions/{transaction_id}", status_code=204)
def delete_transaction(transaction_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(security.get_current_user)):
    deleted = crud.delete_transaction(db, transaction_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Transaction not found or not yours")
    return None  # Змінено: без тіла відповіді

@app.get("/profile/transactions", response_model=list[schemas.TransactionRead])
def read_user_transactions(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
    skip: int = 0,
    limit: int = 100,
    start_date: Optional[datetime] = None,  # Додано фільтрацію за датою
    end_date: Optional[datetime] = None
):
    return crud.get_user_transactions(db, current_user.id, skip, limit, start_date, end_date)

@app.get("/profile/balance", response_model=schemas.BalanceRead)
def get_my_balance(db: Session = Depends(get_db), current_user: models.User = Depends(security.get_current_user)):
    balance = crud.get_user_balance(db, current_user.id)
    return {"balance": balance, "currency": "USD", "updated_at": datetime.utcnow()}

@app.get("/profile/categories/{category_id}/transactions", response_model=list[schemas.TransactionRead])
def read_category_transactions(category_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(security.get_current_user), skip: int = 0, limit: int = 100):
    transactions = crud.get_category_transactions(db, category_id, current_user.id, skip, limit)
    if not transactions and not db.query(models.Category).filter(models.Category.id == category_id, models.Category.user_id == current_user.id).first():
        raise HTTPException(status_code=404, detail="Category not found or not yours")
    return transactions