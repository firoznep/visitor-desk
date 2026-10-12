import { useState } from "react";
import { useAuth } from "../context/AuthContext";

export default function LoginForm() {
  const { login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    if (busy) return;
    setError("");
    setBusy(true);
    try {
      await login(username.trim(), password);
    } catch (err) {
      setError(err.message || "Couldn't sign in.");
      setPassword("");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="w-full max-w-sm rounded-2xl border border-[var(--color-line)] bg-[var(--color-surface)] p-7 shadow-sm">
        <div className="flex items-center gap-2.5 mb-1">
          <span className="text-2xl" aria-hidden="true">🪪</span>
          <h1 className="font-[var(--font-display)] text-xl font-bold tracking-tight">Visitor Desk</h1>
        </div>
        <p className="text-sm text-[var(--color-muted)] mb-6">Sign in to continue.</p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="username" className="block text-xs font-semibold text-[var(--color-muted)] mb-1.5">
              Username
            </label>
            <input
              id="username"
              autoComplete="username"
              autoFocus
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full rounded-lg border border-[var(--color-line)] bg-[var(--color-surface-sunken)] px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-[var(--color-accent)]"
            />
          </div>
          <div>
            <label htmlFor="password" className="block text-xs font-semibold text-[var(--color-muted)] mb-1.5">
              Password
            </label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-lg border border-[var(--color-line)] bg-[var(--color-surface-sunken)] px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-[var(--color-accent)]"
            />
          </div>

          {error && (
            <p role="alert" className="text-sm text-[var(--color-bad)]">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={busy}
            className="w-full rounded-lg bg-[var(--color-accent)] text-[var(--color-accent-ink)] font-semibold text-sm py-2.5 mt-2 disabled:opacity-60"
          >
            {busy ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
