import { useState } from "react";
import { getPlayerHistory, getTeamHistory } from "../api/client";
import RadarOverlay from "../components/RadarOverlay";
import TeamCompare from "../components/TeamCompare";

export default function ComparePage() {
  const [mode, setMode] = useState("players"); // players | teams
  const [idA, setIdA] = useState("");
  const [idB, setIdB] = useState("");
  const [entityA, setEntityA] = useState(null);
  const [entityB, setEntityB] = useState(null);
  const [status, setStatus] = useState("idle"); // idle | loading | done | error
  const [errorMessage, setErrorMessage] = useState("");

  const switchMode = (nextMode) => {
    setMode(nextMode);
    setStatus("idle");
    setEntityA(null);
    setEntityB(null);
    setIdA("");
    setIdB("");
  };

  const handleCompare = async (e) => {
    e.preventDefault();
    setStatus("loading");
    setErrorMessage("");
    try {
      const fetchFn = mode === "players" ? getPlayerHistory : getTeamHistory;
      const [a, b] = await Promise.all([fetchFn(idA), fetchFn(idB)]);
      setEntityA(a);
      setEntityB(b);
      setStatus("done");
    } catch {
      setErrorMessage(
        mode === "players"
          ? "Un des deux joueurs n'a pas d'historique — il doit d'abord apparaître dans un match analysé."
          : "Une des deux équipes n'a pas d'historique — analyse d'abord un de ses matchs."
      );
      setStatus("error");
    }
  };

  return (
    <>
      <header style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: "1.6rem" }}>Comparateur</h1>
        <p style={{ color: "var(--text-dim)", marginTop: 4 }}>
          {mode === "players"
            ? "Compare le profil statistique de deux joueurs déjà analysés (ID visible sur leur fiche)."
            : "Compare le bilan de deux équipes déjà analysées (ID visible dans l'URL de leur fiche)."}
        </p>

        <div style={{ display: "flex", gap: 8, marginTop: 14 }}>
          <button onClick={() => switchMode("players")} style={toggleStyle(mode === "players")}>
            Joueurs
          </button>
          <button onClick={() => switchMode("teams")} style={toggleStyle(mode === "teams")}>
            Équipes
          </button>
        </div>

        <form onSubmit={handleCompare} style={{ display: "flex", gap: 10, marginTop: 16, alignItems: "center" }}>
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
          <button type="submit" style={buttonStyle}>
            Comparer
          </button>
        </form>
      </header>

      {status === "loading" && <p>Chargement…</p>}
      {status === "error" && <p style={{ color: "var(--red)" }}>{errorMessage}</p>}

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
