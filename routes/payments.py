from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from datetime import datetime

from database.db import get_db
from database.models import (
    Order, Payment, PaymentSplit, PaymentStatus, 
    PaymentPurpose, AccountBalance, DebtRecord
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
    Ex: Le client paie 10 000 FCFA au livreur.
    """
    # 1. Vérifier si la commande existe
    order_query = await db.execute(select(Order).where(Order.id == payment_data.order_id))
    order = order_query.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Commande non trouvée")

    # 2. Créer l'enregistrement du paiement principal
    new_payment = Payment(
        order_id=payment_data.order_id,
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

    # 3. Logique de Split (Simplifiée pour l'exemple)
    # Imaginons : 80% vendeur, 15% livreur, 5% plateforme
    amounts = {
        "ITEM_PRICE": payment_data.amount_total * 0.8,
        "DELIVERY_FEE": payment_data.amount_total * 0.15,
        "PLATFORM_COMMISSION": payment_data.amount_total * 0.05
    }

    for purpose_code, amount in amounts.items():
        # On cherche l'ID du but (purpose)
        p_query = await db.execute(select(PaymentPurpose).where(PaymentPurpose.code == purpose_code))
        purpose = p_query.scalar_one_or_none()
        
        if purpose:
            split = PaymentSplit(
                payment_id=new_payment.id,
                purpose_id=purpose.id,
                amount=amount,
                settled=False # Sera marqué true lors du virement réel
            )
            db.add(split)

    # 4. Mise à jour de la dette du livreur (s'il a encaissé du cash)
    # Si le livreur (agent) a collecté l'argent, il doit cet argent à la plateforme
    if order.delivery_agent_id:
        debt = DebtRecord(
            debtor_id=order.delivery_agent_id,
            order_id=order.id,
            amount=payment_data.amount_total,
            reason=f"Encaissement Cash commande {order.id}",
            settled=False
        )
        db.add(debt)

    await db.commit()
    await db.refresh(new_payment)
    return new_payment

@router.get("/balances/{user_id}", response_model=schemas.AccountBalanceOut)
async def get_user_balance(user_id: UUID, db: AsyncSession = Depends(get_db)):
    """Récupère le solde disponible et les dettes d'un utilisateur."""
    query = await db.execute(select(AccountBalance).where(AccountBalance.user_id == user_id))
    balance = query.scalar_one_or_none()
    
    if not balance:
        raise HTTPException(status_code=404, detail="Compte non trouvé")
    return balance
