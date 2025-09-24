from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List

# ---- Users ----
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    username: Optional[str]

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

# ---- Auth token ----
class Token(BaseModel):
    access_token: str
    token_type: str
