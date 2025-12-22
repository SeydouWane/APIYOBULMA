from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


from database.db import engine, Base
import database.models as models

from routes import orders


Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="YOBULMA API",
    description="Backend de livraison groupée - Solution d'optimisation logistique",
    version="1.0.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclusion des routeurs
app.include_router(orders.router)

@app.get("/", tags=["Root"])
def read_root():
    return {
        "project": "Yobulma",
        "team": "Nexus Force",
        "status": "online",
        "message": "Bienvenue sur l'API Yobulma - Le futur de la livraison groupée."
    }

if __name__ == "__main__":
    import uvicorn
    # Lancement du serveur (utile pour le debug local)
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)