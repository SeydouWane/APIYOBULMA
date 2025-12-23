from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from passlib.context import CryptContext
from uuid import UUID

from database.db import get_db
from database.models import User, AccountBalance, Role
from models import schemas
from fastapi import UploadFile, File
from services.security import get_password_hash # Import centralisé

# Configuration du hachage de mot de passe
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter(
    prefix="/users",
    tags=["Users & Profiles"]
)

def get_password_hash(password):
    return pwd_context.hash(password)

@router.post("/register", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
async def register_user(user_in: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    """
    Inscrit un nouvel utilisateur (Vendeur, Livreur ou Client) 
    et initialise son compte financier.
    """
    # 1. Vérifier si le numéro de téléphone existe déjà
    query = select(User).where(User.phone_number == user_in.phone_number)
    result = await db.execute(query)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=400, 
            detail="Un utilisateur avec ce numéro de téléphone existe déjà."
        )

    # 2. Créer l'utilisateur avec mot de passe haché
    hashed_password = get_password_hash(user_in.password)
    new_user = User(
        first_name=user_in.first_name,
        last_name=user_in.last_name,
        phone_number=user_in.phone_number,
        email=user_in.email,
        password=hashed_password,
        role=user_in.role
    )
    
    db.add(new_user)
    await db.flush() # Récupérer l'ID sans commiter tout de suite

    # 3. Initialiser le solde (AccountBalance) pour les Vendeurs et Livreurs
    if user_in.role in [Role.SELLER, Role.DELIVERY_AGENT]:
        new_balance = AccountBalance(
            user_id=new_user.id,
            available_balance=0.0,
            debt_balance=0.0
        )
        db.add(new_balance)

    await db.commit()
    await db.refresh(new_user)
    return new_user

@router.get("/{user_id}", response_model=schemas.UserOut)
async def get_user_profile(user_id: UUID, db: AsyncSession = Depends(get_db)):
    """Récupère les informations publiques et de profil d'un utilisateur."""
    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    return user

@router.patch("/{user_id}/restriction", response_model=schemas.UserOut)
async def update_restriction(
    user_id: UUID, 
    restriction: schemas.AccountRestriction, 
    db: AsyncSession = Depends(get_db)
):
    """Permet à un ADMIN de bloquer ou limiter un compte (ex: fraude ou dette trop élevée)."""
    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    
    user.restriction = restriction
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/me/upload-doc")
async def upload_document(
    doc_type: str, # "identity" ou "vehicle"
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 1. Envoyer le fichier vers un Cloud (ex: Cloudinary)
    file_url = await upload_to_cloud(file)
    
    # 2. Mettre à jour l'URL dans le modèle User
    if doc_type == "identity":
        current_user.identity_document_url = file_url
    else:
        current_user.vehicle_registration_url = file_url
        
    await db.commit()
    return {"url": file_url}











@router.post("/register", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
async def register_user(user_in: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    # 1. Vérification doublon
    result = await db.execute(select(User).where(User.phone_number == user_in.phone_number))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Numéro déjà utilisé.")

    # 2. Création avec mot de passe sécurisé
    new_user = User(
        **user_in.dict(exclude={"password"}), # On unpack les autres champs
        password=get_password_hash(user_in.password)
    )
    
    db.add(new_user)
    await db.flush() 

    # 3. Initialisation financière (Vendeurs et Livreurs uniquement)
    if user_in.role in [Role.SELLER, Role.DELIVERY_AGENT]:
        db.add(AccountBalance(user_id=new_user.id))

    await db.commit()
    await db.refresh(new_user)
    return new_user

@router.post("/me/upload-doc")
async def upload_document(
    doc_type: str, 
    file: UploadFile = File(...),
    # current_user: User = Depends(get_current_user), # À décommenter quand Auth sera prêt
    db: AsyncSession = Depends(get_db)
):
    # Simulation d'URL (En production, envoyez vers Cloudinary/S3)
    file_url = f"https://storage.yobulma.sn/docs/{file.filename}"
    return {"url": file_url, "status": "Uploaded (Simulation)"}
