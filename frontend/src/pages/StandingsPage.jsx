import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { getStandings, getSupportedLeagues } from "../api/client";
import { SkeletonBlock } from "../components/Skeleton";

const rowVariants = {
  hidden: { opacity: 0, x: -8 },
  show: (i) => ({ opacity: 1, x: 0, transition: { delay: i * 0.02 } }),
};

export default function StandingsPage() {
  const [leagues, setLeagues] = useState([]);
  const [leagueId, setLeagueId] = useState(39);
  const [season, setSeason] = useState(2023);
  const [rows, setRows] = useState([]);
  const [status, setStatus] = useState("loading");

  useEffect(() => {
    getSupportedLeagues().then((data) => setLeagues(data.leagues));
  }, []);

  useEffect(() => {
    setStatus("loading");
    getStandings(leagueId, season)
      .then((data) => {
        setRows(data.standings);
        setStatus("done");
      })
      .catch(() => setStatus("error"));
  }, [leagueId, season]);

  return (
    <>
      <header style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: "1.6rem" }}>Classement</h1>
        <div style={{ display: "flex", gap: 10, marginTop: 16 }}>
          <select
            value={leagueId}
            onChange={(e) => setLeagueId(Number(e.target.value))}
            style={selectStyle}
          >
            {leagues.map((l) => (
              <option key={l.league_id} value={l.league_id}>
                {l.name}
              </option>
            ))}
          </select>
          <select value={season} onChange={(e) => setSeason(Number(e.target.value))} style={selectStyle}>
            <option value={2021}>2021-22</option>
            <option value={2022}>2022-23</option>
            <option value={2023}>2023-24</option>
          </select>
        </div>
      </header>

      {status === "loading" && (
        <div className="panel" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {Array.from({ length: 8 }).map((_, i) => (
            <SkeletonBlock key={i} height={32} />
          ))}
        </div>
      )}
      {status === "error" && (
        <p style={{ color: "var(--red)" }}>
          Classement indisponible pour cette ligue/saison (couverture du plan API-Football ou quota).
        </p>
      )}

      {status === "done" && (
        <div className="panel" style={{ padding: 0, overflow: "hidden" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border)" }}>
                {["#", "Équipe", "J", "V", "N", "D", "Diff", "Pts"].map((h) => (
                  <th
                    key={h}
                    style={{
                      textAlign: h === "Équipe" ? "left" : "center",
                      padding: "10px 12px",
                      color: "var(--text-dim)",
                      fontSize: "0.75rem",
                      textTransform: "uppercase",
                    }}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <motion.tr
                  key={r.team.id}
                  custom={i}
                  variants={rowVariants}
                  initial="hidden"
                  animate="show"
                  style={{ borderBottom: "1px solid var(--border)" }}
                >
                  <td className="mono" style={{ textAlign: "center", padding: "8px 12px" }}>
                    {r.rank}
                  </td>
                  <td style={{ padding: "8px 12px", display: "flex", alignItems: "center", gap: 8 }}>
                    <img src={r.team.logo} alt="" style={{ width: 20, height: 20 }} />
                    {r.team.name}
                  </td>
                  <td style={{ textAlign: "center" }}>{r.all.played}</td>
                  <td style={{ textAlign: "center" }}>{r.all.win}</td>
                  <td style={{ textAlign: "center" }}>{r.all.draw}</td>
                  <td style={{ textAlign: "center" }}>{r.all.lose}</td>
                  <td style={{ textAlign: "center" }}>{r.goalsDiff}</td>
                  <td className="mono" style={{ textAlign: "center", fontWeight: 700 }}>
                    {r.points}
                  </td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

const selectStyle = {
  padding: "10px 12px",
  background: "var(--bg-panel)",
  border: "1px solid var(--border)",
  borderRadius: 8,
  color: "var(--text)",
};
