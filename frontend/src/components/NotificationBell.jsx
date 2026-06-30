import { useEffect, useState, useRef } from "react";
import client from "../api/client";

export default function NotificationBell() {

  const [notifications, setNotifications] = useState([]);
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);

  const fetchNotifications = async () => {
    try {
      const res = await client.get("/notifications");
      setNotifications(res.data);
    } catch (e) {
      // Silently ignore poll errors
    }
  };

  useEffect(() => {
    fetchNotifications();

    // Poll every 60 seconds
    const interval = setInterval(fetchNotifications, 60000);
    return () => clearInterval(interval);
  }, []);

  // Close dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleMarkAsRead = async (id) => {
    try {
      const res = await client.patch(`/notifications/${id}`);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? res.data : n))
      );
    } catch (e) {
      // Ignore
    }
  };

  const unreadCount = notifications.filter((n) => !n.read).length;

  const formatTimeElapsed = (dateStr) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    if (diffMins < 1) return "Just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    return date.toLocaleDateString();
  };

  return (
    <div className="notification-bell-container" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="bell-trigger-button relative p-2 text-neutral-400 hover:text-white bg-none border-none cursor-pointer outline-none transition-colors"
      >
        <span className="text-xl">🔔</span>
        {unreadCount > 0 && (
          <span className="absolute top-0 right-0 flex h-4 w-4 items-center justify-center rounded-full bg-red-600 text-[10px] font-extrabold text-white">
            {unreadCount}
          </span>
        )}
      </button>

      {isOpen && (
        <div className="notification-dropdown absolute right-0 mt-2 w-80 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-[var(--radius-lg)] shadow-xl z-50 overflow-hidden">
          <div className="dropdown-header p-4 border-b border-[var(--color-border)] flex items-center justify-between">
            <span className="font-bold text-sm text-[var(--color-text)]">Notifications</span>
            {unreadCount > 0 && (
              <span className="text-xs px-2 py-0.5 bg-red-950/20 text-red-400 rounded-full font-semibold">
                {unreadCount} New
              </span>
            )}
          </div>

          <div className="dropdown-list max-h-64 overflow-y-auto divide-y divide-[var(--color-border)]">
            {notifications.length === 0 ? (
              <div className="text-center py-8 text-xs text-[var(--color-text-secondary)]">
                No notifications yet.
              </div>
            ) : (
              notifications.map((notif) => (
                <div
                  key={notif.id}
                  onClick={() => !notif.read && handleMarkAsRead(notif.id)}
                  className={`notification-item p-4 flex gap-3 cursor-pointer transition-colors ${
                    !notif.read ? "bg-[var(--color-bg-secondary)]/40 hover:bg-[var(--color-bg-secondary)]/70" : "hover:bg-[var(--color-bg-secondary)]/20"
                  }`}
                >
                  {/* Unread indicator */}
                  {!notif.read && (
                    <span className="h-2 w-2 rounded-full bg-blue-500 mt-1.5 flex-shrink-0" />
                  )}

                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-[var(--color-text)] font-medium leading-relaxed">
                      {notif.message}
                    </p>
                    <span className="text-[10px] text-[var(--color-text-muted)] font-semibold mt-1 block">
                      {formatTimeElapsed(notif.created_at)}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
