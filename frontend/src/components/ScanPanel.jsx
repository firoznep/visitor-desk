import { useEffect, useRef, useState } from "react";
import { api } from "../lib/api";

/**
 * Captures input from a USB MRZ / ID-card reader, which behaves like a keyboard: it "types"
 * the 3-line (or 90-character) MRZ text into whatever field has focus, then sends Enter.
 * The textarea below stays focused so the reader can fire at any time during the shift.
 *
 * Camera-based MRZ capture is NOT included here — reading the MRZ from a live camera image
 * needs text recognition (OCR) tuned for the MRZ font, which is a dedicated SDK, not a few
 * lines of browser code. If you want that later, see README.md "Adding camera-based MRZ
 * capture" for the two integration points this component already has ready for it.
 */
export default function ScanPanel({ onScanned, disabled }) {
  const [raw, setRaw] = useState("");
  const [manualOpen, setManualOpen] = useState(false);
  const [manualDetailsOpen, setManualDetailsOpen] = useState(false);
  const [manualDetails, setManualDetails] = useState({
    full_name: "",
    id_number: "",
    date_of_birth: "",
    nationality: "",
    gender: "",
    id_expiry: "",
  });
  const [error, setError] = useState("");
  const [manualError, setManualError] = useState("");
  const [busy, setBusy] = useState(false);
  const inputRef = useRef(null);

  useEffect(() => {
    if (!disabled && !manualOpen) inputRef.current?.focus();
  }, [disabled, manualOpen]);

  async function submitScan(value) {
    const text = value.trim();
    if (!text) return;
    setBusy(true);
    setError("");
    try {
      const result = await api.scan(text);
      onScanned(result);
      setRaw("");
      setManualOpen(false);
    } catch (err) {
      setError(err.message || "Couldn't read this ID.");
    } finally {
      setBusy(false);
      inputRef.current?.focus();
    }
  }

  async function submitManual(e) {
    e.preventDefault();
    setBusy(true);
    setManualError("");
    try {
      const result = await api.manualId(manualDetails);
      onScanned({ ...result, manually_entered: true });
      setManualDetails({
        full_name: "",
        id_number: "",
        date_of_birth: "",
        nationality: "",
        gender: "",
        id_expiry: "",
      });
      setManualDetailsOpen(false);
    } catch (err) {
      setManualError(err.message || "Couldn't validate these ID details.");
    } finally {
      setBusy(false);
    }
  }

  function setManualField(key, value) {
    setManualDetails((details) => ({ ...details, [key]: value }));
  }

  function handleKeyDown(e) {
    // MRZ readers typically send the whole block then Enter; this also lets staff paste
    // a 3-line MRZ and press Enter to submit without an explicit button.
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submitScan(raw);
    }
  }

  return (
    <>
      <div className="flex items-center justify-between mb-1">
        <h2 className="font-[var(--font-display)] font-bold">1. Scan the Qatar ID</h2>
        <span className="flex items-center gap-1.5 text-xs text-[var(--color-muted)]">
          <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-ok)] animate-pulse motion-reduce:animate-none" />
          Entry ready
        </span>
      </div>
      <p className="text-xs text-[var(--color-muted)] mb-3">
        Use a compatible MRZ reader, or enter the ID details manually below.
      </p>

      <textarea
        ref={inputRef}
        value={raw}
        onChange={(e) => setRaw(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={disabled || busy}
        rows={3}
        spellCheck={false}
        placeholder="Waiting for scan…"
        aria-label="MRZ scanner input"
        className="w-full rounded-lg border border-[var(--color-line)] bg-[var(--color-surface-sunken)] px-3 py-2.5 text-sm font-mono outline-none focus:ring-2 focus:ring-[var(--color-accent)] disabled:opacity-60"
      />

      {error && (
        <p role="alert" className="text-sm text-[var(--color-bad)] mt-2">
          {error}
        </p>
      )}

      <div className="mt-3 flex items-center justify-between">
        <button
          type="button"
          onClick={() => setManualOpen((v) => !v)}
          className="text-xs font-semibold text-[var(--color-accent)] underline"
        >
          {manualOpen ? "Hide MRZ entry" : "Enter MRZ manually"}
        </button>
        {busy && <span className="text-xs text-[var(--color-muted)]">Reading…</span>}
      </div>

      {manualOpen && (
        <div className="mt-3 pt-3 border-t border-[var(--color-line)]">
          <p className="text-xs text-[var(--color-muted)] mb-2">
            Paste the 3-line MRZ from the back of the card (or the 90-character single line), then press Enter.
          </p>
          <button
            type="button"
            disabled={!raw.trim() || busy}
            onClick={() => submitScan(raw)}
            className="rounded-md bg-[var(--color-accent)] text-[var(--color-accent-ink)] text-xs font-semibold px-3 py-1.5 disabled:opacity-50"
          >
            Read this MRZ
          </button>
        </div>
      )}

      <div className="mt-3">
        <button
          type="button"
          onClick={() => {
            setManualDetailsOpen((open) => !open);
            setManualError("");
          }}
          className="text-xs font-semibold text-[var(--color-accent)] underline"
        >
          {manualDetailsOpen ? "Hide manual ID details" : "Enter ID details manually"}
        </button>
      </div>

      {manualDetailsOpen && (
        <form onSubmit={submitManual} className="mt-3 pt-3 border-t border-[var(--color-line)]">
          <p className="text-xs text-[var(--color-muted)] mb-3">
            Enter the details as shown on the visitor's ID. Verify them against the physical card.
          </p>
          <div className="grid sm:grid-cols-2 gap-3">
            <ManualInput
              label="Full name"
              value={manualDetails.full_name}
              onChange={(value) => setManualField("full_name", value)}
              required
              maxLength={120}
              disabled={disabled || busy}
              className="sm:col-span-2"
            />
            <ManualInput
              label="ID number"
              value={manualDetails.id_number}
              onChange={(value) => setManualField("id_number", value)}
              required
              maxLength={64}
              disabled={disabled || busy}
            />
            <ManualInput
              label="Nationality"
              value={manualDetails.nationality}
              onChange={(value) => setManualField("nationality", value)}
              required
              maxLength={60}
              disabled={disabled || busy}
            />
            <ManualInput
              label="Date of birth"
              type="date"
              value={manualDetails.date_of_birth}
              onChange={(value) => setManualField("date_of_birth", value)}
              required
              disabled={disabled || busy}
            />
            <div>
              <label className="block text-xs font-semibold text-[var(--color-muted)] mb-1">Gender</label>
              <select
                value={manualDetails.gender}
                onChange={(e) => setManualField("gender", e.target.value)}
                required
                disabled={disabled || busy}
                className="w-full rounded-lg border border-[var(--color-line)] bg-[var(--color-surface-sunken)] px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[var(--color-accent)] disabled:opacity-60"
              >
                <option value="">Select gender</option>
                <option value="Male">Male</option>
                <option value="Female">Female</option>
                <option value="Other">Other</option>
              </select>
            </div>
            <ManualInput
              label="ID expiry"
              type="date"
              value={manualDetails.id_expiry}
              onChange={(value) => setManualField("id_expiry", value)}
              required
              disabled={disabled || busy}
            />
          </div>
          {manualError && (
            <p role="alert" className="text-sm text-[var(--color-bad)] mt-2">
              {manualError}
            </p>
          )}
          <button
            type="submit"
            disabled={disabled || busy}
            className="mt-3 rounded-md bg-[var(--color-accent)] text-[var(--color-accent-ink)] text-xs font-semibold px-3 py-1.5 disabled:opacity-50"
          >
            {busy ? "Checking…" : "Use these ID details"}
          </button>
        </form>
      )}
    </>
  );
}

function ManualInput({ label, value, onChange, type = "text", className = "", ...props }) {
  return (
    <div className={className}>
      <label className="block text-xs font-semibold text-[var(--color-muted)] mb-1">{label}</label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-lg border border-[var(--color-line)] bg-[var(--color-surface-sunken)] px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[var(--color-accent)] disabled:opacity-60"
        {...props}
      />
    </div>
  );
}
