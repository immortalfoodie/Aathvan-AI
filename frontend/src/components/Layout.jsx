/**
 * Layout component — persistent nav bar + content outlet.
 */
import { Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

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
            <div className="header-actions">
              <span className="user-greeting">Hey, {user.name.split(" ")[0]}</span>
              <button className="btn btn-ghost" onClick={handleLogout} id="logout-btn">
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
