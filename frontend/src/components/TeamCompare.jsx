import StatCompareRow from "./StatCompareRow";

function computeRecord(matches) {
  let wins = 0;
  let draws = 0;
  let losses = 0;
  let goalsFor = 0;
  let goalsAgainst = 0;

  for (const m of matches) {
    goalsFor += m.goals_for ?? 0;
    goalsAgainst += m.goals_against ?? 0;
    if (m.goals_for > m.goals_against) wins += 1;
    else if (m.goals_for === m.goals_against) draws += 1;
    else losses += 1;
  }

  return { wins, draws, losses, goalsFor, goalsAgainst };
}

function averageSquadScore(squad) {
  if (!squad.length) return 0;
  return squad.reduce((sum, p) => sum + p.average_score, 0) / squad.length;
}

export default function TeamCompare({ teamA, teamB }) {
  const recordA = computeRecord(teamA.matches);
  const recordB = computeRecord(teamB.matches);
  const avgA = averageSquadScore(teamA.squad);
  const avgB = averageSquadScore(teamB.squad);
  const bestA = teamA.squad[0];
  const bestB = teamB.squad[0];

  return (
    <div className="panel">
      <div style={{ display: "flex", justifyContent: "space-around", marginBottom: 24 }}>
        <div style={{ textAlign: "center" }}>
          {teamA.team_logo && <img src={teamA.team_logo} alt="" style={{ width: 40, height: 40 }} />}
          <div style={{ color: "var(--gold)", fontWeight: 600, marginTop: 6 }}>{teamA.team_name}</div>
        </div>
        <div style={{ textAlign: "center" }}>
          {teamB.team_logo && <img src={teamB.team_logo} alt="" style={{ width: 40, height: 40 }} />}
          <div style={{ color: "var(--blue)", fontWeight: 600, marginTop: 6 }}>{teamB.team_name}</div>
        </div>
      </div>

      <StatCompareRow
        label="Score moyen de l'effectif"
        valueA={avgA}
        valueB={avgB}
        formatValue={(v) => v.toFixed(1)}
      />
      <StatCompareRow label="Victoires (matchs analysés)" valueA={recordA.wins} valueB={recordB.wins} />
      <StatCompareRow label="Buts marqués" valueA={recordA.goalsFor} valueB={recordB.goalsFor} />
      <StatCompareRow
        label="Buts encaissés"
        valueA={recordA.goalsAgainst}
        valueB={recordB.goalsAgainst}
        higherIsBetter={false}
      />

      <div
        style={{
          display: "flex",
          justifyContent: "space-around",
          marginTop: 20,
          paddingTop: 16,
          borderTop: "1px solid var(--border)",
          fontSize: "0.85rem",
        }}
      >
        <div style={{ textAlign: "center" }}>
          <div style={{ color: "var(--text-dim)", marginBottom: 4 }}>Meilleur joueur</div>
          <div>{bestA ? `${bestA.name} (${bestA.average_score.toFixed(1)})` : "—"}</div>
        </div>
        <div style={{ textAlign: "center" }}>
          <div style={{ color: "var(--text-dim)", marginBottom: 4 }}>Meilleur joueur</div>
          <div>{bestB ? `${bestB.name} (${bestB.average_score.toFixed(1)})` : "—"}</div>
        </div>
      </div>
    </div>
  );
}
