# MatchIQ

Analyse de match football : le ML calcule les scores, le LLM les interprète.

## Backend

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest tests/
.\.venv\Scripts\python.exe -m uvicorn api.main:app --reload --port 8000
```

Remplir `.env` (déjà présent, non commité) :
- `API_FOOTBALL_KEY` — déjà configurée
- `GEMINI_API_KEY` — à renseigner pour activer `/matches/{id}/report` et `/matches/{id}/player/{id}`

## Frontend

```powershell
cd frontend
npm install
npm run dev
```

Sert sur http://localhost:5173, consomme l'API sur http://localhost:8000. App multi-pages
(React Router) avec menu latéral : Accueil, Classement, Comparateur, + fiches Joueur/Équipe/Match.

## Routes API

| Route | Description |
|---|---|
| `GET /matches` | Historique des matchs déjà analysés (page d'accueil) |
| `GET /matches/{fixture_id}` | Infos générales, score, timeline des événements |
| `GET /matches/{fixture_id}/players` | Scores composites de tous les joueurs (triés, MOTM en premier) |
| `GET /matches/{fixture_id}/player/{player_id}` | Détail + analyse LLM d'un joueur (radar chart) |
| `GET /matches/{fixture_id}/report` | Rapport complet (MOTM, joueurs, tactique) — nécessite `GEMINI_API_KEY` |
| `GET /players/{player_id}/history` | Carrière d'un joueur agrégée sur tous les matchs analysés (DB uniquement) |
| `GET /teams/{team_id}/history` | Effectif + matchs d'une équipe agrégés (DB uniquement) |
| `GET /standings?league_id=&season=` | Classement d'une ligue (cache fichier) |
| `GET /standings/leagues` | Ligues supportées pour le sélecteur de classement |

Les réponses API-Football sont cachées dans `data/raw/`, les rapports LLM dans `data/processed/`,
et les résultats calculés (scores, rapports) sont persistés dans `data/matchiq.db` (SQLite) pour
l'historique et les fiches joueur/équipe — aucun appel n'est répété une fois caché.
