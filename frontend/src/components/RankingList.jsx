const POSITION_COLORS = {
  Goalkeeper: "var(--gold)",
  Defender: "var(--blue)",
  Midfielder: "var(--green)",
  Attacker: "var(--red)",
};

export default function RankingList({ players, selectedId, onSelect }) {
  return (
    <div className="panel">
      <h3 style={{ marginBottom: 14 }}>Classement du match</h3>
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        {players.map((p, idx) => (
          <button
            key={p.player_id}
            onClick={() => onSelect(p.player_id)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 12,
              width: "100%",
              textAlign: "left",
              background:
                p.player_id === selectedId ? "var(--bg-panel-raised)" : "transparent",
              border: "1px solid",
              borderColor: p.player_id === selectedId ? "var(--border)" : "transparent",
              borderRadius: 8,
              padding: "8px 10px",
              color: "var(--text)",
              cursor: "pointer",
              font: "inherit",
            }}
          >
            <span className="mono" style={{ color: "var(--text-dim)", width: 20 }}>
              {idx + 1}
            </span>
            <span
              style={{
                width: 6,
                height: 28,
                borderRadius: 3,
                background: POSITION_COLORS[p.position] || "var(--text-dim)",
              }}
            />
            <span style={{ flex: 1 }}>
              <div>{p.name}</div>
              <div style={{ fontSize: "0.72rem", color: "var(--text-dim)" }}>
                {p.position} · {p.team_name}
              </div>
            </span>
            <span className="mono" style={{ fontWeight: 600 }}>
              {p.composite_score.toFixed(1)}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
