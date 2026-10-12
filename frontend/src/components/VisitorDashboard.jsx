const metrics = [
  { key: "today_total", label: "Visitors today", detail: "Checked in today" },
  { key: "today_inside", label: "Currently inside", detail: "Not checked out today" },
  { key: "this_week_total", label: "This week", detail: "Since Monday" },
  { key: "this_month_total", label: "This month", detail: "Month to date" },
  { key: "last_month_total", label: "Last month", detail: "Full previous month" },
];

export default function VisitorDashboard({ stats, error }) {
  return (
    <section aria-label="Visitor dashboard" className="lg:col-span-5">
      {error && <p role="alert" className="mb-3 text-sm text-[var(--color-bad)]">{error}</p>}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        {metrics.map((metric) => (
          <article key={metric.key} className="rounded-xl border border-[var(--color-line)] bg-[var(--color-surface)] p-4">
            <p className="text-sm text-[var(--color-muted)]">{metric.label}</p>
            <p className="mt-2 font-[var(--font-display)] text-3xl font-bold">
              {stats ? stats[metric.key].toLocaleString() : "–"}
            </p>
            <p className="mt-1 text-xs text-[var(--color-muted)]">{metric.detail}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
