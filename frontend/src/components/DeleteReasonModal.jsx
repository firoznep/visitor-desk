import { useState } from "react";

export default function DeleteReasonModal({ visit, onConfirm, onCancel, busy }) {
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");

  function handleConfirm() {
    if (reason.trim().length < 3) return setError("Enter a short reason (at least 3 characters).");
    onConfirm(reason.trim());
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">
      <div className="w-full max-w-sm rounded-2xl bg-[var(--color-surface)] border border-[var(--color-line)] p-6">
        <h2 className="font-[var(--font-display)] text-lg font-bold mb-1">Delete visitor record?</h2>
        <p className="text-sm text-[var(--color-muted)] mb-4">
          {visit.badge_no} · {visit.full_name} will be hidden from normal views but kept for the audit log. It can be restored later.
        </p>
        <label className="block text-xs font-semibold text-[var(--color-muted)] mb-1">Reason</label>
        <input
          autoFocus
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="e.g. Entered in error"
          className="w-full rounded-lg border border-[var(--color-line)] bg-[var(--color-surface-sunken)] px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[var(--color-accent)]"
        />
        {error && <p className="text-xs text-[var(--color-bad)] mt-1">{error}</p>}
        <div className="flex gap-2 pt-4">
          <button onClick={onCancel} className="flex-1 rounded-lg border border-[var(--color-line)] py-2.5 text-sm font-semibold">
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            disabled={busy}
            className="flex-1 rounded-lg bg-[var(--color-bad)] text-white py-2.5 text-sm font-semibold disabled:opacity-60"
          >
            {busy ? "Deleting…" : "Delete"}
          </button>
        </div>
      </div>
    </div>
  );
}
