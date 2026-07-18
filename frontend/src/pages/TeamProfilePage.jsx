import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { motion } from "framer-motion";
import { getTeamHistory } from "../api/client";
import { SkeletonBlock } from "../components/Skeleton";

const SILHOUETTE =
  "data:image/svg+xml;utf8," +
  encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" fill="#171f2b"/><circle cx="32" cy="24" r="12" fill="#2a3444"/><path d="M10 58c0-14 10-22 22-22s22 8 22 22" fill="#2a3444"/></svg>`
  );

export default function TeamProfilePage() {
  const { teamId } = useParams();
  const [history, setHistory] = useState(null);
  const [status, setStatus] = useState("loading");

  useEffect(() => {
    setStatus("loading");
    getTeamHistory(teamId)
      .then((data) => {
        setHistory(data);
        setStatus("done");
      })
      .catch(() => setStatus("error"));
  }, [teamId]);

  return (
    <>
      <div style={{ marginBottom: 20 }}>
        <Link to="/" style={{ color: "var(--text-dim)", fontSize: "0.85rem", textDecoration: "none" }}>
          ← Accueil
        </Link>
      </div>

      {status === "loading" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          <div className="panel" style={{ display: "flex", gap: 16, alignItems: "center" }}>
            <SkeletonBlock width={56} height={56} />
            <SkeletonBlock width={220} height={24} />
          </div>
          <SkeletonBlock height={180} />
        </div>
      )}
      {status === "error" && (
        <p style={{ color: "var(--red)" }}>
          Aucun historique pour cette équipe — analyse d'abord un de ses matchs.
        </p>
      )}

      {status === "done" && history && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25 }}
          style={{ display: "flex", flexDirection: "column", gap: 20 }}
        >
          <div className="panel" style={{ display: "flex", alignItems: "center", gap: 16 }}>
            {history.team_logo && (
              <img src={history.team_logo} alt="" style={{ width: 56, height: 56 }} />
            )}
            <div>
              <h2 style={{ fontSize: "1.6rem" }}>{history.team_name}</h2>
              <p style={{ color: "var(--text-dim)", margin: "4px 0 0" }}>
                {history.matches.length} match{history.matches.length > 1 ? "s" : ""} analysé
                {history.matches.length > 1 ? "s" : ""}
              </p>
            </div>
          </div>

          <div className="panel">
            <h3 style={{ marginBottom: 14 }}>Effectif observé</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {history.squad.map((p) => (
                <Link
                  key={p.player_id}
                  to={`/player/${p.player_id}`}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 12,
                    padding: "8px 10px",
                    borderRadius: 8,
                    color: "var(--text)",
                    textDecoration: "none",
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = "var(--bg-panel-raised)")}
                  onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                >
                  <img
                    src={p.photo_url || SILHOUETTE}
                    onError={(e) => {
                      e.currentTarget.onerror = null;
                      e.currentTarget.src = SILHOUETTE;
                    }}
                    alt=""
                    style={{ width: 32, height: 32, borderRadius: "50%", objectFit: "cover" }}
                  />
                  <span style={{ flex: 1 }}>
                    <div>{p.name}</div>
                    <div style={{ fontSize: "0.72rem", color: "var(--text-dim)" }}>
                      {p.position} · {p.appearances} match{p.appearances > 1 ? "s" : ""}
                    </div>
                  </span>
                  <span className="mono" style={{ fontWeight: 600 }}>
                    {p.average_score.toFixed(1)}
                  </span>
                </Link>
              ))}
            </div>
          </div>

          <div className="panel">
            <h3 style={{ marginBottom: 14 }}>Matchs analysés</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {history.matches.map((m) => (
                <Link
                  key={m.fixture_id}
                  to={`/match/${m.fixture_id}`}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    padding: "8px 10px",
                    borderRadius: 8,
                    color: "var(--text)",
                    textDecoration: "none",
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = "var(--bg-panel-raised)")}
                  onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                >
                  <span>vs {m.opponent_name}</span>
                  <span className="mono" style={{ fontWeight: 600 }}>
                    {m.goals_for} - {m.goals_against}
                  </span>
                </Link>
              ))}
            </div>
          </div>
        </motion.div>
      )}
    </>
  );
}
