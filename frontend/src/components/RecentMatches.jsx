import { useEffect, useState } from "react";
import { getRecentMatches } from "../api/client";

export default function RecentMatches({ onSelect, refreshKey }) {
  const [matches, setMatches] = useState([]);

  useEffect(() => {
    getRecentMatches()
      .then((data) => setMatches(data.matches))
      .catch(() => setMatches([]));
  }, [refreshKey]);

  if (!matches.length) return null;

  return (
    <div className="panel" style={{ marginTop: 16 }}>
      <h3 style={{ marginBottom: 12, fontSize: "1rem", color: "var(--text-dim)" }}>
        Matchs récemment analysés
      </h3>
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        {matches.map((m) => (
          <button
            key={m.fixture_id}
            onClick={() => onSelect(m.fixture_id)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              width: "100%",
              background: "transparent",
              border: "1px solid transparent",
              borderRadius: 8,
              padding: "8px 10px",
              color: "var(--text)",
              cursor: "pointer",
              font: "inherit",
              textAlign: "left",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.borderColor = "var(--border)")}
            onMouseLeave={(e) => (e.currentTarget.style.borderColor = "transparent")}
          >
            {m.home_team.logo && (
              <img src={m.home_team.logo} alt="" style={{ width: 22, height: 22 }} />
            )}
            <span style={{ flex: 1 }}>{m.home_team.name}</span>
            <span className="mono" style={{ fontWeight: 600 }}>
              {m.goals.home} - {m.goals.away}
            </span>
            <span style={{ flex: 1, textAlign: "right" }}>{m.away_team.name}</span>
            {m.away_team.logo && (
              <img src={m.away_team.logo} alt="" style={{ width: 22, height: 22 }} />
            )}
            <span
              className="badge badge-blue"
              style={{ marginLeft: 8, flexShrink: 0 }}
              title={m.league_name}
            >
              {m.has_report ? "Rapport IA" : m.league_name}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
