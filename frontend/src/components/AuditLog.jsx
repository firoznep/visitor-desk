export default function AuditLog({ entries }) {
  return (
    <section className="rounded-2xl border border-[var(--color-line)] bg-[var(--color-surface)] p-5">
      <h2 className="font-[var(--font-display)] font-bold">Audit log</h2>
      <p className="text-sm text-[var(--color-muted)] mb-3">
        Every sign-in, save, check-out, delete and restore. Deleted scans are hidden, never erased.
      </p>
      <div className="overflow-x-auto max-h-72 overflow-y-auto">
        <table className="w-full min-w-[560px] text-sm">
          <thead>
            <tr className="text-left text-xs font-semibold text-[var(--color-muted)]">
              <th className="py-2 pr-3">Time</th>
              <th className="py-2 pr-3">User</th>
              <th className="py-2 pr-3">Action</th>
              <th className="py-2 pr-3">Details</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((a, i) => (
              <tr key={i} className="border-t border-[var(--color-line)]">
                <td className="py-2 pr-3 whitespace-nowrap">{new Date(a.at).toLocaleString([], { dateStyle: "short", timeStyle: "short" })}</td>
                <td className="py-2 pr-3">{a.username || "–"}</td>
                <td className="py-2 pr-3">{a.action}</td>
                <td className="py-2 pr-3 text-[var(--color-muted)]">{a.detail || a.target || ""}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
