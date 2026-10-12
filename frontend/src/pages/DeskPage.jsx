import { useCallback, useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import { api } from "../lib/api";
import TopBar from "../components/TopBar";
import ChangePasswordModal from "../components/ChangePasswordModal";
import ScanPanel from "../components/ScanPanel";
import IdReadout from "../components/IdReadout";
import VisitForm from "../components/VisitForm";
import PassPreview from "../components/PassPreview";
import VisitTable from "../components/VisitTable";
import DeleteReasonModal from "../components/DeleteReasonModal";
import AuditLog from "../components/AuditLog";
import VisitorDashboard from "../components/VisitorDashboard";
import UserManagementPage from "./UserManagementPage";

export default function DeskPage() {
  const { user } = useAuth();
  const isAdmin = user.role === "admin";

  const [scan, setScan] = useState(null);
  const [visits, setVisits] = useState({ items: [], total: 0, inside_count: 0 });
  const [audit, setAudit] = useState([]);
  const [stats, setStats] = useState(null);
  const [statsError, setStatsError] = useState("");
  const [search, setSearch] = useState("");
  const [showDeleted, setShowDeleted] = useState(false);
  const [pendingDelete, setPendingDelete] = useState(null);
  const [deleteBusy, setDeleteBusy] = useState(false);
  const [showPasswordModal, setShowPasswordModal] = useState(user.must_change_password);
  const [listError, setListError] = useState("");
  const [activeView, setActiveView] = useState("desk");

  const refresh = useCallback(async () => {
    try {
      const data = await api.listVisits({
        q: search,
        includeDeleted: isAdmin && showDeleted,
        allDates: isAdmin,
        pageSize: 200,
      });
      setVisits(data);
      setListError("");
    } catch (err) {
      setListError(err.message);
    }
    try {
      setStats(await api.visitStats());
      setStatsError("");
    } catch (err) {
      setStatsError(err.message);
    }
    if (isAdmin) {
      try {
        setAudit(await api.listAudit(100));
      } catch {
        /* non-critical for the main flow */
      }
    }
  }, [search, showDeleted, isAdmin]);

  useEffect(() => {
    const t = setTimeout(refresh, search ? 300 : 0); // debounce search typing
    return () => clearTimeout(t);
  }, [refresh, search]);

  async function handleCheckOut(visitId) {
    try {
      await api.checkOut(visitId);
      refresh();
    } catch (err) {
      setListError(err.message);
    }
  }

  async function handleConfirmDelete(reason) {
    setDeleteBusy(true);
    try {
      await api.deleteVisit(pendingDelete.id, reason);
      setPendingDelete(null);
      refresh();
    } catch (err) {
      setListError(err.message);
    } finally {
      setDeleteBusy(false);
    }
  }

  async function handleRestore(visitId) {
    try {
      await api.restoreVisit(visitId);
      refresh();
    } catch (err) {
      setListError(err.message);
    }
  }

  return (
    <div className="min-h-screen pb-10">
      <TopBar
        onChangePassword={() => setShowPasswordModal(true)}
        activeView={activeView}
        onViewChange={setActiveView}
      />

      {activeView === "users" && isAdmin ? (
        <UserManagementPage />
      ) : (
        <main className="max-w-6xl mx-auto px-4 grid lg:grid-cols-5 gap-5">
          <VisitorDashboard stats={stats} error={statsError} />

          <div className="lg:col-span-5">
            {listError && <p className="text-sm text-[var(--color-bad)] mb-3">{listError}</p>}
            <VisitTable
              items={visits.items}
              total={visits.total}
              insideCount={visits.inside_count}
              showDeleted={showDeleted}
              onToggleShowDeleted={setShowDeleted}
              search={search}
              onSearchChange={setSearch}
              onCheckOut={handleCheckOut}
              onDelete={setPendingDelete}
              onRestore={handleRestore}
              isAdmin={isAdmin}
            />
          </div>

          <div className="lg:col-span-2 self-start rounded-2xl border border-[var(--color-line)] bg-[var(--color-surface)] p-5">
            <ScanPanel onScanned={setScan} disabled={false} />
            <IdReadout scan={scan} />
          </div>

          <div className="lg:col-span-3 grid gap-5 self-start">
            <VisitForm scan={scan} onSaved={refresh} onClearScan={() => setScan(null)} />
            <PassPreview scan={scan} />
          </div>

          {isAdmin && (
            <div className="lg:col-span-5">
              <AuditLog entries={audit} />
            </div>
          )}
        </main>
      )}

      {showPasswordModal && (
        <ChangePasswordModal forced={user.must_change_password} onClose={() => setShowPasswordModal(false)} />
      )}
      {pendingDelete && (
        <DeleteReasonModal
          visit={pendingDelete}
          busy={deleteBusy}
          onConfirm={handleConfirmDelete}
          onCancel={() => setPendingDelete(null)}
        />
      )}
      <footer className="mx-auto mt-8 max-w-6xl px-4 text-center text-xs text-[var(--color-muted)]">
        Designed &amp; developed by FIROZ
      </footer>
    </div>
  );
}
