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
class CategoryCreate(BaseModel):
    name: str

class CategoryRead(BaseModel):
    id: int
    name: str
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class CategoryUpdate(BaseModel):
    name: Optional[str] = None

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