from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy.orm import Session
from . import models, schemas, security
from typing import Optional
from sqlalchemy import func
from .schemas import TransactionFilter
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
    if user_in.email and user_in.email != user.email:
        if db.query(models.User).filter(models.User.email == user_in.email).first():
            raise HTTPException(status_code=400, detail="Email already registered")
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
#"Uncategorized" category exists
def create_user(db: Session, user_in: schemas.UserCreate) -> models.User:
    hashed = security.get_password_hash(user_in.password)
    db_user = models.User(email=user_in.email, hashed_password=hashed, username=user_in.username)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # Автоматично створюємо "Uncategorized"
    get_or_create_uncategorized(db, db_user.id)
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
    # Перевірка на унікальність імені в межах користувача і батька
    query = db.query(models.Category).filter(
        models.Category.user_id == user_id,
        models.Category.name == cat_in.name
    )
    if cat_in.parent_id:
        query = query.filter(models.Category.parent_id == cat_in.parent_id)
    else:
        query = query.filter(models.Category.parent_id.is_(None))

    if query.first():
        raise HTTPException(status_code=400, detail="Category name already exists at this level")

    # Валідація parent_id
    if cat_in.parent_id:
        parent = db.query(models.Category).filter(
            models.Category.id == cat_in.parent_id,
            models.Category.user_id == user_id
        ).first()
        if not parent:
            raise HTTPException(status_code=400, detail="Parent category not found")

    db_cat = models.Category(name=cat_in.name, user_id=user_id, parent_id=cat_in.parent_id)
    db.add(db_cat)
    db.commit()
    db.refresh(db_cat)
    return db_cat

# ПОКАЗАТИ УСІ КАТЕГОРІЇ ДЛЯ ПОТОЧНОГО КОРИСТУВАЧА
# crud.py

def get_user_categories(db: Session, user_id: int):
    # Отримуємо кореневі категорії
    root_categories = db.query(models.Category).filter(
        models.Category.user_id == user_id,
        models.Category.parent_id.is_(None)
    ).all()

    def build_tree(categories):
        result = []
        for cat in categories:
            # Серіалізуємо категорію
            serialized = schemas.CategoryRead.from_orm(cat)

            # Отримуємо дочірні категорії
            children = db.query(models.Category).filter(
                models.Category.parent_id == cat.id
            ).all()
            serialized.children = build_tree(children)

            # ДОДАЄМО ТРАНЗАКЦІЇ ЦІЄЇ КАТЕГОРІЇ
            txs = db.query(models.Transaction).filter(
                models.Transaction.category_id == cat.id
            ).order_by(models.Transaction.date.desc()).all()

            serialized.transactions = [
                schemas.TransactionRead.from_orm(tx) for tx in txs
            ]

            result.append(serialized)
        return result

    return build_tree(root_categories)

def get_category(db: Session, category_id: int, user_id: int) -> Optional[models.Category]:
    return db.query(models.Category).filter(models.Category.id == category_id, models.Category.user_id == user_id).first()
    
def update_category(db: Session, category_id: int, user_id: int, cat_in: schemas.CategoryUpdate) -> Optional[models.Category]:
    category = db.query(models.Category).filter(
        models.Category.id == category_id,
        models.Category.user_id == user_id
    ).first()
    if not category:
        return None

    if cat_in.name is not None:
        # Унікальність на тому ж рівні
        query = db.query(models.Category).filter(
            models.Category.user_id == user_id,
            models.Category.name == cat_in.name,
            models.Category.id != category_id
        )
        if category.parent_id:
            query = query.filter(models.Category.parent_id == category.parent_id)
        else:
            query = query.filter(models.Category.parent_id.is_(None))
        if query.first():
            raise HTTPException(status_code=400, detail="Category name already exists at this level")
        category.name = cat_in.name

    if cat_in.parent_id is not None:
        if cat_in.parent_id == category_id:
            raise HTTPException(status_code=400, detail="Category cannot be its own parent")

        # Перевірка, чи parent існує і належить користувачу
        parent = db.query(models.Category).filter(
            models.Category.id == cat_in.parent_id,
            models.Category.user_id == user_id
        ).first()
        if not parent and cat_in.parent_id != 0:  # 0 або None = корінь
            raise HTTPException(status_code=400, detail="Parent category not found")

        # Заборона циклу
        current = parent
        while current:
            if current.id == category_id:
                raise HTTPException(status_code=400, detail="Cannot create category cycle")
            current = current.parent

        category.parent_id = cat_in.parent_id if cat_in.parent_id != 0 else None

    db.commit()
    db.refresh(category)
    return category

def delete_category(db: Session, category_id: int, user_id: int) -> bool:
    category = db.query(models.Category).filter(
        models.Category.id == category_id,
        models.Category.user_id == user_id
    ).first()
    if not category:
        return False

    # Перевіряємо, чи є транзакції
    has_transactions = db.query(models.Transaction).filter(
        models.Transaction.category_id == category_id
    ).first()
    if has_transactions:
        raise HTTPException(status_code=400, detail="Cannot delete category with transactions")

    # Якщо є дочірні категорії — не дозволяємо видаляти
    has_children = db.query(models.Category).filter(
        models.Category.parent_id == category_id
    ).first()
    if has_children:
        raise HTTPException(status_code=400, detail="Cannot delete category with subcategories")

    # Якщо це "Uncategorized" — не дозволяємо видаляти
    if category.name == "Uncategorized":
        raise HTTPException(status_code=400, detail="Cannot delete default category")

    db.delete(category)
    db.commit()
    return True

