import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { getTeamFixtures, searchPlayers, searchTeams } from "../api/client";

const SILHOUETTE =
  "data:image/svg+xml;utf8," +
  encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" fill="#171f2b"/><circle cx="32" cy="24" r="12" fill="#2a3444"/><path d="M10 58c0-14 10-22 22-22s22 8 22 22" fill="#2a3444"/></svg>`
  );

export default function SearchBar() {
  const [query, setQuery] = useState("");
  const [teams, setTeams] = useState([]);
  const [players, setPlayers] = useState([]);
  const [selectedTeam, setSelectedTeam] = useState(null);
  const [fixtures, setFixtures] = useState([]);
  const [fixturesStatus, setFixturesStatus] = useState("idle");
  const navigate = useNavigate();

  useEffect(() => {
    if (query.trim().length < 3) {
      setTeams([]);
      setPlayers([]);
      return;
    }

    const timeout = setTimeout(() => {
      searchTeams(query)
        .then((data) => setTeams(data.teams.slice(0, 6)))
        .catch(() => setTeams([]));
      searchPlayers(query)
        .then((data) => setPlayers(data.players.slice(0, 6)))
        .catch(() => setPlayers([]));
    }, 350);

    return () => clearTimeout(timeout);
  }, [query]);

  const handleSelectTeam = async (team) => {
    setSelectedTeam(team);
    setFixturesStatus("loading");
    try {
      const data = await getTeamFixtures(team.id);
      setFixtures(data.fixtures);
      setFixturesStatus("done");
    } catch {
      setFixturesStatus("error");
    }
  };

  const hasResults = teams.length > 0 || players.length > 0;

  return (
    <div style={{ position: "relative" }}>
      <input
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          setSelectedTeam(null);
        }}
        placeholder="Rechercher une équipe ou un joueur déjà analysé…"
        style={{
          width: "100%",
          maxWidth: 420,
          padding: "10px 12px",
          background: "var(--bg-panel)",
          border: "1px solid var(--border)",
          borderRadius: 8,
          color: "var(--text)",
        }}
      />

      <AnimatePresence>
        {query.trim().length >= 3 && hasResults && !selectedTeam && (
          <motion.div
            initial={{ opacity: 0, y: -6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.15 }}
            className="panel"
            style={{
              position: "absolute",
              top: "calc(100% + 6px)",
              left: 0,
              width: "100%",
              maxWidth: 420,
              zIndex: 10,
              padding: 10,
            }}
          >
            {teams.length > 0 && (
              <div style={{ marginBottom: players.length > 0 ? 10 : 0 }}>
                <div style={{ fontSize: "0.7rem", color: "var(--text-dim)", marginBottom: 6 }}>
                  ÉQUIPES
                </div>
                {teams.map((t) => (
                  <button
                    key={t.id}
                    className="result-row"
                    onClick={() => handleSelectTeam(t)}
                    style={resultButtonStyle}
                  >
                    <img src={t.logo} alt="" style={{ width: 20, height: 20 }} />
                    {t.name}
                    <span style={{ color: "var(--text-dim)", marginLeft: "auto", fontSize: "0.75rem" }}>
                      {t.country}
                    </span>
                  </button>
                ))}
              </div>
            )}
            {players.length > 0 && (
              <div>
                <div style={{ fontSize: "0.7rem", color: "var(--text-dim)", marginBottom: 6 }}>
                  JOUEURS DÉJÀ ANALYSÉS
                </div>
                {players.map((p) => (
                  <button
                    key={p.player_id}
                    className="result-row"
                    onClick={() => navigate(`/player/${p.player_id}`)}
                    style={resultButtonStyle}
                  >
                    <img
                      src={p.photo_url || SILHOUETTE}
                      onError={(e) => {
                        e.currentTarget.onerror = null;
                        e.currentTarget.src = SILHOUETTE;
                      }}
                      alt=""
                      style={{ width: 20, height: 20, borderRadius: "50%", objectFit: "cover" }}
                    />
                    {p.name}
                    <span style={{ color: "var(--text-dim)", marginLeft: "auto", fontSize: "0.75rem" }}>
                      {p.team_name}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {selectedTeam && (
        <div className="panel" style={{ marginTop: 12 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
            <img src={selectedTeam.logo} alt="" style={{ width: 24, height: 24 }} />
            <strong>{selectedTeam.name}</strong>
            <span style={{ color: "var(--text-dim)", fontSize: "0.8rem" }}>
              matchs 2023-24
            </span>
          </div>
          {fixturesStatus === "loading" && <p style={{ color: "var(--text-dim)" }}>Chargement…</p>}
          {fixturesStatus === "error" && (
            <p style={{ color: "var(--red)" }}>Impossible de récupérer les matchs de cette équipe.</p>
          )}
          {fixturesStatus === "done" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 4, maxHeight: 260, overflowY: "auto" }}>
              {fixtures.length === 0 && (
                <p style={{ color: "var(--text-dim)" }}>Aucun match trouvé pour cette saison.</p>
              )}
              {fixtures.map((f) => (
                <button
                  key={f.fixture_id}
                  className="result-row"
                  onClick={() => navigate(`/match/${f.fixture_id}`)}
                  style={resultButtonStyle}
                >
                  <span style={{ flex: 1, textAlign: "left" }}>
                    {f.home_team.name} vs {f.away_team.name}
                  </span>
                  <span className="mono">
                    {f.goals.home ?? "-"} - {f.goals.away ?? "-"}
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

const resultButtonStyle = {
  display: "flex",
  alignItems: "center",
  gap: 8,
  width: "100%",
  background: "transparent",
  border: "none",
  borderRadius: 6,
  padding: "8px 8px",
  color: "var(--text)",
  cursor: "pointer",
  font: "inherit",
  textAlign: "left",
};
