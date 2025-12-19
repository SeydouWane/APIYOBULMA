from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from database.db import get_db
from models.schemas import OrderCreate
from database.models import OrderDB


router = APIRouter()

@router.post("/orders/")
async def create_order(order_data: OrderCreate, db: AsyncSession = Depends(get_db)):
    new_order = OrderDB(
        **order_data.dict(),
        seller_id="TEMP_SELLER_ID", 
        otp="1234" 
    )
    
    db.add(new_order)
    await db.commit()
    await db.refresh(new_order)
    
    return new_order
