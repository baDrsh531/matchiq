import { Link } from "react-router-dom";

function parseGrid(grid) {
  if (!grid) return null;
  const [row, col] = grid.split(":").map(Number);
  if (Number.isNaN(row) || Number.isNaN(col)) return null;
  return { row, col };
}

export default function FormationPitch({ lineup }) {
  if (!lineup?.startXI?.length) return null;

  const positions = lineup.startXI
    .map((entry) => ({ ...entry.player, ...parseGrid(entry.player.grid) }))
    .filter((p) => p.row);

  if (!positions.length) return null;

  const maxRow = Math.max(...positions.map((p) => p.row));
  const colsByRow = {};
  positions.forEach((p) => {
    colsByRow[p.row] = Math.max(colsByRow[p.row] || 0, p.col);
  });

  return (
    <div className="panel">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          {lineup.team?.logo && (
            <img src={lineup.team.logo} alt="" style={{ width: 22, height: 22 }} />
          )}
          <strong>{lineup.team?.name}</strong>
        </div>
        <span className="badge badge-blue">{lineup.formation}</span>
      </div>

      <div
        style={{
          position: "relative",
          height: 380,
          borderRadius: 8,
          overflow: "hidden",
          background:
            "repeating-linear-gradient(0deg, #143a1e, #143a1e 38px, #16401f 38px, #16401f 76px)",
          border: "1px solid rgba(255,255,255,0.12)",
        }}
      >
        <div
          style={{
            position: "absolute",
            top: "50%",
            left: 0,
            right: 0,
            borderTop: "1px dashed rgba(255,255,255,0.25)",
          }}
        />
        {positions.map((p) => {
          const maxCol = colsByRow[p.row];
          const xPct = maxCol > 1 ? 15 + ((p.col - 1) / (maxCol - 1)) * 70 : 50;
          const yPct = 100 - (((p.row - 1) / (maxRow - 1 || 1)) * 78 + 10);

          return (
            <Link
              key={p.id}
              to={`/player/${p.id}`}
              style={{
                position: "absolute",
                left: `${xPct}%`,
                top: `${yPct}%`,
                transform: "translate(-50%, -50%)",
                textAlign: "center",
                textDecoration: "none",
                color: "inherit",
              }}
              title={p.name}
            >
              <div
                style={{
                  width: 30,
                  height: 30,
                  borderRadius: "50%",
                  background: "var(--bg-panel-raised)",
                  border: "2px solid var(--gold)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 12,
                  fontWeight: 700,
                  color: "var(--gold)",
                  margin: "0 auto",
                }}
              >
                {p.number}
              </div>
              <div
                style={{
                  fontSize: 10,
                  color: "#fff",
                  marginTop: 3,
                  whiteSpace: "nowrap",
                  textShadow: "0 1px 2px rgba(0,0,0,0.8)",
                }}
              >
                {p.name}
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
