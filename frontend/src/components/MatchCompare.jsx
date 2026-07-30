import { Link } from "react-router";

function MatchHeader({ match, color }) {
  return (
    <div style={{ flex: 1, textAlign: "center" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}>
        {match.home_team.logo && <img src={match.home_team.logo} alt="" style={{ width: 22, height: 22 }} />}
        <span className="mono" style={{ fontSize: "1.3rem", color }}>
          {match.goals.home ?? "-"} - {match.goals.away ?? "-"}
        </span>
        {match.away_team.logo && <img src={match.away_team.logo} alt="" style={{ width: 22, height: 22 }} />}
      </div>
      <div style={{ fontSize: "0.85rem", marginTop: 4 }}>
        {match.home_team.name} <span style={{ color: "var(--text-dim)" }}>vs</span> {match.away_team.name}
      </div>
      <div style={{ color: "var(--text-dim)", fontSize: "0.72rem", marginTop: 2 }}>
        {(match.date || "").slice(0, 10)}
        {match.league_name ? ` · ${match.league_name}` : ""}
      </div>
      {match.motm && (
        <div style={{ fontSize: "0.75rem", marginTop: 6, color: "var(--text-dim)" }}>
          MOTM : <strong style={{ color: "var(--text)" }}>{match.motm.name}</strong> (
          {match.motm.composite_score.toFixed(1)})
        </div>
      )}
    </div>
  );
}

function deltaColor(delta) {
  if (delta > 0.3) return "var(--green)";
  if (delta < -0.3) return "var(--red)";
  return "var(--text-dim)";
}

export default function MatchCompare({ data }) {
  const { match_a: a, match_b: b, common_players: common } = data;
  const maxScore = 10;

  return (
    <div className="panel">
      <div style={{ display: "flex", alignItems: "flex-start", gap: 12, marginBottom: 8 }}>
        <MatchHeader match={a} color="var(--gold)" />
        <div style={{ alignSelf: "center", color: "var(--text-dim)", fontWeight: 600 }}>vs</div>
        <MatchHeader match={b} color="var(--blue)" />
      </div>

      <div style={{ borderTop: "1px solid var(--border)", marginTop: 12, paddingTop: 14 }}>
        <div style={{ fontSize: "0.72rem", letterSpacing: "0.05em", color: "var(--text-dim)", marginBottom: 10 }}>
          JOUEURS PRÉSENTS DANS LES DEUX MATCHS ({common.length})
        </div>

        {common.length === 0 ? (
          <p style={{ color: "var(--text-dim)", fontSize: "0.9rem" }}>
            Aucun joueur commun aux deux matchs — le comparatif est plus riche entre deux rencontres
            d&apos;une même affiche.
          </p>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {common.map((p) => (
              <div
                key={p.player_id}
                style={{ display: "grid", gridTemplateColumns: "1fr 3rem 5rem 3rem 3.2rem", gap: 8, alignItems: "center" }}
              >
                <Link
                  to={`/player/${p.player_id}`}
                  style={{ color: "var(--text)", textDecoration: "none", fontSize: "0.88rem", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}
                >
                  {p.name}
                </Link>
                <span className="mono" style={{ textAlign: "right", color: "var(--gold)" }}>
                  {p.score_a.toFixed(1)}
                </span>
                {/* petite barre bidirectionnelle : évolution A -> B */}
                <div style={{ position: "relative", height: 6, background: "var(--bg-panel-raised)", borderRadius: 3 }}>
                  <div
                    style={{
                      position: "absolute",
                      left: `${(Math.min(p.score_a, p.score_b) / maxScore) * 100}%`,
                      width: `${(Math.abs(p.score_b - p.score_a) / maxScore) * 100}%`,
                      height: "100%",
                      borderRadius: 3,
                      background: deltaColor(p.delta),
                    }}
                  />
                </div>
                <span className="mono" style={{ textAlign: "left", color: "var(--blue)" }}>
                  {p.score_b.toFixed(1)}
                </span>
                <span className="mono" style={{ textAlign: "right", fontSize: "0.78rem", color: deltaColor(p.delta) }}>
                  {p.delta > 0 ? "+" : ""}
                  {p.delta.toFixed(1)}
                </span>
              </div>
            ))}
          </div>
        )}
        <div style={{ fontSize: "0.7rem", color: "var(--text-dim)", marginTop: 10 }}>
          <span style={{ color: "var(--gold)" }}>■</span> match A ·{" "}
          <span style={{ color: "var(--blue)" }}>■</span> match B · dernière colonne = évolution de la note
        </div>
      </div>
    </div>
  );
}
