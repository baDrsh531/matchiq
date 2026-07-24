# Déployer la démo publique de MatchIQ

## Ce que fait la démo

Une instance publique en **lecture seule** : elle sert uniquement le contenu de
`demo_data/` (cache API, rapports LLM, base SQLite) et refuse tout appel
sortant. Conséquence directe : **aucune clé n'est requise, aucun quota n'est
consommable, aucune facture n'est possible** quoi que fasse un visiteur.

Le verrou est unique et testé : `_get()` dans [ml/ingestion.py](../ml/ingestion.py)
pour API-Football, `generate_report()` dans [llm/llm_client.py](../llm/llm_client.py)
pour Gemini. Les deux lèvent avant toute I/O quand `DEMO_MODE` est actif.
`tests/test_demo_mode.py` le vérifie, y compris qu'aucun client Gemini n'est
même instancié.

## Avant de commencer

Vérifie l'état, ne le suppose pas :

```bash
# le mode démo est-il toujours couvert par les tests ?
.venv/Scripts/python.exe -m pytest tests/test_demo_mode.py -q

# le jeu de démo est-il cohérent (chaque match en base a-t-il son cache) ?
.venv/Scripts/python.exe -c "
import sqlite3, pathlib
c = sqlite3.connect('demo_data/matchiq.db'); raw = pathlib.Path('demo_data/raw')
for fid, h, a in c.execute('select fixture_id, home_team_name, away_team_name from matches'):
    print(fid, h, 'vs', a, '->', 'OK' if (raw/f'{fid}.json').exists() else 'CACHE MANQUANT')
"
```

Un match présent en base sans son JSON dans `demo_data/raw/` s'affichera sur la
page d'accueil puis renverra 503 au clic. C'est le défaut le plus visible d'une
démo, et le plus facile à éviter.

## Étape 1 — Valider le mode démo en local

Toujours reproduire la configuration de production avant de déployer :

```bash
DEMO_MODE=true DATA_DIR=demo_data DATABASE_URL="sqlite:///demo_data/matchiq.db" \
  .venv/Scripts/python.exe -m uvicorn api.main:app --port 8010
```

Puis vérifier les deux moitiés du contrat :

```bash
curl -s localhost:8010/health                    # {"status":"ok","demo_mode":true}
curl -s localhost:8010/matches                   # doit lister les matchs
curl -s localhost:8010/matches/816243/report     # doit renvoyer le rapport caché
curl -s -o /dev/null -w "%{http_code}\n" localhost:8010/matches/999999   # doit valoir 503
curl -s -o /dev/null -w "%{http_code}\n" "localhost:8010/search/teams?query=barcelona"  # 503
```

Ne pas se contenter des 503 : relever le quota API-Football **avant et après**
la série de tests et confirmer qu'il n'a pas bougé. C'est la seule preuve
réelle que rien n'est sorti.

## Étape 2 — Backend sur Render

[render.yaml](../render.yaml) est déjà écrit (plan gratuit, région
Frankfurt, health check sur `/health`).

1. https://dashboard.render.com → **New** → **Blueprint**
2. Connecter le dépôt `baDrsh531/matchiq`, Render détecte `render.yaml`
3. Laisser `DEMO_MODE=true`, **ne renseigner aucune clé**
4. Déployer, attendre que `/health` réponde

Relever l'URL, de la forme `https://matchiq-demo.onrender.com`.

⚠️ **L'offre gratuite met l'instance en veille après 15 min d'inactivité.** Le
premier chargement après une période creuse prend **30 à 60 secondes**. C'est
le principal défaut de cette démo, et il doit être annoncé dans le README
plutôt que subi par un recruteur qui croira le site cassé.

## Étape 3 — Frontend sur Vercel

[frontend/vercel.json](../frontend/vercel.json) gère déjà le rewrite SPA
(sans lui, un rechargement sur `/match/816243` renvoie un 404).

1. https://vercel.com/new → importer le dépôt
2. **Root Directory : `frontend`** — le réglage le plus souvent oublié
3. Variable d'environnement : `VITE_API_BASE_URL` = l'URL Render de l'étape 2
4. Déployer

## Étape 4 — Refermer la boucle CORS

Le backend n'autorise par défaut que `localhost`. Sans cette étape, le front
déployé se fait bloquer par le navigateur sur **chaque** appel — la page
s'affiche mais reste vide, ce qui égare le diagnostic.

Sur Render → Environment → `CORS_ORIGINS` = l'URL Vercel (sans slash final,
plusieurs origines séparées par des virgules), puis redéployer.

Vérifier depuis l'extérieur :

```bash
curl -s -H "Origin: https://<projet>.vercel.app" -D - \
     https://<backend>.onrender.com/matches -o /dev/null | grep -i access-control-allow-origin
```

Absence d'en-tête = CORS toujours fermé.

## Étape 5 — Vérifier comme un visiteur

Ouvrir l'URL Vercel dans une fenêtre privée et parcourir réellement les pages :
accueil, fiche match, rapport IA, comparateur. **Regarder la page** — un backend
en veille ou un CORS fermé produit une page qui se charge sans erreur visible
mais reste désespérément vide.

Puis ajouter le lien en haut du [README](../README.md), avec
l'avertissement sur le réveil de 30 à 60 s.

## Rafraîchir le jeu de démo

Pour ajouter un match à la démo, il faut d'abord l'analyser **en local avec les
vraies clés** (cela consomme du quota), puis recopier ses artefacts :

```bash
# 1. analyser en local (backend normal, sans DEMO_MODE)
curl -s "localhost:8000/matches/<FIXTURE_ID>/players" > /dev/null
curl -s "localhost:8000/matches/<FIXTURE_ID>/report"  > /dev/null

# 2. copier vers le jeu de démo
cp data/raw/<FIXTURE_ID>.json        demo_data/raw/
cp data/processed/<FIXTURE_ID>*.json demo_data/processed/
cp data/matchiq.db                   demo_data/matchiq.db

# 3. revalider la cohérence (voir "Avant de commencer") puis committer
```

`demo_data/` fait exception dans le `.gitignore` (`!demo_data/**`) alors que
`data/` reste exclu : ne pas déplacer cette exception sans vérifier que
`data/matchiq.db` demeure ignoré.

## Diagnostic

| Symptôme | Cause la plus probable |
|---|---|
| Page blanche, aucune donnée | `CORS_ORIGINS` non renseigné sur Render |
| 404 en rechargeant une URL profonde | `vercel.json` absent ou Root Directory ≠ `frontend` |
| Premier chargement très lent | Instance Render en veille (comportement normal du plan gratuit) |
| 503 sur un match visible à l'accueil | Son JSON manque dans `demo_data/raw/` |
| 503 sur « Générer le rapport » | Comportement voulu : la génération LLM est désactivée en démo |
| Le quota API baisse | `DEMO_MODE` n'est pas actif — vérifier `/health` |
