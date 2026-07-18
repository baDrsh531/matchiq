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
        <div>
          <span className="badge badge-gold">Homme du match</span>
          <h2 style={{ fontSize: "1.8rem", marginTop: 10 }}>{player.name}</h2>
          <p style={{ color: "var(--text-dim)", margin: "4px 0 0" }}>
            {player.position} — {player.team_name}
          </p>
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
