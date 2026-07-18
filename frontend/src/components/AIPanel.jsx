import { useState } from "react";
import { getReport } from "../api/client";

export default function AIPanel({ fixtureId }) {
  const [report, setReport] = useState(null);
  const [status, setStatus] = useState("idle"); // idle | loading | error | done
  const [errorMessage, setErrorMessage] = useState("");

  const loadReport = async () => {
    setStatus("loading");
    try {
      const data = await getReport(fixtureId);
      setReport(data);
      setStatus("done");
    } catch (err) {
      setErrorMessage(
        err.response?.data?.detail ||
          "Impossible de générer le rapport IA pour ce match."
      );
      setStatus("error");
    }
  };

  return (
    <div className="panel">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h3>Analyse IA</h3>
        {status !== "loading" && (
          <button
            onClick={loadReport}
            style={{
              background: "var(--bg-panel-raised)",
              border: "1px solid var(--border)",
              color: "var(--text)",
              borderRadius: 8,
              padding: "6px 14px",
              cursor: "pointer",
            }}
          >
            {report ? "Régénérer" : "Générer le rapport"}
          </button>
        )}
      </div>

      {status === "loading" && (
        <p style={{ color: "var(--text-dim)" }}>Génération en cours…</p>
      )}

      {status === "error" && (
        <p style={{ color: "var(--red)" }}>{errorMessage}</p>
      )}

      {report && (
        <div style={{ display: "flex", flexDirection: "column", gap: 18, marginTop: 12 }}>
          <section>
            <div style={{ fontSize: "0.75rem", color: "var(--gold)", marginBottom: 6 }}>
              RAPPORT HOMME DU MATCH
            </div>
            <p style={{ lineHeight: 1.6 }}>{report.motm_report}</p>
          </section>

          <section>
            <div style={{ fontSize: "0.75rem", color: "var(--blue)", marginBottom: 6 }}>
              SUGGESTIONS TACTIQUES
            </div>
            {Object.entries(report.tactical_suggestions).map(([team, text]) => (
              <div key={team} style={{ marginBottom: 10 }}>
                <strong>{team}</strong>
                <p style={{ lineHeight: 1.6, margin: "2px 0 0" }}>{text}</p>
              </div>
            ))}
          </section>
        </div>
      )}
    </div>
  );
}
