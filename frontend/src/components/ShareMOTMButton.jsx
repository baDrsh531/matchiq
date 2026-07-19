import { useRef, useState } from "react";
import { toPng } from "html-to-image";
import MOTMShareCard from "./MOTMShareCard";

export default function ShareMOTMButton({ player, match }) {
  const cardRef = useRef(null);
  const [status, setStatus] = useState("idle"); // idle | loading | error

  if (!player) return null;

  const handleDownload = async () => {
    if (!cardRef.current) return;
    setStatus("loading");
    try {
      // cacheBust ajoute un paramètre `?<timestamp>` aux URLs d'images pour
      // forcer un rechargement — mais le CDN d'API-Football n'envoie
      // l'en-tête CORS que sur l'URL exacte (sans query string), donc
      // cacheBust casse le chargement des photos/logos. On le laisse
      // désactivé (les images sont déjà à jour à chaque montage du composant).
      const dataUrl = await toPng(cardRef.current, { pixelRatio: 2 });
      const link = document.createElement("a");
      const slug = player.name.toLowerCase().replace(/[^a-z0-9]+/g, "-");
      link.download = `matchiq-motm-${slug}.png`;
      link.href = dataUrl;
      link.click();
      setStatus("idle");
    } catch {
      setStatus("error");
    }
  };

  return (
    <>
      <button
        onClick={handleDownload}
        disabled={status === "loading"}
        style={{
          background: "var(--bg-panel-raised)",
          border: "1px solid var(--gold)",
          color: "var(--gold)",
          borderRadius: 8,
          padding: "8px 14px",
          fontSize: "0.82rem",
          fontWeight: 600,
          cursor: status === "loading" ? "wait" : "pointer",
        }}
      >
        {status === "loading" ? "Génération…" : "📸 Télécharger la carte MOTM"}
      </button>
      {status === "error" && (
        <p style={{ color: "var(--red)", fontSize: "0.8rem", marginTop: 6 }}>
          Échec de la génération de l'image (photo/logo bloqué par le navigateur ?).
        </p>
      )}

      {/* Rendue hors-écran : sert uniquement de source à html-to-image */}
      <div style={{ position: "fixed", top: -99999, left: -99999, pointerEvents: "none" }}>
        <MOTMShareCard ref={cardRef} player={player} match={match} />
      </div>
    </>
  );
}
