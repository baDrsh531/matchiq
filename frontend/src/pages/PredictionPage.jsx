import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { getPredictionLeagues, getEloTable, getMatchup } from "../api/client";
import { SkeletonBlock } from "../components/Skeleton";

// Barre V/N/D empilée : trois segments proportionnels aux probabilités.
function ProbaBar({ home, draw, away }) {
  const seg = (w, color, label) => (
    <div
      style={{
        width: `${w * 100}%`,
        background: color,
        color: "#0e0e0e",
        fontSize: "0.72rem",
        fontWeight: 700,
        textAlign: "center",
        lineHeight: "22px",
        overflow: "hidden",
        whiteSpace: "nowrap",
      }}
    >
      {w > 0.08 ? `${Math.round(w * 100)}%` : ""}
      {w > 0.16 ? ` ${label}` : ""}
    </div>
  );
  return (
    <div style={{ display: "flex", height: 22, borderRadius: 6, overflow: "hidden" }}>
      {seg(home, "var(--gold)", "V")}
      {seg(draw, "var(--text-dim)", "N")}
      {seg(away, "var(--blue)", "D")}
    </div>
  );
}

export default function PredictionPage() {
  const [leagues, setLeagues] = useState([]);
  const [leagueId, setLeagueId] = useState(61);
  const [season, setSeason] = useState(2023);
  const [table, setTable] = useState(null);
  const [status, setStatus] = useState("loading");

  const [home, setHome] = useState("");
  const [away, setAway] = useState("");
  const [pred, setPred] = useState(null);
  const [predStatus, setPredStatus] = useState("idle");

  useEffect(() => {
    getPredictionLeagues()
      .then((d) => setLeagues(d.leagues))
      .catch(() => setLeagues([]));
  }, []);

  useEffect(() => {
    setStatus("loading");
    setPred(null);
    setHome("");
    setAway("");
    getEloTable(leagueId, season)
      .then((d) => {
        setTable(d);
        setStatus("done");
      })
      .catch(() => setStatus("error"));
  }, [leagueId, season]);

  const seasons = useMemo(
    () => leagues.find((l) => l.league_id === leagueId)?.seasons || [2023, 2022],
    [leagues, leagueId]
  );

  const runMatchup = async (e) => {
    e.preventDefault();
    if (!home || !away || home === away) return;
    setPredStatus("loading");
    try {
      setPred(await getMatchup(leagueId, season, home, away));
      setPredStatus("done");
    } catch {
      setPredStatus("error");
    }
  };

  const cal = table?.calibration;
  const maxRating = table?.teams?.[0]?.rating || 1600;
  const minRating = table?.teams?.length
    ? table.teams[table.teams.length - 1].rating
    : 1400;

  return (
    <>
      <header style={{ marginBottom: 18 }}>
        <h1 style={{ fontSize: "1.6rem" }}>Pronostics</h1>
        <p style={{ color: "var(--text-dim)", marginTop: 4 }}>
          Classement Elo déterministe construit sur les résultats de la saison — le
          modèle calcule les probabilités, il n&apos;invente rien.
        </p>
      </header>

      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 18 }}>
        <select value={leagueId} onChange={(e) => setLeagueId(Number(e.target.value))} style={selectStyle}>
          {leagues.map((l) => (
            <option key={l.league_id} value={l.league_id}>
              {l.name} ({l.country})
            </option>
          ))}
        </select>
        <select value={season} onChange={(e) => setSeason(Number(e.target.value))} style={selectStyle}>
          {seasons.map((s) => (
            <option key={s} value={s}>
              Saison {s}
            </option>
          ))}
        </select>
      </div>

      {status === "loading" && <SkeletonBlock height={420} />}
      {status === "error" && (
        <p style={{ color: "var(--red)" }}>
          Pronostics indisponibles pour cette ligue-saison (non présente dans le cache de la démo).
        </p>
      )}

      {status === "done" && table && (
        <>
          {/* Prédicteur d'affiche */}
          <motion.div
            className="panel"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            style={{ marginBottom: 18 }}
          >
            <div style={{ fontSize: "0.72rem", letterSpacing: "0.05em", color: "var(--text-dim)", marginBottom: 12 }}>
              SIMULER UNE AFFICHE
            </div>
            <form onSubmit={runMatchup} style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
              <select value={home} onChange={(e) => setHome(e.target.value)} style={selectStyle}>
                <option value="">Domicile…</option>
                {table.teams.map((t) => (
                  <option key={t.team_id} value={t.team_id}>{t.name}</option>
                ))}
              </select>
              <span style={{ color: "var(--text-dim)" }}>vs</span>
              <select value={away} onChange={(e) => setAway(e.target.value)} style={selectStyle}>
                <option value="">Extérieur…</option>
                {table.teams.map((t) => (
                  <option key={t.team_id} value={t.team_id}>{t.name}</option>
                ))}
              </select>
              <button type="submit" style={buttonStyle} disabled={!home || !away || home === away}>
                Prédire
              </button>
            </form>

            {predStatus === "loading" && <p style={{ marginTop: 12 }}>Calcul…</p>}
            {predStatus === "done" && pred && (
              <div style={{ marginTop: 16 }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6, fontSize: "0.9rem" }}>
                  <strong style={{ color: "var(--gold)" }}>{pred.home_name}</strong>
                  <span style={{ color: "var(--text-dim)" }}>Δ Elo {pred.rating_diff > 0 ? "+" : ""}{pred.rating_diff}</span>
                  <strong style={{ color: "var(--blue)" }}>{pred.away_name}</strong>
                </div>
                <ProbaBar home={pred.home} draw={pred.draw} away={pred.away} />
                <div style={{ display: "flex", justifyContent: "space-between", marginTop: 6, fontSize: "0.78rem", color: "var(--text-dim)" }}>
                  <span>Victoire {pred.home_name}</span>
                  <span>Nul</span>
                  <span>Victoire {pred.away_name}</span>
                </div>
              </div>
            )}
          </motion.div>

          {/* Classement Elo + calibration */}
          <motion.div className="panel" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 12, flexWrap: "wrap", gap: 8 }}>
              <div style={{ fontSize: "0.72rem", letterSpacing: "0.05em", color: "var(--text-dim)" }}>
                CLASSEMENT ELO — FIN DE SAISON
              </div>
              {cal && cal.brier != null && (
                <div style={{ fontSize: "0.75rem", color: "var(--text-dim)" }} title="Score de Brier walk-forward : le modèle est évalué en ne prédisant chaque match qu'avec les données antérieures.">
                  Calibration : Brier {cal.brier} ·{" "}
                  <span style={{ color: cal.skill > 0 ? "var(--green)" : "var(--red)" }}>
                    skill {cal.skill > 0 ? "+" : ""}{Math.round(cal.skill * 1000) / 10}%
                  </span>{" "}
                  vs moyenne · {cal.n} matchs
                </div>
              )}
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
              {table.teams.map((t, i) => {
                const frac = maxRating > minRating ? (t.rating - minRating) / (maxRating - minRating) : 1;
                return (
                  <div key={t.team_id} style={{ display: "grid", gridTemplateColumns: "1.8rem 1fr 4rem", gap: 10, alignItems: "center", padding: "5px 6px" }}>
                    <span className="mono" style={{ color: "var(--text-dim)", textAlign: "right" }}>{i + 1}</span>
                    <div style={{ minWidth: 0 }}>
                      <div style={{ fontSize: "0.88rem", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", marginBottom: 3 }}>
                        {t.name}
                      </div>
                      <div style={{ height: 4, background: "var(--bg-panel-raised)", borderRadius: 2 }}>
                        <div style={{ width: `${20 + frac * 80}%`, height: "100%", background: "var(--gold)", borderRadius: 2 }} />
                      </div>
                    </div>
                    <span className="mono" style={{ textAlign: "right", fontWeight: 600 }}>{Math.round(t.rating)}</span>
                  </div>
                );
              })}
            </div>
          </motion.div>
        </>
      )}
    </>
  );
}

const selectStyle = {
  padding: "9px 12px",
  background: "var(--bg-panel)",
  border: "1px solid var(--border)",
  borderRadius: 8,
  color: "var(--text)",
  maxWidth: 240,
};

const buttonStyle = {
  padding: "9px 18px",
  background: "var(--gold)",
  border: "none",
  borderRadius: 8,
  color: "#141414",
  fontWeight: 600,
  cursor: "pointer",
};
