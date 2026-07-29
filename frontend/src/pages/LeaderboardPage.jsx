import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { getLeaderboard } from "../api/client";
import { SkeletonBlock } from "../components/Skeleton";

const POSITION_FR = {
  Goalkeeper: "Gardiens",
  Defender: "Défenseurs",
  Midfielder: "Milieux",
  Attacker: "Attaquants",
};

const SILHOUETTE =
  "data:image/svg+xml;utf8," +
  encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" fill="#171f2b"/><circle cx="32" cy="24" r="12" fill="#2a3444"/><path d="M10 58c0-14 10-22 22-22s22 8 22 22" fill="#2a3444"/></svg>`
  );

function scoreColor(score) {
  if (score >= 8) return "var(--gold)";
  if (score >= 6) return "var(--green)";
  if (score >= 4) return "var(--text)";
  return "var(--text-dim)";
}

export default function LeaderboardPage() {
  const [data, setData] = useState(null);
  const [position, setPosition] = useState(null); // null = tous
  const [status, setStatus] = useState("loading");

  useEffect(() => {
    setStatus("loading");
    getLeaderboard(position, 30)
      .then((d) => {
        setData(d);
        setStatus("done");
      })
      .catch(() => setStatus("error"));
  }, [position]);

  const positions = data?.positions || [];

  return (
    <>
      <header style={{ marginBottom: 20 }}>
        <h1 style={{ fontSize: "1.6rem" }}>Palmarès</h1>
        <p style={{ color: "var(--text-dim)", marginTop: 4 }}>
          Meilleures notes composites, tous les matchs analysés confondus.
        </p>
      </header>

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 18 }}>
        <FilterButton active={position === null} onClick={() => setPosition(null)}>
          Tous
        </FilterButton>
        {positions.map((p) => (
          <FilterButton key={p} active={position === p} onClick={() => setPosition(p)}>
            {POSITION_FR[p] || p}
          </FilterButton>
        ))}
      </div>

      {status === "loading" && <SkeletonBlock height={360} />}
      {status === "error" && (
        <p style={{ color: "var(--red)" }}>
          Palmarès indisponible — analyse d&apos;abord quelques matchs.
        </p>
      )}

      {status === "done" && data && (
        <motion.div
          className="panel"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25 }}
        >
          {data.performances.length === 0 ? (
            <p style={{ color: "var(--text-dim)" }}>Aucune performance pour ce filtre.</p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              {data.performances.map((p, i) => (
                <Link
                  key={`${p.player_id}-${p.fixture_id}`}
                  to={`/match/${p.fixture_id}`}
                  style={{
                    display: "grid",
                    gridTemplateColumns: "2rem 34px 1fr auto",
                    gap: 12,
                    alignItems: "center",
                    padding: "8px 10px",
                    borderRadius: 8,
                    color: "var(--text)",
                    textDecoration: "none",
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = "var(--bg-panel-raised)")}
                  onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                >
                  <span className="mono" style={{ color: "var(--text-dim)", textAlign: "right" }}>
                    {i + 1}
                  </span>
                  <img
                    src={p.photo_url || SILHOUETTE}
                    onError={(e) => {
                      e.currentTarget.onerror = null;
                      e.currentTarget.src = SILHOUETTE;
                    }}
                    alt=""
                    style={{ width: 34, height: 34, borderRadius: "50%", objectFit: "cover" }}
                  />
                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontWeight: 600, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                      {p.name}
                    </div>
                    <div style={{ color: "var(--text-dim)", fontSize: "0.78rem" }}>
                      {p.team_name}
                      {p.opponent_name ? ` · vs ${p.opponent_name}` : ""} · {POSITION_FR[p.position] || p.position}
                    </div>
                  </div>
                  <span
                    className="mono"
                    style={{ fontSize: "1.1rem", fontWeight: 700, color: scoreColor(p.composite_score) }}
                  >
                    {p.composite_score.toFixed(1)}
                  </span>
                </Link>
              ))}
            </div>
          )}
        </motion.div>
      )}
    </>
  );
}

function FilterButton({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: "6px 14px",
        borderRadius: 8,
        border: "1px solid var(--border)",
        background: active ? "var(--bg-panel-raised)" : "transparent",
        color: active ? "var(--gold)" : "var(--text-dim)",
        fontWeight: active ? 600 : 400,
        cursor: "pointer",
      }}
    >
      {children}
    </button>
  );
}
