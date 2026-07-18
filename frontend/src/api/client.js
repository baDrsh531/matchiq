import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000",
});

export const getRecentMatches = (limit = 20) =>
  api.get("/matches", { params: { limit } }).then((res) => res.data);

export const getMatch = (fixtureId) =>
  api.get(`/matches/${fixtureId}`).then((res) => res.data);

export const getPlayers = (fixtureId) =>
  api.get(`/matches/${fixtureId}/players`).then((res) => res.data);

export const getPlayerDetail = (fixtureId, playerId) =>
  api.get(`/matches/${fixtureId}/player/${playerId}`).then((res) => res.data);

export const getReport = (fixtureId, refresh = false) =>
  api
    .get(`/matches/${fixtureId}/report`, { params: { refresh } })
    .then((res) => res.data);

export const getPlayerHistory = (playerId) =>
  api.get(`/players/${playerId}/history`).then((res) => res.data);

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

export default api;
