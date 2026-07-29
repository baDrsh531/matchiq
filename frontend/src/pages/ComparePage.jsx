import { useEffect, useState } from "react";
import {
  getMatchComparison,
  getPlayerHistory,
  getRecentMatches,
  getTeamHistory,
} from "../api/client";
import RadarOverlay from "../components/RadarOverlay";
import TeamCompare from "../components/TeamCompare";
import MatchCompare from "../components/MatchCompare";

const SUBS = {
  players: "Compare le profil statistique de deux joueurs déjà analysés (ID visible sur leur fiche).",
  teams: "Compare le bilan de deux équipes déjà analysées (ID visible dans l'URL de leur fiche).",
  matches: "Compare deux matchs analysés : scores, homme du match et joueurs communs (idéal entre deux rencontres d'une même affiche).",
};

export default function ComparePage() {
  const [mode, setMode] = useState("players"); // players | teams | matches
  const [idA, setIdA] = useState("");
  const [idB, setIdB] = useState("");
  const [entityA, setEntityA] = useState(null);
  const [entityB, setEntityB] = useState(null);
  const [comparison, setComparison] = useState(null); // mode matches
  const [matchList, setMatchList] = useState([]);
  const [status, setStatus] = useState("idle"); // idle | loading | done | error
  const [errorMessage, setErrorMessage] = useState("");

  // Charge la liste des matchs analysés pour les menus déroulants du mode "matchs".
  useEffect(() => {
    if (mode === "matches" && matchList.length === 0) {
      getRecentMatches(50)
        .then((d) => setMatchList(d.matches))
        .catch(() => setMatchList([]));
    }
  }, [mode, matchList.length]);

  const switchMode = (nextMode) => {
    setMode(nextMode);
    setStatus("idle");
    setEntityA(null);
    setEntityB(null);
    setComparison(null);
    setIdA("");
    setIdB("");
  };

  const handleCompare = async (e) => {
    e.preventDefault();
    setStatus("loading");
    setErrorMessage("");
    try {
      if (mode === "matches") {
        setComparison(await getMatchComparison(idA, idB));
      } else {
        const fetchFn = mode === "players" ? getPlayerHistory : getTeamHistory;
        const [a, b] = await Promise.all([fetchFn(idA), fetchFn(idB)]);
        setEntityA(a);
        setEntityB(b);
      }
      setStatus("done");
    } catch {
      setErrorMessage(
        {
          players: "Un des deux joueurs n'a pas d'historique — il doit d'abord apparaître dans un match analysé.",
          teams: "Une des deux équipes n'a pas d'historique — analyse d'abord un de ses matchs.",
          matches: "Un des deux matchs n'a pas été analysé.",
        }[mode]
      );
      setStatus("error");
    }
  };

  const matchLabel = (m) =>
    `${m.home_team.name} ${m.goals.home ?? "-"}-${m.goals.away ?? "-"} ${m.away_team.name}`;

  return (
    <>
      <header style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: "1.6rem" }}>Comparateur</h1>
        <p style={{ color: "var(--text-dim)", marginTop: 4 }}>{SUBS[mode]}</p>

        <div style={{ display: "flex", gap: 8, marginTop: 14 }}>
          <button onClick={() => switchMode("players")} style={toggleStyle(mode === "players")}>
            Joueurs
          </button>
          <button onClick={() => switchMode("teams")} style={toggleStyle(mode === "teams")}>
            Équipes
          </button>
          <button onClick={() => switchMode("matches")} style={toggleStyle(mode === "matches")}>
            Matchs
          </button>
        </div>

        <form onSubmit={handleCompare} style={{ display: "flex", gap: 10, marginTop: 16, alignItems: "center", flexWrap: "wrap" }}>
          {mode === "matches" ? (
            <>
              <select value={idA} onChange={(e) => setIdA(e.target.value)} style={selectStyle}>
                <option value="">Match A…</option>
                {matchList.map((m) => (
                  <option key={m.fixture_id} value={m.fixture_id}>{matchLabel(m)}</option>
                ))}
              </select>
              <span style={{ color: "var(--text-dim)" }}>vs</span>
              <select value={idB} onChange={(e) => setIdB(e.target.value)} style={selectStyle}>
                <option value="">Match B…</option>
                {matchList.map((m) => (
                  <option key={m.fixture_id} value={m.fixture_id}>{matchLabel(m)}</option>
                ))}
              </select>
            </>
          ) : (
            <>
              <input
                value={idA}
                onChange={(e) => setIdA(e.target.value)}
                placeholder={mode === "players" ? "ID joueur A" : "ID équipe A"}
                style={inputStyle}
              />
              <span style={{ color: "var(--text-dim)" }}>vs</span>
              <input
                value={idB}
                onChange={(e) => setIdB(e.target.value)}
                placeholder={mode === "players" ? "ID joueur B" : "ID équipe B"}
                style={inputStyle}
              />
            </>
          )}
          <button type="submit" style={buttonStyle} disabled={!idA || !idB}>
            Comparer
          </button>
        </form>
      </header>

      {status === "loading" && <p>Chargement…</p>}
      {status === "error" && <p style={{ color: "var(--red)" }}>{errorMessage}</p>}

      {status === "done" && mode === "matches" && comparison && <MatchCompare data={comparison} />}

      {status === "done" && entityA && entityB && mode === "players" && (
        <div className="panel">
          <div style={{ display: "flex", justifyContent: "space-around", marginBottom: 10 }}>
            <div style={{ textAlign: "center" }}>
              <strong style={{ color: "var(--gold)" }}>{entityA.name}</strong>
              <div className="mono" style={{ fontSize: "1.4rem" }}>{entityA.average_score.toFixed(1)}</div>
            </div>
            <div style={{ textAlign: "center" }}>
              <strong style={{ color: "var(--blue)" }}>{entityB.name}</strong>
              <div className="mono" style={{ fontSize: "1.4rem" }}>{entityB.average_score.toFixed(1)}</div>
            </div>
          </div>
          <RadarOverlay playerA={entityA} playerB={entityB} />
        </div>
      )}

      {status === "done" && entityA && entityB && mode === "teams" && (
        <TeamCompare teamA={entityA} teamB={entityB} />
      )}
    </>
  );
}

const inputStyle = {
  padding: "10px 12px",
  background: "var(--bg-panel)",
  border: "1px solid var(--border)",
  borderRadius: 8,
  color: "var(--text)",
  width: 140,
};

const selectStyle = {
  padding: "10px 12px",
  background: "var(--bg-panel)",
  border: "1px solid var(--border)",
  borderRadius: 8,
  color: "var(--text)",
  maxWidth: 260,
};

const buttonStyle = {
  padding: "10px 18px",
  background: "var(--gold)",
  border: "none",
  borderRadius: 8,
  color: "#141414",
  fontWeight: 600,
  cursor: "pointer",
};

function toggleStyle(active) {
  return {
    padding: "6px 16px",
    borderRadius: 8,
    border: "1px solid var(--border)",
    background: active ? "var(--bg-panel-raised)" : "transparent",
    color: active ? "var(--gold)" : "var(--text-dim)",
    cursor: "pointer",
    fontWeight: active ? 600 : 400,
  };
}
