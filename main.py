from fastapi import FastAPI
from routes import orders

app = FastAPI(title="YOBULMA API", description="Backend de livraison groupée Dakar")

app.include_router(orders.router)

@app.get("/")
def read_root():
    return {"message": "Bienvenue sur l'API Yobulma - Team Nexus Force"}
