const POSITION_COLORS = {
  Goalkeeper: "var(--gold)",
  Defender: "var(--blue)",
  Midfielder: "var(--green)",
  Attacker: "var(--red)",
};

const SILHOUETTE =
  "data:image/svg+xml;utf8," +
  encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" fill="#171f2b"/><circle cx="32" cy="24" r="12" fill="#2a3444"/><path d="M10 58c0-14 10-22 22-22s22 8 22 22" fill="#2a3444"/></svg>`
  );

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
              gap: 10,
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
                flexShrink: 0,
                background: POSITION_COLORS[p.position] || "var(--text-dim)",
              }}
            />
            <img
              src={p.photo_url || SILHOUETTE}
              onError={(e) => {
                e.currentTarget.onerror = null;
                e.currentTarget.src = SILHOUETTE;
              }}
              alt=""
              style={{
                width: 28,
                height: 28,
                borderRadius: "50%",
                objectFit: "cover",
                flexShrink: 0,
                background: "var(--bg-panel-raised)",
              }}
            />
            <span style={{ flex: 1, minWidth: 0 }}>
              <div>{p.name}</div>
              <div
                style={{
                  fontSize: "0.72rem",
                  color: "var(--text-dim)",
                  display: "flex",
                  alignItems: "center",
                  gap: 4,
                }}
              >
                {p.team_logo && (
                  <img src={p.team_logo} alt="" style={{ width: 12, height: 12 }} />
                )}
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
