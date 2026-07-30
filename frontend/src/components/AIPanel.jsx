import { useEffect, useRef, useState } from "react";
import { chatMatch, getReport, reportPdfUrl } from "../api/client";

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

// Conversation multi-tours : le fil est conservé, le LLM résout « et lui ? » /
// « pourquoi ? » depuis les tours précédents (réponses toujours ancrées aux données).
function MatchChat({ fixtureId, lang }) {
  const [messages, setMessages] = useState([]); // {role:"user"|"assistant", content}
  const [input, setInput] = useState("");
  const [status, setStatus] = useState("idle"); // idle | loading | error
  const [errorMessage, setErrorMessage] = useState("");
  const threadRef = useRef(null);

  // Changer de langue repart d'une conversation vierge (cohérence de langue).
  useEffect(() => {
    setMessages([]);
    setStatus("idle");
    setErrorMessage("");
  }, [lang]);

  useEffect(() => {
    if (threadRef.current) threadRef.current.scrollTop = threadRef.current.scrollHeight;
  }, [messages, status]);

  const send = async (q) => {
    const text = (q ?? input).trim();
    if (text.length < 3 || status === "loading") return;
    const next = [...messages, { role: "user", content: text }];
    setMessages(next);
    setInput("");
    setStatus("loading");
    setErrorMessage("");
    try {
      const data = await chatMatch(fixtureId, next, lang);
      setMessages([...next, { role: "assistant", content: data.answer }]);
      setStatus("idle");
    } catch (err) {
      setErrorMessage(err.response?.data?.detail || "Impossible de répondre pour le moment.");
      setStatus("error");
    }
  };

  return (
    <section style={{ borderBottom: "1px solid var(--border)", paddingBottom: 16, marginBottom: 4 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
        <div style={{ fontSize: "0.75rem", color: "var(--gold)" }}>DISCUTER DE CE MATCH</div>
        {messages.length > 0 && (
          <button
            onClick={() => { setMessages([]); setStatus("idle"); }}
            style={{ background: "transparent", border: "none", color: "var(--text-dim)", fontSize: "0.72rem", cursor: "pointer" }}
          >
            Réinitialiser
          </button>
        )}
      </div>

      {messages.length > 0 && (
        <div ref={threadRef} style={{ display: "flex", flexDirection: "column", gap: 8, maxHeight: 260, overflowY: "auto", marginBottom: 10 }}>
          {messages.map((m, i) => (
            <div
              key={i}
              style={{
                alignSelf: m.role === "user" ? "flex-end" : "flex-start",
                maxWidth: "85%",
                background: m.role === "user" ? "var(--gold)" : "var(--bg-panel-raised)",
                color: m.role === "user" ? "#141414" : "var(--text)",
                borderRadius: 12,
                padding: "8px 12px",
                fontSize: "0.9rem",
                lineHeight: 1.5,
              }}
            >
              {m.content}
            </div>
          ))}
          {status === "loading" && (
            <div style={{ alignSelf: "flex-start", color: "var(--text-dim)", fontSize: "0.85rem", padding: "4px 12px" }}>
              …
            </div>
          )}
        </div>
      )}

      <form onSubmit={(e) => { e.preventDefault(); send(); }} style={{ display: "flex", gap: 8 }}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={messages.length ? "Poser une question de suivi…" : "Ex : pourquoi ce joueur a-t-il la meilleure note ?"}
          aria-label="Message"
          style={{ flex: 1, minWidth: 0, background: "var(--bg-panel-raised)", border: "1px solid var(--border)", borderRadius: 8, color: "var(--text)", padding: "8px 12px", fontSize: "0.9rem" }}
        />
        <button
          type="submit"
          disabled={status === "loading" || input.trim().length < 3}
          style={{ background: "var(--gold)", border: "none", borderRadius: 8, color: "#141414", fontWeight: 600, padding: "8px 16px", cursor: "pointer", opacity: status === "loading" || input.trim().length < 3 ? 0.6 : 1 }}
        >
          Envoyer
        </button>
      </form>

      {messages.length === 0 && status !== "loading" && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 10 }}>
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              onClick={() => send(s)}
              style={{ background: "transparent", border: "1px solid var(--border)", borderRadius: 999, color: "var(--text-dim)", fontSize: "0.76rem", padding: "4px 10px", cursor: "pointer" }}
            >
              {s}
            </button>
          ))}
        </div>
      )}

      {status === "error" && <p style={{ color: "var(--red)", marginTop: 10 }}>{errorMessage}</p>}
      <p style={{ fontSize: "0.7rem", color: "var(--text-dim)", marginTop: 8 }}>
        Réponses fondées uniquement sur les scores et statistiques calculés de ce match.
      </p>
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

      <MatchChat fixtureId={fixtureId} lang={lang} />

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

          <a
            href={reportPdfUrl(fixtureId, lang)}
            target="_blank"
            rel="noreferrer"
            style={{
              alignSelf: "flex-start",
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
              background: "var(--bg-panel-raised)",
              border: "1px solid var(--border)",
              color: "var(--text)",
              borderRadius: 8,
              padding: "8px 14px",
              fontSize: "0.85rem",
              textDecoration: "none",
            }}
          >
            <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.8">
              <path d="M12 3v12m0 0l-4-4m4 4l4-4" strokeLinecap="round" strokeLinejoin="round" />
              <path d="M4 17v2a2 2 0 002 2h12a2 2 0 002-2v-2" strokeLinecap="round" />
            </svg>
            Télécharger le rapport (PDF)
          </a>
        </div>
      )}
    </div>
  );
}
