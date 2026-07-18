import { useState } from "react";
import { getPlayerHistory } from "../api/client";
import RadarOverlay from "../components/RadarOverlay";

export default function ComparePage() {
  const [idA, setIdA] = useState("");
  const [idB, setIdB] = useState("");
  const [playerA, setPlayerA] = useState(null);
  const [playerB, setPlayerB] = useState(null);
  const [status, setStatus] = useState("idle"); // idle | loading | done | error
  const [errorMessage, setErrorMessage] = useState("");

  const handleCompare = async (e) => {
    e.preventDefault();
    setStatus("loading");
    setErrorMessage("");
    try {
      const [a, b] = await Promise.all([getPlayerHistory(idA), getPlayerHistory(idB)]);
      setPlayerA(a);
      setPlayerB(b);
      setStatus("done");
    } catch {
      setErrorMessage(
        "Un des deux joueurs n'a pas d'historique — il doit d'abord apparaître dans un match analysé."
      );
      setStatus("error");
    }
  };

  return (
    <>
      <header style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: "1.6rem" }}>Comparateur de joueurs</h1>
        <p style={{ color: "var(--text-dim)", marginTop: 4 }}>
          Compare le profil statistique de deux joueurs déjà analysés (ID visible sur leur fiche).
        </p>

        <form onSubmit={handleCompare} style={{ display: "flex", gap: 10, marginTop: 16, alignItems: "center" }}>
          <input
            value={idA}
            onChange={(e) => setIdA(e.target.value)}
            placeholder="ID joueur A"
            style={inputStyle}
          />
          <span style={{ color: "var(--text-dim)" }}>vs</span>
          <input
            value={idB}
            onChange={(e) => setIdB(e.target.value)}
            placeholder="ID joueur B"
            style={inputStyle}
          />
          <button type="submit" style={buttonStyle}>
            Comparer
          </button>
        </form>
      </header>

      {status === "loading" && <p>Chargement…</p>}
      {status === "error" && <p style={{ color: "var(--red)" }}>{errorMessage}</p>}

      {status === "done" && playerA && playerB && (
        <div className="panel">
          <div style={{ display: "flex", justifyContent: "space-around", marginBottom: 10 }}>
            <div style={{ textAlign: "center" }}>
              <strong style={{ color: "var(--gold)" }}>{playerA.name}</strong>
              <div className="mono" style={{ fontSize: "1.4rem" }}>{playerA.average_score.toFixed(1)}</div>
            </div>
            <div style={{ textAlign: "center" }}>
              <strong style={{ color: "var(--blue)" }}>{playerB.name}</strong>
              <div className="mono" style={{ fontSize: "1.4rem" }}>{playerB.average_score.toFixed(1)}</div>
            </div>
          </div>
          <RadarOverlay playerA={playerA} playerB={playerB} />
        </div>
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
