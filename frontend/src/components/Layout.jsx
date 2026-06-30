/**
 * Layout component — persistent nav bar + content outlet.
 */
import { Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import NotificationBell from "./NotificationBell";

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className="app-layout">
      <header className="app-header">
        <div className="header-inner">
          <button className="logo-link" onClick={() => navigate("/")}>
            <span className="logo-icon">⚡</span>
            <span className="logo-text">LifeSaver</span>
          </button>
          {user && (
            <div className="header-actions flex items-center gap-4">
              {/* Classroom Import Link if Google connected */}
              {user.google_connected && (
                <button className="btn btn-ghost text-sm font-semibold flex items-center gap-1.5" onClick={() => navigate("/classroom")}>
                  <span>🏫</span> Import
                </button>
              )}
              
              <button className="btn btn-ghost text-sm font-semibold flex items-center gap-1.5" onClick={() => navigate("/settings")}>
                <span>⚙️</span> Settings
              </button>

              <NotificationBell />

              <span className="user-greeting border-l border-[var(--color-border)] pl-4 text-xs text-[var(--color-text-secondary)] font-semibold hidden sm:inline">
                Hey, {user.name.split(" ")[0]}
              </span>

              <button className="btn btn-ghost text-sm font-semibold text-neutral-400 hover:text-white" onClick={handleLogout} id="logout-btn">
                Log out
              </button>
            </div>
          )}
        </div>
      </header>
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}
