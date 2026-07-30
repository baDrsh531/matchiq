import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { getLlmMetrics } from "../api/client";
import { SkeletonBlock } from "../components/Skeleton";

function Stat({ label, value, sub }) {
  return (
    <div className="panel" style={{ flex: "1 1 140px", minWidth: 140 }}>
      <div style={{ color: "var(--text-dim)", fontSize: "0.72rem", letterSpacing: "0.04em", marginBottom: 6 }}>
        {label}
      </div>
      <div className="mono" style={{ fontSize: "1.5rem", fontWeight: 700 }}>{value}</div>
      {sub && <div style={{ color: "var(--text-dim)", fontSize: "0.75rem", marginTop: 4 }}>{sub}</div>}
    </div>
  );
}

const fmt = (n) => (n >= 1000 ? `${(n / 1000).toFixed(1)}k` : `${n}`);

export default function LlmOpsPage() {
  const [data, setData] = useState(null);
  const [status, setStatus] = useState("loading");

  useEffect(() => {
    getLlmMetrics(15)
      .then((d) => { setData(d); setStatus("done"); })
      .catch(() => setStatus("error"));
  }, []);

  return (
    <>
      <header style={{ marginBottom: 18 }}>
        <h1 style={{ fontSize: "1.6rem" }}>Monitoring LLM</h1>
        <p style={{ color: "var(--text-dim)", marginTop: 4 }}>
          Coût, tokens et latence mesurés à chaque appel — le point de passage unique du
          client LLM est instrumenté (approche FinOps/MLOps).
        </p>
      </header>

      {status === "loading" && <SkeletonBlock height={240} />}
      {status === "error" && <p style={{ color: "var(--red)" }}>Métriques indisponibles.</p>}

      {status === "done" && data && data.calls === 0 && (
        <div className="panel">
          <p style={{ color: "var(--text-dim)" }}>
            Aucun appel LLM enregistré. En mode démo la génération est désactivée : le tableau de
            bord se remplit quand l&apos;application tourne avec un vrai backend LLM (Gemini ou modèle local).
          </p>
        </div>
      )}

      {status === "done" && data && data.calls > 0 && (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 16 }}>
            <Stat label="APPELS" value={data.calls} sub={`${Math.round(data.success_rate * 100)}% réussis`} />
            <Stat label="TOKENS" value={fmt(data.total_tokens)} sub={`${fmt(data.prompt_tokens)} in · ${fmt(data.completion_tokens)} out`} />
            <Stat label="COÛT ESTIMÉ" value={`$${data.cost_usd.toFixed(4)}`} sub="grille tarifaire par modèle" />
            <Stat label="LATENCE MOY." value={data.avg_latency_ms ? `${Math.round(data.avg_latency_ms)} ms` : "—"} />
          </div>

          <div className="panel" style={{ marginBottom: 16 }}>
            <div style={{ fontSize: "0.72rem", letterSpacing: "0.05em", color: "var(--text-dim)", marginBottom: 12 }}>
              PAR MODÈLE
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {data.by_model.map((m) => (
                <div key={m.model} style={{ display: "grid", gridTemplateColumns: "1fr 4rem 5rem 5rem", gap: 10, alignItems: "center", fontSize: "0.85rem" }}>
                  <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {m.model} <span style={{ color: "var(--text-dim)", fontSize: "0.75rem" }}>({m.provider})</span>
                  </span>
                  <span className="mono" style={{ textAlign: "right" }}>{m.calls}</span>
                  <span className="mono" style={{ textAlign: "right", color: "var(--text-dim)" }}>{fmt(m.tokens)} tok</span>
                  <span className="mono" style={{ textAlign: "right" }}>${m.cost_usd.toFixed(4)}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="panel">
            <div style={{ fontSize: "0.72rem", letterSpacing: "0.05em", color: "var(--text-dim)", marginBottom: 12 }}>
              DERNIERS APPELS
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              {data.recent.map((r, i) => (
                <div key={i} style={{ display: "grid", gridTemplateColumns: "1rem 1fr 4rem 4rem", gap: 10, alignItems: "center", fontSize: "0.8rem" }}>
                  <span style={{ color: r.ok ? "var(--green)" : "var(--red)" }}>{r.ok ? "●" : "✕"}</span>
                  <span style={{ color: "var(--text-dim)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{r.model}</span>
                  <span className="mono" style={{ textAlign: "right", color: "var(--text-dim)" }}>
                    {(r.prompt_tokens + r.completion_tokens)} tok{r.estimated_tokens ? "*" : ""}
                  </span>
                  <span className="mono" style={{ textAlign: "right", color: "var(--text-dim)" }}>{Math.round(r.latency_ms)} ms</span>
                </div>
              ))}
            </div>
            <div style={{ color: "var(--text-dim)", fontSize: "0.7rem", marginTop: 10 }}>
              * tokens estimés (usage non exposé par le backend)
            </div>
          </div>
        </motion.div>
      )}
    </>
  );
}
