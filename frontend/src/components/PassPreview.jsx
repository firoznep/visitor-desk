export default function PassPreview({ scan }) {
  return (
    <div className="rounded-2xl p-5 flex flex-wrap justify-between gap-4 text-[var(--color-ink)]"
         style={{ background: "linear-gradient(160deg, var(--color-accent-soft), var(--color-surface))", border: "1px solid var(--color-line)" }}>
      <div>
        <p className="text-xs opacity-80">Visitor pass</p>
        <p className="font-[var(--font-display)] text-xl font-bold mt-1">
          {scan ? scan.full_name : "No visitor scanned"}
        </p>
        <p className="text-sm opacity-90 mt-1">
          {scan
            ? [scan.already_checked_in && "Already checked in", scan.id_expired && "ID expired"].filter(Boolean).join(" · ") || "Ready to check in"
            : "Scan an ID to start"}
        </p>
      </div>
      <div className="text-right">
        <p className="text-xs opacity-80">QID</p>
        <p className="badge-code text-lg font-semibold">{scan ? `•••• ${scan.id_last4}` : "–"}</p>
      </div>
    </div>
  );
}
