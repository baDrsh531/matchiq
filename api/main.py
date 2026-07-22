import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import matches, players, profiles, reports, search, standings
from config import DEMO_MODE
from persistence.database import init_db

app = FastAPI(title="MatchIQ API", version="0.1.0")

# En local, le front tourne sur Vite (5173). En démo déployée, il vit sur un
# autre domaine : sans son origine ici, le navigateur bloquerait chaque appel.
# CORS_ORIGINS accepte une liste séparée par des virgules.
_DEFAULT_ORIGINS = ["http://localhost:5173", "http://localhost:3000"]
_EXTRA_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_DEFAULT_ORIGINS + _EXTRA_ORIGINS,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


app.include_router(matches.router)
app.include_router(players.router)
app.include_router(reports.router)
app.include_router(profiles.router)
app.include_router(standings.router)
app.include_router(search.router)


@app.get("/health")
def health():
    """Sonde de santé, utilisée aussi par les hébergeurs pour le keep-alive.

    Expose `demo_mode` pour qu'un client sache si l'instance est en lecture
    seule (aucun nouveau match analysable, aucun rapport générable).
    """
    return {"status": "ok", "demo_mode": DEMO_MODE}
