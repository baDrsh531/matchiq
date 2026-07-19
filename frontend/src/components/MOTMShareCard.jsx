import { forwardRef } from "react";

const SILHOUETTE =
  "data:image/svg+xml;utf8," +
  encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" fill="#171f2b"/><circle cx="32" cy="24" r="12" fill="#2a3444"/><path d="M10 58c0-14 10-22 22-22s22 8 22 22" fill="#2a3444"/></svg>`
  );

/**
 * Carte "Homme du Match" au format carré (1080x1080, adapté LinkedIn/Instagram),
 * rendue hors-écran puis capturée en PNG par ShareMOTMButton (html-to-image).
 * Conçue séparément de MOTMCard (qui reste optimisée pour l'affichage in-app).
 */
const MOTMShareCard = forwardRef(function MOTMShareCard({ player, match }, ref) {
  if (!player) return null;

  return (
    <div
      ref={ref}
      style={{
        width: 1080,
        height: 1080,
        background: "radial-gradient(circle at 50% 0%, #17202f 0%, #0b0f14 65%)",
        color: "#e7ecf3",
        fontFamily: "'Inter', sans-serif",
        padding: 64,
        boxSizing: "border-box",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        position: "relative",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          position: "absolute",
          inset: 0,
          border: "1px solid rgba(217,180,74,0.25)",
          margin: 24,
          borderRadius: 16,
          pointerEvents: "none",
        }}
      />

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ fontFamily: "'Oswald', sans-serif", fontSize: 34, fontWeight: 700 }}>
          Match<span style={{ color: "#d9b44a" }}>IQ</span>
        </div>
        {match && (
          <div style={{ fontSize: 20, color: "#8b96a8" }}>
            {match.teams?.home?.name} {match.goals?.home} - {match.goals?.away} {match.teams?.away?.name}
          </div>
        )}
      </div>

      <div style={{ textAlign: "center" }}>
        <img
          src={player.photo_url || SILHOUETTE}
          crossOrigin="anonymous"
          alt={player.name}
          style={{
            width: 260,
            height: 260,
            borderRadius: "50%",
            objectFit: "cover",
            border: "6px solid #d9b44a",
            boxShadow: "0 0 70px rgba(217,180,74,0.45)",
          }}
        />
        <div
          style={{
            marginTop: 26,
            fontSize: 20,
            letterSpacing: 3,
            color: "#d9b44a",
            textTransform: "uppercase",
            fontWeight: 600,
          }}
        >
          Homme du match
        </div>
        <div style={{ fontFamily: "'Oswald', sans-serif", fontSize: 58, fontWeight: 700, marginTop: 8 }}>
          {player.name}
        </div>
        <div
          style={{
            fontSize: 22,
            color: "#8b96a8",
            marginTop: 8,
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            gap: 8,
          }}
        >
          {player.team_logo && (
            <img src={player.team_logo} crossOrigin="anonymous" alt="" style={{ width: 24, height: 24 }} />
          )}
          {player.position} — {player.team_name}
        </div>
        <div
          style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 130,
            color: "#d9b44a",
            marginTop: 26,
            lineHeight: 1,
          }}
        >
          {player.composite_score.toFixed(1)}
        </div>
        <div style={{ fontSize: 16, color: "#8b96a8", letterSpacing: 2 }}>SCORE / 10</div>
      </div>

      <div style={{ display: "flex", justifyContent: "center", gap: 12, flexWrap: "wrap" }}>
        {player.strengths.map((s) => (
          <span
            key={s}
            style={{
              padding: "8px 18px",
              borderRadius: 999,
              background: "rgba(34,197,94,0.15)",
              color: "#22c55e",
              fontSize: 17,
              fontWeight: 600,
              textTransform: "uppercase",
            }}
          >
            {s}
          </span>
        ))}
      </div>
    </div>
  );
});

export default MOTMShareCard;
