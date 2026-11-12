/**
 * Shared API client, session state helpers, and UI toast notifications.
 */
window.AppState = {
  token: localStorage.getItem("docverify_token") || "",
  user: JSON.parse(localStorage.getItem("docverify_user") || "null"),
  lastScanResult: null,
};

function setAuthSession(token, user) {
  window.AppState.token = token;
  window.AppState.user = user;
  localStorage.setItem("docverify_token", token);
  localStorage.setItem("docverify_user", JSON.stringify(user));
}

function clearAuthSession() {
  window.AppState.token = "";
  window.AppState.user = null;
  localStorage.removeItem("docverify_token");
  localStorage.removeItem("docverify_user");
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text == null ? "" : String(text);
  return div.innerHTML;
}

function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 3500);
}

async function apiRequest(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (window.AppState.token) {
    headers.set("Authorization", `Bearer ${window.AppState.token}`);
  }
  if (options.body && !(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${window.APP_CONFIG.API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 401) {
      clearAuthSession();
      window.location.hash = "#/login";
    }
    throw new Error(payload.error || `Request failed (${response.status})`);
  }
  return payload;
}

function assetUrl(relativePath) {
  if (!relativePath) return "";
  return `${window.APP_CONFIG.API_BASE_URL}${relativePath}`;
}

