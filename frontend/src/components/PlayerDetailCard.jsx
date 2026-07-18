import { useEffect, useState } from "react";
import { getPlayerDetail } from "../api/client";

const SILHOUETTE =
  "data:image/svg+xml;utf8," +
  encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" fill="#171f2b"/><circle cx="32" cy="24" r="12" fill="#2a3444"/><path d="M10 58c0-14 10-22 22-22s22 8 22 22" fill="#2a3444"/></svg>`
  );

export default function PlayerDetailCard({ fixtureId, player }) {
  const [analysis, setAnalysis] = useState(null);
  const [status, setStatus] = useState("idle"); // idle | loading | done | error

  useEffect(() => {
    setAnalysis(null);
    setStatus("idle");
  }, [player?.player_id]);

  if (!player) return null;

  const loadAnalysis = async () => {
    setStatus("loading");
    try {
      const data = await getPlayerDetail(fixtureId, player.player_id);
      setAnalysis(data.analysis);
      setStatus("done");
    } catch {
      setStatus("error");
    }
  };

  return (
    <div className="panel" style={{ display: "flex", gap: 16 }}>
      <img
        src={player.photo_url || SILHOUETTE}
        onError={(e) => {
          e.currentTarget.onerror = null;
          e.currentTarget.src = SILHOUETTE;
        }}
        alt={player.name}
        style={{
          width: 72,
          height: 72,
          borderRadius: "50%",
          objectFit: "cover",
          background: "var(--bg-panel-raised)",
          border: "2px solid var(--border)",
          flexShrink: 0,
        }}
      />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          {player.team_logo && (
            <img src={player.team_logo} alt="" style={{ width: 20, height: 20 }} />
          )}
          <strong>{player.name}</strong>
        </div>
        <div style={{ color: "var(--text-dim)", fontSize: "0.82rem", marginTop: 2 }}>
          {player.position} · {player.team_name} · {player.minutes}&apos;
        </div>

        {status === "idle" && (
          <button
            onClick={loadAnalysis}
            style={{
              marginTop: 10,
              background: "var(--bg-panel-raised)",
              border: "1px solid var(--border)",
              color: "var(--text)",
              borderRadius: 8,
              padding: "6px 12px",
              fontSize: "0.82rem",
              cursor: "pointer",
            }}
          >
            Analyse IA de ce joueur
          </button>
        )}
        {status === "loading" && (
          <p style={{ color: "var(--text-dim)", marginTop: 10 }}>Analyse en cours…</p>
        )}
        {status === "error" && (
          <p style={{ color: "var(--red)", marginTop: 10 }}>Analyse indisponible pour le moment.</p>
        )}
        {status === "done" && (
          <p style={{ marginTop: 10, lineHeight: 1.55 }}>{analysis}</p>
        )}
      </div>
    </div>
  );
}
