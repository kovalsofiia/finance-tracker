from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime
from typing import Optional

class TransactionFilter(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    category_id: Optional[int] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    title: Optional[str] = None

# ---- Users ----
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    username: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Пароль має містити щонайменше 8 символів")
        return v
    
class UserRead(BaseModel):
    id: int
    email: EmailStr
    username: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    password: Optional[str] = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if v is None:
            return v  # Дозволяємо не змінювати пароль
        if len(v) < 8:
            raise ValueError("Пароль має містити щонайменше 8 символів")
        return v

# ---- Categories ----
class CategoryBase(BaseModel):
    name: str
    parent_id: Optional[int] = None

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    parent_id: Optional[int] = None  # Дозволяємо змінювати батька


# ---- Transactions ----
class TransactionCreate(BaseModel):
    title: Optional[str]
    amount: float
    category_id: Optional[int] = None
    date: Optional[datetime] = None   # Optional + datetime
    notes: Optional[str] = None       # Optional!

class TransactionRead(BaseModel):
    id: int
    user_id: int
    category_id: Optional[int]
    title: Optional[str]
    amount: float
    date: datetime
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class TransactionUpdate(BaseModel):
    title: Optional[str] = None
    amount: Optional[float] = None
    category_id: Optional[int] = None
    date: Optional[datetime] = None
    notes: Optional[str] = None

class CategoryRead(BaseModel):
    id: int
    name: str
    user_id: int
    parent_id: Optional[int]
    created_at: datetime
    children: list['CategoryRead'] = []
    transactions: list['TransactionRead'] = []  # ← ДОДАЄМО

    class Config:
        from_attributes = True

# ---- Auth token ----
class Token(BaseModel):
    access_token: str
    token_type: str

# ---- Balance ----
class BalanceRead(BaseModel):
    balance: float
    currency: str = "USD"  # За замовчуванням, можна зробити конфігурацією
    updated_at: datetime

    class Config:
        from_attributes = True


# MKR-1
# Libraries

class LibraryCreate(BaseModel):
    library_name: str
    city: str
    books_amount: int
    visitors_per_year: int

    @field_validator("books_amount", "visitors_per_year")
    @classmethod
    def non_negative(cls, v):
        if v < 0:
            raise ValueError("Кількість книг та відвідувачів не може бути від'ємною")
        return v

    @field_validator("library_name", "city")
    @classmethod
    def not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Назва бібліотеки та місто не можуть бути порожніми")
        return v.strip()

    @field_validator("library_name", "city")
    @classmethod
    def max_length(cls, v):
        if len(v) > 100:
            raise ValueError("Поле не може перевищувати 100 символів")
        return v

class LibraryRead(BaseModel):
    id: int
    library_name: str
    city: str
    books_amount: int
    visitors_per_year: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class LibraryUpdate(BaseModel):
    library_name: Optional[str] = None
    city: Optional[str] = None
    books_amount: Optional[int] = None
    visitors_per_year: Optional[int] = None


class LibraryFilter(BaseModel):
    search: Optional[str] = None
    city: Optional[str] = None
    min_books: Optional[int] = None
    sort_by: Optional[str] = None  # "name", "books", "visitors", "created"
    sort_order: Optional[str] = "desc"  # "asc" or "desc"


class LibraryStats(BaseModel):
    total_libraries: int
    total_books: int
    total_visitors: int


# Оновлюємо рекурсію
CategoryRead.model_rebuild()