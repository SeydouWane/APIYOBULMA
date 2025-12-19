from fastapi import FastAPI
from routes import orders

app = FastAPI(
    title="YOBULMA API", 
    description="Backend de livraison groupée Dakar"
)

# Inclusion du routeur des commandes
app.include_router(orders.router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "Bienvenue sur l'API Yobulma - Team Nexus Force"}
