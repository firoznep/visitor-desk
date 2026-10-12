import { useAuth } from "../context/AuthContext";

export default function TopBar({ onChangePassword, activeView, onViewChange }) {
  const { user, logout } = useAuth();

  return (
    <header className="max-w-6xl mx-auto px-4 pt-6 pb-4 flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 className="font-[var(--font-display)] text-2xl font-bold tracking-tight">Visitor Desk</h1>
        <p className="text-sm text-[var(--color-muted)]">Scan an ID, confirm the visit, print the pass.</p>
      </div>
      <div className="flex items-center gap-2 text-sm">
        {user.role === "admin" && (
          <>
            <button
              onClick={() => onViewChange("desk")}
              aria-current={activeView === "desk" ? "page" : undefined}
              className={`rounded-md border px-3 py-1.5 text-xs font-semibold ${activeView === "desk" ? "border-[var(--color-accent)] text-[var(--color-accent)]" : "border-[var(--color-line)] hover:border-[var(--color-accent)]"}`}
            >
              Desk
            </button>
            <button
              onClick={() => onViewChange("users")}
              aria-current={activeView === "users" ? "page" : undefined}
              className={`rounded-md border px-3 py-1.5 text-xs font-semibold ${activeView === "users" ? "border-[var(--color-accent)] text-[var(--color-accent)]" : "border-[var(--color-line)] hover:border-[var(--color-accent)]"}`}
            >
              Manage users
            </button>
          </>
        )}
        <span className="px-2.5 py-1.5 rounded-md text-xs font-semibold bg-[var(--color-surface-sunken)] border border-[var(--color-line)]">
          {user.role === "admin" ? "Admin" : "Receptionist"} · {user.username}
        </span>
        <button
          onClick={onChangePassword}
          className="rounded-md border border-[var(--color-line)] px-3 py-1.5 text-xs font-semibold hover:border-[var(--color-accent)]"
        >
          Change password
        </button>
        <button
          onClick={logout}
          className="rounded-md border border-[var(--color-line)] px-3 py-1.5 text-xs font-semibold hover:border-[var(--color-accent)]"
        >
          Log out
        </button>
      </div>
    </header>
  );
}
