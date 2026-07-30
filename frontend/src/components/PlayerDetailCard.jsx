import { useEffect, useState } from "react";
import { Link } from "react-router";
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

  const CONFIDENCE_COLOR = { high: "var(--green)", medium: "var(--gold)", low: "var(--red)" };
  const contributions = player.contributions || [];
  const maxAbs = contributions.reduce((m, c) => Math.max(m, Math.abs(c.value)), 0) || 1;

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

        {player.confidence && (
          <div
            title={`Score calculé sur ${player.confidence.minutes} minutes de jeu`}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
              marginTop: 8,
              fontSize: "0.74rem",
              color: "var(--text-dim)",
            }}
          >
            <span
              style={{
                width: 8,
                height: 8,
                borderRadius: "50%",
                background: CONFIDENCE_COLOR[player.confidence.level] || "var(--text-dim)",
              }}
            />
            {player.confidence.label}
          </div>
        )}

        {contributions.length > 0 && (
          <div style={{ marginTop: 14 }}>
            <div
              style={{
                fontSize: "0.72rem",
                textTransform: "uppercase",
                letterSpacing: "0.05em",
                color: "var(--text-dim)",
                marginBottom: 8,
              }}
            >
              Comment se construit ce score
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6, width: "100%" }}>
              {contributions.map((c) => {
                const positive = c.value >= 0;
                const pct = Math.max(Math.round((Math.abs(c.value) / maxAbs) * 100), 3);
                return (
                  <div
                    key={c.category}
                    style={{ display: "flex", alignItems: "center", gap: 8, width: "100%" }}
                  >
                    <span
                      style={{
                        width: "7.5rem",
                        flexShrink: 0,
                        fontSize: "0.78rem",
                        color: "var(--text-dim)",
                        whiteSpace: "nowrap",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                      }}
                    >
                      {c.label}
                    </span>
                    <div
                      style={{
                        flex: 1,
                        minWidth: 32,
                        height: 8,
                        borderRadius: 4,
                        background: "var(--bg-panel-raised)",
                        overflow: "hidden",
                      }}
                    >
                      <div
                        style={{
                          height: "100%",
                          width: `${pct}%`,
                          borderRadius: 4,
                          background: positive ? "var(--green)" : "var(--red)",
                        }}
                      />
                    </div>
                    <span
                      className="mono"
                      style={{
                        width: "3.2rem",
                        flexShrink: 0,
                        fontSize: "0.72rem",
                        textAlign: "right",
                        color: positive ? "var(--green)" : "var(--red)",
                      }}
                    >
                      {positive ? "+" : "−"}
                      {Math.abs(c.value).toFixed(2)}
                    </span>
                  </div>
                );
              })}
            </div>
            <div style={{ fontSize: "0.7rem", color: "var(--text-dim)", marginTop: 8 }}>
              Contribution pondérée selon le poste · le vert ajoute, le rouge retire
            </div>
          </div>
        )}

        <div style={{ display: "flex", gap: 8, marginTop: 14, flexWrap: "wrap" }}>
          {status === "idle" && (
            <button
              onClick={loadAnalysis}
              style={{
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
          <Link
            to={`/player/${player.player_id}`}
            style={{
              background: "transparent",
              border: "1px solid var(--border)",
              color: "var(--text-dim)",
              borderRadius: 8,
              padding: "6px 12px",
              fontSize: "0.82rem",
              textDecoration: "none",
            }}
          >
            Fiche complète →
          </Link>
        </div>
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
