/**
 * Hash-based client router, navigation state, and backend health monitor.
 */
const ROUTES = {
  login: { render: renderLoginView, authRequired: false },
  register: { render: renderRegisterView, authRequired: false },
  scan: { render: renderScanView, authRequired: true },
  camera: { render: renderCameraView, authRequired: true },
  result: { render: renderResultView, authRequired: true },
  history: { render: renderHistoryView, authRequired: true },
  profile: { render: renderProfileView, authRequired: true },
};

function updateNavbar(routeName) {
  const isLoggedIn = Boolean(window.AppState.token);
  const navLinks = document.getElementById("nav-links");
  const logoutBtn = document.getElementById("logout-btn");

  navLinks.hidden = !isLoggedIn;
  logoutBtn.hidden = !isLoggedIn;

  navLinks.querySelectorAll("a").forEach((link) => {
    link.classList.toggle("active", link.dataset.route === routeName);
  });
}

function navigate() {
  stopCameraStream();
  const rawHash = window.location.hash.replace(/^#\/?/, "");
  const routeName = ROUTES[rawHash] ? rawHash : window.AppState.token ? "scan" : "login";
  const route = ROUTES[routeName];

  if (route.authRequired && !window.AppState.token) {
    window.location.hash = "#/login";
    return;
  }
  if (!route.authRequired && window.AppState.token) {
    window.location.hash = "#/scan";
    return;
  }

  updateNavbar(routeName);
  route.render(document.getElementById("app-root"));
}

async function checkBackendHealth() {
  const pill = document.getElementById("api-status");
  const text = document.getElementById("api-status-text");
  try {
    const res = await fetch(`${window.APP_CONFIG.API_BASE_URL}/api/health`);
    const data = await res.json();
    pill.classList.remove("offline");
    pill.classList.add("online");
    text.textContent = data.model_loaded ? "API + Model Ready" : "API Ready (Demo Mode)";
  } catch {
    pill.classList.remove("online");
    pill.classList.add("offline");
    text.textContent = "Backend Offline";
  }
}

document.getElementById("logout-btn").addEventListener("click", () => {
  clearAuthSession();
  showToast("Signed out.", "info");
  window.location.hash = "#/login";
});

window.addEventListener("hashchange", navigate);
window.addEventListener("DOMContentLoaded", () => {
  checkBackendHealth();
  navigate();
});

