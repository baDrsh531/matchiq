const SILHOUETTE =
  "data:image/svg+xml;utf8," +
  encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" fill="#171f2b"/><circle cx="32" cy="24" r="12" fill="#2a3444"/><path d="M10 58c0-14 10-22 22-22s22 8 22 22" fill="#2a3444"/></svg>`
  );

export default function MOTMCard({ player }) {
  if (!player) return null;

  return (
    <div
      className="panel"
      style={{
        borderColor: "var(--gold)",
        boxShadow: "0 0 0 1px rgba(217,180,74,0.25), 0 12px 30px -14px rgba(217,180,74,0.35)",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
          <img
            src={player.photo_url || SILHOUETTE}
            onError={(e) => {
              e.currentTarget.onerror = null;
              e.currentTarget.src = SILHOUETTE;
            }}
            alt={player.name}
            style={{
              width: 64,
              height: 64,
              borderRadius: "50%",
              objectFit: "cover",
              border: "2px solid var(--gold)",
              flexShrink: 0,
            }}
          />
          <div>
            <span className="badge badge-gold">Homme du match</span>
            <h2 style={{ fontSize: "1.8rem", marginTop: 10 }}>{player.name}</h2>
            <p style={{ color: "var(--text-dim)", margin: "4px 0 0", display: "flex", alignItems: "center", gap: 6 }}>
              {player.team_logo && (
                <img src={player.team_logo} alt="" style={{ width: 16, height: 16 }} />
              )}
              {player.position} — {player.team_name}
            </p>
          </div>
        </div>
        <div style={{ textAlign: "right" }}>
          <div className="mono" style={{ fontSize: "2.6rem", color: "var(--gold)", lineHeight: 1 }}>
            {player.composite_score.toFixed(1)}
          </div>
          <div style={{ color: "var(--text-dim)", fontSize: "0.75rem" }}>SCORE / 10</div>
        </div>
      </div>

      <div style={{ display: "flex", gap: 24, marginTop: 18, flexWrap: "wrap" }}>
        <div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-dim)", marginBottom: 6 }}>
            POINTS FORTS
          </div>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            {player.strengths.map((s) => (
              <span key={s} className="badge badge-green">
                {s}
              </span>
            ))}
          </div>
        </div>
        <div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-dim)", marginBottom: 6 }}>
            POINTS FAIBLES
          </div>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            {player.weaknesses.map((w) => (
              <span
                key={w}
                className="badge"
                style={{ background: "rgba(239,68,68,0.12)", color: "var(--red)" }}
              >
                {w}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
