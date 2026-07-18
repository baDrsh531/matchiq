import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  Line,
  LineChart,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { motion } from "framer-motion";
import { getPlayerHistory } from "../api/client";
import { SkeletonBlock } from "../components/Skeleton";

const SILHOUETTE =
  "data:image/svg+xml;utf8," +
  encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" fill="#171f2b"/><circle cx="32" cy="24" r="12" fill="#2a3444"/><path d="M10 58c0-14 10-22 22-22s22 8 22 22" fill="#2a3444"/></svg>`
  );

export default function PlayerProfilePage() {
  const { playerId } = useParams();
  const [history, setHistory] = useState(null);
  const [status, setStatus] = useState("loading");

  useEffect(() => {
    setStatus("loading");
    getPlayerHistory(playerId)
      .then((data) => {
        setHistory(data);
        setStatus("done");
      })
      .catch(() => setStatus("error"));
  }, [playerId]);

  return (
    <>
      <div style={{ marginBottom: 20 }}>
        <Link to="/" style={{ color: "var(--text-dim)", fontSize: "0.85rem", textDecoration: "none" }}>
          ← Accueil
        </Link>
      </div>

      {status === "loading" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          <div className="panel" style={{ display: "flex", gap: 20, alignItems: "center" }}>
            <SkeletonBlock width={96} height={96} style={{ borderRadius: "50%" }} />
            <SkeletonBlock width={200} height={28} />
          </div>
          <SkeletonBlock height={220} />
        </div>
      )}
      {status === "error" && (
        <p style={{ color: "var(--red)" }}>
          Aucun historique pour ce joueur — il doit d'abord apparaître dans un match analysé.
        </p>
      )}

      {status === "done" && history && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25 }}
          style={{ display: "flex", flexDirection: "column", gap: 20 }}
        >
          <div className="panel" style={{ display: "flex", gap: 20, alignItems: "center" }}>
            <img
              src={history.photo_url || SILHOUETTE}
              onError={(e) => {
                e.currentTarget.onerror = null;
                e.currentTarget.src = SILHOUETTE;
              }}
              alt={history.name}
              style={{
                width: 96,
                height: 96,
                borderRadius: "50%",
                objectFit: "cover",
                border: "2px solid var(--gold)",
              }}
            />
            <div style={{ flex: 1 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                {history.team_logo && (
                  <Link to={`/team/${history.team_id}`}>
                    <img src={history.team_logo} alt="" style={{ width: 22, height: 22 }} />
                  </Link>
                )}
                <h2 style={{ fontSize: "1.6rem" }}>{history.name}</h2>
              </div>
              <p style={{ color: "var(--text-dim)", margin: "4px 0 0" }}>{history.team_name}</p>
            </div>
            <div style={{ textAlign: "right" }}>
              <div className="mono" style={{ fontSize: "2.2rem", color: "var(--gold)" }}>
                {history.average_score.toFixed(1)}
              </div>
              <div style={{ color: "var(--text-dim)", fontSize: "0.75rem" }}>
                MOYENNE / {history.matches_played} MATCH{history.matches_played > 1 ? "S" : ""}
              </div>
            </div>
          </div>

          <div className="panel">
            <h3 style={{ marginBottom: 14 }}>Forme (score composite par match)</h3>
            <div style={{ height: 220 }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={history.matches}>
                  <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" />
                  <XAxis
                    dataKey="opponent_name"
                    tick={{ fill: "var(--text-dim)", fontSize: 11 }}
                  />
                  <YAxis domain={[0, 10]} tick={{ fill: "var(--text-dim)", fontSize: 11 }} />
                  <Tooltip
                    contentStyle={{
                      background: "var(--bg-panel-raised)",
                      border: "1px solid var(--border)",
                      borderRadius: 8,
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="composite_score"
                    stroke="var(--gold)"
                    strokeWidth={2}
                    dot={{ fill: "var(--gold)" }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="panel">
            <h3 style={{ marginBottom: 14 }}>Historique des matchs</h3>
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
                  <span style={{ color: "var(--text-dim)" }}>{m.position} · {m.minutes}&apos;</span>
                  <span className="mono" style={{ fontWeight: 600 }}>
                    {m.composite_score.toFixed(1)}
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
