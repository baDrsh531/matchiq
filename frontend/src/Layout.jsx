import { AnimatePresence, motion } from "framer-motion";
import { NavLink, Outlet, useLocation } from "react-router-dom";

const NAV_ITEMS = [
  { to: "/", label: "Accueil", icon: "🏠", end: true },
  { to: "/standings", label: "Classement", icon: "🏆" },
  { to: "/compare", label: "Comparateur", icon: "⚖️" },
];

function NavItem({ to, label, icon, end }) {
  return (
    <NavLink
      to={to}
      end={end}
      style={({ isActive }) => ({
        display: "flex",
        alignItems: "center",
        gap: 10,
        padding: "10px 12px",
        borderRadius: 8,
        marginBottom: 4,
        color: isActive ? "var(--gold)" : "var(--text-dim)",
        background: isActive ? "var(--bg-panel-raised)" : "transparent",
        textDecoration: "none",
        fontSize: "0.9rem",
        transition: "background 0.15s, color 0.15s",
      })}
    >
      <span style={{ width: 18, textAlign: "center" }}>{icon}</span>
      {label}
    </NavLink>
  );
}

function AnimatedOutlet() {
  const location = useLocation();
  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={location.pathname}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -10 }}
        transition={{ duration: 0.22, ease: "easeOut" }}
      >
        <Outlet />
      </motion.div>
    </AnimatePresence>
  );
}

export default function Layout() {
  return (
    <div style={{ display: "flex", alignItems: "flex-start" }}>
      <nav
        style={{
          width: 200,
          flexShrink: 0,
          position: "sticky",
          top: 0,
          height: "100vh",
          borderRight: "1px solid var(--border)",
          padding: "24px 12px",
          boxSizing: "border-box",
        }}
      >
        <div
          style={{
            fontFamily: "var(--font-display)",
            fontSize: "1.25rem",
            padding: "0 12px 24px",
          }}
        >
          Match<span style={{ color: "var(--gold)" }}>IQ</span>
        </div>
        {NAV_ITEMS.map((item) => (
          <NavItem key={item.to} {...item} />
        ))}
      </nav>
      <main style={{ flex: 1, minWidth: 0 }}>
        <div className="page-content">
          <AnimatedOutlet />
        </div>
      </main>
    </div>
  );
}
