from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from datetime import datetime

from database.db import get_db
# Changement : Order -> Delivery
from database.models import (
    Delivery, Payment, PaymentSplit, PaymentStatus, 
    PaymentPurpose, AccountBalance, DebtRecord, User
)
from models import schemas

router = APIRouter(
    prefix="/payments",
    tags=["Finance & Payments"]
)

@router.post("/collect", response_model=schemas.PaymentOut)
async def collect_payment(
    payment_data: schemas.PaymentCreate, 
    db: AsyncSession = Depends(get_db)
):
    """
    Enregistre un paiement et ventile automatiquement les montants.
    Met à jour la balance du vendeur et la dette du livreur.
    """
    # 1. Vérifier si la livraison existe (Changement : Order -> Delivery)
    delivery_query = await db.execute(select(Delivery).where(Delivery.id == payment_data.delivery_id))
    delivery = delivery_query.scalar_one_or_none()
    if not delivery:
        raise HTTPException(status_code=404, detail="Livraison non trouvée")

    # 2. Créer l'enregistrement du paiement principal (Changement : delivery_id)
    new_payment = Payment(
        delivery_id=payment_data.delivery_id,
        payment_method_id=payment_data.payment_method_id,
        amount_total=payment_data.amount_total,
        paid_by_id=payment_data.paid_by_id,
        received_by_id=payment_data.received_by_id,
        collected_by_id=payment_data.collected_by_id,
        status=PaymentStatus.PAID,
        paid_at=datetime.utcnow()
    )
    db.add(new_payment)
    await db.flush()

    # 3. Logique de Split et mise à jour de la balance du vendeur
    amounts = {
        "ITEM_PRICE": payment_data.amount_total * 0.85, # 85% pour le vendeur
        "DELIVERY_FEE": payment_data.amount_total * 0.10,
        "PLATFORM_COMMISSION": payment_data.amount_total * 0.05
    }

    for purpose_code, amount in amounts.items():
        p_query = await db.execute(select(PaymentPurpose).where(PaymentPurpose.code == purpose_code))
        purpose = p_query.scalar_one_or_none()
        
        if purpose:
            split = PaymentSplit(
                payment_id=new_payment.id,
                purpose_id=purpose.id,
                amount=amount,
                settled=(purpose_code == "ITEM_PRICE")
            )
            db.add(split)
            
            # MISE À JOUR : Créditer la balance disponible du VENDEUR
            if purpose_code == "ITEM_PRICE" and delivery.seller_id:
                bal_query = await db.execute(select(AccountBalance).where(AccountBalance.user_id == delivery.seller_id))
                seller_balance = bal_query.scalar_one_or_none()
                if seller_balance:
                    seller_balance.available_balance += amount

    # 4. Mise à jour de la dette du livreur (Changement : delivery_id et delivery_agent_id)
    if delivery.delivery_agent_id:
        debt = DebtRecord(
            debtor_id=delivery.delivery_agent_id,
            delivery_id=delivery.id,
            amount=payment_data.amount_total,
            reason=f"Encaissement Cash livraison {delivery.id}",
            settled=False
        )
        db.add(debt)
        
        # Augmenter sa dette globale
        agent_bal_query = await db.execute(select(AccountBalance).where(AccountBalance.user_id == delivery.delivery_agent_id))
        agent_balance = agent_bal_query.scalar_one_or_none()
        if agent_balance:
            agent_balance.debt_balance += payment_data.amount_total

    await db.commit()
    await db.refresh(new_payment)
    return new_payment

@router.get("/balances/{user_id}", response_model=schemas.AccountBalanceOut)
async def get_user_balance(user_id: UUID, db: AsyncSession = Depends(get_db)):
    """Récupère le solde disponible et les dettes d'un utilisateur."""
    query = await db.execute(select(AccountBalance).where(AccountBalance.user_id == user_id))
    balance = query.scalar_one_or_none()
    
    if not balance:
        raise HTTPException(status_code=404, detail="Compte financier non trouvé")
    return balance

@router.post("/withdraw", status_code=status.HTTP_202_ACCEPTED)
async def request_withdrawal(
    withdrawal_in: schemas.WithdrawalRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Demande de retrait vers Wave ou Orange Money.
    """
    result = await db.execute(select(AccountBalance).where(AccountBalance.user_id == withdrawal_in.user_id))
    balance = result.scalar_one_or_none()

    if not balance or balance.available_balance < withdrawal_in.amount:
        raise HTTPException(
            status_code=400, 
            detail=f"Solde insuffisant. Disponible: {balance.available_balance if balance else 0} FCFA"
        )

    # Déduction immédiate pour éviter le double retrait (sécurité)
    balance.available_balance -= withdrawal_in.amount
    
    await db.commit()
    
    return {
        "status": "PENDING",
        "message": f"Demande de retrait de {withdrawal_in.amount} FCFA enregistrée vers {withdrawal_in.phone_number} ({withdrawal_in.provider}).",
        "new_balance": balance.available_balance
    }
