import { StrictMode, Suspense, lazy } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import "./index.css";
import Layout from "./Layout.jsx";

// Chargement à la demande : les pages lourdes (Recharts pour les radars,
// html-to-image pour l'export de la carte MOTM) ne sont téléchargées qu'à la
// visite de la route concernée, ce qui allège le bundle initial.
const HomePage = lazy(() => import("./pages/HomePage.jsx"));
const MatchPage = lazy(() => import("./pages/MatchPage.jsx"));
const PlayerProfilePage = lazy(() => import("./pages/PlayerProfilePage.jsx"));
const TeamProfilePage = lazy(() => import("./pages/TeamProfilePage.jsx"));
const ComparePage = lazy(() => import("./pages/ComparePage.jsx"));
const StandingsPage = lazy(() => import("./pages/StandingsPage.jsx"));

function RouteFallback() {
  return <p style={{ color: "var(--text-dim)" }}>Chargement…</p>;
}

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <BrowserRouter>
      <Suspense fallback={<RouteFallback />}>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<HomePage />} />
            <Route path="match/:fixtureId" element={<MatchPage />} />
            <Route path="player/:playerId" element={<PlayerProfilePage />} />
            <Route path="team/:teamId" element={<TeamProfilePage />} />
            <Route path="compare" element={<ComparePage />} />
            <Route path="standings" element={<StandingsPage />} />
          </Route>
        </Routes>
      </Suspense>
    </BrowserRouter>
  </StrictMode>
);
