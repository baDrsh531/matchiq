import { useEffect, useState } from "react";
import { getMatch, getPlayers } from "./api/client";
import MOTMCard from "./components/MOTMCard";
import RankingList from "./components/RankingList";
import RadarComparison from "./components/RadarComparison";
import Timeline from "./components/Timeline";
import AIPanel from "./components/AIPanel";

function App() {
  const [fixtureIdInput, setFixtureIdInput] = useState("");
  const [fixtureId, setFixtureId] = useState(null);
  const [match, setMatch] = useState(null);
  const [players, setPlayers] = useState([]);
  const [selectedPlayerId, setSelectedPlayerId] = useState(null);
  const [status, setStatus] = useState("idle"); // idle | loading | error | done
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    if (!fixtureId) return;

    let cancelled = false;
    setStatus("loading");
    setErrorMessage("");

    Promise.all([getMatch(fixtureId), getPlayers(fixtureId)])
      .then(([matchData, playersData]) => {
        if (cancelled) return;
        setMatch(matchData);
        setPlayers(playersData.players);
        setSelectedPlayerId(playersData.players[0]?.player_id ?? null);
        setStatus("done");
      })
      .catch((err) => {
        if (cancelled) return;
        setErrorMessage(
          err.response?.data?.detail || "Impossible de charger ce match."
        );
        setStatus("error");
      });

    return () => {
      cancelled = true;
    };
  }, [fixtureId]);

  const handleLoadMatch = (e) => {
    e.preventDefault();
    const id = parseInt(fixtureIdInput, 10);
    if (!Number.isNaN(id)) setFixtureId(id);
  };

  const motm = players[0];
  const selectedPlayer =
    players.find((p) => p.player_id === selectedPlayerId) || null;

  return (
    <>
      <header style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: "1.9rem" }}>
          Match<span style={{ color: "var(--gold)" }}>IQ</span>
        </h1>
        <p style={{ color: "var(--text-dim)", marginTop: 4 }}>
          Analyse de match par ML + LLM
        </p>

        <form
          onSubmit={handleLoadMatch}
          style={{ display: "flex", gap: 8, marginTop: 16 }}
        >
          <input
            value={fixtureIdInput}
            onChange={(e) => setFixtureIdInput(e.target.value)}
            placeholder="ID de fixture (ex: 1035038)"
            style={{
              flex: 1,
              maxWidth: 320,
              padding: "10px 12px",
              background: "var(--bg-panel)",
              border: "1px solid var(--border)",
              borderRadius: 8,
              color: "var(--text)",
            }}
          />
          <button
            type="submit"
            style={{
              padding: "10px 18px",
              background: "var(--gold)",
              border: "none",
              borderRadius: 8,
              color: "#141414",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            Charger le match
          </button>
        </form>
      </header>

      {status === "loading" && <p>Chargement du match…</p>}
      {status === "error" && <p style={{ color: "var(--red)" }}>{errorMessage}</p>}

      {status === "done" && match && (
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          <div className="panel" style={{ display: "flex", justifyContent: "space-between" }}>
            <div>
              <div style={{ fontWeight: 600 }}>{match.teams?.home?.name}</div>
              <div style={{ color: "var(--text-dim)", fontSize: "0.8rem" }}>Domicile</div>
            </div>
            <div className="mono" style={{ fontSize: "1.8rem" }}>
              {match.goals?.home} - {match.goals?.away}
            </div>
            <div style={{ textAlign: "right" }}>
              <div style={{ fontWeight: 600 }}>{match.teams?.away?.name}</div>
              <div style={{ color: "var(--text-dim)", fontSize: "0.8rem" }}>Extérieur</div>
            </div>
          </div>

          <MOTMCard player={motm} />

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
            <RankingList
              players={players}
              selectedId={selectedPlayerId}
              onSelect={setSelectedPlayerId}
            />
            <RadarComparison player={selectedPlayer} />
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
            <Timeline events={match.events} />
            <AIPanel fixtureId={fixtureId} />
          </div>
        </div>
      )}
    </>
  );
}

export default App;
