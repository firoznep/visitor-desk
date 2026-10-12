import { useState } from "react";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";

export default function ChangePasswordModal({ forced, onClose }) {
  const { markPasswordChanged, logout } = useAuth();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    if (next !== confirm) return setError("New passwords don't match.");
    if (next.length < 12) return setError("New password must be at least 12 characters.");
    setBusy(true);
    setError("");
    try {
      await api.changePassword(current, next);
      markPasswordChanged();
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">
      <div className="w-full max-w-sm rounded-2xl bg-[var(--color-surface)] border border-[var(--color-line)] p-6">
        <h2 className="font-[var(--font-display)] text-lg font-bold mb-1">Change password</h2>
        <p className="text-sm text-[var(--color-muted)] mb-4">
          {forced ? "You're using a temporary password. Set a new one to continue." : "Update your password."}
        </p>
        <form onSubmit={handleSubmit} className="space-y-3">
          <Field label="Current password" type="password" value={current} onChange={setCurrent} autoFocus />
          <Field label="New password (12+ characters)" type="password" value={next} onChange={setNext} />
          <Field label="Confirm new password" type="password" value={confirm} onChange={setConfirm} />
          {error && <p role="alert" className="text-sm text-[var(--color-bad)]">{error}</p>}
          <div className="flex gap-2 pt-2">
            {!forced && (
              <button type="button" onClick={onClose} className="flex-1 rounded-lg border border-[var(--color-line)] py-2.5 text-sm font-semibold">
                Cancel
              </button>
            )}
            <button type="submit" disabled={busy} className="flex-1 rounded-lg bg-[var(--color-accent)] text-[var(--color-accent-ink)] py-2.5 text-sm font-semibold disabled:opacity-60">
              {busy ? "Saving…" : "Save password"}
            </button>
          </div>
          {forced && (
            <button type="button" onClick={logout} className="w-full text-xs text-[var(--color-muted)] pt-1 underline">
              Sign out instead
            </button>
          )}
        </form>
      </div>
    </div>
  );
}

function Field({ label, type = "text", value, onChange, autoFocus }) {
  return (
    <div>
      <label className="block text-xs font-semibold text-[var(--color-muted)] mb-1">{label}</label>
      <input
        type={type}
        value={value}
        autoFocus={autoFocus}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-lg border border-[var(--color-line)] bg-[var(--color-surface-sunken)] px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[var(--color-accent)]"
      />
    </div>
  );
}
