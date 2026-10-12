import axios from "axios";

// All requests go through same-origin "/api" (proxied to the backend in dev by vite.config.js,
// and by nginx in production — see ../nginx/nginx.conf). Session auth is an HttpOnly cookie,
// so axios must send credentials; CSRF is a double-submit token read from a response header
// after login and attached to every state-changing request afterwards.
const client = axios.create({ baseURL: "/api", withCredentials: true, timeout: 15000 });

let csrfToken = null;
export function setCsrfToken(token) {
  csrfToken = token || null;
}

client.interceptors.request.use((config) => {
  const method = (config.method || "get").toLowerCase();
  if (csrfToken && !["get", "head", "options"].includes(method)) {
    config.headers["X-CSRF-Token"] = csrfToken;
  }
  return config;
});

export class ApiError extends Error {
  constructor(message, status, fieldErrors) {
    super(message);
    this.status = status;
    this.fieldErrors = fieldErrors || null;
  }
}

client.interceptors.response.use(
  (res) => res,
  (err) => {
    const status = err.response?.status;
    const data = err.response?.data;
    let message = "Something went wrong. Please try again.";
    if (status === 0 || err.code === "ERR_NETWORK") {
      message = "Can't reach the server. Check your connection and try again.";
    } else if (data?.detail) {
      message = data.detail;
    } else if (status === 401) {
      message = "Your session has expired. Please sign in again.";
    } else if (status === 429) {
      message = "Too many attempts. Please wait a moment and try again.";
    }
    throw new ApiError(message, status, data?.errors || null);
  }
);

export const api = {
  async login(username, password) {
    const res = await client.post("/auth/login", { username, password });
    setCsrfToken(res.headers["x-csrf-token"]);
    return res.data; // { username, full_name, role, must_change_password }
  },
  async logout() {
    await client.post("/auth/logout");
    setCsrfToken(null);
  },
  async me() {
    const res = await client.get("/auth/me");
    return res.data;
  },
  async changePassword(current_password, new_password) {
    await client.post("/auth/change-password", { current_password, new_password });
  },

  async scan(raw) {
    const res = await client.post("/visits/scan", { raw });
    return res.data;
  },
  async manualId(details) {
    const res = await client.post("/visits/manual", details);
    return res.data;
  },
  async createVisit(payload) {
    const res = await client.post("/visits", payload);
    return res.data;
  },
  async listVisits({ q, includeDeleted, allDates, page = 1, pageSize = 50 } = {}) {
    const res = await client.get("/visits", {
      params: {
        q: q || undefined,
        include_deleted: includeDeleted || undefined,
        all_dates: allDates || undefined,
        page,
        page_size: pageSize,
      },
    });
    return res.data; // { items, total, inside_count }
  },
  async visitStats() {
    const res = await client.get("/visits/stats");
    return res.data;
  },
  async listDepartments() {
    const res = await client.get("/visits/departments");
    return res.data;
  },
  async createDepartment(name) {
    const res = await client.post("/admin/departments", { name });
    return res.data;
  },
  async listCompanies() {
    const res = await client.get("/visits/companies");
    return res.data;
  },
  async createCompany(name) {
    const res = await client.post("/admin/companies", { name });
    return res.data;
  },
  async checkOut(visitId) {
    const res = await client.post(`/visits/${visitId}/check-out`);
    return res.data;
  },
  async deleteVisit(visitId, reason) {
    await client.delete(`/visits/${visitId}`, { data: { reason } });
  },
  async restoreVisit(visitId) {
    const res = await client.post(`/visits/${visitId}/restore`);
    return res.data;
  },

  async listAudit(limit = 200) {
    const res = await client.get("/admin/audit", { params: { limit } });
    return res.data;
  },
  async listUsers() {
    const res = await client.get("/admin/users");
    return res.data;
  },
  async createUser(payload) {
    const res = await client.post("/admin/users", payload);
    return res.data;
  },
  async resetUserPassword(userId, temporaryPassword) {
    await client.post(`/admin/users/${userId}/reset-password`, { temporary_password: temporaryPassword });
  },
  async disableUser(userId) {
    await client.post(`/admin/users/${userId}/disable`);
  },
  async enableUser(userId) {
    await client.post(`/admin/users/${userId}/enable`);
  },
};
