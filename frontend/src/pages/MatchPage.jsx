import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { motion } from "framer-motion";
import { getMatch, getPlayers } from "../api/client";
import MOTMCard from "../components/MOTMCard";
import RankingList from "../components/RankingList";
import RadarComparison from "../components/RadarComparison";
import PlayerDetailCard from "../components/PlayerDetailCard";
import Timeline from "../components/Timeline";
import AIPanel from "../components/AIPanel";
import ShareMOTMButton from "../components/ShareMOTMButton";
import FormationPitch from "../components/FormationPitch";
import { MatchSkeleton } from "../components/Skeleton";

export default function MatchPage() {
  const { fixtureId: fixtureIdParam } = useParams();
  const fixtureId = parseInt(fixtureIdParam, 10);

  const [match, setMatch] = useState(null);
  const [players, setPlayers] = useState([]);
  const [selectedPlayerId, setSelectedPlayerId] = useState(null);
  const [status, setStatus] = useState("loading"); // loading | error | done
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    if (Number.isNaN(fixtureId)) return;

    let cancelled = false;
    setStatus("loading");
    setMatch(null);
    setPlayers([]);
    setErrorMessage("");

    Promise.all([getMatch(fixtureId), getPlayers(fixtureId)])
      .then(([matchData, playersData]) => {
        if (cancelled) return;
        setMatch(matchData);
        setPlayers(playersData.players);
        setSelectedPlayerId(playersData.players[0]?.player_id ?? null);
        setStatus("done");
      })
      .catch((err) => {
        if (cancelled) return;
        setErrorMessage(err.response?.data?.detail || "Impossible de charger ce match.");
        setStatus("error");
      });

    return () => {
      cancelled = true;
    };
  }, [fixtureId]);

  const motm = players[0];
  const selectedPlayer = players.find((p) => p.player_id === selectedPlayerId) || null;

  return (
    <>
      <div style={{ marginBottom: 20 }}>
        <Link to="/" style={{ color: "var(--text-dim)", fontSize: "0.85rem", textDecoration: "none" }}>
          ← Accueil
        </Link>
      </div>

      {status === "loading" && <MatchSkeleton />}
      {status === "error" && <p style={{ color: "var(--red)" }}>{errorMessage}</p>}

      {status === "done" && match && (
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          <motion.div
            className="panel"
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25 }}
            style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}
          >
            <Link
              to={`/team/${match.teams?.home?.id}`}
              style={{ display: "flex", alignItems: "center", gap: 10, textDecoration: "none", color: "inherit" }}
            >
              {match.teams?.home?.logo && (
                <img src={match.teams.home.logo} alt="" style={{ width: 32, height: 32 }} />
              )}
              <div>
                <div style={{ fontWeight: 600 }}>{match.teams?.home?.name}</div>
                <div style={{ color: "var(--text-dim)", fontSize: "0.8rem" }}>Domicile</div>
              </div>
            </Link>
            <div className="mono" style={{ fontSize: "1.8rem" }}>
              {match.goals?.home} - {match.goals?.away}
            </div>
            <Link
              to={`/team/${match.teams?.away?.id}`}
              style={{ display: "flex", alignItems: "center", gap: 10, textDecoration: "none", color: "inherit" }}
            >
              <div style={{ textAlign: "right" }}>
                <div style={{ fontWeight: 600 }}>{match.teams?.away?.name}</div>
                <div style={{ color: "var(--text-dim)", fontSize: "0.8rem" }}>Extérieur</div>
              </div>
              {match.teams?.away?.logo && (
                <img src={match.teams.away.logo} alt="" style={{ width: 32, height: 32 }} />
              )}
            </Link>
          </motion.div>

          <MOTMCard player={motm} />
          <div style={{ display: "flex", justifyContent: "flex-end" }}>
            <ShareMOTMButton player={motm} match={match} />
          </div>

          {match.lineups?.length === 2 && (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
              <FormationPitch lineup={match.lineups[0]} />
              <FormationPitch lineup={match.lineups[1]} />
            </div>
          )}

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
            <RankingList
              players={players}
              selectedId={selectedPlayerId}
              onSelect={setSelectedPlayerId}
            />
            <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
              <PlayerDetailCard fixtureId={fixtureId} player={selectedPlayer} />
              <RadarComparison player={selectedPlayer} />
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
            <Timeline events={match.events} />
            <AIPanel fixtureId={fixtureId} />
          </div>
        </div>
      )}
    </>
  );
}
