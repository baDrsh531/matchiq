import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
} from "recharts";

export default function RadarComparison({ player }) {
  if (!player?.radar) return null;

  const data = Object.entries(player.radar).map(([category, value]) => ({
    category,
    value,
  }));

  return (
    <div className="panel">
      <h3 style={{ marginBottom: 4 }}>{player.name}</h3>
      <p style={{ color: "var(--text-dim)", marginTop: 0, fontSize: "0.85rem" }}>
        Profil statistique (0-10) pondéré selon le poste : {player.position}
      </p>
      <div style={{ height: 300 }}>
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart data={data} outerRadius="75%">
            <PolarGrid stroke="var(--border)" />
            <PolarAngleAxis
              dataKey="category"
              tick={{ fill: "var(--text-dim)", fontSize: 11 }}
            />
            <PolarRadiusAxis
              angle={30}
              domain={[0, 10]}
              tick={{ fill: "var(--text-dim)", fontSize: 10 }}
            />
            <Radar
              dataKey="value"
              stroke="var(--blue)"
              fill="var(--blue)"
              fillOpacity={0.35}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
