@echo off
setlocal
cd /d "%~dp0"

set "NODE_DIR=C:\Program Files\nodejs"
set "PATH=%NODE_DIR%;%PATH%"
set "FALLBACK_PY=C:\Users\sahra\AppData\Local\Programs\Python\Python312\python.exe"

if not exist ".venv\Scripts\python.exe" (
    echo [MatchIQ] Environnement Python introuvable, creation...
    where python >nul 2>nul
    if errorlevel 1 (
        "%FALLBACK_PY%" -m venv .venv
    ) else (
        python -m venv .venv
    )
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
)

if not exist "frontend\node_modules" (
    echo [MatchIQ] Installation des dependances frontend...
    pushd frontend
    call npm install
    popd
)

echo [MatchIQ] Demarrage du backend (FastAPI) sur http://localhost:8000 ...
start "MatchIQ - Backend" cmd /k "cd /d "%~dp0" && .venv\Scripts\python.exe -m uvicorn api.main:app --reload --port 8000"

echo [MatchIQ] Demarrage du frontend (Vite) sur http://localhost:5173 ...
start "MatchIQ - Frontend" cmd /k "cd /d "%~dp0frontend" && set "PATH=%NODE_DIR%;%PATH%" && npm run dev"

timeout /t 4 /nobreak >nul
start "" "http://localhost:5173"

echo [MatchIQ] Lance ! Ferme les deux fenetres de terminal pour arreter l'app.
endlocal
