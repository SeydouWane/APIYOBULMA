from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.db import SessionLocal
from database.models import User
from services.security import verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["Auth"])

async def get_db():
    async with SessionLocal() as session:
        yield session

@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    # On cherche l'utilisateur par son numéro de téléphone (utilisé comme username)
    result = await db.execute(select(User).where(User.phone_number == form_data.username))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(status_code=401, detail="Identifiants incorrects")
    
    # Génération du token avec l'ID et le rôle pour les permissions futures
    access_token = create_access_token(data={"sub": str(user.id), "role": user.role})
    return {"access_token": access_token, "token_type": "bearer"}
