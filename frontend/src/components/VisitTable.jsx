export default function VisitTable({ items, insideCount, total, showDeleted, onToggleShowDeleted,
                                      search, onSearchChange, onCheckOut, onDelete, onRestore, isAdmin }) {
  return (
    <section className="rounded-2xl border border-[var(--color-line)] bg-[var(--color-surface)] p-5">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
        <div>
          <h2 className="font-[var(--font-display)] font-bold">{isAdmin ? "All visitors" : "Today's visitors"}</h2>
          <p className="text-sm text-[var(--color-muted)]">
            {insideCount} in the building · {total}{isAdmin ? " records in total" : " total today"}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          {isAdmin && (
            <label className="text-sm flex items-center gap-2">
              <input type="checkbox" checked={showDeleted} onChange={(e) => onToggleShowDeleted(e.target.checked)} />
              Show deleted
            </label>
          )}
          <input
            value={search}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search name, company, host, badge"
            aria-label="Search visitors"
            className="rounded-lg border border-[var(--color-line)] bg-[var(--color-surface-sunken)] px-3 py-1.5 text-sm outline-none focus:ring-2 focus:ring-[var(--color-accent)] max-w-[260px]"
          />
        </div>
      </div>

      <div className="max-h-[38rem] min-h-[30rem] overflow-auto">
        <table className="w-full min-w-[1120px] text-sm">
          <thead>
            <tr className="text-left text-xs font-semibold text-[var(--color-muted)]">
              <th className="sticky top-0 bg-[var(--color-surface)] py-2 pr-3">Badge</th>
              {isAdmin && <th className="sticky top-0 bg-[var(--color-surface)] py-2 pr-3">Date</th>}
              <th className="sticky top-0 bg-[var(--color-surface)] py-2 pr-3">Visitor</th>
              <th className="sticky top-0 bg-[var(--color-surface)] py-2 pr-3">Company</th>
              <th className="sticky top-0 bg-[var(--color-surface)] py-2 pr-3">ID</th>
              <th className="sticky top-0 bg-[var(--color-surface)] py-2 pr-3">ID status</th>
              <th className="sticky top-0 bg-[var(--color-surface)] py-2 pr-3">Floor</th>
              <th className="sticky top-0 bg-[var(--color-surface)] py-2 pr-3">Meeting</th>
              <th className="sticky top-0 bg-[var(--color-surface)] py-2 pr-3">Purpose</th>
              <th className="sticky top-0 bg-[var(--color-surface)] py-2 pr-3">In</th>
              <th className="sticky top-0 bg-[var(--color-surface)] py-2 pr-3">Visit</th>
              {isAdmin && <th className="sticky top-0 bg-[var(--color-surface)] py-2 pr-3">Admin</th>}
            </tr>
          </thead>
          <tbody>
            {items.map((v) => (
              <Row key={v.id} v={v} isAdmin={isAdmin} onCheckOut={onCheckOut} onDelete={onDelete} onRestore={onRestore} />
            ))}
          </tbody>
        </table>
      </div>
      {items.length === 0 && (
        <p className="text-sm text-center py-8 text-[var(--color-muted)]">
          No matching visitors. Scan an ID to add the first one.
        </p>
      )}
    </section>
  );
}

function Row({ v, isAdmin, onCheckOut, onDelete, onRestore }) {
  return (
    <tr className={`border-t border-[var(--color-line)] ${v.is_deleted ? "opacity-55" : ""}`}>
      <td className="py-2.5 pr-3 font-semibold badge-code">
        {v.badge_no}
        {v.is_deleted && <Tag tone="bad" className="ml-1.5">Deleted</Tag>}
      </td>
      {isAdmin && <td className="py-2.5 pr-3">{v.visit_date}</td>}
      <td className="py-2.5 pr-3">{v.full_name}</td>
      <td className="py-2.5 pr-3">{v.company || "–"}</td>
      <td className="py-2.5 pr-3 badge-code">•••• {v.id_last4}</td>
      <td className="py-2.5 pr-3">
        <Tag tone={v.id_expired ? "warn" : "ok"}>{v.id_expired ? "Expired" : "Valid"}</Tag>
      </td>
      <td className="py-2.5 pr-3">{v.floor}</td>
      <td className="py-2.5 pr-3">{v.host_name}</td>
      <td className="py-2.5 pr-3">{v.purpose}</td>
      <td className="py-2.5 pr-3">{new Date(v.checked_in_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</td>
      <td className="py-2.5 pr-3">
        {v.checked_out_at ? (
          <span className="text-[var(--color-muted)]">
            Out {new Date(v.checked_out_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
          </span>
        ) : v.is_deleted ? (
          "–"
        ) : (
          <SmallButton onClick={() => onCheckOut(v.id)}>Check out</SmallButton>
        )}
      </td>
      {isAdmin && (
        <td className="py-2.5 pr-3">
          {v.is_deleted ? (
            <SmallButton onClick={() => onRestore(v.id)}>Restore</SmallButton>
          ) : (
            <SmallButton danger onClick={() => onDelete(v)}>Delete</SmallButton>
          )}
        </td>
      )}
    </tr>
  );
}

function Tag({ tone, children, className = "" }) {
  const color = { ok: "var(--color-ok)", warn: "var(--color-warn)", bad: "var(--color-bad)" }[tone];
  return (
    <span className={`text-xs font-bold px-1.5 py-0.5 rounded border ${className}`} style={{ color, borderColor: color }}>
      {children}
    </span>
  );
}

function SmallButton({ onClick, danger, children }) {
  return (
    <button
      onClick={onClick}
      className={`rounded-md border border-[var(--color-line)] px-2.5 py-1 text-xs font-semibold ${danger ? "text-[var(--color-bad)]" : ""}`}
    >
      {children}
    </button>
  );
}
