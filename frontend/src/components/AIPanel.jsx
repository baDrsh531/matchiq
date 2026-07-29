import { useEffect, useState } from "react";
import { askMatch, getReport } from "../api/client";

const SUGGESTIONS = [
  "Pourquoi ce joueur est-il l'homme du match ?",
  "Quelle équipe a été la plus dangereuse ?",
  "Quel défenseur a le mieux tenu ?",
];

function LangToggle({ lang, onChange }) {
  return (
    <div
      role="group"
      aria-label="Langue de l'analyse IA"
      style={{ display: "inline-flex", border: "1px solid var(--border)", borderRadius: 8, overflow: "hidden" }}
    >
      {["fr", "en"].map((l) => (
        <button
          key={l}
          type="button"
          aria-pressed={lang === l}
          onClick={() => onChange(l)}
          style={{
            border: 0,
            cursor: "pointer",
            padding: "4px 10px",
            fontSize: "0.72rem",
            fontWeight: 600,
            letterSpacing: "0.03em",
            background: lang === l ? "var(--gold)" : "transparent",
            color: lang === l ? "#141414" : "var(--text-dim)",
          }}
        >
          {l.toUpperCase()}
        </button>
      ))}
    </div>
  );
}

function MatchQA({ fixtureId, lang }) {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState(null);
  const [status, setStatus] = useState("idle"); // idle | loading | error | done
  const [errorMessage, setErrorMessage] = useState("");

  // La réponse est dans une langue donnée : si on change de langue, on la retire
  // pour ne pas afficher une réponse FR sous un libellé EN (et inversement).
  useEffect(() => {
    setAnswer(null);
    setStatus("idle");
  }, [lang]);

  const ask = async (q) => {
    const text = (q ?? question).trim();
    if (text.length < 3) return;
    setQuestion(text);
    setStatus("loading");
    setAnswer(null);
    try {
      const data = await askMatch(fixtureId, text, lang);
      setAnswer(data.answer);
      setStatus("done");
    } catch (err) {
      setErrorMessage(
        err.response?.data?.detail || "Impossible de répondre à cette question pour le moment."
      );
      setStatus("error");
    }
  };

  return (
    <section
      style={{
        borderBottom: "1px solid var(--border)",
        paddingBottom: 16,
        marginBottom: 4,
      }}
    >
      <div style={{ fontSize: "0.75rem", color: "var(--gold)", marginBottom: 8 }}>
        POSER UNE QUESTION SUR CE MATCH
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          ask();
        }}
        style={{ display: "flex", gap: 8 }}
      >
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ex : pourquoi ce joueur a-t-il la meilleure note ?"
          aria-label="Question sur le match"
          style={{
            flex: 1,
            minWidth: 0,
            background: "var(--bg-panel-raised)",
            border: "1px solid var(--border)",
            borderRadius: 8,
            color: "var(--text)",
            padding: "8px 12px",
            fontSize: "0.9rem",
          }}
        />
        <button
          type="submit"
          disabled={status === "loading" || question.trim().length < 3}
          style={{
            background: "var(--gold)",
            border: "none",
            borderRadius: 8,
            color: "#141414",
            fontWeight: 600,
            padding: "8px 16px",
            cursor: status === "loading" ? "default" : "pointer",
            opacity: status === "loading" || question.trim().length < 3 ? 0.6 : 1,
          }}
        >
          Demander
        </button>
      </form>

      {status === "idle" && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 10 }}>
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              onClick={() => ask(s)}
              style={{
                background: "transparent",
                border: "1px solid var(--border)",
                borderRadius: 999,
                color: "var(--text-dim)",
                fontSize: "0.76rem",
                padding: "4px 10px",
                cursor: "pointer",
              }}
            >
              {s}
            </button>
          ))}
        </div>
      )}

      {status === "loading" && (
        <p style={{ color: "var(--text-dim)", marginTop: 10 }}>Recherche dans les données du match…</p>
      )}
      {status === "error" && <p style={{ color: "var(--red)", marginTop: 10 }}>{errorMessage}</p>}
      {status === "done" && answer && (
        <p style={{ lineHeight: 1.6, marginTop: 12 }}>{answer}</p>
      )}

      {status === "done" && (
        <p style={{ fontSize: "0.7rem", color: "var(--text-dim)", marginTop: 8 }}>
          Réponse fondée uniquement sur les scores et statistiques calculés de ce match.
        </p>
      )}
    </section>
  );
}

export default function AIPanel({ fixtureId }) {
  const [lang, setLang] = useState("fr");
  const [report, setReport] = useState(null);
  const [status, setStatus] = useState("idle"); // idle | loading | error | done
  const [errorMessage, setErrorMessage] = useState("");

  const loadReport = async (targetLang = lang) => {
    setStatus("loading");
    try {
      const data = await getReport(fixtureId, false, targetLang);
      setReport(data);
      setStatus("done");
    } catch (err) {
      setErrorMessage(
        err.response?.data?.detail || "Impossible de générer le rapport IA pour ce match."
      );
      setStatus("error");
    }
  };

  // Si un rapport est déjà affiché et qu'on change de langue, on le recharge
  // dans la nouvelle langue (mis en cache par langue côté serveur, donc rapide).
  useEffect(() => {
    if (report) loadReport(lang);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lang]);

  return (
    <div className="panel">
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 12 }}>
        <LangToggle lang={lang} onChange={setLang} />
      </div>

      <MatchQA fixtureId={fixtureId} lang={lang} />

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h3>Analyse IA</h3>
        {status !== "loading" && (
          <button
            onClick={() => loadReport()}
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