# Transactions

# ДОДАТИ ТРАНЗАКЦІЮ ДЛЯ ПОТОЧНОГО КОРИСТУВАЧА

def get_or_create_uncategorized(db: Session, user_id: int) -> models.Category:
    uncategorized = db.query(models.Category).filter(
        models.Category.user_id == user_id,
        models.Category.name == "Uncategorized"
    ).first()
    if not uncategorized:
        uncategorized = models.Category(name="Uncategorized", user_id=user_id)
        db.add(uncategorized)
        db.commit()
        db.refresh(uncategorized)
    return uncategorized

def create_transaction(db: Session, user_id: int, tx_in: schemas.TransactionCreate) -> models.Transaction:
    data = tx_in.model_dump(exclude_unset=True)

    if "date" not in data or data["date"] is None:
        data["date"] = datetime.now(timezone.utc)

    # Валідація category_id
    category = None
    if "category_id" in data and data["category_id"] is not None:
        category = db.query(models.Category).filter(
            models.Category.id == data["category_id"],
            models.Category.user_id == user_id
        ).first()
        if not category:
            raise HTTPException(status_code=400, detail="Invalid category")

    # Якщо категорія не вказана — використовуємо "Uncategorized"
    if category is None:
        category = get_or_create_uncategorized(db, user_id)
        data["category_id"] = category.id

    db_tx = models.Transaction(user_id=user_id, **data)
    db.add(db_tx)
    db.commit()
    db.refresh(db_tx)
    return db_tx

def update_transaction(db: Session, transaction_id: int, user_id: int, tx_in: schemas.TransactionUpdate) -> Optional[models.Transaction]:
    transaction = get_transaction(db, transaction_id, user_id)
    if not transaction:
        return None

    data = tx_in.model_dump(exclude_unset=True)

    if "category_id" in data and data["category_id"] is not None:
        category = db.query(models.Category).filter(
            models.Category.id == data["category_id"],
            models.Category.user_id == user_id
        ).first()
        if not category:
            raise HTTPException(status_code=400, detail="Category not found or not yours")
    elif "category_id" in data and data["category_id"] is None:
        # Дозволяємо встановити NULL → перемістити в "Uncategorized"
        uncategorized = get_or_create_uncategorized(db, user_id)
        data["category_id"] = uncategorized.id

    for key, value in data.items():
        setattr(transaction, key, value)

    db.commit()
    db.refresh(transaction)
    return transaction

def delete_transaction(db: Session, transaction_id: int, user_id: int) -> bool:
    transaction = get_transaction(db, transaction_id, user_id)
    if not transaction:
        return False
    db.delete(transaction)
    db.commit()
    return True

# ПОКАЗАТИ УСІ ТРАНЗАКЦІЇ ПОТОЧНОГО КОРИСТУВАЧА
def get_user_transactions(
    db: Session,
    user_id: int,
    filters: TransactionFilter,
    skip: int = 0,
    limit: int = 100
) -> list[models.Transaction]:
    
    query = db.query(models.Transaction).filter(models.Transaction.user_id == user_id)

    # Фільтр за датою
    if filters.start_date:
        query = query.filter(models.Transaction.date >= filters.start_date)
    if filters.end_date:
        query = query.filter(models.Transaction.date <= filters.end_date)

    # Фільтр за категорією
    if filters.category_id is not None:
        query = query.filter(models.Transaction.category_id == filters.category_id)

    # Фільтр за сумою
    if filters.min_amount is not None:
        query = query.filter(models.Transaction.amount >= filters.min_amount)
    if filters.max_amount is not None:
        query = query.filter(models.Transaction.amount <= filters.max_amount)

    # Пошук за назвою
    if filters.title:
        query = query.filter(models.Transaction.title.ilike(f"%{filters.title}%"))

    return query.order_by(models.Transaction.date.desc()).offset(skip).limit(limit).all()

# ПОКАЗАТИ ТРАНЗАКЦІЇ ПОТОЧНОГО КОРИСТУВАЧА ЗА КАТЕГОРІЄЮ
def get_transactions_by_category(db: Session, category_id: int):
    return db.query(models.Transaction).filter(models.Transaction.category_id == category_id).all()

def get_transaction(db: Session, transaction_id: int, user_id: int) -> Optional[models.Transaction]:
    return db.query(models.Transaction).filter(models.Transaction.id == transaction_id, models.Transaction.user_id == user_id).first()

# ПОКАЗАТИ БАЛАНС ПОТОЧНОГО КОРИСТУВАЧА
def get_user_balance(db: Session, user_id: int) -> float:
    total = db.query(func.coalesce(func.sum(models.Transaction.amount), 0.0)).filter(models.Transaction.user_id == user_id).scalar()
    return float(total)

# Update get_category_transactions to support pagination
def get_category_transactions(db: Session, category_id: int, user_id: int, skip: int = 0, limit: int = 100) -> list[models.Transaction]:
    cat = db.query(models.Category).filter(models.Category.id == category_id, models.Category.user_id == user_id).first()
    if not cat:
        return []
    return db.query(models.Transaction).filter(models.Transaction.category_id == category_id).order_by(models.Transaction.date.desc()).offset(skip).limit(limit).all()