import uuid
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from database.db import get_db
from database.models import User, AccountBalance, Role
from models import schemas
from services.security import get_password_hash
from routes.auth import get_current_user

router = APIRouter(
    prefix="/users",
    tags=["Users & Profiles"]
)

# --- FONCTION UTILITAIRE SIMULÉE (À remplacer par Cloudinary/S3 en prod) ---
async def upload_to_cloud(file: UploadFile) -> str:
    # Ici, nous simulons l'upload. En réalité, vous utiliseriez une lib cloud.
    return f"https://storage.yobulma.sn/docs/{uuid.uuid4()}_{file.filename}"

# --- ENDPOINTS ---

@router.post("/register", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
async def register_user(user_in: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    """
    Inscrit un nouvel utilisateur et initialise son compte financier
    si c'est un vendeur ou un livreur.
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
    await db.flush() 

    # 3. Initialiser le solde financier pour les rôles concernés
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
    """Récupère les informations publiques d'un profil."""
    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    return user

@router.post("/me/upload-doc")
async def upload_document(
    doc_type: str, # "identity" ou "vehicle"
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Endpoint sécurisé permettant à l'utilisateur connecté d'uploader
    ses documents justificatifs.
    """
    # 1. Upload simulé
    file_url = await upload_to_cloud(file)
    
    # 2. Mise à jour du modèle utilisateur
    if doc_type == "identity":
        current_user.identity_document_url = file_url
    elif doc_type == "vehicle":
        current_user.vehicle_registration_url = file_url
    else:
        raise HTTPException(status_code=400, detail="Type de document invalide")
        
    await db.commit()
    await db.refresh(current_user)
    return {"url": file_url, "message": "Document mis à jour avec succès"}

@router.patch("/{user_id}/restriction", response_model=schemas.UserOut)
async def update_restriction(
    user_id: UUID, 
    restriction: schemas.AccountRestriction, 
    db: AsyncSession = Depends(get_db)
):
    """Action administrative pour restreindre un compte."""
    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    
    user.restriction = restriction
    await db.commit()
    await db.refresh(user)
    return user
