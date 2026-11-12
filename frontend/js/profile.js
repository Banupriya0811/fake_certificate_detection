/**
 * User Profile, Scan Statistics, and Edit Profile view.
 */
function renderProfileView(root) {
  root.innerHTML = `
    <div class="page-header">
      <div class="page-eyebrow">Account</div>
      <h1 class="page-title">User Profile</h1>
      <p class="page-subtitle">Manage your account details and view overall verification statistics.</p>
    </div>

    <div class="grid-2">
      <div class="card">
        <div style="text-align: center; margin-bottom: 1.25rem;">
          <div class="avatar" id="profile-avatar">?</div>
          <h2 id="profile-name" style="font-size: 1.2rem;">Loading...</h2>
          <div id="profile-email" style="color: var(--text-muted); font-size: 0.86rem;"></div>
        </div>

        <form id="profile-form">
          <div class="form-group">
            <label for="prof-avatar-file">Profile Picture (optional)</label>
            <input id="prof-avatar-file" type="file" accept=".png,.jpg,.jpeg,.webp" />
          </div>
          <div class="form-group">
            <label for="prof-username">Username</label>
            <input id="prof-username" type="text" required maxlength="100" />
          </div>
          <div class="form-group">
            <label for="prof-email">Email</label>
            <input id="prof-email" type="email" required />
          </div>
          <div class="form-group">
            <label for="prof-password">New Password (leave blank to keep current)</label>
            <input id="prof-password" type="password" minlength="6" placeholder="••••••" />
          </div>
          <button type="submit" class="btn btn-primary" style="width: 100%;">Save Changes</button>
        </form>
      </div>

      <div>
        <div class="stats-grid">
          <div class="stat-card">
            <div class="stat-label">Total Scans</div>
            <div class="stat-value" id="stat-total">0</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Genuine</div>
            <div class="stat-value" id="stat-real" style="color: var(--teal);">0</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Fake Found</div>
            <div class="stat-value" id="stat-fake" style="color: var(--danger);">0</div>
          </div>
        </div>

        <div class="card">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
            <div class="page-eyebrow" style="margin: 0;">Recent Activity</div>
            <a href="#/history" class="btn btn-outline btn-sm">View All</a>
          </div>
          <ul class="meta-list" id="recent-scans-list">
            <li style="color: var(--text-muted);">Loading...</li>
          </ul>
        </div>
      </div>
    </div>
  `;

  function populateUser(user) {
    const avatarEl = document.getElementById("profile-avatar");
    document.getElementById("profile-name").textContent = user.username;
    document.getElementById("profile-email").textContent = user.email;
    document.getElementById("prof-username").value = user.username;
    document.getElementById("prof-email").value = user.email;

    if (user.profile_pic && user.profile_pic !== "default.png") {
      avatarEl.innerHTML = `<img src="${escapeHtml(assetUrl('/api/files/avatars/' + user.profile_pic))}" alt="Avatar" />`;
    } else {
      avatarEl.textContent = (user.username || "?")[0].toUpperCase();
    }
  }

  apiRequest("/api/profile")
    .then((data) => {
      populateUser(data.user);
      document.getElementById("stat-total").textContent = data.stats.total;
      document.getElementById("stat-real").textContent = data.stats.reals;
      document.getElementById("stat-fake").textContent = data.stats.fakes;

      const listEl = document.getElementById("recent-scans-list");
      if (!data.recent.length) {
        listEl.innerHTML = `<li style="color: var(--text-muted);">No scans yet.</li>`;
      } else {
        listEl.innerHTML = data.recent
          .map(
            (s) => `
            <li>
              <span>${escapeHtml(s.display_name)}</span>
              <span class="badge ${s.is_fake ? "badge-fake" : "badge-real"}">
                ${s.is_fake ? "Fake" : "Genuine"} (${s.confidence}%)
              </span>
            </li>
          `
          )
          .join("");
      }
    })
    .catch((err) => showToast(err.message, "error"));

  document.getElementById("profile-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const formData = new FormData();
    formData.append("username", document.getElementById("prof-username").value.trim());
    formData.append("email", document.getElementById("prof-email").value.trim());

    const pwd = document.getElementById("prof-password").value;
    if (pwd) formData.append("new_password", pwd);

    const avatarInput = document.getElementById("prof-avatar-file");
    if (avatarInput.files[0]) formData.append("profile_pic", avatarInput.files[0]);

    try {
      const data = await apiRequest("/api/profile", {
        method: "PUT",
        body: formData,
      });
      setAuthSession(window.AppState.token, data.user);
      populateUser(data.user);
      document.getElementById("prof-password").value = "";
      showToast("Profile updated successfully!", "success");
    } catch (err) {
      showToast(err.message, "error");
    }
  });
}

