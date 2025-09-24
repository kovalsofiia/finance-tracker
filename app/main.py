from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from . import models, database, schemas, crud, security

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

# Dependency
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Auth / Users ---

# Create user (register)
@app.post("/users/", response_model=schemas.UserRead, status_code=201)
def register_user(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = crud.get_user_by_email(db, user_in.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = crud.create_user(db, user_in)
    return user

# Get all users
@app.get("/users/", response_model=list[schemas.UserRead])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(security.get_current_user)):
    return crud.get_users(db, skip=skip, limit=limit)


# Get current logged-in user
@app.get("/users/me", response_model=schemas.UserRead)
def read_current_user(current_user: models.User = Depends(security.get_current_user)):
    return current_user

# Update current user
@app.put("/users/me", response_model=schemas.UserRead)
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
@app.delete("/users/me", status_code=204)
def delete_current_user(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    crud.delete_user(db, current_user.id)
    return {"detail": "User deleted"}

# Get user by ID
@app.get("/users/{user_id}", response_model=schemas.UserRead)
def read_user(user_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(security.get_current_user)):
    user = crud.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.post("/token", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # OAuth2PasswordRequestForm has fields username & password (we use username for email)
    user = crud.authenticate_user(db, email=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    access_token = security.create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

# --- Categories ---
@app.post("/categories/", response_model=schemas.CategoryRead)
def create_category(cat_in: schemas.CategoryCreate, db: Session = Depends(get_db), current_user: models.User = Depends(security.get_current_user)):
    return crud.create_category(db, current_user.id, cat_in)

@app.get("/users/{user_id}/categories", response_model=list[schemas.CategoryRead])
def read_user_categories(user_id: int, db: Session = Depends(get_db)):
    return crud.get_user_categories(db, user_id)

# --- Transactions ---
@app.post("/transactions/", response_model=schemas.TransactionRead)
def create_transaction(tx_in: schemas.TransactionCreate, db: Session = Depends(get_db), current_user: models.User = Depends(security.get_current_user)):
    # Optional: ensure category belongs to this user
    if tx_in.category_id:
        cat = db.query(models.Category).filter(models.Category.id == tx_in.category_id).first()
        if not cat or cat.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid category")
    tx = crud.create_transaction(db, current_user.id, tx_in)
    return tx

@app.get("/users/me/transactions", response_model=list[schemas.TransactionRead])
def read_my_transactions(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(security.get_current_user)):
    return crud.get_user_transactions(db, current_user.id, skip, limit)

@app.get("/users/me/balance")
def get_my_balance(db: Session = Depends(get_db), current_user: models.User = Depends(security.get_current_user)):
    return {"balance": crud.get_user_balance(db, current_user.id)}
