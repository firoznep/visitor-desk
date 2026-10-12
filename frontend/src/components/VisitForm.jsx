import { useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import { api, ApiError } from "../lib/api";

const FLOORS = ["Ground", ...Array.from({ length: 99 }, (_, index) => String(index + 1))];
const PURPOSES = ["Meeting", "Interview", "Delivery", "Maintenance", "Contractor work", "Personal visit", "Other"];

const EMPTY = { floor: "", purpose: "", host_name: "", department: "", phone: "", company: "", vehicle_plate: "", notes: "" };

export default function VisitForm({ scan, onSaved, onClearScan }) {
  const { user } = useAuth();
  const [form, setForm] = useState(EMPTY);
  const [departments, setDepartments] = useState([]);
  const [companies, setCompanies] = useState([]);
  const [addingDepartment, setAddingDepartment] = useState(false);
  const [departmentName, setDepartmentName] = useState("");
  const [addingCompany, setAddingCompany] = useState(false);
  const [companyName, setCompanyName] = useState("");
  const [fieldErrors, setFieldErrors] = useState({});
  const [message, setMessage] = useState(null); // { text, ok }
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let mounted = true;
    api.listDepartments()
      .then((items) => {
        if (mounted) setDepartments(items);
      })
      .catch((err) => {
        if (mounted) setMessage({ text: `Could not load departments: ${err.message}`, ok: false });
      });
    api.listCompanies()
      .then((items) => {
        if (mounted) setCompanies(items);
      })
      .catch((err) => {
        if (mounted) setMessage({ text: `Could not load companies: ${err.message}`, ok: false });
      });
    return () => {
      mounted = false;
    };
  }, []);

  function set(key, value) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  function validate() {
    const errs = {};
    if (!form.floor) errs.floor = "Choose a floor.";
    if (!form.purpose) errs.purpose = "Choose a purpose.";
    if (form.host_name.trim() && form.host_name.trim().length < 2) errs.host_name = "Enter at least 2 characters or leave blank.";
    if (form.phone.trim() && !/^\+?[0-9 ]{7,15}$/.test(form.phone.trim())) errs.phone = "Enter a valid phone number or leave blank.";
    setFieldErrors(errs);
    return Object.keys(errs).length === 0;
  }

  function reset() {
    setForm(EMPTY);
    setFieldErrors({});
    onClearScan();
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!scan) return setMessage({ text: "Scan an ID before saving.", ok: false });
    if (scan.already_checked_in) return setMessage({ text: "This visitor is already checked in today.", ok: false });
    if (!validate()) return setMessage({ text: "Fix the highlighted fields.", ok: false });

    setBusy(true);
    setMessage(null);
    try {
      const visit = await api.createVisit({ scan_token: scan.scan_token, ...form });
      onSaved(visit);
      reset();
      setMessage({ text: `Saved. Badge ${visit.badge_no} issued.`, ok: true });
    } catch (err) {
      if (err instanceof ApiError && err.fieldErrors) {
        const errs = {};
        for (const fe of err.fieldErrors) {
          const key = fe.loc?.[fe.loc.length - 1];
          if (key) errs[key] = fe.msg;
        }
        setFieldErrors(errs);
      }
      setMessage({ text: err.message, ok: false });
    } finally {
      setBusy(false);
    }
  }

  async function handleAddDepartment() {
    const name = departmentName.trim();
    if (name.length < 2) {
      setMessage({ text: "Department name must contain at least 2 characters.", ok: false });
      return;
    }
    setBusy(true);
    setMessage(null);
    try {
      const added = await api.createDepartment(name);
      setDepartments((current) => [...current, added.name].sort((a, b) => a.localeCompare(b)));
      set("department", added.name);
      setDepartmentName("");
      setAddingDepartment(false);
      setMessage({ text: `Added department: ${added.name}.`, ok: true });
    } catch (err) {
      setMessage({ text: err.message, ok: false });
    } finally {
      setBusy(false);
    }
  }

  async function handleAddCompany() {
    const name = companyName.trim();
    if (name.length < 2) {
      setMessage({ text: "Company name must contain at least 2 characters.", ok: false });
      return;
    }
    setBusy(true);
    setMessage(null);
    try {
      const added = await api.createCompany(name);
      setCompanies((current) => [...current, added.name].sort((a, b) => a.localeCompare(b)));
      set("company", added.name);
      setCompanyName("");
      setAddingCompany(false);
      setMessage({ text: `Added company: ${added.name}.`, ok: true });
    } catch (err) {
      setMessage({ text: err.message, ok: false });
    } finally {
      setBusy(false);
    }
  }

  const disabled = !scan || scan.already_checked_in;

  return (
    <div className="rounded-2xl border border-[var(--color-line)] bg-[var(--color-surface)] p-5">
      <h2 className="font-[var(--font-display)] font-bold mb-3">2. Visit details</h2>
      <form onSubmit={handleSubmit}>
        <div className="grid sm:grid-cols-2 gap-3">
          <Select label="Floor" value={form.floor} onChange={(v) => set("floor", v)} options={FLOORS} placeholder="Select floor" error={fieldErrors.floor} disabled={disabled} />
          <Select label="Visiting purpose" value={form.purpose} onChange={(v) => set("purpose", v)} options={PURPOSES} placeholder="Select purpose" error={fieldErrors.purpose} disabled={disabled} />
          <Input label="Person to meet (optional)" value={form.host_name} onChange={(v) => set("host_name", v)} placeholder="e.g. Sara Haddad" maxLength={80} error={fieldErrors.host_name} disabled={disabled} />
          <div>
            <div className="mb-1 flex items-center justify-between">
              <label htmlFor="visit-department" className="block text-xs font-semibold text-[var(--color-muted)]">Department (optional)</label>
              {user.role === "admin" && (
                <button
                  type="button"
                  onClick={() => setAddingDepartment((open) => !open)}
                  disabled={busy}
                  aria-label="Add department"
                  title="Add department"
                  className="rounded border border-[var(--color-line)] px-2 text-sm font-bold disabled:opacity-50"
                >
                  +
                </button>
              )}
            </div>
            <select
              id="visit-department"
              value={form.department}
              onChange={(e) => set("department", e.target.value)}
              disabled={disabled}
              className="w-full rounded-lg border border-[var(--color-line)] bg-[var(--color-surface-sunken)] px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[var(--color-accent)] disabled:opacity-60"
            >
              <option value="">No department</option>
              {departments.map((department) => <option key={department} value={department}>{department}</option>)}
            </select>
            {addingDepartment && (
              <div className="mt-2 flex gap-2">
                <input
                  value={departmentName}
                  onChange={(e) => setDepartmentName(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      handleAddDepartment();
                    }
                  }}
                  required
                  minLength={2}
                  maxLength={60}
                  aria-label="New department name"
                  placeholder="New department"
                  className="min-w-0 flex-1 rounded-lg border border-[var(--color-line)] bg-[var(--color-surface-sunken)] px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[var(--color-accent)]"
                />
                <button
                  type="button"
                  onClick={handleAddDepartment}
                  disabled={busy}
                  className="rounded-lg border border-[var(--color-line)] px-3 py-2 text-xs font-semibold disabled:opacity-50"
                >
                  {busy ? "Adding…" : "Add"}
                </button>
              </div>
            )}
          </div>
          <Input label="Visitor phone (optional)" value={form.phone} onChange={(v) => set("phone", v)} placeholder="+974 5555 0000" maxLength={20} error={fieldErrors.phone} disabled={disabled} />
          <div>
            <div className="mb-1 flex items-center justify-between">
              <label htmlFor="visit-company" className="block text-xs font-semibold text-[var(--color-muted)]">Company (optional)</label>
              {user.role === "admin" && (
                <button
                  type="button"
                  onClick={() => setAddingCompany((open) => !open)}
                  disabled={busy}
                  aria-label="Add company"
                  title="Add company"
                  className="rounded border border-[var(--color-line)] px-2 text-sm font-bold disabled:opacity-50"
                >
                  +
                </button>
              )}
            </div>
            <select
              id="visit-company"
              value={form.company}
              onChange={(e) => set("company", e.target.value)}
              disabled={disabled}
              className="w-full rounded-lg border border-[var(--color-line)] bg-[var(--color-surface-sunken)] px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[var(--color-accent)] disabled:opacity-60"
            >
              <option value="">No company</option>
              {companies.map((company) => <option key={company} value={company}>{company}</option>)}
            </select>
            {addingCompany && (
              <div className="mt-2 flex gap-2">
                <input
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      handleAddCompany();
                    }
                  }}
                  required
                  minLength={2}
                  maxLength={80}
                  aria-label="New company name"
                  placeholder="New company"
                  className="min-w-0 flex-1 rounded-lg border border-[var(--color-line)] bg-[var(--color-surface-sunken)] px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[var(--color-accent)]"
                />
                <button
                  type="button"
                  onClick={handleAddCompany}
                  disabled={busy}
                  className="rounded-lg border border-[var(--color-line)] px-3 py-2 text-xs font-semibold disabled:opacity-50"
                >
                  {busy ? "Adding…" : "Add"}
                </button>
              </div>
            )}
          </div>
          <Input label="Vehicle plate (optional)" value={form.vehicle_plate} onChange={(v) => set("vehicle_plate", v)} maxLength={15} disabled={disabled} />
          <Input label="Notes (optional)" value={form.notes} onChange={(v) => set("notes", v)} maxLength={200} disabled={disabled} />
        </div>

        <div className="flex flex-wrap items-center gap-2 mt-4">
          <button
            type="submit"
            disabled={disabled || busy}
            className="rounded-lg bg-[var(--color-accent)] text-[var(--color-accent-ink)] font-semibold text-sm px-4 py-2 disabled:opacity-50"
          >
            {busy ? "Saving…" : "Save visitor"}
          </button>
          <button type="button" onClick={reset} className="rounded-lg border border-[var(--color-line)] font-semibold text-sm px-4 py-2">
            Clear form
          </button>
          {message && (
            <span role="status" className={`text-sm ${message.ok ? "text-[var(--color-ok)]" : "text-[var(--color-bad)]"}`}>
              {message.text}
            </span>
          )}
        </div>
      </form>
    </div>
  );
}

function Input({ label, value, onChange, error, disabled, ...rest }) {
  return (
    <div>
      <label className="block text-xs font-semibold text-[var(--color-muted)] mb-1">{label}</label>
      <input
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-lg border border-[var(--color-line)] bg-[var(--color-surface-sunken)] px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[var(--color-accent)] disabled:opacity-60"
        {...rest}
      />
      {error && <p className="text-xs text-[var(--color-bad)] mt-1">{error}</p>}
    </div>
  );
}

function Select({ label, value, onChange, options, placeholder, error, disabled }) {
  return (
    <div>
      <label className="block text-xs font-semibold text-[var(--color-muted)] mb-1">{label}</label>
      <select
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-lg border border-[var(--color-line)] bg-[var(--color-surface-sunken)] px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[var(--color-accent)] disabled:opacity-60"
      >
        <option value="">{placeholder}</option>
        {options.map((o) => (
          <option key={o} value={o}>{o}</option>
        ))}
      </select>
      {error && <p className="text-xs text-[var(--color-bad)] mt-1">{error}</p>}
    </div>
  );
}
