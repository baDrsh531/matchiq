const EVENT_STYLE = {
  Goal: { icon: "⚽", color: "var(--green)" },
  Card: { icon: "🟨", color: "var(--gold)" },
  subst: { icon: "⇄", color: "var(--blue)" },
  Var: { icon: "VAR", color: "var(--text-dim)" },
};

export default function Timeline({ events }) {
  if (!events?.length) {
    return (
      <div className="panel">
        <h3>Timeline</h3>
        <p style={{ color: "var(--text-dim)" }}>Aucun événement disponible.</p>
      </div>
    );
  }

  const sorted = [...events].sort(
    (a, b) => (a.time?.elapsed ?? 0) - (b.time?.elapsed ?? 0)
  );

  return (
    <div className="panel">
      <h3 style={{ marginBottom: 14 }}>Timeline</h3>
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {sorted.map((event, idx) => {
          const style = EVENT_STYLE[event.type] || { icon: "•", color: "var(--text-dim)" };
          const minute = event.time?.elapsed;
          const extra = event.time?.extra;
          return (
            <div key={idx} style={{ display: "flex", gap: 12, alignItems: "center" }}>
              <span className="mono" style={{ width: 40, color: "var(--text-dim)" }}>
                {minute}{extra ? `+${extra}` : ""}'
              </span>
              <span style={{ width: 24, textAlign: "center", color: style.color }}>
                {style.icon}
              </span>
              <span style={{ flex: 1 }}>
                <strong>{event.player?.name}</strong>{" "}
                <span style={{ color: "var(--text-dim)" }}>
                  ({event.team?.name}) — {event.detail}
                </span>
                {event.assist?.name && (
                  <span style={{ color: "var(--text-dim)" }}>
                    {" "}
                    · passe de {event.assist.name}
                  </span>
                )}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
