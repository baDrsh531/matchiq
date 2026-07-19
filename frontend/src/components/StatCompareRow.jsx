export default function StatCompareRow({
  label,
  valueA,
  valueB,
  higherIsBetter = true,
  formatValue = (v) => v,
}) {
  const total = valueA + valueB || 1;
  const pctA = (valueA / total) * 100;
  const aWins = higherIsBetter ? valueA >= valueB : valueA <= valueB;

  return (
    <div style={{ marginBottom: 14 }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
          fontSize: "0.85rem",
          marginBottom: 4,
        }}
      >
        <span
          className="mono"
          style={{ color: aWins ? "var(--gold)" : "var(--text-dim)", fontWeight: aWins ? 700 : 400 }}
        >
          {formatValue(valueA)}
        </span>
        <span style={{ color: "var(--text-dim)" }}>{label}</span>
        <span
          className="mono"
          style={{ color: !aWins ? "var(--blue)" : "var(--text-dim)", fontWeight: !aWins ? 700 : 400 }}
        >
          {formatValue(valueB)}
        </span>
      </div>
      <div
        style={{
          display: "flex",
          height: 6,
          borderRadius: 3,
          overflow: "hidden",
          background: "var(--bg-panel-raised)",
        }}
      >
        <div style={{ width: `${pctA}%`, background: "var(--gold)" }} />
        <div style={{ width: `${100 - pctA}%`, background: "var(--blue)" }} />
      </div>
    </div>
  );
}
