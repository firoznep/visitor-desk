import { useCallback, useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import { api } from "../lib/api";

const emptyForm = { username: "", full_name: "", role: "receptionist", temporary_password: "" };

export default function UserManagementPage() {
  const { user: admin } = useAuth();
  const [users, setUsers] = useState([]);
  const [form, setForm] = useState(emptyForm);
  const [resetUserId, setResetUserId] = useState(null);
  const [temporaryPassword, setTemporaryPassword] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [disablingId, setDisablingId] = useState(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const loadUsers = useCallback(async () => {
    try {
      setUsers(await api.listUsers());
      setError("");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let mounted = true;
    api.listUsers()
      .then((data) => {
        if (mounted) {
          setUsers(data);
          setError("");
        }
      })
      .catch((err) => {
        if (mounted) setError(err.message);
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, []);

  function updateForm(event) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: name === "username" ? value.toLowerCase() : value }));
  }

  async function createUser(event) {
    event.preventDefault();
    setSaving(true);
    setError("");
    setNotice("");
    try {
      const created = await api.createUser(form);
      setForm(emptyForm);
      setNotice(`Created ${created.username}. They must change their temporary password at first login.`);
      await loadUsers();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function disableUser(user) {
    if (!window.confirm(`Disable the account for ${user.full_name} (${user.username})?`)) return;
    setDisablingId(user.id);
    setError("");
    setNotice("");
    try {
      await api.disableUser(user.id);
      setNotice(`${user.username} has been disabled.`);
      await loadUsers();
    } catch (err) {
      setError(err.message);
    } finally {
      setDisablingId(null);
    }
  }

  async function enableUser(user) {
    setDisablingId(user.id);
    setError("");
    setNotice("");
    try {
      await api.enableUser(user.id);
      setNotice(`${user.username} has been enabled.`);
      await loadUsers();
    } catch (err) {
      setError(err.message);
    } finally {
      setDisablingId(null);
    }
  }

  async function resetPassword(event, target) {
    event.preventDefault();
    setResetting(true);
    setError("");
    setNotice("");
    try {
      await api.resetUserPassword(target.id, temporaryPassword);
      setTemporaryPassword("");
      setResetUserId(null);
      setNotice(`Password reset for ${target.username}. Give them the temporary password securely; they must change it at next login.`);
      await loadUsers();
    } catch (err) {
      setError(err.message);
    } finally {
      setResetting(false);
    }
  }

  return (
    <main className="max-w-6xl mx-auto px-4 grid lg:grid-cols-5 gap-5">
      <section className="lg:col-span-2 self-start rounded-2xl border border-[var(--color-line)] bg-[var(--color-surface)] p-5">
        <h2 className="font-[var(--font-display)] text-lg font-bold">Create user</h2>
        <p className="text-sm text-[var(--color-muted)] mt-1 mb-4">
          New users must change their temporary password when they first sign in.
        </p>
        <form onSubmit={createUser} className="grid gap-3">
          <label className="grid gap-1 text-sm">
            Username
            <input
              name="username"
              value={form.username}
              onChange={updateForm}
              required
              minLength={3}
              maxLength={32}
              pattern="[a-z0-9._-]+"
              autoComplete="off"
              className={inputClass}
            />
            <span className="text-xs text-[var(--color-muted)]">3–32 characters: lowercase letters, numbers, ., _ or -</span>
          </label>
          <label className="grid gap-1 text-sm">
            Full name
            <input
              name="full_name"
              value={form.full_name}
              onChange={updateForm}
              required
              minLength={2}
              maxLength={80}
              autoComplete="name"
              className={inputClass}
            />
          </label>
          <label className="grid gap-1 text-sm">
            Role
            <select name="role" value={form.role} onChange={updateForm} className={inputClass}>
              <option value="receptionist">Receptionist</option>
              <option value="admin">Admin</option>
            </select>
          </label>
          <label className="grid gap-1 text-sm">
            Temporary password
            <input
              type="password"
              name="temporary_password"
              value={form.temporary_password}
              onChange={updateForm}
              required
              minLength={12}
              maxLength={128}
              autoComplete="new-password"
              className={inputClass}
            />
            <span className="text-xs text-[var(--color-muted)]">
              At least 12 characters; don’t include the username or use a common password.
            </span>
          </label>
          <button
            type="submit"
            disabled={saving}
            className="mt-1 rounded-lg bg-[var(--color-accent)] px-4 py-2 text-sm font-bold text-[var(--color-accent-ink)] disabled:opacity-50"
          >
            {saving ? "Creating…" : "Create user"}
          </button>
        </form>
      </section>

      <section className="lg:col-span-3 self-start rounded-2xl border border-[var(--color-line)] bg-[var(--color-surface)] p-5">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="font-[var(--font-display)] text-lg font-bold">Users</h2>
            <p className="text-sm text-[var(--color-muted)]">Manage application sign-in accounts.</p>
          </div>
          <button
            type="button"
            onClick={loadUsers}
            disabled={loading}
            className="rounded-md border border-[var(--color-line)] px-3 py-1.5 text-xs font-semibold hover:border-[var(--color-accent)] disabled:opacity-50"
          >
            Refresh
          </button>
        </div>

        {error && <p role="alert" className="mt-4 text-sm text-[var(--color-bad)]">{error}</p>}
        {notice && <p role="status" className="mt-4 text-sm text-[var(--color-ok)]">{notice}</p>}

        <div className="mt-3 overflow-x-auto">
          <table className="w-full min-w-[460px] text-sm">
            <thead>
              <tr className="text-left text-xs font-semibold text-[var(--color-muted)]">
                <th className="py-2 pr-3">Name</th>
                <th className="py-2 pr-3">Username</th>
                <th className="py-2 pr-3">Role</th>
                <th className="py-2 pr-3">Status</th>
                <th className="py-2 pr-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => {
                const isCurrentUser = user.username === admin.username;
                return (
                  <tr key={user.id} className="border-t border-[var(--color-line)]">
                    <td className="py-2.5 pr-3">{user.full_name}</td>
                    <td className="py-2.5 pr-3">{user.username}</td>
                    <td className="py-2.5 pr-3 capitalize">{user.role}</td>
                    <td className="py-2.5 pr-3">
                      <span className={user.is_active ? "text-[var(--color-ok)]" : "text-[var(--color-muted)]"}>
                        {user.is_active ? (user.must_change_password ? "Must change password" : "Active") : "Disabled"}
                      </span>
                    </td>
                    <td className="py-2.5 pr-3">
                      <div className="flex flex-wrap gap-2">
                        {!isCurrentUser && (
                        <button
                          type="button"
                          onClick={() => {
                            setResetUserId(resetUserId === user.id ? null : user.id);
                            setTemporaryPassword("");
                          }}
                          disabled={resetting}
                          className="rounded-md border border-[var(--color-line)] px-2.5 py-1 text-xs font-semibold disabled:opacity-50"
                        >
                          Reset password
                        </button>
                      )}
                      {user.is_active ? (
                        <button
                          type="button"
                          onClick={() => disableUser(user)}
                          disabled={disablingId === user.id || isCurrentUser}
                          title={isCurrentUser ? "You cannot disable your own account" : undefined}
                          className="rounded-md border border-[var(--color-line)] px-2.5 py-1 text-xs font-semibold text-[var(--color-bad)] disabled:cursor-not-allowed disabled:opacity-40"
                        >
                          {disablingId === user.id ? "Disabling…" : "Disable"}
                        </button>
                      ) : !isCurrentUser && (
                          <button
                            type="button"
                            onClick={() => enableUser(user)}
                            disabled={disablingId === user.id}
                            className="rounded-md border border-[var(--color-line)] px-2.5 py-1 text-xs font-semibold text-[var(--color-ok)] disabled:opacity-50"
                          >
                            {disablingId === user.id ? "Enabling…" : "Enable"}
                          </button>
                      )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        {resetUserId && (() => {
          const target = users.find((candidate) => candidate.id === resetUserId);
          if (!target) return null;
          return (
            <form onSubmit={(event) => resetPassword(event, target)} className="mt-4 rounded-lg border border-[var(--color-line)] p-4">
              <h3 className="text-sm font-semibold">Reset password for {target.username}</h3>
              <p className="mt-1 text-xs text-[var(--color-muted)]">
                The new temporary password must be given to the user securely. They will be required to change it at their next login.
              </p>
              <div className="mt-3 flex flex-wrap items-end gap-2">
                <label className="grid flex-1 gap-1 text-sm">
                  Temporary password
                  <input
                    type="password"
                    value={temporaryPassword}
                    onChange={(event) => setTemporaryPassword(event.target.value)}
                    required
                    minLength={12}
                    maxLength={128}
                    autoComplete="new-password"
                    className={inputClass}
                  />
                </label>
                <button
                  type="submit"
                  disabled={resetting}
                  className="rounded-lg bg-[var(--color-accent)] px-4 py-2 text-sm font-bold text-[var(--color-accent-ink)] disabled:opacity-50"
                >
                  {resetting ? "Resetting…" : "Set temporary password"}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setResetUserId(null);
                    setTemporaryPassword("");
                  }}
                  disabled={resetting}
                  className="rounded-lg border border-[var(--color-line)] px-4 py-2 text-sm font-semibold disabled:opacity-50"
                >
                  Cancel
                </button>
              </div>
            </form>
          );
        })()}
        {loading ? (
          <p className="py-6 text-center text-sm text-[var(--color-muted)]">Loading users…</p>
        ) : users.length === 0 && !error ? (
          <p className="py-6 text-center text-sm text-[var(--color-muted)]">No user accounts found.</p>
        ) : null}
      </section>
    </main>
  );
}

const inputClass = "rounded-lg border border-[var(--color-line)] bg-[var(--color-surface-sunken)] px-3 py-2 outline-none focus:ring-2 focus:ring-[var(--color-accent)]";
