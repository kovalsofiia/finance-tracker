from sqlalchemy.orm import Session
from . import models, schemas, security
from typing import Optional
from sqlalchemy import func

# Users
def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.email == email).first()

# Get all users
def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()

# Get single user by ID
def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()

# Update user
def update_user(db: Session, user_id: int, user_in: schemas.UserUpdate):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return None
    if user_in.username:
        user.username = user_in.username
    if user_in.email:
        user.email = user_in.email
    if user_in.password:
        user.hashed_password = security.get_password_hash(user_in.password)
    db.commit()
    db.refresh(user)
    return user

# Delete user
def delete_user(db: Session, user_id: int):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user:
        db.delete(user)
        db.commit()

# СТВОРИТИ КОРИСТУВАЧА
def create_user(db: Session, user_in: schemas.UserCreate) -> models.User:
    hashed = security.get_password_hash(user_in.password)
    db_user = models.User(email=user_in.email, hashed_password=hashed, username=user_in.username)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# ОТРИМАТИ ТОКЕН = ЛОГІН ДЛЯ КОРИСТУВАЧА
def authenticate_user(db: Session, email: str, password: str) -> Optional[models.User]:
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not security.verify_password(password, user.hashed_password):
        return None
    return user

# Categories

# СТВОРИТИ КАТЕГОРІЮ ДЛЯ ПОТОЧНОГО КОРИСТУВАЧА
def create_category(db: Session, user_id: int, cat_in: schemas.CategoryCreate) -> models.Category:
    db_cat = models.Category(name=cat_in.name, user_id=user_id)
    db.add(db_cat)
    db.commit()
    db.refresh(db_cat)
    return db_cat

# ПОКАЗАТИ УСІ КАТЕГОРІЇ ДЛЯ ПОТОЧНОГО КОРИСТУВАЧА
def get_user_categories(db: Session, user_id: int):
    return db.query(models.Category).filter(models.Category.user_id == user_id).all()

def get_category(db: Session, category_id: int, user_id: int) -> Optional[models.Category]:
    return db.query(models.Category).filter(models.Category.id == category_id, models.Category.user_id == user_id).first()
    
def update_category(db: Session, category_id: int, user_id: int, cat_in: schemas.CategoryUpdate) -> Optional[models.Category]:
    category = get_category(db, category_id, user_id)
    if not category:
        return None
    if cat_in.name is not None:
        category.name = cat_in.name
    db.commit()
    db.refresh(category)
    return category

def delete_category(db: Session, category_id: int, user_id: int) -> bool:
    category = get_category(db, category_id, user_id)
    if not category:
        return False
    # Find or create default "Uncategorized" category
    default_cat = db.query(models.Category).filter(models.Category.user_id == user_id, models.Category.name == "Uncategorized").first()
    if not default_cat:
        default_cat = models.Category(name="Uncategorized", user_id=user_id)
        db.add(default_cat)
        db.commit()
        db.refresh(default_cat)
    # Reassign transactions to default category
    db.query(models.Transaction).filter(models.Transaction.category_id == category_id).update({"category_id": default_cat.id})
    db.delete(category)
    db.commit()
    return True

# Transactions

# ДОДАТИ ТРАНЗАКЦІЮ ДЛЯ ПОТОЧНОГО КОРИСТУВАЧА
def create_transaction(db: Session, user_id: int, tx_in: schemas.TransactionCreate) -> models.Transaction:
    data = tx_in.dict()
    # ensure date is set if not provided (Pydantic will allow None)
    if data.get("date") is None:
        from datetime import datetime
        data["date"] = datetime.utcnow()
    db_tx = models.Transaction(user_id=user_id, **data)
    db.add(db_tx)
    db.commit()
    db.refresh(db_tx)
    return db_tx

# ПОКАЗАТИ УСІ ТРАНЗАКЦІЇ ПОТОЧНОГО КОРИСТУВАЧА
def get_user_transactions(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.Transaction).filter(models.Transaction.user_id == user_id).order_by(models.Transaction.date.desc()).offset(skip).limit(limit).all()

# ПОКАЗАТИ ТРАНЗАКЦІЇ ПОТОЧНОГО КОРИСТУВАЧА ЗА КАТЕГОРІЄЮ
def get_transactions_by_category(db: Session, category_id: int):
    return db.query(models.Transaction).filter(models.Transaction.category_id == category_id).all()

def get_transaction(db: Session, transaction_id: int, user_id: int) -> Optional[models.Transaction]:
    return db.query(models.Transaction).filter(models.Transaction.id == transaction_id, models.Transaction.user_id == user_id).first()

# Update create_user to ensure "Uncategorized" category exists
def create_user(db: Session, user_in: schemas.UserCreate) -> models.User:
    hashed = security.get_password_hash(user_in.password)
    db_user = models.User(email=user_in.email, hashed_password=hashed, username=user_in.username)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    # Create default "Uncategorized" category
    default_cat = models.Category(name="Uncategorized", user_id=db_user.id)
    db.add(default_cat)
    db.commit()
    return db_user

def delete_transaction(db: Session, transaction_id: int, user_id: int) -> bool:
    transaction = get_transaction(db, transaction_id, user_id)
    if not transaction:
        return False
    db.delete(transaction)
    db.commit()
    return True

# ПОКАЗАТИ БАЛАНС ПОТОЧНОГО КОРИСТУВАЧА
def get_user_balance(db: Session, user_id: int) -> float:
    total = db.query(func.coalesce(func.sum(models.Transaction.amount), 0.0)).filter(models.Transaction.user_id == user_id).scalar()
    return float(total)


def get_category_transactions(db: Session, category_id: int, user_id: int) -> list[models.Transaction]:
    # Check if category belongs to the user
    cat = db.query(models.Category).filter(models.Category.id == category_id, models.Category.user_id == user_id).first()
    if not cat:
        return []
    return db.query(models.Transaction).filter(models.Transaction.category_id == category_id).all()
