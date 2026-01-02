from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError, jwt
from uuid import UUID
from database.db import get_db
from database.models import User, AccountBalance, Role
from models import schemas
from services.security import SECRET_KEY, ALGORITHM, verify_password, create_access_token, get_password_hash
from fastapi.security import OAuth2PasswordBearer

router = APIRouter(prefix="/auth", tags=["Authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# Configuration JWT
#SECRET_KEY = "votre_secret_key"  # À mettre dans .env
#ALGORITHM = "HS256"

# --- REGISTER ---
@router.post("/register", response_model=schemas.LoginResponse, status_code=status.HTTP_201_CREATED)
async def register(user_in: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    """Inscription d'un nouvel utilisateur."""

    # 1. Vérifier l'existence du numéro
    query = select(User).where(User.phone_number == user_in.phone_number)
    result = await db.execute(query)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Un utilisateur avec ce numéro de téléphone existe déjà."
        )

    # 2. Créer l'utilisateur
    hashed_password = get_password_hash(user_in.password)
    new_user = User(
        first_name=user_in.first_name,
        last_name=user_in.last_name,
        phone_number=user_in.phone_number,
        email=user_in.email,
        password=hashed_password,
        role=user_in.role,
        accepted_terms_of_use=user_in.accepted_terms_of_use,
        accepted_privacy_policy=user_in.accepted_privacy_policy,
        terms_accepted_at=datetime.utcnow() if user_in.accepted_terms_of_use else None
    )

    db.add(new_user)
    await db.flush()

    # 3. Initialiser le solde financier pour vendeurs et livreurs
    if user_in.role in [Role.SELLER, Role.DELIVERY_AGENT]:
        new_balance = AccountBalance(
            user_id=new_user.id,
            available_balance=0.0,
            debt_balance=0.0
        )
        db.add(new_balance)

    await db.commit()
    await db.refresh(new_user)

    # 4. Générer le token JWT
    access_token = create_access_token(data={
        "sub": str(new_user.id),
        "role": str(new_user.role.value)
    })

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": new_user
    }


# --- ENDPOINT DE LOGIN ---
@router.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: AsyncSession = Depends(get_db)
):
    """Endpoint pour obtenir le token JWT (username = phone_number)."""
    # Recherche par numéro de téléphone (username dans le formulaire OAuth2)
    result = await db.execute(select(User).where(User.phone_number == form_data.username))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Numéro de téléphone ou mot de passe incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # On s'assure que user.role est passé en string si c'est une Enum
    access_token = create_access_token(data={
        "sub": str(user.id), 
        "role": str(user.role.value) if hasattr(user.role, 'value') else str(user.role)
    })
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": schemas.UserOut.model_validate(user)
    }

# --- LOGIN (JSON body) ---
@router.post("/login-json", response_model=schemas.LoginResponse)
async def login_json(
        credentials: schemas.LoginRequest,
        db: AsyncSession = Depends(get_db)
):
    """Endpoint de login avec JSON body."""
    result = await db.execute(select(User).where(User.phone_number == credentials.phone_number))
    user = result.scalar_one_or_none()

    if not user or not verify_password(credentials.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Numéro de téléphone ou mot de passe incorrect"
        )

    access_token = create_access_token(data={
        "sub": str(user.id),
        "role": str(user.role.value)
    })

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }

# --- DÉPENDANCE GET_CURRENT_USER ---
async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    """Dépendance pour récupérer l'utilisateur connecté via son JWT."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        user_uuid = UUID(user_id)
    except (JWTError, ValueError):
        raise credentials_exception
        
    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
        
    return user

# --- GET ME ---
@router.get("/me", response_model=schemas.UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    """Récupère les informations de l'utilisateur connecté."""
    return current_user

# --- LOGOUT ---
@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """Déconnexion (côté client, supprime le token)."""
    return {"message": "Déconnexion réussie"}