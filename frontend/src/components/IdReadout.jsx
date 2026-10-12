export default function IdReadout({ scan }) {
  if (!scan) {
    return (
      <div className="mt-4 pt-4 border-t border-[var(--color-line)] text-sm text-[var(--color-muted)]">
        Scan an ID or enter the holder's details manually.
      </div>
    );
  }

  let banner = scan.manually_entered
    ? { text: "Details entered manually. Verify them against the physical ID.", tone: "ok" }
    : { text: "ID read successfully.", tone: "ok" };
  if (scan.id_expired) banner = { text: "This ID has expired. You can still save the visit.", tone: "warn" };
  else if (scan.already_checked_in) banner = { text: "This visitor is already checked in today.", tone: "warn" };

  const toneClass = { ok: "text-[var(--color-ok)]", warn: "text-[var(--color-warn)]" }[banner.tone];

  return (
    <div className="mt-4 pt-4 border-t border-[var(--color-line)]">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-bold">{scan.manually_entered ? "Entered manually" : "Read from ID"}</h3>
        <span className="text-xs text-[var(--color-muted)]">Locked</span>
      </div>
      <p className={`text-xs font-semibold mb-3 ${toneClass}`}>{banner.text}</p>
      <dl className="grid grid-cols-2 gap-x-3 gap-y-2.5 text-sm">
        <Field label="Full name" value={scan.full_name} span2 />
        <Field label="QID number" value={`•••• ${scan.id_last4}`} mono />
        <Field label="Date of birth" value={scan.date_of_birth} mono />
        <Field label="Nationality" value={scan.nationality} />
        <Field label="Gender" value={scan.gender} />
        <Field
          label="ID expiry"
          value={scan.id_expiry}
          mono
          valueClass={scan.id_expired ? "text-[var(--color-warn)]" : undefined}
        />
      </dl>
    </div>
  );
}

function Field({ label, value, span2, mono, valueClass }) {
  return (
    <div className={span2 ? "col-span-2" : ""}>
      <dt className="text-xs text-[var(--color-muted)]">{label}</dt>
      <dd className={`font-medium ${mono ? "font-mono" : ""} ${valueClass || ""}`}>{value}</dd>
    </div>
  );
}
