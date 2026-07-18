import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Legend,
} from "recharts";

export default function RadarOverlay({ playerA, playerB }) {
  const categories = Array.from(
    new Set([...Object.keys(playerA.radar || {}), ...Object.keys(playerB.radar || {})])
  );

  const data = categories.map((category) => ({
    category,
    [playerA.name]: playerA.radar?.[category] ?? 0,
    [playerB.name]: playerB.radar?.[category] ?? 0,
  }));

  return (
    <div style={{ height: 380 }}>
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart data={data} outerRadius="70%">
          <PolarGrid stroke="var(--border)" />
          <PolarAngleAxis dataKey="category" tick={{ fill: "var(--text-dim)", fontSize: 11 }} />
          <PolarRadiusAxis angle={30} domain={[0, 10]} tick={{ fill: "var(--text-dim)", fontSize: 10 }} />
          <Radar name={playerA.name} dataKey={playerA.name} stroke="var(--gold)" fill="var(--gold)" fillOpacity={0.25} />
          <Radar name={playerB.name} dataKey={playerB.name} stroke="var(--blue)" fill="var(--blue)" fillOpacity={0.25} />
          <Legend wrapperStyle={{ color: "var(--text-dim)" }} />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
