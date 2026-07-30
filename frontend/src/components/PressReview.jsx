import { useState } from "react";
import { getMatchPress } from "../api/client";

// Revue de presse EXTERNE : chargée à la demande (appel sortant), affichée dans
// un cadre distinct avec un badge de confiance séparé des données calculées.
export default function PressReview({ fixtureId }) {
  const [state, setState] = useState("idle"); // idle | loading | done | error | empty
  const [data, setData] = useState(null);
  const [message, setMessage] = useState("");

  const load = async () => {
    setState("loading");
    try {
      const res = await getMatchPress(fixtureId);
      setData(res);
      setState(res.sources.length ? "done" : "empty");
    } catch (err) {
      setMessage(err.response?.data?.detail || "Revue de presse indisponible.");
      setState("error");
    }
  };

  return (
    <div className="panel">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 8 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <h3 style={{ margin: 0 }}>Revue de presse</h3>
          <span
            title="Sources externes non vérifiées — n'entrent jamais dans le calcul des scores."
            style={{ fontSize: "0.66rem", color: "var(--text-dim)", border: "1px solid var(--border)", borderRadius: 999, padding: "2px 8px" }}
          >
            externe · non vérifié
          </span>
        </div>
        {state === "idle" && (
          <button onClick={load} style={{ padding: "6px 14px", borderRadius: 8, border: "1px solid var(--border)", background: "transparent", color: "var(--text)", cursor: "pointer", fontSize: "0.82rem" }}>
            Charger
          </button>
        )}
      </div>

      {state === "loading" && <p style={{ color: "var(--text-dim)", marginTop: 10 }}>Recherche en cours…</p>}
      {state === "error" && <p style={{ color: "var(--text-dim)", marginTop: 10, fontSize: "0.85rem" }}>{message}</p>}
      {state === "empty" && (
        <p style={{ color: "var(--text-dim)", marginTop: 10, fontSize: "0.85rem" }}>
          Aucun article trouvé pour cette affiche.
        </p>
      )}

      {state === "done" && data && (
        <div style={{ marginTop: 12 }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {data.sources.map((s, i) => (
              <a
                key={i}
                href={s.url}
                target="_blank"
                rel="noopener noreferrer"
                style={{ display: "block", padding: "8px 10px", borderRadius: 8, border: "1px solid var(--border)", textDecoration: "none", color: "var(--text)" }}
              >
                <div style={{ fontSize: "0.85rem", marginBottom: 2, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{s.title}</div>
                <div style={{ color: "var(--text-dim)", fontSize: "0.72rem" }}>{s.domain}</div>
              </a>
            ))}
          </div>
          <p style={{ color: "var(--text-dim)", fontSize: "0.7rem", marginTop: 10 }}>{data.disclaimer}</p>
        </div>
      )}
    </div>
  );
}
