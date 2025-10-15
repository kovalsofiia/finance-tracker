from pydantic import BaseModel, EmailStr, validator
from datetime import datetime
from typing import Optional

# ---- Users ----
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    username: str

    @validator("password")
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v

class UserRead(BaseModel):
    id: int
    email: EmailStr
    username: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        orm_mode = True

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    password: Optional[str] = None

# ---- Categories ----
class CategoryCreate(BaseModel):
    name: str

class CategoryRead(BaseModel):
    id: int
    name: str
    user_id: int
    created_at: datetime

    class Config:
        orm_mode = True

class CategoryUpdate(BaseModel):
    name: Optional[str] = None

# ---- Transactions ----
class TransactionCreate(BaseModel):
    title: Optional[str]
    amount: float
    category_id: Optional[int]
    date: Optional[datetime]
    notes: Optional[str]

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
        orm_mode = True

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
        orm_mode = True