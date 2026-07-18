import { useState } from "react";
import { useNavigate } from "react-router-dom";
import RecentMatches from "../components/RecentMatches";
import SearchBar from "../components/SearchBar";

export default function HomePage() {
  const [fixtureIdInput, setFixtureIdInput] = useState("");
  const navigate = useNavigate();

  const handleSubmit = (e) => {
    e.preventDefault();
    const id = parseInt(fixtureIdInput, 10);
    if (!Number.isNaN(id)) navigate(`/match/${id}`);
  };

  return (
    <>
      <header style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: "1.9rem" }}>
          Match<span style={{ color: "var(--gold)" }}>IQ</span>
        </h1>
        <p style={{ color: "var(--text-dim)", marginTop: 4 }}>
          Analyse de match par ML + LLM
        </p>

        <div style={{ marginTop: 16 }}>
          <SearchBar />
        </div>

        <form onSubmit={handleSubmit} style={{ display: "flex", gap: 8, marginTop: 14 }}>
          <input
            value={fixtureIdInput}
            onChange={(e) => setFixtureIdInput(e.target.value)}
            placeholder="…ou ID de fixture directement (ex: 1035038)"
            style={{
              flex: 1,
              maxWidth: 320,
              padding: "10px 12px",
              background: "var(--bg-panel)",
              border: "1px solid var(--border)",
              borderRadius: 8,
              color: "var(--text)",
            }}
          />
          <button
            type="submit"
            style={{
              padding: "10px 18px",
              background: "var(--gold)",
              border: "none",
              borderRadius: 8,
              color: "#141414",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            Charger le match
          </button>
        </form>
      </header>

      <RecentMatches onSelect={(id) => navigate(`/match/${id}`)} />
    </>
  );
}
