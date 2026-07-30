import axios from "axios";

export const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const api = axios.create({ baseURL: API_BASE });

// URL directe du PDF (le navigateur télécharge/ouvre via ce lien, pas via axios).
export const reportPdfUrl = (fixtureId, lang = "fr") =>
  `${API_BASE}/matches/${fixtureId}/report.pdf?lang=${lang}`;

export const getRecentMatches = (limit = 20) =>
  api.get("/matches", { params: { limit } }).then((res) => res.data);

export const getMatch = (fixtureId) =>
  api.get(`/matches/${fixtureId}`).then((res) => res.data);

export const getPlayers = (fixtureId) =>
  api.get(`/matches/${fixtureId}/players`).then((res) => res.data);

export const getPlayerDetail = (fixtureId, playerId, lang = "fr") =>
  api
    .get(`/matches/${fixtureId}/player/${playerId}`, { params: { lang } })
    .then((res) => res.data);

export const getReport = (fixtureId, refresh = false, lang = "fr") =>
  api
    .get(`/matches/${fixtureId}/report`, { params: { refresh, lang } })
    .then((res) => res.data);

export const askMatch = (fixtureId, q, lang = "fr") =>
  api.get(`/matches/${fixtureId}/ask`, { params: { q, lang } }).then((res) => res.data);

export const getPlayerHistory = (playerId) =>
  api.get(`/players/${playerId}/history`).then((res) => res.data);

export const getSimilarPlayers = (playerId, limit = 5) =>
  api.get(`/players/${playerId}/similar`, { params: { limit } }).then((res) => res.data);

export const getTeamHistory = (teamId) =>
  api.get(`/teams/${teamId}/history`).then((res) => res.data);

export const getSupportedLeagues = () =>
  api.get("/standings/leagues").then((res) => res.data);

export const getStandings = (leagueId, season) =>
  api
    .get("/standings", { params: { league_id: leagueId, season } })
    .then((res) => res.data);

export const searchTeams = (query) =>
  api.get("/search/teams", { params: { query } }).then((res) => res.data);

export const getTeamFixtures = (teamId, season = 2023) =>
  api.get(`/search/teams/${teamId}/fixtures`, { params: { season } }).then((res) => res.data);

export const searchPlayers = (query) =>
  api.get("/search/players", { params: { query } }).then((res) => res.data);

export const getLeaderboard = (position, limit = 20) =>
  api.get("/leaderboard", { params: { position, limit } }).then((res) => res.data);

export const getMatchComparison = (a, b) =>
  api.get("/compare/matches", { params: { a, b } }).then((res) => res.data);

// ── Prédiction pré-match (Elo) ──────────────────────────────────────────────
export const getPredictionLeagues = () =>
  api.get("/predict/leagues").then((res) => res.data);

export const getEloTable = (leagueId, season) =>
  api
    .get("/predict/table", { params: { league_id: leagueId, season } })
    .then((res) => res.data);

export const getMatchup = (leagueId, season, home, away) =>
  api
    .get("/predict/matchup", { params: { league_id: leagueId, season, home, away } })
    .then((res) => res.data);

export const getFixturePrediction = (fixtureId, leagueId, season) =>
  api
    .get(`/predict/fixture/${fixtureId}`, { params: { league_id: leagueId, season } })
    .then((res) => res.data);

export default api;
