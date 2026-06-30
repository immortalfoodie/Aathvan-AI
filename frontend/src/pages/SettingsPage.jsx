import { useState } from "react";
import { useAuth } from "../contexts/AuthContext";
import client from "../api/client";

export default function SettingsPage() {
  const { user } = useAuth();

  const [loading, setLoading] = useState(false);
  const [notifMessage, setNotifMessage] = useState("");
  const [errorMessage, setErrorMessage] = useState("");

  const handleConnectGoogle = async () => {
    setLoading(true);
    setErrorMessage("");
    try {
      // Pass current JWT to state so callback knows who to link it to
      const token = localStorage.getItem("token") || "";
      const res = await client.get(`/auth/google/login?token=${token}`);
      if (res.data && res.data.auth_url) {
        window.location.href = res.data.auth_url;
      } else {
        setErrorMessage("OAuth URL generation failed.");
      }
    } catch (e) {
      setErrorMessage("Error connecting to Google API.");
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateNotification = async () => {
    setLoading(true);
    setNotifMessage("");
    setErrorMessage("");
    try {
      const res = await client.post("/notifications/generate-now");
      setNotifMessage(`Success: "${res.data.message}"`);
    } catch (e) {
      const errDetail = e.response?.data?.detail || "Make sure you have at least one approved task plan!";
      setErrorMessage(`Failed: ${errDetail}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto p-6 settings-page">
      <h1 className="text-3xl font-extrabold mb-8 text-[var(--color-text)]">Settings</h1>

      <div className="flex flex-col gap-6">
        {/* Google Classroom Connection Panel */}
        <section className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-[var(--radius-lg)] p-6 shadow-md">
          <h2 className="text-xl font-bold mb-3 flex items-center gap-2">
            <span>🏫</span> Google Classroom & Calendar
          </h2>
          <p className="text-[var(--color-text-secondary)] text-sm mb-6 leading-relaxed">
            Connect your Google account to automatically import Classroom coursework assignments 
            and sync your AI-generated task step schedules into Google Calendar.
          </p>

          {user?.google_connected ? (
            <div className="flex items-center justify-between p-4 bg-emerald-950/20 border border-emerald-800/40 rounded-[var(--radius-md)]">
              <div className="flex items-center gap-3">
                <span className="text-emerald-400 text-xl">✓</span>
                <div>
                  <div className="font-bold text-emerald-300 text-sm">Account Linked</div>
                  <div className="text-xs text-[var(--color-text-secondary)]">Classroom & Calendar integrations active.</div>
                </div>
              </div>
              <span className="text-xs font-semibold px-2 py-1 bg-emerald-900/40 text-emerald-400 rounded-full">Connected</span>
            </div>
          ) : (
            <button
              onClick={handleConnectGoogle}
              disabled={loading}
              className="google-connect-btn w-full flex items-center justify-center gap-3 font-semibold text-sm bg-white text-black hover:bg-neutral-100 disabled:opacity-50 py-3 rounded-[var(--radius-md)] border transition-all cursor-pointer"
            >
              <svg className="w-5 h-5" viewBox="0 0 24 24">
                <path
                  fill="#EA4335"
                  d="M23.49 12.275c0-.825-.075-1.62-.21-2.385H12v4.515h6.44c-.28 1.485-1.12 2.745-2.385 3.595l3.705 2.87c2.165-2 3.73-4.945 3.73-8.595z"
                />
                <path
                  fill="#FBBC05"
                  d="M12 24c3.24 0 5.955-1.075 7.94-2.915l-3.705-2.87c-1.025.685-2.335 1.1-4.235 1.1-3.255 0-6.015-2.2-7.005-5.165L1.22 17.07C3.195 21.01 7.27 24 12 24z"
                />
                <path
                  fill="#34A853"
                  d="M4.995 14.16C4.74 13.385 4.6 12.565 4.6 11.71c0-.855.14-1.675.395-2.45L1.22 6.29C.44 7.845 0 9.585 0 11.71c0 2.125.44 3.865 1.22 5.42l3.775-2.97z"
                />
                <path
                  fill="#4285F4"
                  d="M12 4.77c1.765 0 3.345.61 4.59 1.8l3.43-3.43C17.945 1.14 15.225 0 12 0 7.27 0 3.195 2.99 1.22 6.29l3.775 2.97c.99-2.965 3.75-5.165 7.005-5.165z"
                />
              </svg>
              <span>Connect Google Account</span>
            </button>
          )}
        </section>

        {/* Demo Notifications Controls */}
        <section className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-[var(--radius-lg)] p-6 shadow-md">
          <h2 className="text-xl font-bold mb-3 flex items-center gap-2">
            <span>📢</span> Demo & Presentation Controls
          </h2>
          <p className="text-[var(--color-text-secondary)] text-sm mb-6 leading-relaxed">
            Trigger a daily notification run immediately. Note: Requires at least one active, approved task step schedule.
          </p>

          <button
            onClick={handleGenerateNotification}
            disabled={loading}
            className="btn btn-secondary w-full"
          >
            {loading ? "Generating..." : "Generate Priority Notification Now"}
          </button>

          {notifMessage && (
            <div className="mt-4 p-3 bg-blue-950/20 border border-blue-800/40 text-blue-300 rounded-[var(--radius-md)] text-xs font-semibold leading-relaxed">
              {notifMessage}
            </div>
          )}

          {errorMessage && (
            <div className="mt-4 p-3 bg-red-950/20 border border-red-800/40 text-red-300 rounded-[var(--radius-md)] text-xs font-semibold leading-relaxed">
              {errorMessage}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
