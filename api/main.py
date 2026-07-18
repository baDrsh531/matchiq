from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import matches, players, profiles, reports, search, standings
from persistence.database import init_db

app = FastAPI(title="MatchIQ API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
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
    return {"status": "ok"}
