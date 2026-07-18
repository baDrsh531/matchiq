import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import "./index.css";
import Layout from "./Layout.jsx";
import HomePage from "./pages/HomePage.jsx";
import MatchPage from "./pages/MatchPage.jsx";
import PlayerProfilePage from "./pages/PlayerProfilePage.jsx";
import TeamProfilePage from "./pages/TeamProfilePage.jsx";
import ComparePage from "./pages/ComparePage.jsx";
import StandingsPage from "./pages/StandingsPage.jsx";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <BrowserRouter>
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
    </BrowserRouter>
  </StrictMode>
);
