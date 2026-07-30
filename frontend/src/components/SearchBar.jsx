import { useEffect, useState } from "react";
import { useNavigate } from "react-router";
import { motion, AnimatePresence } from "framer-motion";
import { getTeamFixtures, searchPlayers, searchTeams } from "../api/client";

const SILHOUETTE =
  "data:image/svg+xml;utf8," +
  encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" fill="#171f2b"/><circle cx="32" cy="24" r="12" fill="#2a3444"/><path d="M10 58c0-14 10-22 22-22s22 8 22 22" fill="#2a3444"/></svg>`
  );

const SEASONS = [2023, 2022, 2021]; // couvertes par le plan gratuit API-Football

export default function SearchBar() {
  const [query, setQuery] = useState("");
  const [teams, setTeams] = useState([]);
  const [players, setPlayers] = useState([]);
  const [selectedTeam, setSelectedTeam] = useState(null);
  const [season, setSeason] = useState(SEASONS[0]);
  const [fixtures, setFixtures] = useState([]);
  const [fixturesStatus, setFixturesStatus] = useState("idle");
  const navigate = useNavigate();

  const loadFixtures = async (team, seasonYear) => {
    setFixturesStatus("loading");
    try {
      const data = await getTeamFixtures(team.id, seasonYear);
      // matchs terminés d'abord, du plus récent au plus ancien
      const sorted = [...data.fixtures].sort((a, b) => (b.date || "").localeCompare(a.date || ""));
      setFixtures(sorted);
      setFixturesStatus("done");
    } catch {
      setFixturesStatus("error");
    }
  };

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

  const handleSelectTeam = (team) => {
    setSelectedTeam(team);
    loadFixtures(team, season);
  };

  const handleSeasonChange = (year) => {
    setSeason(year);
    if (selectedTeam) loadFixtures(selectedTeam, year);
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
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10, flexWrap: "wrap" }}>
            <img src={selectedTeam.logo} alt="" style={{ width: 24, height: 24 }} />
            <strong>{selectedTeam.name}</strong>
            <div style={{ display: "flex", gap: 4, marginLeft: "auto" }}>
              {SEASONS.map((y) => (
                <button
                  key={y}
                  onClick={() => handleSeasonChange(y)}
                  style={{
                    padding: "3px 8px",
                    fontSize: "0.72rem",
                    borderRadius: 6,
                    border: "1px solid var(--border)",
                    background: season === y ? "var(--bg-panel-raised)" : "transparent",
                    color: season === y ? "var(--gold)" : "var(--text-dim)",
                    cursor: "pointer",
                  }}
                >
                  {y}–{(y + 1) % 100}
                </button>
              ))}
            </div>
          </div>
          {fixturesStatus === "loading" && <p style={{ color: "var(--text-dim)" }}>Chargement…</p>}
          {fixturesStatus === "error" && (
            <p style={{ color: "var(--red)" }}>Impossible de récupérer les matchs de cette équipe.</p>
          )}
          {fixturesStatus === "done" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 2, maxHeight: 300, overflowY: "auto" }}>
              {fixtures.length === 0 && (
                <p style={{ color: "var(--text-dim)" }}>Aucun match trouvé pour cette saison.</p>
              )}
              {fixtures.map((f) => {
                const finished = f.status === "FT" || f.status === "AET" || f.status === "PEN";
                const row = (
                  <>
                    <span style={{ color: "var(--text-dim)", fontSize: "0.72rem", width: 74, flexShrink: 0 }}>
                      {(f.date || "").slice(0, 10)}
                    </span>
                    <span style={{ flex: 1, textAlign: "left", minWidth: 0 }}>
                      {f.home_team.name} <span style={{ color: "var(--text-dim)" }}>vs</span> {f.away_team.name}
                    </span>
                    {finished ? (
                      <span className="mono" style={{ flexShrink: 0 }}>
                        {f.goals.home ?? "-"} - {f.goals.away ?? "-"}
                      </span>
                    ) : (
                      <span style={{ color: "var(--text-dim)", fontSize: "0.72rem", flexShrink: 0 }}>
                        à venir
                      </span>
                    )}
                  </>
                );
                return finished ? (
                  <button
                    key={f.fixture_id}
                    className="result-row"
                    onClick={() => navigate(`/match/${f.fixture_id}`)}
                    style={resultButtonStyle}
                    title="Analyser ce match"
                  >
                    {row}
                  </button>
                ) : (
                  <div
                    key={f.fixture_id}
                    style={{ ...resultButtonStyle, cursor: "default", opacity: 0.55 }}
                    title="Match non joué — pas d'analyse possible"
                  >
                    {row}
                  </div>
                );
              })}
            </div>
          )}
          <p style={{ color: "var(--text-dim)", fontSize: "0.7rem", marginTop: 8 }}>
            Seuls les matchs terminés sont analysables.
          </p>
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
